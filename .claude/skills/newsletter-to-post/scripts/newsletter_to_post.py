#!/usr/bin/env python3
"""Turn one sent MailerLite newsletter into a Jekyll post in _posts/.

Usage: newsletter_to_post.py <campaign-id> --category "<Category>" [--title "<Title>"] [--force]

Run from the repo root. Reads the campaign through the read-only API client,
takes the content from the email's web preview, and does only mechanical
work: it keeps the newsletter's words, removes email wrapping, greetings and
workshop promos, embeds YouTube videos, downloads images, and writes the
front matter. Everything it removes is printed so it can be reviewed.
"""
import argparse
import html
import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import mailerlite  # noqa: E402

BLOCK = re.compile(
    r"(?P<heading><h([1-6])\b[^>]*>.*?</h\2>)"
    r"|(?P<list><(ul|ol)\b[^>]*>.*?</\4>)"
    r"|(?P<button><a\b[^>]*>\s*<div\b[^>]*>.*?</div>\s*</a>)"
    r"|(?P<image>(?:<a\b[^>]*>\s*)?<img\b[^>]*>(?:\s*</a>)?)"
    r"|(?P<para><p\b[^>]*>.*?</p>)",
    re.S)
FOOTER = re.compile(r"^(Automated AF|You received this email\b.*)$")
# Hosts that serve MailerLite's own icons and badges rather than newsletter content.
CHROME_IMAGE_HOSTS = {"assets.mlcdn.com"}
GREETING = re.compile(r"^(hi|hello|hey|happy|good (morning|afternoon|evening)|morning)\b", re.I)
# A workshop promo mentions a workshop AND has a promo signal (a booking link, "coming up", "tickets"…).
# Paragraphs that only mention workshops are article content. Real promos are short (16-34 words in the
# 2025-26 newsletters); a longer one with a signal mixes promo and content, so it's kept and flagged.
WORKSHOP = re.compile(r"\bworkshops?\b", re.I)
PROMO_SIGNAL = re.compile(r"luma\.com|automatedaf\.dev/workshops|\btickets?\b|\bbook\b|coming (right )?up|\blaunching\b"
                          r"|\bslots?\b|\bsee some of you\b|happening in", re.I)
PROMO_MAX_WORDS = 35
YOUTUBE = re.compile(r"https?://(?:www\.)?(?:youtu\.be/|youtube\.com/watch\?v=)([\w-]{11})")
KEEP_ATTRS = {"a": ("href",), "img": ("src", "alt")}


ZERO_WIDTH = re.compile("[\ufeff\u200b\u200c\u200d]")


def text_of(fragment):
    return " ".join(ZERO_WIDTH.sub("", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).split())


def clean(fragment):
    """Strip email styling: unwrap layout tags, drop attributes except href/src/alt."""
    fragment = ZERO_WIDTH.sub("", fragment.replace("&#xfeff;", "").replace("&#65279;", ""))
    fragment = re.sub(r"</?(span|u|font|div|th|td|tr|table|tbody|center)\b[^>]*>", "", fragment)

    def tag(m):
        name, attrs = m.group(1).lower(), m.group(2)
        kept = [f'{a}="{v}"' for a, v in re.findall(r'\s([\w-]+)="([^"]*)"', attrs) if a in KEEP_ATTRS.get(name, ())]
        return f"<{name}{''.join(' ' + k for k in kept)}{' /' if name in ('img', 'br') else ''}>"
    fragment = re.sub(r"<(\w+)\b([^>]*?)/?>", tag, fragment)
    fragment = re.sub(r'<a href="">(.*?)</a>', r"\1", fragment, flags=re.S)
    # The email editor leaves links wrapped around nothing but zero-width characters.
    fragment = re.sub(r'<a\b[^>]*>(?:\s|<(?!img\b|a\b|/)[^>]*>|</(?!a>)[^>]*>)*</a>', "", fragment)
    return re.sub(r"\s+", " ", fragment).strip()


def decode_cf_email(hexstr):
    key = int(hexstr[:2], 16)
    return "".join(chr(int(hexstr[i:i + 2], 16) ^ key) for i in range(2, len(hexstr), 2))


def restore_emails(page):
    """Undo Cloudflare's email obfuscation on the preview page, restoring the addresses the email contained."""
    # An obfuscated address inside a link becomes plain text; the link itself gets a mailto href below.
    page = re.sub(r'<span\b[^>]*data-cfemail="([0-9a-f]+)"[^>]*>.*?</span>',
                  lambda m: decode_cf_email(m.group(1)), page, flags=re.S)
    page = re.sub(r'<a\b[^>]*data-cfemail="([0-9a-f]+)"[^>]*>.*?</a>',
                  lambda m: (lambda e: f'<a href="mailto:{e}">{e}</a>')(decode_cf_email(m.group(1))), page, flags=re.S)
    return re.sub(r'href="/cdn-cgi/l/email-protection#([0-9a-f]+)"',
                  lambda m: f'href="mailto:{decode_cf_email(m.group(1))}"', page)


def extract_blocks(page):
    """Return the newsletter's content blocks as dicts of kind, html and text, without email wrapping."""
    body = restore_emails(re.sub(r"(?s)<!--.*?-->|<(script|style|head)\b.*?</\1>", "", page))
    blocks = []
    for m in BLOCK.finditer(body):
        kind = m.lastgroup
        raw = m.group(0)
        text = text_of(raw)
        if FOOTER.match(text):
            break
        if kind == "image":
            src = re.search(r'<img\b[^>]*\ssrc="([^"]+)"', raw)
            if not src or urllib.parse.urlparse(src.group(1)).netloc in CHROME_IMAGE_HOSTS:
                continue
        elif not text:
            continue
        level = int(m.group(2)) if kind == "heading" else None
        blocks.append({"kind": kind, "html": clean(raw), "text": text, "level": level})
    return blocks


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", re.sub(r"['’]", "", title.lower())).strip("-")


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=300) as r:
        expected = r.headers.get("Content-Length")
        with open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
    if expected and os.path.getsize(dest) != int(expected):
        sys.exit(f"ERROR: {url} downloaded incompletely")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("campaign_id")
    ap.add_argument("--category", required=True)
    ap.add_argument("--title", help="post title; required when the subject is generic")
    ap.add_argument("--force", action="store_true", help="overwrite an existing post for this newsletter")
    args = ap.parse_args()
    if not os.path.isdir("_posts"):
        sys.exit("ERROR: run from the Jekyll repo root")

    for path in os.listdir("_posts"):
        if re.search(rf"^newsletter_id:\s*{args.campaign_id}\s*$", open(f"_posts/{path}").read(), re.M) and not args.force:
            sys.exit(f"ERROR: _posts/{path} already has this newsletter (use --force to redo it)")

    campaign = mailerlite.get(f"/api/campaigns/{args.campaign_id}")["data"]
    email = campaign["emails"][0]
    subject, sent = email["subject"], campaign["finished_at"]
    req = urllib.request.Request(email["preview_url"], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        blocks = extract_blocks(r.read().decode("utf-8", "replace"))

    removed, warnings, review = [], [], []
    headline = blocks.pop(0)["text"] if blocks and blocks[0]["kind"] == "heading" and blocks[0]["level"] == 1 else None
    title = args.title or headline or subject
    if not args.title and not headline and re.search(r"newsletter", subject, re.I):
        sys.exit(f"ERROR: the subject {subject!r} is generic and there's no headline; pass --title")
    first_para = next((b for b in blocks if b["kind"] == "para"), None)
    if first_para and GREETING.match(first_para["text"]) and len(first_para["text"].split()) < 25:
        removed.append(("conversational opener", first_para))
        blocks.remove(first_para)
    # A call-to-action button and the paragraph introducing it are a promo ("NEXT WEEK: Join me…" + "Book").
    for b in [b for b in blocks if b["kind"] == "button"]:
        i = blocks.index(b)
        if i > 0 and blocks[i - 1]["kind"] == "para":
            removed.append(("promo introducing a button", blocks.pop(i - 1)))
        removed.append(("call-to-action button", b))
        blocks.remove(b)
    for b in list(blocks):
        if b["kind"] in ("para", "list") and WORKSHOP.search(b["text"]) and PROMO_SIGNAL.search(b["html"]):
            if len(b["text"].split()) <= PROMO_MAX_WORDS:
                removed.append(("workshop promo", b))
                blocks.remove(b)
            else:
                review.append("part workshop promo, kept: " + b["text"])

    for b in blocks:
        if b["kind"] == "para" and (re.match(r"^(P+S\b|thanks,?\s*andrew$|andrew$|happy \w+!?$)", b["text"], re.I)):
            review.append(b["text"])

    yyyy, mm, dd = sent[:4], sent[5:7], sent[8:10]
    slug = slugify(title)
    img_dir = f"images/blog/{yyyy}/{mm}"
    out, cover, n_img = [], None, 0
    for b in blocks:
        h = b["html"]
        if b["kind"] == "heading":
            h = re.sub(r"^<h[1-6]>(.*)</h[1-6]>$", r"<h2>\1</h2>", h, flags=re.S)
        elif b["kind"] == "image":
            link = re.search(r'<a href="([^"]*)"', h)
            video = YOUTUBE.search(link.group(1)) if link else None
            if video:
                vid = video.group(1)
                h = (f'<iframe loading="lazy" class="youtube-player" width="640" height="360" '
                     f'src="https://www.youtube.com/embed/{vid}" title="{html.escape(title)} (video)" '
                     f'allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                     f'allowfullscreen style="border:0;"></iframe>')
                if not cover:
                    os.makedirs(img_dir, exist_ok=True)
                    thumb = f"{img_dir}/{slug}-video-thumbnail.jpg"
                    try:
                        download(f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg", thumb)
                    except Exception:
                        download(f"https://img.youtube.com/vi/{vid}/hqdefault.jpg", thumb)
                    cover = "/" + thumb
            else:
                src = re.search(r'src="([^"]+)"', h).group(1)
                n_img += 1
                ext = os.path.splitext(urllib.parse.urlparse(src).path)[1] or ".img"
                os.makedirs(img_dir, exist_ok=True)
                local = f"{img_dir}/{slug}-image-{n_img}{ext}"
                download(html.unescape(src), local)
                img = re.search(r"<img\b[^>]*>", h).group(0).replace(src, "/" + local)
                # No click-to-open: drop a link that only leads to a copy of the image itself.
                links_to_image = link and (link.group(1) == src or "media.licdn.com" in link.group(1)
                                           or re.search(r"\.(png|jpe?g|gif|webp)(\?|$)", link.group(1), re.I))
                inner = f'<a href="{link.group(1)}">{img}</a>' if link and not links_to_image else img
                h = f"<figure>{inner}</figure>"
                cover = cover or "/" + local
                if 'alt=""' in img or "alt=" not in img:
                    warnings.append(f"image {local} has no alt text")
        # Links to old WordPress posts that have been ported point at the local copy instead.
        def local_post(m):
            local = f"/{m.group(1)}/{m.group(2)}/{m.group(3)}/{m.group(4)}/"
            return f'href="{local}"' if os.path.exists(f"_posts/{m.group(1)}-{m.group(2)}-{m.group(3)}-{m.group(4)}.html") else m.group(0)
        h = re.sub(r'href="https?://andrewfray\.wordpress\.com/(\d{4})/(\d{2})/(\d{2})/([a-z0-9-]+)/?"', local_post, h)
        for href in re.findall(r'href="([^"]+)"', h):
            host = urllib.parse.urlparse(href).netloc
            if "mailerlite" in host or "mlsend" in host or href.startswith("/cdn-cgi/"):
                warnings.append(f"link may be tracked or obfuscated: {href}")
        out.append(h)

    path = f"_posts/{yyyy}-{mm}-{dd}-{slug}.html"
    fm = ["---", "layout: post", f"title: {json.dumps(title, ensure_ascii=False)}", f"date: {sent[:19]} +0000"]
    if cover:
        fm.append(f"image: {cover}")
    fm += [f"categories: [{args.category}]", "newsletter: true", f"newsletter_id: {args.campaign_id}", "---"]
    with open(path, "w") as f:
        f.write("\n".join(fm) + "\n\n" + "\n\n".join(out) + "\n")

    print(f"Wrote {path} ({len(out)} blocks), sent {sent}")
    print(f"  title: {title!r}  (subject: {subject!r}" + (f", headline: {headline!r})" if headline else ")"))
    for why, b in removed:
        print(f"  removed {why}: {b['text'][:110]}")
    for t in review:
        print(f"  REVIEW (kept — remove if it's dated, chatty or promotional): {t[:110]}")
    for w in warnings:
        print(f"  WARNING: {w}")
    if not cover:
        print("  WARNING: no image or video, so no cover image")


if __name__ == "__main__":
    main()
