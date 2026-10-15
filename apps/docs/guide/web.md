# Web console

```bash
cd apps/web && npm ci && npm run build
xzkit serve -p COM3
```

Open http://127.0.0.1:8787

Features: port connect, live log stream (WebSocket), send/presets, ESP reset, SoftAP provision card.

Only one owner may hold the serial port (CLI and Web are mutually exclusive).
