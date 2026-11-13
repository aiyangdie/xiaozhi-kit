<p align="center"><img src="assets/covers/25-xiaozhi-kit.jpg" alt="xiaozhi-kit 项目封面" width="100%"></p>

# Xiaozhi Kit

Open-source toolkit for **ESP32 Xiaozhi** boards: AI-friendly CLI, local Web console, and Cursor Skill.

Replaces closed serial GUIs that monopolize the COM port and cannot be driven by agents.

## Install

```bash
git clone https://github.com/aiyangdie/xiaozhi-kit.git
cd xiaozhi-kit
pip install -e ".[dev]"
xzkit doctor --json
```

Docs: https://aiyangdie.github.io/xiaozhi-kit/

## Quick start (AI / CLI)

```bash
xzkit doctor --json
xzkit list --json
xzkit status -p COM3 --json
xzkit read -p COM3 -t 10 --json
xzkit reset -p COM3 --json
xzkit provision status -p COM3 --json
xzkit parse examples/fixtures/provision_ap.log --json
xzkit serve -p COM3          # http://127.0.0.1:8787
```

Exit codes: `0` ok · `1` unhealthy/crash · `2` port busy/missing · `3` timeout · `4` dependency · `5` usage.

**Agents:** never run infinite monitors; always use bounded `-t` / `--timeout`. Prefer `doctor` then `status`.

## Web console

```bash
cd apps/web && npm install && npm run build   # once
xzkit serve -p COM3
```

Open http://127.0.0.1:8787 — logs, send, reset, SoftAP provision card.

## Cursor Skill

See [`skills/xiaozhi-kit/SKILL.md`](skills/xiaozhi-kit/SKILL.md). Copy into `~/.cursor/skills/xiaozhi-kit/`.

## Layout

```
packages/xzkit_core/     # serial, parse, provision, presets, services
packages/xzkit_cli/      # xzkit CLI
packages/xzkit_server/   # FastAPI + static console
apps/web/                # Vite + React console
apps/docs/               # VitePress site
skills/xiaozhi-kit/      # Cursor Skill
examples/fixtures/       # sample logs (no real WiFi passwords)
```

## License

MIT — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
