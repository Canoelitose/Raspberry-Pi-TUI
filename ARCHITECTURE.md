# 🔧 Multi-Hacker Tool - Dokumentation

## Architektur-Überblick

Das Projekt wurde umstrukturiert zu einem vollständigen **Multi-Hacker-Tool** mit folgenden Hauptkomponenten:

### 📊 Hub-Struktur

```
Main Menu (🔧 Multi-Hacker Tool)
├── 🌐 Network Hub
│   ├── Network Interfaces
│   ├── Network Diagnostics
│   ├── WLAN Status
│   └── DNS & Routes
├── 📱 Bluetooth Hub
│   ├── BT Devices
│   └── BT Status
├── 💻 System Info
│   ├── System Information
│   ├── Memory Stats
│   └── Disk Usage
├── 🔧 Hacker Tools
│   ├── Port Scanner
│   ├── Network Sniffer (Coming Soon)
│   └── Packet Tools (Coming Soon)
├── ⚙️  Settings
└── ❌ Exit
```

---

## 📱 Portrait-Mode Optimierung

Das UI wurde speziell für **hochkant/Portrait-Bildschirme** optimiert:

### Technische Details:
- **Max Width**: 40-50 Zeichen (konfigurierbar in `config.py`)
- **Safe Width Function**: `get_safe_width(stdscr)` in `widgets.py`
- **Automatische Anpassung**: Alle Widgets respektieren die Portrait-Grenzen
- **Button-Bar**: 2-3 Buttons pro Zeile auf schmalen Screens

### Features:
- ✅ Text-Truncation bei langen Zeilen
- ✅ Responsive Button-Layouts
- ✅ Touch-freundliche Tap-Ziele
- ✅ Keine horizontale Scrolling nötig

---

## 🌐 Network Hub

### InterfacesScreen
Zeigt alle Netzwerk-Interfaces mit:
- Interface-Namen
- Status (UP/DOWN)
- MAC-Adressen
- IPv4 und IPv6 Adressen

### NetDiagScreen & NetDiagDetailScreen
Detaillierte Netzwerk-Diagnose:
- Interface-Health-Check
- Gateway-Informationen
- Connectivity-Tests (Ping)
- State-Informationen

### WifiScreen
WLAN-Status via `iw dev`:
- Wireless-Geräte
- SSID-Informationen
- Signal-Stärke (wenn verfügbar)

### DnsRoutesScreen
DNS- und Routing-Informationen:
- DNS-Server (aus `/etc/resolv.conf`)
- Default-Gateway
- Routing-Informationen

---

## 📱 Bluetooth Hub

### BluetoothDevicesScreen
Liste aller gekoppelten Bluetooth-Geräte:
- `bluetoothctl paired-devices` Output
- Geräte-Namen und MAC-Adressen

### BluetoothStatusScreen
Bluetooth-Controller-Status:
- Power-Status
- Discoverable-Status
- Pairable-Status
- Alias und weitere Informationen

---

## 💻 System Info

### SystemInfoScreen (3-teilig)

#### 📊 System Information
- Hostname
- Uptime
- Kernel-Version
- CPU-Cores

#### 💾 Memory
- Total RAM
- Available RAM
- Free RAM

#### 💿 Disk
- Filesystem-Größe
- Verwendeter Speicher
- Verfügbarer Speicher
- Nutzungspercentage

---

## 🔧 Hacker Tools

### PortScannerScreen
Zeigt offene/abhörende Ports:
- Nutzt `netstat -tuln` oder `ss -tuln` als Fallback
- Filtert LISTEN-Ports
- Zeigt Proto/Local Address/State

### SnifferScreen & PacketsScreen
Platzhalter für zukünftige Features:
- Network Packet Sniffing (tcpdump Integration)
- Advanced Packet Analysis Tools
- Mit ethischen Richtlinien

---

## 🔗 Navigation & Datenfluss

```
MainMenuScreen
    ↓ (Screen-Name)
    ├─→ net_hub → NetworkHubScreen
    │       ├─→ ifaces → InterfacesScreen
    │       ├─→ netdiag → NetDiagScreen
    │       │   └─→ netdiag_detail → NetDiagDetailScreen
    │       ├─→ wifi → WifiScreen
    │       └─→ dns_routes → DnsRoutesScreen
    ├─→ bt_hub → BluetoothHubScreen
    │       ├─→ bt_devices → BluetoothDevicesScreen
    │       └─→ bt_status → BluetoothStatusScreen
    ├─→ sys_info → SystemInfoScreen
    ├─→ hacker → HackerToolsScreen
    │       ├─→ port_scan → PortScannerScreen
    │       ├─→ sniffer → SnifferScreen
    │       └─→ packets → PacketsScreen
    ├─→ settings → SettingsScreen
    └─→ quit
```

---

## 🔄 Daten-Quellen

### `netinfo.py` Functions

**Network:**
- `get_interfaces()` - via `ip addr` & `ip -brief link`
- `get_dns()` - via `/etc/resolv.conf`
- `get_default_route()` - via `ip route show default`
- `ping()`, `ping_via_interface()` - via `ping` command
- `get_interface_stats()` - kombiniert obige Funktionen
- `wifi_status()` - via `iw dev`

**Bluetooth:**
- `get_bluetooth_devices()` - via `bluetoothctl paired-devices`
- `get_bluetooth_status()` - via `bluetoothctl show`
- `get_bluetooth_powered()` - parsed `bluetoothctl show` Output

**System:**
- `get_system_info()` - via `hostname`, `uptime -p`, `uname`, `nproc`
- `get_memory_info()` - via `/proc/meminfo`
- `get_disk_usage()` - via `df -h`
- `check_open_ports()` - via `netstat -tuln` oder `ss -tuln`

---

## 🛠️ Konfiguration

### `config.py`
```python
APP_NAME = "🔧 Multi-Hacker Tool"
VERSION = "0.3.0"
MAX_WIDTH = 45  # Portrait-Mode Width
PORTRAIT_MODE = True  # Portrait-Optimierungen
```

---

## 🖱️ UI/UX Features

### widgets.py Funktionen

- `draw_header()` - Top-Bar mit Title/Subtitle
- `draw_footer()` - Bottom-Bar mit Hilfetext
- `menu()` - Menü-Items mit Click-Regions
- `draw_text_block()` - Text-Anzeige mit Formatierung
- `draw_touch_button_bar()` - Responsive Button-Bar
- `check_mouse_click()` - Click-Event-Verarbeitung
- `get_safe_width()` - Portrait-Mode Breiten-Berechnung

### Touch-Mode Features
- Größere Tap-Ziele
- 2 Zeilen pro Menu-Item
- Große Buttons in Button-Bar
- Reverse-Video-Highlighting

---

## 🚀 Erweiterbarkeit

Neue Screens hinzufügen:

1. **Neue Screen-Klasse** in `screens.py`:
```python
class MyNewScreen(BaseScreen):
    name = "my_screen"
    title = "My Title"
    
    def render(self, stdscr):
        # Render logic
        pass
    
    def handle_key(self, key):
        # Input handling
        pass
```

2. **Screen-Map** in `app.py` aktualisieren:
```python
self.screen_map["my_screen"] = MyNewScreen
```

3. **Navigation** in Parent-Screen verlinken

---

## 📝 Version History

- **v0.1.0** - Initial Network Monitor
- **v0.2.0** - UI Improvements, English
- **v0.3.0** - Multi-Hacker Tool, Bluetooth, System Info, Portrait Mode ← **CURRENT**
- **v0.4.0** - Advanced Port Scanning, Firewall Info
- **v0.5.0+** - Network Sniffing, Packet Analysis

---

**Dokumentation erstellt**: 2026-01-19  
**Tool Version**: v0.3.0
