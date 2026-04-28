"""
hn_scraper.py
HN scraper using Algolia API — reliable, no auth, no rate limits.
Usage: python hn_scraper.py
Import: from hn_scraper import fetch_front_page, fetch_comments, fetch_article_text
"""

import re
import json
import requests


def fetch_front_page(limit=30):
    r = requests.get(
        "https://hn.algolia.com/api/v1/search",
        params={"tags": "front_page", "hitsPerPage": limit},
        timeout=10
    )
    r.raise_for_status()
    hits = r.json().get("hits", [])
    return [{
        "id": int(h["objectID"]),
        "title": h.get("title", ""),
        "url": h.get("url", ""),
        "score": h.get("points", 0),
        "num_comments": h.get("num_comments", 0),
    } for h in hits]


def fetch_comments(story_id, max_comments=40):
    r = requests.get(
        f"https://hn.algolia.com/api/v1/items/{story_id}",
        timeout=10
    )
    r.raise_for_status()
    data = r.json()

    comments = []
    for child in data.get("children", [])[:max_comments]:
        text = child.get("text") or ""
        author = child.get("author") or "anonymous"

        # Clean HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        text = (text.replace("&#x27;", "'").replace("&quot;", '"')
                    .replace("&gt;", ">").replace("&lt;", "<")
                    .replace("&amp;", "&").strip())

        if text and not child.get("deleted"):
            comments.append({"author": author, "text": text})

    return comments


def fetch_article_text(url, max_chars=3000):
    if not url or url.startswith("item?id="):
        return ""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        return (trafilatura.extract(downloaded) or "")[:max_chars]
    except Exception:
        return ""


if __name__ == "__main__":
    print("=" * 60)
    print("HN SCRAPER TEST (Algolia API)")
    print("=" * 60)

    # 1. Front page
    print("\n[1] Fetching front page...")
    stories = fetch_front_page(limit=30)
    print(f"    Found {len(stories)} stories\n")
    for s in stories[:5]:
        print(f"    [{s['score']} pts, {s['num_comments']} comments] {s['title']}")
        print(f"    id={s['id']}  url={s['url'][:70]}")
        print()

    # 2. Comments for most-discussed story
    best = max(stories, key=lambda s: s["num_comments"])
    print(f"\n[2] Fetching comments for: '{best['title']}'")
    print(f"    Expects ~{best['num_comments']} comments")
    comments = fetch_comments(best["id"], max_comments=40)
    print(f"    Got {len(comments)} top-level comments\n")
    for c in comments[:3]:
        print(f"    [{c['author']}]: {c['text'][:150]}...")
        print()

    # 3. Article text
    print(f"\n[3] Fetching article: {best['url'][:70]}")
    article = fetch_article_text(best["url"])
    if article:
        print(f"    Got {len(article)} chars")
        print(f"    Preview: {article[:200]}...")
    else:
        print("    (unavailable)")

    # 4. Save full output
    output = {
        "stories": stories[:10],
        "sample_comments": comments[:10],
        "sample_article": article[:500] if article else ""
    }
    with open("scraper_test_output.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Full output saved to scraper_test_output.json")