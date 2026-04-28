"""
script_generator.py
Takes a briefing doc → returns a podcast script as list of (speaker, text) tuples.
Uses Claude Haiku for cost efficiency (~$0.01 per script).

Import: from script_generator import generate_script
"""

import re
from anthropic import Anthropic

from dotenv import load_dotenv
load_dotenv()

client = Anthropic()

SCRIPT_PROMPT = """You are writing a podcast script for a show called "HN Daily".

The show has two hosts:
- JORDAN: enthusiastic generalist, the curious host. Asks questions, reacts, brings the human angle. Speaks in short punchy sentences.
- ALEX: knowledgeable expert. Explains things clearly, builds context before opinions, engages with debate. Measured but opinionated.

CRITICAL STRUCTURE — follow this exactly for each story:

1. HOOK (Jordan, 2-3 sentences)
   Tease the most surprising or interesting thing about this topic. Don't explain it yet, just make the listener curious.

2. PLAIN ENGLISH EXPLAINER (Jordan asks, Alex explains, 3-4 exchanges)
   Jordan asks "ok so what actually IS this?" in plain terms.
   Alex explains the topic from scratch — assume the listener knows nothing.
   Cover: what it is, who's involved, why it exists, why it matters now.
   No debate yet. Just clear context. Use analogies if helpful.

3. WHY THIS IS A BIG DEAL (2-3 exchanges)
   Alex explains the significance. Jordan reacts with genuine surprise or skepticism.
   Make the stakes clear before any debate begins.

4. THE COMMUNITY DEBATE (4-5 exchanges)
   NOW introduce the different perspectives from the HN community.
   Jordan presents a viewpoint, Alex responds with nuance.
   Steelman both sides — don't strawman any position.
   Jordan should push back and play devil's advocate.
   Use specific details and examples from the briefing.

5. NUANCE & RABBIT HOLES (2-3 exchanges)
   The surprising, counterintuitive, or underexplored angles.
   The stuff that makes you go "huh, I hadn't thought of it that way."

6. TAKEAWAY (Jordan asks, Alex answers, 1-2 exchanges)
   "So what should people actually take away from this?"
   Concrete, not wishy-washy.

TRANSITION between stories: Jordan does a natural 2-3 sentence pivot to the next topic.

RULES:
- Each line should be 1-4 sentences max. No monologues.
- Alex should NEVER lecture for more than 4 sentences without Jordan responding.
- Use natural speech — contractions, incomplete thoughts, "I mean", "right?", "yeah but"
- Reference specific details from the briefing — names, numbers, quotes from commenters
- Do NOT use filler like "great question" or "absolutely"
- Total word count: ~1800-2200 words (roughly 12-15 min at speaking pace)

FORMAT — output ONLY the script, no preamble. Use exactly this format for every line:
JORDAN: text here
ALEX: text here

Here is the briefing material:
{briefing}"""


def generate_script(briefing: str) -> list[tuple[str, str]]:
    """
    Takes a briefing doc string, returns script as list of (speaker, text) tuples.
    e.g. [("JORDAN", "Welcome to HN Daily..."), ("ALEX", "Thanks Jordan..."), ...]
    """
    print("🖊️  Generating script (Claude Haiku)...")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": SCRIPT_PROMPT.format(briefing=briefing)
        }]
    )

    raw = response.content[0].text.strip()

    # Parse into (speaker, text) tuples
    script = []
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("JORDAN:"):
            text = line[len("JORDAN:"):].strip()
            if text:
                script.append(("JORDAN", text))
        elif line.startswith("ALEX:"):
            text = line[len("ALEX:"):].strip()
            if text:
                script.append(("ALEX", text))

    print(f"   Generated {len(script)} lines of dialogue")
    return script


def print_script(script: list[tuple[str, str]]):
    """Pretty print the script to terminal for review"""
    print("\n" + "=" * 60)
    print("GENERATED SCRIPT")
    print("=" * 60 + "\n")
    for speaker, text in script:
        label = f"{speaker}:"
        print(f"{label:<8} {text}\n")


if __name__ == "__main__":
    # Test with a dummy briefing
    DUMMY = """
    # STORY 1: GitHub Copilot moves to usage-based billing
    
    ## What This Is About
    GitHub Copilot, the AI coding assistant used by millions of developers,
    is switching from a flat $10/month subscription to usage-based billing.
    You pay per suggestion accepted, per line generated. Microsoft owns GitHub
    and is clearly trying to align costs with the underlying API costs from OpenAI.
    
    ## Why HN Cares
    Developers hate unpredictable bills. This could make Copilot much more
    expensive for heavy users or much cheaper for light users. It also signals
    that the "all you can eat AI" era might be ending.
    
    ## Key Points
    - Current flat rate: $10/month individual, $19/month business
    - New model: pay per completion, estimated $0.04 per 1000 tokens
    - Heavy users (8+ hours/day coding) could see bills of $40-80/month
    - Light users might pay $2-3/month
    
    ## Community Perspectives
    "This is the end of Copilot for me" — many devs saying they'll switch to Cursor or Codeium
    "Finally fair pricing" — some argue heavy users were subsidized by light users
    "Microsoft is extracting value now that the market is established" — cynical take
    "This will kill adoption at startups" — concern about budget unpredictability
    
    ## Surprising Takes
    One commenter noted that at $0.04/1000 tokens, writing a simple CRUD app
    costs about the same as a cup of coffee. The outrage might be disproportionate.
    
    ## On-Air Questions
    1. Is usage-based billing actually fairer, or just a price hike in disguise?
    2. Will this accelerate the move to open source alternatives?
    3. What does this mean for companies that have built Copilot into their dev workflow?
    """

    script = generate_script(DUMMY)
    print_script(script)