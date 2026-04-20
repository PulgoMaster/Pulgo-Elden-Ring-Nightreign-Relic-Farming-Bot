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
- Keep each PR small and focused. One concern per PR.
- Match the surrounding code style. No reformatting passes.
- No AI-authorship attribution in commits or code. The project is human-authored.

## Multiplayer and competitive use

This tool is **single-player only**. Features that would facilitate multiplayer disruption, EAC evasion beyond what's already documented, or competitive advantage in co-op will not be accepted.

## License

By contributing, you agree your contributions are licensed under the Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
