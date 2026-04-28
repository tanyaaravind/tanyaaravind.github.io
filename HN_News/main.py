"""
HN Podcast Generator
Usage: python main.py
Pipeline: HN scrape → story selection → briefing → script → TTS → MP3
"""

import re
import json
from datetime import date
from anthropic import Anthropic

from hn_scraper import fetch_front_page, fetch_comments, fetch_article_text
from script_generator import generate_script, print_script
from tts import script_to_audio

from dotenv import load_dotenv
load_dotenv()

client = Anthropic()

# ─────────────────────────────────────────────
# STORY SELECTION
# ─────────────────────────────────────────────

SELECTION_PROMPT = """You are helping select 2 Hacker News stories for a podcast.

USER INTERESTS: {interests}

Today's top HN stories:
{story_list}

Pick exactly 2 stories that match the user's interests, have strong discussion
potential, and are varied in topic.

Respond with JSON only:
{{
  "selected": [
    {{"id": 12345, "title": "...", "reason": "one sentence why"}},
    {{"id": 67890, "title": "...", "reason": "one sentence why"}}
  ]
}}"""

def select_stories(stories, interests):
    story_list = "\n".join(
        f"[ID: {s['id']}] {s['title']} ({s['score']} pts, {s['num_comments']} comments)"
        for s in stories
    )
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": SELECTION_PROMPT.format(
            interests=interests, story_list=story_list
        )}]
    )
    raw = re.sub(r"```json|```", "", response.content[0].text).strip()
    return json.loads(raw)["selected"]


# ─────────────────────────────────────────────
# BRIEFING GENERATION
# ─────────────────────────────────────────────

BRIEFING_PROMPT = """You are preparing source material for a podcast. Write a rich BRIEFING DOCUMENT about this Hacker News story and its community discussion.

This will be used to generate a podcast script with two hosts:
- JORDAN: enthusiastic generalist host — curious, asks great questions, brings human angle
- ALEX: knowledgeable expert — explains clearly, builds context before opinions, engages with debate

---
# STORY: {title}
Source: {url}

## What This Is About
2-3 paragraphs for a smart non-expert. Be specific — assume zero prior knowledge.
Explain what this is, who's involved, why it exists, why it matters right now.

## Why The HN Community Cares
What angle makes this compelling for tech people?

## Key Points Worth Discussing
4-5 most interesting, surprising, or debatable points. Include real numbers and specifics.

## Community Perspectives (MOST IMPORTANT)
Synthesize comments into distinct viewpoints and real tensions.
For each: what the position is, why people hold it, the strongest counter-argument.
Cover these themes:
{comment_themes}

## Surprising or Counterintuitive Takes
What was unexpected, funny, or genuinely insightful from commenters?

## On-Air Questions
5 specific, concrete debate questions for the hosts.

## Fun Tangents
Any fascinating rabbit holes or related topics?
---

Article text:
{article_text}

HN Comments:
{comments}

Be specific and rich. Every line should give the hosts something real to say."""


def generate_briefing(story, article_text, comments):
    comments_text = "\n\n".join(
        f"[{c['author']}]: {c['text']}" for c in comments[:35]
    )

    # Extract comment themes with Haiku
    theme_response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": f"List 4-5 distinct debate themes from these HN comments as bullet points:\n\n{comments_text[:2000]}"}]
    )
    comment_themes = theme_response.content[0].text.strip()

    print(f"\n📝 Generating briefing: {story['title']}\n" + "─" * 60)

    full_text = ""
    with client.messages.stream(
        model="claude-sonnet-4-6",
        max_tokens=2500,
        messages=[{"role": "user", "content": BRIEFING_PROMPT.format(
            title=story["title"],
            url=story.get("url", "N/A"),
            article_text=article_text or "(unavailable — use comments as primary source)",
            comments=comments_text,
            comment_themes=comment_themes,
        )}]
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text

    print("\n" + "─" * 60)
    return full_text


def websearch_fallback(title, url):
    print("   Article unavailable — using web search fallback...")
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": f"Search for context about this and summarize in 3-4 paragraphs: {title} ({url})"}]
    )
    return "\n\n".join(
        block.text for block in response.content if hasattr(block, "text")
    )


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def run(interests: str):
    print("🎙️  HN Podcast Generator")
    print("=" * 60)

    # 1. Scrape front page
    print("\n📡 Fetching HN front page...")
    stories = fetch_front_page(limit=30)
    print(f"   Found {len(stories)} stories")

    # 2. Select 2 stories
    print("\n🤔 Selecting stories for your interests...")
    selected = select_stories(stories, interests)
    for s in selected:
        print(f"   → {s['title']}")
        print(f"     {s['reason']}")

    # 3. Fetch data + generate briefing for each story
    story_lookup = {s["id"]: s for s in stories}
    briefings = []

    for sel in selected:
        story = story_lookup.get(sel["id"], sel)
        print(f"\n🔍 Fetching data for: {story['title']}")

        comments = fetch_comments(story["id"])
        print(f"   Got {len(comments)} comments")

        article_text = fetch_article_text(story.get("url", ""))
        if article_text:
            print(f"   Got {len(article_text)} chars of article text")
        else:
            article_text = websearch_fallback(story["title"], story.get("url", ""))

        briefing = generate_briefing(story, article_text, comments)
        briefings.append(briefing)

    # 4. Combine briefings into one document
    combined = f"""# HN PODCAST SOURCE — {date.today().strftime('%B %d, %Y')}
User interests: {interests}

---

{"---".join(briefings)}"""

    # Save briefing doc
    briefing_path = "podcast_source.md"
    with open(briefing_path, "w") as f:
        f.write(combined)
    print(f"\n💾 Briefing saved to: {briefing_path}")

    # 5. Generate script
    script = generate_script(combined)
    print_script(script)

    # Save script as text for review
    script_path = "podcast_script.txt"
    with open(script_path, "w") as f:
        for speaker, text in script:
            f.write(f"{speaker}: {text}\n\n")
    print(f"💾 Script saved to: {script_path}")

    # 6. Generate audio
    audio_path = script_to_audio(script, output_path="podcast.mp3")

    print(f"\n✅ Done!")
    print(f"   📄 Briefing : {briefing_path}")
    print(f"   📝 Script   : {script_path}")
    print(f"   🎧 Podcast  : {audio_path}")


if __name__ == "__main__":
    interests = input("\nWhat topics interest you? (e.g. AI, open source, privacy): ").strip()
    if not interests:
        interests = "technology, software engineering, open source"
    run(interests)