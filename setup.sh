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
print_header "Schritt 2/5: Netzwerk-Tools installieren"

TOOLS=("nmap" "tcpdump" "net-tools" "iproute2" "iputils-ping" "wireless-tools" "wireshark" "tshark")

for tool in "${TOOLS[@]}"; do
    if ! command -v $tool &> /dev/null; then
        print_info "Installiere $tool..."
        apt-get install -y $tool > /dev/null 2>&1
        print_success "$tool installiert"
    else
        print_success "$tool ist bereits installiert"
    fi
done

# ============================================================================
# 3. Python und pip installieren
# ============================================================================
print_header "Schritt 3/5: Python-Umgebung konfigurieren"

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
print_header "Schritt 4/5: Python-Abhängigkeiten installieren"

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    print_info "Installiere Python-Pakete aus requirements.txt..."
    python3 -m pip install -r "$SCRIPT_DIR/requirements.txt" > /dev/null 2>&1
    print_success "Python-Abhängigkeiten installiert"
else
    print_info "requirements.txt nicht gefunden (nicht kritisch)"
fi

# ============================================================================
# 5. Berechtigungen und Finale Checks
# ============================================================================
print_header "Schritt 5/5: Finale Konfiguration"

# Berechtigungen für tcpdump (für nicht-root Benutzer)
if [ -f /usr/bin/tcpdump ]; then
    chmod +s /usr/bin/tcpdump
    print_success "tcpdump Berechtigungen gesetzt"
fi

# Berechtigungen für nmap (optional)
if [ -f /usr/bin/nmap ]; then
    chmod +s /usr/bin/nmap
    print_success "nmap Berechtigungen gesetzt"
fi

# ============================================================================
# Setup abgeschlossen
# ============================================================================
print_header "🎉 Setup abgeschlossen!"

echo -e "${GREEN}Installation erfolgreich!${NC}"
echo ""
echo "Die App ist jetzt bereit zum Starten:"
echo ""
echo -e "  ${BLUE}cd $SCRIPT_DIR${NC}"
echo -e "  ${BLUE}python3 src/main.py${NC}"
echo ""
echo "Oder starten Sie die App direkt mit:"
echo ""
echo -e "  ${BLUE}bash start.sh${NC}"
echo ""
echo "Verfügbare Tools:"
echo "  ✓ Network Interfaces - Netzwerkkarten anzeigen"
echo "  ✓ Network Diagnostics - Ping, DNS, Routes"
echo "  ✓ Bluetooth - Geräte und Status"
echo "  ✓ System Info - RAM, Disk, Uptime"
echo "  ✓ Port Scanner - Mit nmap und Custom Ports"
echo "  ✓ Network Sniffer - Pakete erfassen"
echo ""
print_info "Für volls Funktionalität tcpdump mit sudo nutzen:"
echo "  sudo python3 src/main.py"
echo ""
