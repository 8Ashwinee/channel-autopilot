# Contributing to channel-autopilot

Thank you for helping. Every size of contribution counts: a typo fix, a test, a new platform.

## Quick start

```bash
git clone https://github.com/ClayDesk/channel-autopilot && cd channel-autopilot
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev,youtube,maker,research]'
pytest                      # the tests mock the network: nothing is posted anywhere
```

## How to send a change

1. Find or open an issue first for anything larger than a small fix, so we can agree on the shape before you build it.
2. Fork, create a branch (`feat/tiktok`, `fix/queue-retry`), and keep each pull request to one topic.
3. Add or update tests; `pytest` must pass.
4. Update the docs in `docs/` when you change how something is used.
5. Open the pull request and describe what changed and how you tested it.

## Adding a platform

A platform is one module in `src/autopilot/platforms/`. Copy the shape of `youtube.py`: an `actions` mapping
(for example `tiktok.video`), a function per action that takes a queue item and returns the live URL, and a clear
"stop for today" error when the platform's daily limit is reached. Mock every network call in the tests.

## Rules that keep the project safe to use

- **Never commit keys, tokens or account IDs.** Configuration and secrets stay in the user's own files (`secrets/` is git-ignored).
- **Respect each platform's terms.** No scraping, no workarounds for rate limits or reviews, no posting to accounts the user does not own.
- **No invented facts in examples.** Example scripts state numbers only with their source.

## Code of conduct

Be kind and assume good intent. Harassment or personal attacks are not accepted; maintainers may remove comments or
contributors that break this.

## Licence

By contributing you agree that your contribution is licensed under the project's MIT licence.
