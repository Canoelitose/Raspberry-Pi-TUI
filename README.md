# 🔧 Multi-Hacker Tool - Network & System Monitor TUI

A comprehensive Terminal User Interface (TUI) for network diagnostics, system monitoring, and hacker tools on Linux/Raspberry Pi systems. Optimized for portrait (vertical) screens!

## ✨ Features 🎯

### 🌐 **Network Hub**
- **Network Interfaces**: View all network interfaces with IPv4/IPv6 addresses
- **Network Diagnostics**: Check interface health, gateway, and connectivity
- **WLAN Status**: Display wireless device information (requires `iw` package)
- **DNS & Routes**: View DNS servers and default gateway

### 📱 **Bluetooth Hub**
- **Bluetooth Devices**: List paired BT devices
- **BT Status**: Show Bluetooth controller status

### 💻 **System Info**
- **System Information**: Hostname, Uptime, Kernel version, CPU cores
- **Memory Stats**: Total, Available, Free memory
- **Disk Usage**: Storage capacity, used space, percentage

### 🔧 **Hacker Tools** (Expandable)
- **Port Scanner**: View listening ports on system
- **Network Sniffer**: Coming soon
- **Packet Tools**: Coming soon

### ✅ **Other Features**
- **Mouse & Touchscreen Support**: Full click interaction
- **Portrait Mode Optimized**: Works perfectly on vertical screens (40-45 char width)
- **Touch-Friendly**: Large buttons and tap targets
- **Beautiful UI**: Emojis, ASCII art, clean formatting

## 🚀 Installation & Usage

### Local Development
```bash
python3 src/main.py
```

### Raspberry Pi
```bash
./scripts/run.sh
```

### Touchscreen Mode (Automatic)
The tool automatically enables touchscreen-friendly interface with larger buttons.

## 📋 Requirements

- Python 3.6+
- Linux/Raspberry Pi with `ip` command
- (Optional) `iw` package for WLAN: `sudo apt install iw`
- (Optional) `bluetoothctl` for Bluetooth: usually included
- Curses library (built-in on Linux)

## 🎮 Controls

- **🖱️ Mouse/Touch**: Click on any menu item or button
- **Esc**: Go back to previous screen
- **q**: Quit application

## 📁 Project Structure

```
├── src/
│   ├── main.py           # Entry point
│   ├── config.py         # Configuration & constants
│   ├── utils.py          # Utility functions (subprocess)
│   ├── netinfo.py        # Network & system data functions
│   └── tui/
│       ├── app.py        # TUI application core
│       ├── screens.py    # Screen classes (15+)
│       └── widgets.py    # UI components & rendering
├── scripts/
│   └── run.sh            # Raspberry Pi launcher script
└── README.md             # This file
```

## 🎯 Roadmap

- ✅ v0.3.0: Bluetooth, System Info, Hacker Tools, Portrait Mode
- 🚧 v0.4.0: Advanced port scanning, firewall rules
- 📋 v0.5.0+: Network sniffing (tcpdump integration), packet analysis

## 📝 License

Open source - Feel free to modify and extend!

## 🙏 Credits

Built with ❤️ for Raspberry Pi and Linux enthusiasts.

---

**Current Version**: v0.3.0  
**Last Updated**: 2026-01-19

## Author

Built with ❤️ for network monitoring on Raspberry Pi
