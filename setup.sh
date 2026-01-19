#!/bin/bash

################################################################################
# Multi-Hacker Tool - Setup Script
# Installiert alle Abhängigkeiten und bereitet die App vor
# Verwendung: sudo bash setup.sh
################################################################################

set -e  # Exit on error

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
print_header() {
    echo -e "\n${BLUE}=================================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    print_error "Dieses Skript muss als root (sudo) ausgeführt werden!"
    echo "Verwende: sudo bash setup.sh"
    exit 1
fi

print_header "🔧 Multi-Hacker Tool - Automatisches Setup"

# ============================================================================
# 1. Paketmanager Update
# ============================================================================
print_header "Schritt 1/5: Paketmanager aktualisieren"

apt-get update > /dev/null 2>&1
print_success "apt-get aktualisiert"

# ============================================================================
# 2. System-Tools installieren
# ============================================================================
print_header "Schritt 2/6: Netzwerk- und Security-Tools installieren"

TOOLS=("nmap" "tcpdump" "net-tools" "iproute2" "iputils-ping" "wireless-tools" "wireshark" "tshark" "evtest" "libinput-tools" "usbutils")

for tool in "${TOOLS[@]}"; do
    # Special handling for wireshark (includes tshark)
    if [ "$tool" = "wireshark" ]; then
        if ! command -v wireshark &> /dev/null; then
            print_info "Installiere $tool..."
            apt-get install -y $tool tshark > /dev/null 2>&1
            print_success "$tool und tshark installiert"
        else
            print_success "$tool ist bereits installiert"
        fi
    # Special handling for libinput-tools
    elif [ "$tool" = "libinput-tools" ]; then
        if ! command -v libinput &> /dev/null; then
            print_info "Installiere $tool..."
            apt-get install -y $tool > /dev/null 2>&1
            print_success "$tool installiert"
        else
            print_success "$tool ist bereits installiert"
        fi
    else
        if ! command -v $tool &> /dev/null; then
            print_info "Installiere $tool..."
            apt-get install -y $tool > /dev/null 2>&1
            print_success "$tool installiert"
        else
            print_success "$tool ist bereits installiert"
        fi
    fi
done

# ============================================================================
# 3. Python und pip installieren
# ============================================================================
print_header "Schritt 3/6: Python-Umgebung konfigurieren"

if ! command -v python3 &> /dev/null; then
    print_info "Installiere Python3..."
    apt-get install -y python3 python3-pip > /dev/null 2>&1
    print_success "Python3 installiert"
else
    print_success "Python3 ist bereits installiert"
fi

# Upgrade pip
print_info "Upgrade pip..."
python3 -m pip install --upgrade pip > /dev/null 2>&1
print_success "pip aktualisiert"

# ============================================================================
# 4. Python-Abhängigkeiten installieren
# ============================================================================
print_header "Schritt 4/6: Python-Abhängigkeiten installieren"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    print_info "Installiere Python-Pakete aus requirements.txt..."
    python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
    print_success "Python-Abhängigkeiten installiert"
else
    print_info "requirements.txt nicht gefunden (nicht kritisch)"
fi

# ============================================================================
# 5. Sudoers-Konfiguration (Auto-Sudo für privilegierte Tools)
# ============================================================================
print_header "Schritt 5/6: Sudo-Berechtigungen konfigurieren"

CURRENT_USER=${SUDO_USER:-$(whoami)}

if [ "$CURRENT_USER" != "root" ]; then
    print_info "Konfiguriere NOPASSWD sudo für Benutzer: $CURRENT_USER"
    
    # Create sudo rules for privileged tools
    SUDO_RULES="/etc/sudoers.d/raspi-tui-tools"
    
    # Check if file already exists
    if [ ! -f "$SUDO_RULES" ]; then
        # Create sudoers file with proper permissions
        cat > /tmp/raspi-tui-sudo << EOF
# Raspberry Pi TUI - Auto-Sudo for Security Tools
# Allows $CURRENT_USER to run security tools without password
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/sbin/tcpdump
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/nmap
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/wireshark
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/tshark
$CURRENT_USER ALL=(ALL) NOPASSWD: /usr/bin/evtest
$CURRENT_USER ALL=(ALL) NOPASSWD: /bin/timeout
EOF
        
        # Install sudoers file with validation
        visudo -c -f /tmp/raspi-tui-sudo > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            mv /tmp/raspi-tui-sudo "$SUDO_RULES"
            chmod 0440 "$SUDO_RULES"
            print_success "Sudoers-Konfiguration erstellt: $SUDO_RULES"
        else
            print_error "Sudoers-Validierung fehlgeschlagen"
            rm -f /tmp/raspi-tui-sudo
        fi
    else
        print_success "Sudoers-Konfiguration bereits vorhanden"
    fi
else
    print_info "Root-Benutzer - Sudoers-Konfiguration übersprungen"
fi

# ============================================================================
# 6. Berechtigungen und Finale Checks
# ============================================================================
print_header "Schritt 6/6: Finale Konfiguration und Tests"

# Test tool availability
print_info "Teste verfügbare Tools:"

REQUIRED_TOOLS=("tcpdump" "nmap" "tshark" "evtest")
ALL_OK=true

for tool in "${REQUIRED_TOOLS[@]}"; do
    if command -v $tool &> /dev/null; then
        print_success "$tool verfügbar"
    else
        print_error "$tool NICHT GEFUNDEN"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    print_success "Alle Tools verfügbar!"
else
    print_error "Einige Tools fehlen - bitte manuell installieren"
fi

# Berechtigungen für tcpdump (für nicht-root Benutzer)
if [ -f /usr/bin/tcpdump ]; then
    chmod +s /usr/bin/tcpdump 2>/dev/null
    print_success "tcpdump Berechtigungen gesetzt"
fi

# Berechtigungen für nmap (optional)
if [ -f /usr/bin/nmap ]; then
    chmod +s /usr/bin/nmap 2>/dev/null
    print_success "nmap Berechtigungen gesetzt"
fi

# ============================================================================
# Setup abgeschlossen
# ============================================================================
print_header "🎉 Setup abgeschlossen!"

echo -e "${GREEN}✓ Installation erfolgreich abgeschlossen!${NC}"
echo ""
echo "Die Multi-Hacker Tool App ist jetzt bereit zum Starten:"
echo ""
echo -e "  ${BLUE}cd $SCRIPT_DIR${NC}"
echo -e "  ${BLUE}python3 src/main.py${NC}"
echo ""
echo "Oder starten Sie die App direkt mit:"
echo ""
echo -e "  ${BLUE}bash start.sh${NC}"
echo ""
echo -e "${BLUE}Verfügbare Tools:${NC}"
echo "  🌐 Network Interfaces - Netzwerkkarten anzeigen"
echo "  🌐 Network Diagnostics - Ping, DNS, Routes"
echo "  📱 Bluetooth - Geräte und Status"
echo "  💻 System Info - RAM, Disk, Uptime"
echo "  🔧 Port Scanner - Mit nmap und Custom Ports"
echo "  🔧 Network Sniffer - TcpDump/TShark/Wireshark Live"
echo "  🔧 Keystroke Logger - Input Event Monitoring"
echo ""
echo -e "${GREEN}Auto-Sudo aktiviert:${NC}"
echo "  ✓ tcpdump, nmap, tshark, wireshark, evtest"
echo "  ✓ Kein Passwort erforderlich!"
echo ""
echo -e "${YELLOW}⚠️  WICHTIG:${NC}"
echo "  Diese Tools sind für Sicherheitstesting auf Ihrem"
echo "  eigenen System konzipiert. Unbefugter Einsatz ist ILLEGAL!"
echo ""
