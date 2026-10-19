#!/usr/bin/env python3
"""List sent MailerLite newsletters, oldest first, with their status on the blog.

Usage: list_newsletters.py

Run from the repo root. For each newsletter shows its campaign id, send date,
subject, whether a post already has its `newsletter_id`, and how much of its
text already appears in the best-matching existing post (a high overlap means
it repeats a blog post and shouldn't be converted).
"""
import glob
import html
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import mailerlite  # noqa: E402
from newsletter_to_post import extract_blocks  # noqa: E402


def words(text):
    return re.findall(r"[a-z0-9']+", html.unescape(text).lower().replace("’", "'"))


def shingles(ws, n=5):
    return {tuple(ws[i:i + n]) for i in range(len(ws) - n + 1)}


def main():
    posts, converted = {}, {}
    for path in glob.glob("_posts/*.html"):
        doc = open(path).read()
        m = re.search(r"^newsletter_id:\s*(\d+)", doc, re.M)
        if m:
            converted[m.group(1)] = os.path.basename(path)
        body = re.sub(r"(?s)\{% highlight.*?endhighlight %\}", "", doc.split("\n---\n", 1)[-1])
        posts[os.path.basename(path)] = shingles(words(re.sub(r"<[^>]+>", " ", body)))

    campaigns, page = [], 1
    while True:
        data = mailerlite.get("/api/campaigns", {"filter[status]": "sent", "limit": 25, "page": page})
        campaigns += data["data"]
        if page >= data["meta"]["last_page"]:
            break
        page += 1
    campaigns.sort(key=lambda c: c["finished_at"] or "")

    for c in campaigns:
        email = c["emails"][0]
        status = f"converted: {converted[c['id']]}" if c["id"] in converted else ""
        if not status:
            req = urllib.request.Request(email["preview_url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                blocks = extract_blocks(r.read().decode("utf-8", "replace"))
            sh = shingles(words(" ".join(b["text"] for b in blocks)))
            best = max(posts, key=lambda p: len(sh & posts[p])) if sh else None
            overlap = len(sh & posts[best]) / len(sh) if sh else 0
            status = f"overlap {overlap:.0%} with {best}" if overlap >= 0.2 else "new"
        print(f"{c['id']}  {c['finished_at'][:10]}  {email['subject'][:60]:60}  {status}")


if __name__ == "__main__":
    main()
