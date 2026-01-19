#!/bin/bash

################################################################################
# Multi-Hacker Tool - Start Script
# Startet die TUI-Anwendung
# Verwendung: bash start.sh  oder  sudo bash start.sh (für volle Funktionalität)
################################################################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "🚀 Starte Multi-Hacker Tool..."
echo ""

# Check if running as sudo
if [[ $EUID -eq 0 ]]; then
    echo "🔐 Läuft als root (sudo) - Volle Funktionalität aktiviert"
    echo "   ✓ tcpdump (Packet Sniffer)"
    echo "   ✓ nmap Scans"
    echo ""
else
    echo "⚠️  Läuft ohne root - Einige Features könnten eingeschränkt sein:"
    echo "   ✗ tcpdump (Packet Sniffer) - Benötigt sudo"
    echo "   ✗ nmap - Benötigt sudo für vollständige Scans"
    echo ""
    echo "Für volle Funktionalität verwende: sudo bash start.sh"
    echo ""
fi

cd "$SCRIPT_DIR"
python3 src/main.py
