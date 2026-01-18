from __future__ import annotations
import curses
from dataclasses import dataclass
from typing import List, Optional, Dict

from config import APP_NAME, VERSION, KEY_HELP
from tui.widgets import draw_header, draw_footer, menu, draw_text_block, draw_separator, draw_section_header, draw_touch_button_bar, ClickRegion, check_mouse_click
from netinfo import get_interfaces, get_dns, get_default_route, ping, wifi_status, get_interface_stats


@dataclass
class ScreenResult:
    next_screen: Optional[str] = None
    message: Optional[str] = None


class BaseScreen:
    name: str = "base"
    title: str = ""
    touch_mode: bool = False

    def set_touch_mode(self, enabled: bool) -> None:
        """Enable or disable touch mode for this screen"""
        self.touch_mode = enabled

    def render(self, stdscr) -> None:
        raise NotImplementedError

    def handle_key(self, key: int) -> ScreenResult:
        return ScreenResult()


class MainMenuScreen(BaseScreen):
    name = "main"
    title = f"{APP_NAME}"

    def __init__(self):
        self.items = [
            "Network Interfaces & IPs",
            "Network Diagnostics (Route, DNS, Ping)",
            "WLAN Status",
            "Settings",
            "Exit",
        ]
        self.menu_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title, f"v{VERSION}")
        h, w = stdscr.getmaxyx()
        y_pos = 3
        
        stdscr.addstr(y_pos, 2, "👉 TAP AN OPTION BELOW")
        
        # Draw clickable menu items
        self.menu_regions = menu(stdscr, y_pos + 2, 4, w - 6, self.items, 0, touch_mode=True)
        
        draw_footer(stdscr, "Click on an option to select it")

    def handle_key(self, key: int) -> ScreenResult:
        # Handle mouse events ONLY
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    screens = ["ifaces", "netdiag", "wifi", "settings", "quit"]
                    if clicked_item < len(screens):
                        return ScreenResult(next_screen=screens[clicked_item])
            except:
                pass
        
        return ScreenResult()


class InterfacesScreen(BaseScreen):
    name = "ifaces"
    title = "Network Interfaces & IP Addresses"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        ifaces, warnings = get_interfaces()
        lines: List[str] = []
        
        # Add warnings
        for w in warnings:
            lines.append(f"⚠ WARNING: {w}")
        
        if not ifaces:
            lines.append("")
            lines.append("❌ No network interfaces found or 'ip' command not available.")
            self.lines = lines
            return
        
        lines.append("")
        for iface in ifaces:
            lines.append(f"┌─ Interface: {iface.name}")
            lines.append(f"│  State: {iface.state or '?'} | MTU: {iface.mtu or '?'}")
            lines.append(f"│  MAC: {iface.mac or 'N/A'}")
            
            if iface.ipv4:
                lines.append(f"│  IPv4 Addresses:")
                for ip in iface.ipv4:
                    lines.append(f"│    • {ip}")
            else:
                lines.append(f"│  IPv4: (none)")
            
            if iface.ipv6:
                lines.append(f"│  IPv6 Addresses:")
                for ip in iface.ipv6:
                    lines.append(f"│    • {ip}")
            
            lines.append(f"└─")
            lines.append("")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
            ("Quit", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        # Handle mouse events ONLY
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:  # Back
                    return ScreenResult(next_screen="main")
                elif button_clicked == 1:  # Refresh
                    self._load()
                    return ScreenResult()
                elif button_clicked == 2:  # Quit
                    return ScreenResult(next_screen="quit")
            except:
                pass
        
        return ScreenResult()


class NetDiagScreen(BaseScreen):
    name = "netdiag"
    title = "Network Diagnostics - Select Interface"

    def __init__(self):
        self.interfaces: List[str] = []
        self.menu_regions: List[ClickRegion] = []
        self.button_regions: List[ClickRegion] = []
        self.selected_index: int = -1
        self._load_interfaces()

    def _load_interfaces(self) -> None:
        """Load list of network interfaces"""
        ifaces, _ = get_interfaces()
        self.interfaces = [iface.name for iface in ifaces]
        if not self.interfaces:
            self.interfaces = ["(No interfaces found)"]

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        
        stdscr.addstr(3, 2, "👉 Click on a network interface to diagnose:")
        self.menu_regions = menu(stdscr, 5, 4, w - 6, self.interfaces, 0, touch_mode=True)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        # Handle mouse ONLY
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                # Check button bar first
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:  # Back
                    return ScreenResult(next_screen="main")
                # Check menu items
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    self.selected_index = clicked_item
                    return ScreenResult(next_screen="netdiag_detail")
            except:
                pass
        
        return ScreenResult()


class NetDiagDetailScreen(BaseScreen):
    name = "netdiag_detail"
    title = "Network Diagnostics - Interface Details"

    def __init__(self, interface: str = ""):
        self.interface = interface
        self.lines: List[str] = []
        self.stats: Dict = {}
        self.button_regions: List[ClickRegion] = []
        self._load()

    def set_interface(self, interface: str) -> None:
        """Set the interface to diagnose"""
        self.interface = interface
        self._load()

    def _load(self) -> None:
        """Load diagnostics for the selected interface"""
        if not self.interface:
            self.lines = ["No interface selected"]
            return
        
        lines: List[str] = []
        self.stats, warnings = get_interface_stats(self.interface)
        
        if not self.stats:
            lines.append(f"❌ Could not load stats for {self.interface}")
            for w in warnings:
                lines.append(f"  ⚠ {w}")
            self.lines = lines
            return
        
        # Show interface info
        lines.append("═══════════════════════════════════════════")
        lines.append(f"🔌 INTERFACE: {self.stats.get('name', '?')}")
        lines.append("═══════════════════════════════════════════")
        lines.append(f"  State: {self.stats.get('state', '?')}")
        lines.append(f"  MTU: {self.stats.get('mtu', '?')}")
        lines.append(f"  MAC: {self.stats.get('mac', 'N/A')}")
        lines.append("")
        
        # Show IP addresses
        lines.append("📍 IP ADDRESSES")
        ipv4_list = self.stats.get('ipv4', [])
        if ipv4_list:
            for ip in ipv4_list:
                lines.append(f"  IPv4: {ip}")
        else:
            lines.append(f"  IPv4: (none)")
        
        ipv6_list = self.stats.get('ipv6', [])
        if ipv6_list:
            for ip in ipv6_list:
                lines.append(f"  IPv6: {ip}")
        lines.append("")
        
        # Show gateway
        lines.append("🌐 GATEWAY")
        gw = self.stats.get('gateway')
        if gw:
            lines.append(f"  ✓ {gw}")
        else:
            lines.append(f"  ✗ Not reachable from this interface")
        lines.append("")
        
        # Show DNS (global)
        lines.append("🔍 DNS SERVERS")
        dns, dns_warn = get_dns()
        for w in dns_warn:
            lines.append(f"  ⚠ {w}")
        if dns:
            for d in dns:
                lines.append(f"  • {d}")
        else:
            lines.append("  (none found)")
        lines.append("")
        
        # Show ping test via this interface
        lines.append("📡 CONNECTIVITY TEST (Ping 1.1.1.1)")
        if 'ping_ok' in self.stats:
            ok = self.stats['ping_ok']
            status = "✓ ONLINE" if ok else "✗ OFFLINE"
            lines.append(f"  Status: {status}")
            lines.append("")
            ping_output = self.stats.get('ping_output', '')
            for ln in ping_output.splitlines()[:4]:
                lines.append(f"  {ln}")
        else:
            lines.append("  (No IP address - ping not possible)")
        
        # Add warnings
        if warnings:
            lines.append("")
            lines.append("⚠️  WARNINGS")
            for w in warnings:
                lines.append(f"  • {w}")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title, self.interface)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
            ("Quit", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        # Handle mouse events ONLY
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:  # Back
                    return ScreenResult(next_screen="netdiag")
                elif button_clicked == 1:  # Refresh
                    self._load()
                    return ScreenResult()
                elif button_clicked == 2:  # Quit
                    return ScreenResult(next_screen="quit")
            except:
                pass
        
        return ScreenResult()


class WifiScreen(BaseScreen):
    name = "wifi"
    title = "WLAN Status"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        out, err = wifi_status()
        lines: List[str] = []
        if err:
            lines.append("ℹ️  INFO: WLAN Information")
            lines.append("─" * 40)
            lines.append("")
            lines.append(f"Status: {err}")
            lines.append("")
            lines.append("To enable this feature, install on Raspberry Pi:")
            lines.append("  $ sudo apt install iw")
        else:
            lines.append("📶 WLAN CONFIGURATION (via 'iw dev')")
            lines.append("─" * 40)
            lines.append("")
            lines.extend(out.splitlines()[:200])
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
            ("Quit", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        # Handle mouse events ONLY
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:  # Back
                    return ScreenResult(next_screen="main")
                elif button_clicked == 1:  # Refresh
                    self._load()
                    return ScreenResult()
                elif button_clicked == 2:  # Quit
                    return ScreenResult(next_screen="quit")
            except:
                pass
        
        return ScreenResult()


class SettingsScreen(BaseScreen):
    name = "settings"
    title = "Settings & Configuration"

    def __init__(self):
        self.button_regions: List[ClickRegion] = []
        self.lines = [
            "",
            "⚙️  SETTINGS & CONFIGURATION",
            "─" * 40,
            "",
            "Future settings that can be configured here:",
            "",
            "  • Default Ping Host / Target",
            "  • Refresh Interval (auto-update)",
            "  • UI Theme & Color Options",
            "  • Log File Configuration",
            "  • Network Interface Filters",
            "",
            "Coming in version 0.3.0+",
            "",
            "Note: Security features (packet sniffing, handshake",
            "capture) will NOT be implemented in this tool.",
        ]

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("Quit", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        # Handle mouse events ONLY
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:  # Back
                    return ScreenResult(next_screen="main")
                elif button_clicked == 1:  # Quit
                    return ScreenResult(next_screen="quit")
            except:
                pass
        
        return ScreenResult()