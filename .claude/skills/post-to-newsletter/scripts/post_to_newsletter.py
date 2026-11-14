#!/usr/bin/env python3
"""Turn a blog post in _posts/ into a draft MailerLite newsletter.

Usage (from the repo root, after `bundle exec jekyll build`):
    post_to_newsletter.py _posts/<file>             # write email HTML for local preview only
    post_to_newsletter.py _posts/<file> --create    # also create a DRAFT campaign in MailerLite

It reads the rendered post from _site/, so Liquid, Markdown and code
highlighting are already resolved. It never sends: the draft is reviewed,
tested and sent by the user in MailerLite. With --create it records the
campaign id as `newsletter_id` in the post's front matter, which also stops
newsletter_to_post.py converting the sent email back into a duplicate post.
"""
import argparse
import datetime
import html
import os
import re
import sys

# The restricted MailerLite client is shared with the newsletter-to-post skill.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "newsletter-to-post", "scripts"))
import mailerlite  # noqa: E402



def site_url():
    """The blog's address from _config.yml's `url`, always over https."""
    m = re.search(r'^url:\s*"?([^"\s#]+)', open("_config.yml", encoding="utf-8").read(), re.M)
    if not m:
        sys.exit("ERROR: no url in _config.yml")
    return re.sub(r"^http://", "https://", m.group(1).rstrip("/"))


SITE = site_url()
ADDRESS = "Automated AF<br>35 Foxes Meadow, Birmingham<br>United Kingdom"
FONT = "Helvetica, Arial, sans-serif"
TEXT, MUTED, LINK = "#222222", "#666666", "#1a73c9"

STYLES = {
    "p": f"margin:0 0 16px;font-family:{FONT};font-size:16px;line-height:1.6;color:{TEXT};",
    "h2": f"margin:28px 0 12px;font-family:{FONT};font-size:22px;line-height:1.3;color:{TEXT};",
    "h3": f"margin:24px 0 10px;font-family:{FONT};font-size:18px;line-height:1.3;color:{TEXT};",
    "h4": f"margin:20px 0 8px;font-family:{FONT};font-size:16px;line-height:1.3;color:{TEXT};",
    "ul": f"margin:0 0 16px;padding-left:24px;font-family:{FONT};font-size:16px;line-height:1.6;color:{TEXT};",
    "ol": f"margin:0 0 16px;padding-left:24px;font-family:{FONT};font-size:16px;line-height:1.6;color:{TEXT};",
    "li": "margin:0 0 6px;",
    "a": f"color:{LINK};text-decoration:underline;",
    "blockquote": f"margin:0 0 16px;padding:0 0 0 16px;border-left:3px solid #dddddd;color:{MUTED};",
    "figure": "margin:0 0 16px;text-align:center;",
    "figcaption": f"margin:6px 0 0;font-family:{FONT};font-size:13px;line-height:1.4;color:{MUTED};text-align:center;",
    "img": "display:block;max-width:100%;height:auto;margin:0 auto;border:0;",
    "pre": "margin:0 0 16px;padding:12px;background:#f4f4f4;border-radius:4px;overflow-x:auto;"
           "font-family:Menlo,Consolas,monospace;font-size:13px;line-height:1.45;color:#222222;white-space:pre;",
    "code": "font-family:Menlo,Consolas,monospace;font-size:14px;background:#f4f4f4;padding:1px 4px;border-radius:3px;",
    "hr": "border:0;border-top:1px solid #dddddd;margin:24px 0;",
    "table": f"border-collapse:collapse;margin:0 0 16px;font-family:{FONT};font-size:14px;",
    "th": "border:1px solid #dddddd;padding:6px 8px;text-align:left;",
    "td": "border:1px solid #dddddd;padding:6px 8px;",
}


def front_matter(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"ERROR: no front matter in {path}")
    fm = {}
    for line in m.group(1).splitlines():
        k = re.match(r"^(\w+):\s*(.*)$", line)
        if k:
            fm[k.group(1)] = k.group(2).strip().strip('"').strip("'")
    return text, m, fm


def post_url(path, fm):
    """The post's permalink, /:year/:month/:day/:title/, from its filename."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})-(.+)\.(md|markdown|html)$", os.path.basename(path))
    if not m:
        sys.exit(f"ERROR: can't read a date and slug from {path}")
    y, mo, d, slug, _ = m.groups()
    return f"/{y}/{mo}/{d}/{slug}/"


def rendered_content(url):
    site_file = os.path.join("_site", url.strip("/"), "index.html")
    if not os.path.exists(site_file):
        sys.exit(f"ERROR: {site_file} not found: run `bundle exec jekyll build` first")
    page = open(site_file, encoding="utf-8").read()
    start = page.find('<div class="post-content">')
    if start < 0:
        sys.exit(f"ERROR: no post-content in {site_file}")
    # Walk nested <div>s to find the matching close.
    i, depth = start + len('<div class="post-content">'), 1
    for m in re.finditer(r"<(/?)div\b", page[i:]):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return page[i:i + m.start()], site_file
    sys.exit("ERROR: unbalanced post-content div")


def absolutise(content):
    return re.sub(r'(\s(?:src|href)=")/(?!/)', rf"\1{SITE}/", content)


def convert(content, report):
    c = content
    c = re.sub(r"(?s)<script\b.*?</script>", "", c)
    # YouTube embeds: email can't play video, so show the thumbnail linking to the video.
    def yt(m):
        vid = m.group(1)
        report.append(f"video {vid}: embed replaced with a linked thumbnail")
        return (f'<p><a href="https://www.youtube.com/watch?v={vid}">'
                f'<img src="https://img.youtube.com/vi/{vid}/maxresdefault.jpg" alt="Watch the video on YouTube" width="560"></a></p>')
    c = re.sub(r'(?s)<iframe[^>]*youtube(?:-nocookie)?\.com/embed/([\w-]+)[^>]*>.*?</iframe>', yt, c)
    for m in re.finditer(r"<iframe[^>]*>", c):
        report.append(f"REVIEW: other iframe left in, which most email clients won't show: {m.group(0)[:100]}")
    # Rouge highlighting: email clients drop class-based colours, so keep plain preformatted code.
    def code_block(m):
        inner = re.sub(r"</?span[^>]*>", "", m.group(1))
        return f"<pre><code>{inner}</code></pre>"
    c = re.sub(r'(?s)<div class="language-[^"]*highlighter-rouge">\s*<div class="highlight">\s*'
               r'<pre class="highlight"><code>(.*?)</code></pre>\s*</div>\s*</div>', code_block, c)
    c = re.sub(r'(?s)<figure class="highlight">\s*<pre><code[^>]*>(.*?)</code></pre>\s*</figure>', code_block, c)
    # Drop heading ids and classes, which mean nothing in email.
    c = re.sub(r'(<h[1-6])\s+id="[^"]*"', r"\1", c)
    c = re.sub(r'\s(?:class|id)="[^"]*"', "", c)
    # An image alone in a paragraph: centre it with a width hint for Outlook.
    c = re.sub(r"<img\b(?![^>]*\bwidth=)", '<img width="560"', c)
    c = absolutise(c)
    # Inline styles. <code> inside <pre> takes the <pre>'s look instead.
    def style(m):
        tag, attrs, close = m.group(1).lower(), m.group(2) or "", m.group(3)
        css = STYLES[tag]
        if re.search(r'\sstyle="', attrs):
            attrs = re.sub(r'\sstyle="', f' style="{css}', attrs, count=1)
        else:
            attrs += f' style="{css}"'
        return f"<{m.group(1)}{attrs}{close}>"
    c = re.sub(r"<(%s)\b([^>]*?)(\s*/?)>" % "|".join(STYLES), style, c)
    c = re.sub(r'(<pre style="[^"]*"><code) style="[^"]*"', r'\1 style="font-family:inherit;font-size:inherit;background:none;padding:0;"', c)
    return c


def plain(fragment):
    t = re.sub(r"<[^>]+>", " ", fragment)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def preview_text(fm, content):
    if fm.get("description"):
        return fm["description"]
    for p in re.findall(r"(?s)<p\b[^>]*>(.*?)</p>", content):
        t = plain(p)
        if t:
            return t if len(t) <= 140 else t[:137].rsplit(" ", 1)[0] + "…"
    return ""


def wording_review(content, report):
    """Blog-to-newsletter wording is the user's call, so only flag it."""
    for p in re.findall(r"(?s)<(?:p|li|h[1-6])\b[^>]*>(.*?)</(?:p|li|h[1-6])>", content):
        t = plain(p)
        for w in re.findall(r"\b((?:this|that|the|my|a|next|previous|last|today's|last week's|next week's|another|earlier|blog)"
                            r"[’']?\s+posts?|blog(?:s|ged|ging)?)\b(?!-)", t, re.I):
            report.append(f'REVIEW wording ("{w}"): {t[:160]}')
            break


def email_html(title, preheader, body, url):
    pre = html.escape(preheader)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f2f2f2;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:#f2f2f2;">{pre}&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;&#8204;&nbsp;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f2f2f2;">
<tr><td align="center" style="padding:16px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;">
<tr><td align="right" style="padding:0 4px 8px;font-family:{FONT};font-size:12px;color:{MUTED};">
<a href="{{$url}}" style="color:{MUTED};">View in browser</a>
</td></tr>
<tr><td style="background:#ffffff;padding:32px 32px 16px;border-radius:6px;">
<h1 style="margin:0 0 20px;font-family:{FONT};font-size:28px;line-height:1.25;color:{TEXT};">{html.escape(title)}</h1>
{body}
<p style="margin:24px 0 16px;font-family:{FONT};font-size:14px;line-height:1.6;color:{MUTED};">This newsletter is also on the blog: <a href="{SITE}{url}" style="color:{LINK};text-decoration:underline;">read it on {SITE.split("//", 1)[1]}</a>.</p>
</td></tr>
<tr><td align="center" style="padding:20px 16px;font-family:{FONT};font-size:12px;line-height:1.5;color:{MUTED};">
{ADDRESS}<br><br>
You received this email because you signed up on our website or made a purchase from us.<br><br>
<a href="{{$unsubscribe}}" style="color:{MUTED};">Unsubscribe</a>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>
"""


def record_campaign(path, text, fm_match, campaign_id):
    fm = fm_match.group(1)
    if re.search(r"^newsletter_id:", fm, re.M):
        fm = re.sub(r"^newsletter_id:.*$", f"newsletter_id: {campaign_id}", fm, flags=re.M)
    else:
        fm += f"\nnewsletter_id: {campaign_id}"
    open(path, "w", encoding="utf-8").write(f"---\n{fm}\n---\n" + text[fm_match.end():])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("post")
    ap.add_argument("--create", action="store_true", help="create a draft campaign in MailerLite")
    ap.add_argument("--subject", help="email subject (default: the post title)")
    ap.add_argument("--preview-text", help="inbox preview text (default: description or first paragraph)")
    ap.add_argument("--out", help="where to write the email HTML")
    ap.add_argument("--force", action="store_true", help="create even if the post already has a newsletter_id")
    a = ap.parse_args()

    text, fm_match, fm = front_matter(a.post)
    if fm.get("newsletter_id") and a.create and not a.force:
        sys.exit(f"ERROR: post already has newsletter_id {fm['newsletter_id']}; pass --force to make another draft")
    if fm.get("newsletter") == "true":
        print("REVIEW: this post was converted FROM a newsletter, so it has probably been sent already")
    title = fm.get("title") or sys.exit("ERROR: post has no title")
    url = post_url(a.post, fm)
    raw, site_file = rendered_content(url)

    report = []
    body = convert(raw, report)
    wording_review(raw, report)
    pre = a.preview_text if a.preview_text is not None else preview_text(fm, raw)
    out_html = email_html(title, pre, body, url)

    out = a.out or os.path.join("_site", "newsletter-preview", os.path.basename(url.strip("/")) + ".html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write(out_html)

    print(f"Post:         {a.post}  ({site_file})")
    print(f"Subject:      {a.subject or title}")
    print(f"Preview text: {pre}")
    print(f"Email HTML:   {out}")
    for line in report:
        print(line)
    for m in re.finditer(r'<img\b[^>]*>', body):
        if not re.search(r'\salt="[^"]+"', m.group(0)):
            print(f"WARNING: image without alt text: {m.group(0)[:120]}")

    if not a.create:
        print("\nLocal preview only. Re-run with --create to make a MailerLite draft.")
        return

    # Copy sender details from the most recent sent campaign, so they match what's verified.
    last = mailerlite.get("/api/campaigns", {"filter[status]": "sent", "limit": 1})["data"]
    if not last:
        sys.exit("ERROR: no sent campaign to copy sender details from")
    e = mailerlite.get("/api/campaigns/" + last[0]["id"])["data"]["emails"][0]
    payload = {
        "name": f"{datetime.date.today().isoformat()}: {title}",
        "type": "regular",
        "emails": [{
            "subject": a.subject or title,
            "from_name": e["from_name"],
            "from": e["from"],
            "reply_to": e.get("reply_to") or e["from"],
            "content": out_html,
        }],
    }
    result = mailerlite.create_draft_campaign(payload)["data"]
    cid = result["id"]
    record_campaign(a.post, text, fm_match, cid)
    print(f"\nCreated DRAFT campaign {cid} ({result.get('status')}): \"{payload['name']}\"")
    print(f"Sender: {e['from_name']} <{e['from']}>; audience: all subscribers unless changed in MailerLite")
    print(f"Recorded newsletter_id: {cid} in {a.post}")
    print("Nothing has been sent. Review, test and send it from MailerLite.")


if __name__ == "__main__":
    main()
