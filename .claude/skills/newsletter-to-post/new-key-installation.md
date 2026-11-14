# Installing a new MailerLite API key

The scripts read the key from the macOS Keychain, from a generic-password item whose service name is `mailerlite-api` (see `scripts/mailerlite.py`). They look it up by service name only, so the account name can be anything.

Run these commands yourself in a terminal. Don't paste the key into a chat with Claude.

## 1. Remove the old key

```
security delete-generic-password -s mailerlite-api
```

Run it again until it says `The specified item could not be found in the keychain.`, so no stale copies are left. If there was never a key, you'll see that message the first time, which is fine.

## 2. Add the new key

Copy the new key from MailerLite, then run:

```
security add-generic-password -U -s mailerlite-api -a "$USER" -w "$(pbpaste)"
pbcopy < /dev/null
```

The first command reads the key from the clipboard. Your shell history records the literal `$(pbpaste)`, not the key. The second command clears the clipboard.

Don't use the interactive prompt (`-w` with nothing after it). It silently keeps only the first 128 characters, and MailerLite keys are much longer, so the stored key is cut off and the API returns HTTP 401. To check the length without printing the key, run `security find-generic-password -s mailerlite-api -w | tr -d '\n' | wc -c`. Anything at or near 128 is truncated.

## 3. Check it works

Make sure the item exists. This prints nothing secret:

```
security find-generic-password -s mailerlite-api >/dev/null && echo "key installed"
```

Then make a real read-only API call from the repo root:

```
python3 .claude/skills/newsletter-to-post/scripts/list_newsletters.py
```

If it lists newsletters, the key works. If you get HTTP 401, the key was mistyped or has been revoked, so go back to step 1.

The first time a script reads the item, macOS might ask whether `security` can access it. Choose **Always Allow**.

## 4. Revoke the old key

In MailerLite, go to **Integrations → MailerLite API** and delete the old token, so the only working key is the one in the Keychain.

## Don't

- Run `security find-generic-password … -w`. It prints the key. Only `mailerlite.py` does that, internally.
- Put the key in a file, an environment variable, `.env` or the repo.
