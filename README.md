# Raspberry Pi Network Monitor TUI

A beautiful, interactive Terminal User Interface (TUI) for monitoring and diagnosing network configuration and connectivity on Linux/Raspberry Pi systems.

## Features 🎯

- **Network Interface Monitor**: View all network interfaces with detailed IPv4/IPv6 addresses
- **Network Diagnostics**: Check default gateway, DNS servers, and connectivity (ping test)
- **WLAN Status**: Display wireless device information (requires `iw` package)
- **Settings Panel**: Placeholder for future configuration options
- **Mouse Support**: Click on menu items and buttons for navigation
- **Touchscreen Optimized**: Special touch mode with larger tap targets and button bar (use `--touch` flag)
- **Keyboard Navigation**: Full keyboard support with intuitive controls
- **Beautiful UI**: Enhanced with ASCII art, emojis, and improved formatting

## Quick Start

### Local Development
```bash
python3 src/main.py
```

### Touchscreen Mode (larger buttons, touch-friendly)
```bash
python3 src/main.py --touch
```

### Raspberry Pi (via script)
```bash
./scripts/run.sh
```

### Raspberry Pi with Touchscreen
```bash
./scripts/run.sh --touch
```

## Requirements

- Python 3.6+
- Linux/Raspberry Pi with `ip` command
- (Optional) `iw` package for WLAN features: `sudo apt install iw`
- Curses library (built-in on Linux)

## Controls 🎮

| Key | Action |
|-----|--------|
| ↑/↓ or `j`/`k` | Navigate menu |
| Enter | Select option |
| Esc / Backspace | Go back |
| `r` | Refresh data |
| `q` | Quit application |
| **Mouse Click** | Click menu items or refresh buttons |

## Project Structure

```
├── src/
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration & constants
│   ├── utils.py          # Utility functions
│   ├── netinfo.py        # Network data collection
│   └── tui/
│       ├── app.py        # TUI application core
│       ├── screens.py    # Screen definitions
│       └── widgets.py    # UI widgets & components
├── scripts/
│   └── run.sh            # Raspberry Pi launcher
└── README.md             # This file
```

## Version

v0.2.0 - Now with English UI and improved design! 🎨

## Author

Built with ❤️ for network monitoring on Raspberry Pi
