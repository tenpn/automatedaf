---
name: newsletter-to-post
description: Turn a sent Automated AF newsletter (MailerLite) into a blog post in this Jekyll site's _posts/. Use when asked to convert, import or post a newsletter, list which newsletters are on the blog, or check the newsletter conversion rules.
---

# Newsletter to blog post

Converts sent MailerLite campaigns into posts using the `post` layout. The rules below are the user's decisions. Follow them exactly, and ask before deviating.

## API safety (read first)

- **The MailerLite API key is unscoped.** It can change subscribers and campaigns, so all API access goes through `scripts/mailerlite.py`. That client only sends GET requests, and only to `/api/campaigns` and `/api/campaigns/<id>`. Never add other methods or paths without the user's explicit agreement, and never call the API any other way.
- **The key lives in the macOS Keychain** item `mailerlite-api`. Never print it, log it or write it anywhere, and never run `security find-generic-password … -w` except inside `mailerlite.py`.
- **The API doesn't hold the content.** Campaign `content` is empty and `plain_text` is a placeholder. The newsletter's content comes from each email's public web preview (`preview_url`), which is fetched as an ordinary web page without the key.

## Rules

1. **Never change the words.** Newsletter text stays exactly as sent. The only text removals are rules 2 to 4, and the only other text changes are fixing typos (rule 12), contact addresses (rule 13) and references to the newsletter (rule 14). Presentational markup may change: email layout tables, inline styles, classes, attributes, `<u>` in links, and zero-width characters.
2. **Trim a conversational opener**, e.g. "Hi! I hope you all had a great weekend." or "Hi, automation fans! Welcome to your Monday newsletter."
3. **Remove workshop promos:**
   - A promo paragraph mentions a workshop and has a promo signal: a luma.com or workshops link, "coming up", "tickets", "slots", "launching" or "happening in". The converter removes these when they're 35 words or fewer.
   - Longer paragraphs with a signal mix promo and article (e.g. "In my workshop … (first one coming up next week! Get tickets here…) we go through an example…"), so they're kept and flagged for review.
   - Paragraphs that just mention workshops ("So in my workshops on test automation, we talk about…") are article content and stay.
   - "Book" buttons and the paragraph introducing them (e.g. "NEXT WEEK: Join me for a deep dive into automation in Unity:") are removed.
4. **Remove email wrapping:** preview text, "View in browser", the "Automated AF" footer block, postal address, social icons and unsubscribe text.
5. **Remove dated event calls to action and "Andrew" sign-offs. Other sign-offs are the user's call.**
   - **Remove** paragraphs inviting readers to meet at or attend a time-bound event:
     - "PS I'm looking forward to GDC in March – if you'll be there and want to chat, ping me…"
     - "PS I'm heading down to Pocketgamer Connects today!…"
     - "Save the date: If you're going to be in Brighton for Develop…"
     - "Going to Brighton for Develop? Bespoke CI are sponsoring a meetup…"
     - "Going to Gamescom? I'll be in town…"
     - the "I'll be in town too talking to studios…" paragraph that follows one of these
   - **Remove** a closing "Andrew" sign-off. If the line before it ends with a comma that led into the name ("As always, happy testing,"), change that comma to a full stop.
   - **Keep, and flag for review:** sign-offs like "Happy testing!", and PS lines that aren't time-bound, e.g. "PPS the Automated Testing In Games community I run finally has a website!…". If removing a PS leaves a PPS behind, point that out to the user.
6. **Title:** the newsletter's opening `<h1>` headline if it has one (it's dropped from the body, because the layout shows the title), otherwise the subject. Generic subjects like "Test Automation In Games Newsletter" need a real title: propose one, and expect the user to rename it. The file slug matches the title. For example, the user titled the 15 September 2025 issue "Test Automation In Ten Minutes".
7. **Videos:** an image linking to YouTube becomes an embedded player (`<iframe class="youtube-player" src="https://www.youtube.com/embed/ID">`), and YouTube's `maxresdefault.jpg` thumbnail becomes the cover image.
8. **Images** follow the porting skill's rules:
   - stored in `images/blog/YYYY/MM/` with descriptive names
   - shown as centred `<figure>`s
   - alt text that describes the image
   - third-party images credited in the caption
   - large GIFs shrunk
9. **Front matter:**
   - `layout: post`, `title`, `date` (the send time) and one existing category: Test Automation, Build Engineering, Culture And Process, Game AI or General. Don't add categories.
     - **Culture And Process** covers how teams work together and treat quality: build-failure etiquette, blame, QA's place in the team, studio culture, team dynamics and what quality engineering is. Posts about techniques or tools go in their technical category, even when they touch process (e.g. "Shifting left without test automation" is Test Automation).
   - `image:` for the cover: the YouTube thumbnail or the first image.
   - `newsletter: true`, which adds the footer "This post was originally sent to subscribers of the Automated AF newsletter", linking to https://automatedaf.dev/newsletter.
   - `newsletter_id: <campaign id>`, which marks it as converted.
   - No `original_url`.
10. **Don't convert duplicates or pure announcements.** Skip newsletters that repeat an existing post (the list script shows the overlap), and ones that are entirely a workshop or event announcement. Ask if unsure.
11. **Don't commit or push** unless asked.
12. **Fix single-word spelling typos, conservatively.** This is an exception to rule 1.
    - **Fix** a word only when it's clearly misspelt and the intended word is certain. Examples the user approved:
      - Misspellings: teny→teeny, frametate→framerate, mecahnics→mechanics, piepelines→pipelines, Jenkinfile→Jenkinsfile, Unty's→Unity's, Infact→In fact, Performace→Performance. This includes inline code in prose, e.g. "the `pipeine` keyword"→`pipeline`.
      - Real words that only one other word could replace: "a client that scraps the local machine"→scrapes, "watch to catch up"→want to, "pair down costs"→pare down, "you can even next these"→nest.
    - **Leave alone:**
      - British spellings, informal words and slang ("urgh", "lalala", "fave"), deliberate jokes and coinages.
      - Technical terms and product names written the author's way (gameobjects, jenkinsfile, smoketests).
      - Grammar, punctuation and capitalisation.
      - Anything in code blocks, URLs or text inside images (e.g. "producitivity" in a meme).
    - **Ask the user, don't change:**
      - Misspelt names or titles (e.g. "Fraiser" for the TV show Frasier).
      - Words where the intended word is a guess.
      - Fixes that would change more than one word or alter the meaning.
      - Anything that might be deliberate.
    - **Find candidates** with `python3 .claude/skills/port-wordpress-post/scripts/find_typos.py _posts/<file>.html`, which lists words not in the dictionary. It only reports, and most of its hits are fine. It can't catch real-word slips, so read the post too.
    - **Report** every fix to the user, with the post, the old word and the new word, along with any borderline cases you left alone.
13. **Contact and business references point to automatedaf.dev.** This is an exception to rule 1.
    - **Change:** links or email addresses on andrewfray.dev or automateyour.games that invite the reader to get in touch, work together or find out more about the user's services. Change the visible text as well as the link.
      - `andrew@andrewfray.dev` → `andrew@automatedaf.dev`, e.g. "ping me andrew@andrewfray.dev".
      - `https://andrewfray.dev` → `https://automatedaf.dev`, e.g. "Of course, <a>I can help with those problems</a>" and "I don't <a>charge my clients</a> $270/hr".
      - `automateyour.games` (an older domain that redirects to automatedaf.dev) → `automatedaf.dev`, including link text, e.g. "Find out more details at automateyour.games". Text inside images, such as the "automateyour.games" on video thumbnails, stays as it is.
    - **Leave alone:**
      - References that describe andrewfray.dev itself, e.g. "which is what you still see right now on https://andrewfray.dev".
      - Links to blog posts or pages on this site.
    - **Ask the user** if it's unclear whether a reference is about contact or business.
14. **References to the newsletter become references to the blog.** This is an exception to rule 1. Change only the noun.
    - **The publication as a whole → "blog":** "on this newsletter" → "on this blog", "on this mailing list" → "on this blog".
    - **The single issue → "post":** "in today's newsletter" → "in today's post", "Last week's newsletter" → "Last week's post", "a piece for another newsletter" → "another post", "beyond the scope of this newsletter" → "this post", "This email summarises…" → "This post summarises…".
    - **Other cases the user has decided:**
      - "I'm open to newsletter sponsorships!" → "blog sponsorships".
      - "Reply to this email and let me know!" → "<a href="mailto:andrew@automatedaf.dev">Reach out</a> and let me know!"
    - **Link back-references** like "Last week's post" or "Last week we talked about…" to the post they mean, when it's on the blog. Link only the time phrase. For example, the shadow tests post links "Last week's post" to `/2026/03/23/do-passing-tests-provide-any-value/`, and the Actor Tests post links "Last week" to `/2026/04/27/can-we-use-unit-tests-in-gameplay-code/`.
    - **Ask the user** when it isn't covered here and one word won't do, or the meaning would change.
15. **Link unlinked workshop mentions** to `https://automatedaf.dev/workshops`. Words stay the same.
    - Applies to a mention of the user's workshops ("my workshops on test automation", "in the workshop") with no link in its paragraph and none in the paragraphs right around it.
    - Link only the word "workshop" or "workshops", e.g. `in the <a href="https://automatedaf.dev/workshops">workshop</a>`.
    - Leave mentions that already have a link nearby. For example, "In my workshop … Get tickets here: https://automatedaf.dev/workshops" already links to the workshops, and so does the smoke tests post's "Find out more details at automatedaf.dev".
    - Ask the user if it's unclear whether the workshop is the user's own.
16. **Emphasis is italic, never bold.** Convert `<strong>` and `<b>` to `<em>`. The user finds the site font's bold ugly. Where text was both bold and italic, the result is `<em><em>…</em></em>`; merge it into a single `<em>` when nothing else is inside.

## Known newsletters

- **Converted:** all except the five below. Each converted post's `newsletter_id` front matter records its campaign, and `list_newsletters.py` shows the current state.
- **Duplicates of existing posts, don't convert:**
  - 184561289308145124 (13 April 2026, "Exploding barrels with Asset Tests"), about 85% the same as the exploding barrels post.
  - 185195784503821352 (20 April 2026, "No Fire Without Smoke Tests"), about 87% the same as the smoke tests post.
- **Pure announcements, held for the user to decide:**
  - 184183464779580419 (10 April 2026, workshop launch).
  - 191150598520833560 (24 June 2026, Develop Brighton happy hour).
  - 196128442072171863 (18 August 2026, "Quality Engineering At Gamescom 2026": talks, a panel and a mixer).

## Process (one newsletter at a time)

All commands run from the repo root.

1. **List newsletters**, oldest first, with each one's status: converted, overlap with an existing post, or new.
   ```
   python3 .claude/skills/newsletter-to-post/scripts/list_newsletters.py
   ```
2. **Convert one.** Choose the category by its subject. Pass `--title` if the subject is generic and there's no headline.
   ```
   python3 .claude/skills/newsletter-to-post/scripts/newsletter_to_post.py <campaign-id> --category "<Category>" [--title "<Title>"]
   ```
   It refuses if the newsletter is already converted, unless given `--force`. It prints:
   - the title it chose, alongside the subject and headline
   - everything it removed (opener, promos, buttons)
   - REVIEW lines for sign-offs and PS lines
   - warnings: images without alt text, links that look tracked, no cover image
3. **Read the report.** Check the removals are right, and pass the REVIEW lines and the title choice on to the user.
   The converter also rewrites links to ported WordPress posts to their local addresses, drops empty links left by the email editor, and unwraps images that only link to a copy of themselves.
4. **Images:** rename each downloaded image (`<slug>-image-N.ext`) descriptively and write alt text, using the porting skill's tools:
   ```
   python3 .claude/skills/port-wordpress-post/scripts/rename_image.py images/blog/YYYY/MM/<slug>-image-1.png descriptive-name.png
   ```
   Add `image_fit: contain` if the cover is a chart or a screenshot with text at its edges. Shrink GIFs over a few MB, as in the porting skill's rule 8. Credit third-party images (adverts, game art, others' photos) in a `<figcaption>`.
5. **Code:** newsletters don't use code blocks. Code arrives as ordinary paragraphs with `<br>` line breaks (e.g. the `.prom` and `config.alloy` examples in the Grafana post).
   - Turn each into a `{% highlight <lang> %}` block. Rebuild it from the newsletter's preview HTML: one line per `<br>`, with non-breaking spaces turned back into indentation and zero-width characters dropped.
   - Check the code's words are unchanged.
   - Rouge lexers used so far: `csharp`, `cpp`, `groovy`, `prometheus` and `hcl` (Alloy config), or `plaintext`.
6. **Check spelling** (rule 12): run the porting skill's `find_typos.py` on the post, read it for real-word slips, fix only the clear-cut typos, and list borderline ones for the user. Then search the post for `andrewfray.dev` and `automateyour.games` and apply rule 13. Then search it for "newsletter", "email", "mailing list" and "subscribers" and apply rule 14. Then search it for "workshop" and apply rule 15.
7. **Build and check:**
   ```
   bundle exec jekyll build
   ```
   - the post appears on `/blog.html` under its category
   - images load, and the video embed plays
   - the newsletter footer shows
8. **Update "Known newsletters"** above, and tell the user what was converted and what needs their review.
