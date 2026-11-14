---
name: post-to-newsletter
description: Turn a blog post in this Jekyll site's _posts/ into a draft Automated AF newsletter in MailerLite, for the user to preview and send. Use when asked to send, email or newsletter a blog post, make a newsletter or MailerLite draft from a post, or check the post-to-newsletter rules.
---

# Blog post to newsletter

This is the reverse of the newsletter-to-post skill. It takes a post the user has written for the blog and makes a **draft** MailerLite campaign from it. The user previews, tests, schedules and sends it in MailerLite. The rules below are the user's decisions. Follow them exactly, and ask before deviating.

## API safety (read first)

- **All API access goes through the newsletter-to-post skill's `scripts/mailerlite.py`.** Its API safety rules apply here too. The key lives in the macOS Keychain item `mailerlite-api`. Never print it, log it or write it anywhere.
- **The only write is creating a draft.** `mailerlite.create_draft_campaign` sends `POST /api/campaigns` and nothing else. It refuses schedule and delivery fields, and the client has no route to `/api/campaigns/<id>/schedule`.
  - **Never send, schedule or test-send a campaign.** Never change subscribers or groups. Never edit or delete an existing campaign. All of that is the user's job in MailerLite.
  - Don't add API paths or methods without the user's explicit agreement.
- **Creating a draft is still an outward action.** Create one only when the user has asked for a newsletter from that post. Create one draft per request, and don't create another for the same post unless asked (`--force`).

## Rules

1. **The words stay as the post has them.** Only the wording reviews in rule 5 may change text, and only with the user's agreement.
2. **Shape of the email.** This matches the user's recent issues:
   - No conversational opener and no "Andrew" sign-off are added.
   - The post title goes at the top as an `<h1>`, then the post body.
   - After the body: "This newsletter is also on the blog: read it on andrewfray.dev", linking to the post.
   - The footer has the "View in browser" link (`{$url}`), the Automated AF postal address, the "You received this email…" line and the unsubscribe link (`{$unsubscribe}`). MailerLite requires the unsubscribe tag.
3. **The subject is the post title.** The campaign name is `YYYY-MM-DD: <title>`, using the date the draft was made. The preview text is the post's `description` if it has one, otherwise its first paragraph cut to about 140 characters. Use `--subject` or `--preview-text` when the user wants something else.
4. **The sender is copied from the most recent sent campaign** (currently Automated AF <andrew@andrewfray.dev>), so it's always an address MailerLite has verified. Recipients are left unset, and the user picks them when sending.
5. **Wording is reviewed by the user, not changed automatically.** The script flags phrases like "this post", "last week's post" and "the blog". Pass them to the user with a suggested email wording (e.g. "this post" → "this newsletter") and change them only if the user agrees. Make the change in the email, never in the post. "Post-" as a prefix ("post-AI-bubble") is not a reference to the blog.
6. **Links and images use the blog's address**, `https://andrewfray.dev`, taken from `_config.yml`'s `url`. automatedaf.dev is the user's separate business site and doesn't host blog pages or images. The post and its images have to be live on andrewfray.dev before the draft is sent, or the images break.
7. **Email-safe conversion** (the script does this):
   - Styles are inlined, inside a 600px centred layout.
   - YouTube embeds become a thumbnail linking to the video. Other iframes are flagged.
   - Highlighted code becomes plain preformatted code.
   - Ids, classes and scripts are dropped.
   - Images get `width="560"`, and any without alt text are flagged.
8. **Record the campaign.** After `--create`, the post gets `newsletter_id: <campaign id>` in its front matter. This stops the newsletter-to-post skill converting the sent email back into a duplicate post. Don't add `newsletter: true`, which would wrongly label the post as originally a newsletter. If the user deletes the draft, remove the `newsletter_id`.
9. **Don't convert posts that came from newsletters** (`newsletter: true`). They've already been sent. The script warns about these.
10. **Don't commit or push** unless asked.

## Process (one post at a time)

All commands run from the repo root.

1. **Build the site.** The script reads the rendered post from `_site/`. The shell may pick up Homebrew's Ruby 4.0, which can't run this Jekyll, rather than the locked 3.3.13, so load rbenv first:
   ```
   eval "$(rbenv init - zsh)" && bundle exec jekyll build
   ```
2. **Check the post is live.** Confirm `https://andrewfray.dev/YYYY/MM/DD/<slug>/` and its images return 200. If they don't, tell the user that the post needs deploying before the email goes out. They can still make the draft.
3. **Dry run.** This writes the email HTML and creates nothing:
   ```
   python3 .claude/skills/post-to-newsletter/scripts/post_to_newsletter.py _posts/<file> --out <scratchpad>/<slug>.html
   ```
   It prints the subject, preview text, REVIEW lines (wording, iframes) and warnings (missing alt text). Check the image and link URLs in the HTML are absolute andrewfray.dev addresses.
4. **Settle the review lines with the user.** Edit the generated HTML for any agreed wording changes, or pass `--subject` / `--preview-text`. (If wording changes become common, add a way to pass them to the script, rather than editing the HTML by hand each time.)
5. **Create the draft:**
   ```
   python3 .claude/skills/post-to-newsletter/scripts/post_to_newsletter.py _posts/<file> --create
   ```
   Then read the campaign back with `mailerlite.get("/api/campaigns/<id>")` to confirm `status` is `draft` and `emails[0].content` holds the HTML.
6. **Tell the user:**
   - the campaign name, subject, sender and preview text
   - that nothing has been sent, and that they choose the recipients when sending
   - that it's worth sending themselves a test, especially to see images on mobile
   - the front matter change
