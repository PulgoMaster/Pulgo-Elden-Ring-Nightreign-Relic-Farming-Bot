# Security Policy

## Supported Versions

Only the latest GitHub release receives security attention. Update before filing a report if you're on an older version.

## Reporting a Vulnerability

Please **do not open a public issue** for security problems. Use one of these private channels:

- **Preferred:** GitHub's [Private Vulnerability Reporting](../../security/advisories/new) on this repository.
- Alternative: private message `PulgoMaster` on GitHub.

### Include in your report

- Description of the issue and impact.
- Steps to reproduce or a proof of concept.
- RelicBot version and OS.
- Relevant log or diagnostic output (scrub personal info first).

### What to expect

- Acknowledgement within a few days.
- Fixes ship in the next patch or minor release.
- You'll be credited in release notes unless you ask otherwise.

## Scope

**In-scope**
- Code execution or privilege escalation via config files, profile files, or update ZIPs loaded by the bot.
- Sensitive data unintentionally written to disk or included in diagnostic output.
- Tampered binaries in this project's releases.

**Out-of-scope**
- Issues requiring prior root access or physical access to the machine.
- Anti-cheat (EAC) or Steam / Elden Ring / Nightreign behavior — those are vendor concerns.
- Misuse unrelated to the bot's actual attack surface (e.g. how users play the game after farming) — not a security issue for this project.
- Third-party dependency CVEs without a realistic exploit path through this project.

## Not a Security Issue

Bugs, crashes, OCR misreads, and feature requests go in [regular issues](../../issues) or the `BUG_REPORT.md` workflow — not here.
