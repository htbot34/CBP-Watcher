# Global Entry Watcher

Checks CBP's Trusted Traveler scheduler for interview openings and emails
you the instant one appears at a location you're willing to travel to.

## How it works
CBP's site exposes a public (undocumented, no login needed) JSON API
listing every enrollment center and its next open slots. This script polls
it and emails henrylachtur@gmail.com when something opens up. It only
reads public appointment data — it never touches your TTP account or
books anything for you.

## Getting a Gmail App Password (needed once)
1. Turn on 2-Step Verification on the sending Gmail account, if it isn't
   already: myaccount.google.com/security
2. Go to myaccount.google.com/apppasswords
3. Create an app password (any name is fine, e.g. "GE Watcher").
4. Copy the 16-character password — you'll paste it into a GitHub secret,
   never into the code itself. Google shows it as four groups of four
   (`abcd efgh ijkl mnop`); the spaces are display formatting only. The
   script strips them for you, but your normal Google account password
   will never work here — it has to be an App Password.

## Deploy to GitHub Actions (recommended — runs in the cloud, no computer needed)
1. Confirm this repo is public (public keeps Actions minutes free at this
   frequency): repo Settings → General → Danger Zone → Change visibility.
2. In the repo: Settings → Secrets and variables → Actions → New repository secret
   - `SMTP_PASS` = the app password from above

   That's the only secret needed. The sending address is set as `SMTP_USER`
   directly in `ge_watcher.yml`, since it's the same address the alerts go
   to and is already visible in this repo — only the app password is worth
   protecting.
3. GitHub will run the check every 15 minutes automatically. You can also
   trigger it manually from the Actions tab ("Run workflow").
4. Confirm alerts actually reach you, once: Actions tab → Run workflow →
   tick **Send a test email** → Run. An email should arrive within a
   minute. Do this now rather than finding out the app password is wrong
   at the moment a slot appears.

## Run locally instead

```
export SMTP_USER="your.address@gmail.com"
export SMTP_PASS="your16charapppassword"
python3 global_entry_watcher.py
```

To check the email path works before relying on it:

```
python3 global_entry_watcher.py --test-email
```

## Notes
- Edit `LOCATIONS` in the script to widen your search — Boise is
  notoriously slow to open up, and watching a few alternate cities at
  once (e.g. `["Boise", "Salt Lake City", "Spokane"]`) usually finds
  something sooner.
- Slots go fast, sometimes within minutes — when you get the email, book
  right away.
- Secrets stored in GitHub Actions are encrypted and never appear in the
  code or logs, even in a public repo.
