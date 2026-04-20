# Contributing

Thanks for your interest. This project is a hobby bot maintained by one person. Contributions are appreciated, but the project has a strong opinionated direction, so please read this before investing time.

## Filing issues

- **Security issues** — do NOT open a public issue. Use [Private Vulnerability Reporting](../../security/advisories/new). See [SECURITY.md](SECURITY.md).
- **Bugs** — use the Bug Report issue template. OCR and calibration problems have their own template.
- **Feature requests** — use the Feature Request template.
- **Questions** — prefer [GitHub Discussions](../../discussions) over issues.

## Before filing a bug

- Confirm you're on the latest release. Older releases don't receive fixes.
- For OCR problems, verify your setup matches the README requirements: 1920x1080, English game language, Borderless Fullscreen, 100% DPI scaling.
- Include version, OS, GPU, and a clear description. The issue template lists every required field.

## Pull requests

- **Drive-by PRs are unlikely to be merged.** This is a specialized automation bot. Most changes require knowledge of the OCR pipeline, iteration loop, or game-specific quirks.
- If you want to contribute code, **open an issue first** to discuss the approach. You'll get early feedback on whether it's something I'd merge.
- No AI-authorship attribution in commits or code. The project is human-authored.

## Operational scope

The bot is designed to run **single-player, with Steam or Nightreign set to offline mode**. It automates the tedious save-scum cycle for relic farming — a workaround for how Nightreign's relic system works, not a cheat or exploit.

The bot **does not evade EAC** because it doesn't do anything EAC cares about: no DLL injection, no memory editing, no in-process hooks. It's screen-capture OCR plus keyboard/mouse input, with `.sl2` save backup/restore happening while the game is at a menu or closed.

Contributions that change that stance are out of scope and will not be merged:
- Features that act *during live multiplayer or co-op sessions*, or that affect other players in any way.
- Features that actually attempt to bypass, tamper with, or hook into EAC or the game's memory.

What users do with the relics they farm — including taking them into co-op afterwards — is their own choice, not something this project tries to police.

## License

By contributing, you agree your contributions are licensed under the Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
