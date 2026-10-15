# Install

## Requirements

- Python 3.10+
- USB serial driver (CH340 / CP210x / ESP USB-JTAG)
- Optional: Node.js 18+ to rebuild the Web UI / docs

## From source (recommended)

```bash
git clone https://github.com/xiaozhi-kit/xiaozhi-kit.git
cd xiaozhi-kit
pip install -e ".[dev]"
xzkit doctor --json
```

## From PyPI (when published)

```bash
pip install xiaozhi-kit
xzkit --version
```

## Config

Optional user config: `~/.xzkit/config.toml`

```toml
port = "COM3"
baud = 115200

[presets]
ping = "ping"
```

Project override: `xzkit.toml` in the working directory.
