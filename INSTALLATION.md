# Multi-Hacker Tool - Installationsanleitung

## Schnellstart

```bash
# 1. Setup-Skript ausführen (alle Abhängigkeiten installieren)
sudo bash setup.sh

# 2. App starten (ohne sudo erforderlich - Auto-Sudo ist aktiviert!)
python3 src/main.py
```

## Schritt-für-Schritt Installation

### Voraussetzungen
- Raspberry Pi / Linux System
- Internet-Verbindung
- Root-Zugriff (sudo) für Installation

### 1. System-Updates
```bash
sudo apt-get update
sudo apt-get upgrade
```

### 2. Abhängige Tools installieren

#### Netzwerk-Tools
```bash
sudo apt-get install -y nmap
sudo apt-get install -y tcpdump
sudo apt-get install -y net-tools
sudo apt-get install -y iproute2
sudo apt-get install -y iputils-ping
sudo apt-get install -y wireless-tools
sudo apt-get install -y wireshark       # Für GUI-basierte Paketanalyse
sudo apt-get install -y tshark          # Für Terminal-basierte Wireshark-Analyse
```

#### Python
```bash
sudo apt-get install -y python3
sudo apt-get install -y python3-pip
```

### 3. Python-Abhängigkeiten (falls vorhanden)
```bash
pip3 install -r requirements.txt
```

### 4. Auto-Sudo Konfiguration (Wichtig!)

Die App nutzt **automatische Sudo-Erhöhung** für privilegierte Befehle wie `tcpdump` und `nmap`. Dies bedeutet, dass Sie die App NICHT mit `sudo` starten müssen - sie fordert automatisch Berechtigungen an, wenn nötig.

Damit dies ohne Passwort-Eingabe funktioniert, richten Sie NOPASSWD sudo für die notwendigen Befehle ein:

```bash
# Als sudo Benutzer:
sudo visudo

# Fügen Sie diese Zeilen am Ende der Datei hinzu:
your_username ALL=(ALL) NOPASSWD: /usr/sbin/tcpdump
your_username ALL=(ALL) NOPASSWD: /usr/bin/nmap
your_username ALL=(ALL) NOPASSWD: /usr/bin/wireshark
your_username ALL=(ALL) NOPASSWD: /usr/bin/tshark
```

Ersetzen Sie `your_username` durch Ihren tatsächlichen Benutzernamen.

**Alternative:** Wenn Sie sich eine Passwort-Eingabe leisten können, funktioniert die App auch ohne diese Konfiguration - sie zeigt dann die Passwort-Aufforderung an.

### 5. Sniffer Modi

Der Network Sniffer bietet drei verschiedene Capture-Modi:

1. **📊 TcpDump** (Immer verfügbar)
   - Einfache Paketerfassung
   - Leichtgewichtig und schnell
   - Standard tcpdump Ausgabe

2. **🔍 TShark** (Terminal-Version von Wireshark)
   - Bessere Formatierung und Analyse als tcpdump
   - Wireshark-Features im Terminal
   - Keine GUI erforderlich (funktioniert auch auf Headless-Systemen!)
   - Detaillierte Paketinformationen

3. **🖥️ Wireshark GUI** (Nur wenn Display verfügbar)
   - Vollständige grafische Wireshark-Oberfläche
   - Interaktive Paket-Inspektion
   - Statistiken und Protokoll-Analyse
   - Automatische Rückkehr zum TUI nach Schließen

### 6. Berechtigungen setzen (optional, wird durch Auto-Sudo ersetzt)
# Erlaubt tcpdump als normaler Benutzer
sudo chmod +s /usr/bin/tcpdump

# Erlaubt nmap als normaler Benutzer  
sudo chmod +s /usr/bin/nmap
```

### 5. App starten

#### Option A: Mit automatischem Setup
```bash
cd Raspberry-Pi-TUI
sudo bash setup.sh
bash start.sh
```

#### Option B: Manuelle Installation
```bash
cd Raspberry-Pi-TUI
python3 src/main.py
```

#### Option C: Mit sudo (empfohlen)
```bash
cd Raspberry-Pi-TUI
sudo python3 src/main.py
```

## Features und Requirements

### Network Interfaces
- Zeigt alle Netzwerkkarten
- IP-Adressen (IPv4/IPv6)
- MAC-Adressen
- **Kein zusätzliches Tool nötig**

### Network Diagnostics
- Ping zu Hosts
- DNS-Server anzeigen
- Default Route
- **Tools: ping, ip route**

### Bluetooth
- Geräte anzeigen
- Bluetooth-Status
- **Tool: bluetoothctl**

### System Info
- Hostname, Uptime
- RAM-Auslastung
- Disk-Auslastung
- **Tools: /proc/meminfo, df**

### Port Scanner
- Local Ports (netstat)
- **NMAP Scans** (benötigt: `sudo apt install nmap`)
  - Localhost-Scan
  - Netzwerk-Discovery (-sn)
  - Custom Port Ranges
  - Interface-Auswahl
- **Berechtigungen**: sudo empfohlen

### Network Sniffer  
- Packet Capture
- Interface-Auswahl
- **Tool: tcpdump** (benötigt: `sudo apt install tcpdump`)
- **Berechtigungen**: sudo erforderlich

## Fehlerbehebung

### "nmap not installed"
```bash
sudo apt-get install nmap
```

### "tcpdump not installed"
```bash
sudo apt-get install tcpdump
```

### "Permission denied" bei tcpdump/nmap
```bash
# Entweder mit sudo starten:
sudo python3 src/main.py

# Oder Berechtigungen setzen:
sudo chmod +s /usr/bin/nmap
sudo chmod +s /usr/bin/tcpdump
```

### "No module named 'curses'"
```bash
python3 -m curses
# Falls das fehlschlägt:
sudo apt-get install python3-dev
```

## System-Anforderungen

### Minimum
- Python 3.6+
- 256 MB RAM
- Linux/Raspberry Pi OS
- curses library (standardmäßig enthalten)

### Empfohlen
- Python 3.8+
- 512 MB RAM
- Neuere Raspberry Pi (3B+ oder besser)
- sudo-Zugriff

## Automatisierung

### Systemd Service (optional)

Erstelle `/etc/systemd/system/hacker-tool.service`:
```ini
[Unit]
Description=Multi-Hacker Tool TUI
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Raspberry-Pi-TUI
ExecStart=/usr/bin/python3 /home/pi/Raspberry-Pi-TUI/src/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Dann starten mit:
```bash
sudo systemctl start hacker-tool
sudo systemctl enable hacker-tool  # Auto-start
```

## Lizenz & Sicherheit

⚠️ **Security Notice:**
- Dieses Tool ist nur für Netzwerk-Administratoren und ethisches Hacking gedacht
- Benutzen Sie es nur in Netzwerken, deren Eigentümer Sie sind oder für die Sie Erlaubnis haben
- Packet Sniffing und Port Scanning ohne Erlaubnis ist illegal
- Folgt allen Linux-Richtlinien und Gesetzen

## Support

Für Probleme bitte die Logs überprüfen:
```bash
# Mit stderr anzeigen:
python3 src/main.py 2>&1
```

---

**Version**: 0.3.1  
**Status**: Production Ready ✓
