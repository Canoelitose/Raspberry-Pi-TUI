# Wireshark Integration - Network Sniffer

## 📋 Überblick

Der **Network Sniffer** bietet jetzt zwei Capture-Modi:

### 1. **📊 TcpDump Modus** (Standard)
- Erfasst Pakete direkt im TUI-Terminal
- Zeigt Live-Paketdaten in der Console an
- Schnell und lightweight
- Touchscreen-optimiert

### 2. **🔍 Wireshark Modus** (Neu!)
- Öffnet Wireshark GUI für erweiterte Paketanalyse
- Detaillierte Packet Inspection
- Filter und Statistiken
- Nach dem Schließen: **Automatische Rückkehr zum TUI** zur gleichen Stelle

## 🎯 Verwendung

### Im Network Sniffer Screen:

1. **Interface wählen**: Klicken Sie auf das gewünschte Interface (eth0, wlan0, etc.)

2. **Capture-Modus wählen**:
   - **📊 TcpDump**: Erfasst Pakete im Terminal
   - **🔍 Wireshark**: Öffnet Wireshark GUI

3. **Nach Wireshark**: 
   - Wireshark schließen → TUI wird automatisch wiederhergestellt
   - Sie sind wieder im Network Sniffer Screen beim gleichen Interface

## 💻 Installation

Wireshark muss installiert sein:

```bash
# Über setup.sh (automatisch installiert)
sudo bash setup.sh

# Oder manuell:
sudo apt-get install wireshark
```

## 🔐 Permissions

Damit Wireshark mit der Auto-Sudo-Funktion funktioniert:

```bash
sudo visudo

# Fügen Sie hinzu:
your_username ALL=(ALL) NOPASSWD: /usr/bin/wireshark
```

## 🔄 Workflow

```
TUI Main Menu
    ↓
🔧 Hacker Tools
    ↓
Network Sniffer Screen
    ↓
[Wähle Interface] [Wähle Capture-Modus]
    ↓
    ├─ TcpDump: Erfasst Pakete im TUI
    │   └─ 🔄 Sync zum Aktualisieren
    │
    └─ Wireshark: Öffnet GUI
        └─ [Wireshark Fenster offen]
        └─ [Benutzer interagiert mit Touchscreen]
        └─ [Wireshark schließen]
        └─ ← TUI wird automatisch wiederhergestellt
        └─ Zurück im Network Sniffer Screen
```

## ✅ Features

- ✅ Interface-Auswahl
- ✅ TcpDump Live-Capture im Terminal
- ✅ Wireshark GUI für detaillierte Analyse
- ✅ Automatische TUI-Wiederherstellung nach Wireshark
- ✅ Touchscreen-optimiert
- ✅ Auto-Sudo für privilegierte Befehle
- ✅ Konsistente Button-Bar (← Back | 🔄 Sync | Home)

## 🚀 Tipps

### TcpDump Modus:
- Klicken Sie **🔄 Sync**, um Pakete zu aktualisieren
- Schnell und responsiv auf Raspberry Pi

### Wireshark Modus:
- Besser für detaillierte Paket-Inspektionen
- Nutzen Sie die Wireshark-Filter (z.B. `tcp port 80`)
- Statistiken und Protokoll-Hierarchie verfügbar
- Grafische Flows und Trends

## ⚙️ Troubleshooting

**Problem**: Wireshark öffnet nicht
- **Lösung**: `sudo apt-get install wireshark` und Permissions konfigurieren

**Problem**: Permissions-Fehler bei Wireshark
- **Lösung**: Siehe NOPASSWD sudoers Konfiguration in INSTALLATION.md

**Problem**: Wireshark stellt TUI nicht wieder her
- **Lösung**: Sie können `Ctrl+C` im Terminal drücken und das Programm erneut starten

## 📝 Technische Details

### Implementierung

Die Wireshark-Integration nutzt:
- `subprocess.Popen()` zum Öffnen von Wireshark
- Automatische Sudo-Erhöhung via `run_cmd_with_sudo()`
- Touchscreen Click-Detection für Button-Interaktion
- TUI bleibt im Speicher während Wireshark offen ist

### Funktionen

- `open_wireshark(interface)` - Öffnet Wireshark GUI
- `check_wireshark_available()` - Prüft Verfügbarkeit
- SnifferScreen zeigt beide Optionen wenn Wireshark verfügbar

## 🎓 Verwendungsbeispiele

### Schnelle Paket-Analyse
```
1. Network Sniffer → Interface wählen
2. TcpDump Modus → Live-Paketdaten
3. 🔄 Sync → Aktualisieren nach Bedarf
```

### Detaillierte Analyse
```
1. Network Sniffer → Interface wählen
2. Wireshark Modus → GUI öffnet sich
3. Filter anwenden (z.B. "tcp.port == 22")
4. Paketdetails inspizieren
5. Wireshark schließen
6. ← Automatisch zurück im TUI
```

---

**Version**: 0.3.1+  
**Kompatibilität**: Raspberry Pi, Linux x64, WSL  
**Touchscreen**: ✅ Voll optimiert
