from __future__ import annotations
import curses
from dataclasses import dataclass
from typing import List, Optional, Dict

from config import APP_NAME, VERSION, KEY_HELP, MAX_WIDTH
from tui.widgets import draw_header, draw_footer, menu, draw_text_block, draw_separator, draw_section_header, draw_touch_button_bar, ClickRegion, check_mouse_click, get_safe_width
from netinfo import (
    get_interfaces, get_dns, get_default_route, ping, wifi_status, get_interface_stats,
    get_bluetooth_devices, get_bluetooth_status, get_bluetooth_powered,
    get_system_info, get_disk_usage, get_memory_info, check_open_ports
)


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


# ============ MAIN MENU & HUBS ============

class MainMenuScreen(BaseScreen):
    """Main menu with category hubs"""
    name = "main"
    title = f"{APP_NAME}"

    def __init__(self):
        self.items = [
            "🌐 Network Hub",
            "📱 Bluetooth Hub",
            "💻 System Info",
            "🔧 Hacker Tools",
            "⚙️  Settings",
            "❌ Exit",
        ]
        self.menu_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title, f"v{VERSION}")
        h, w = stdscr.getmaxyx()
        y_pos = 3
        
        safe_w = get_safe_width(stdscr)
        try:
            title_line = "☞ SELECT A HUB"
            stdscr.addstr(y_pos, 2, title_line)
        except curses.error:
            pass
        
        # Draw clickable menu items
        self.menu_regions = menu(stdscr, y_pos + 2, 2, safe_w - 4, self.items, 0, touch_mode=True)
        
        draw_footer(stdscr, "Tap to select")

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    screens = ["net_hub", "bt_hub", "sys_info", "hacker", "settings", "quit"]
                    if clicked_item < len(screens):
                        return ScreenResult(next_screen=screens[clicked_item])
            except:
                pass
        
        return ScreenResult()


# ============ NETWORK HUB ============

class NetworkHubScreen(BaseScreen):
    """Network Hub - main category with sub-options"""
    name = "net_hub"
    title = "🌐 Network Hub"

    def __init__(self):
        self.items = [
            "Network Interfaces",
            "Network Diagnostics",
            "WLAN Status",
            "DNS & Routes",
            "← Back",
        ]
        self.menu_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        y_pos = 3
        
        safe_w = get_safe_width(stdscr)
        self.menu_regions = menu(stdscr, y_pos, 2, safe_w - 4, self.items, 0, touch_mode=True)
        
        draw_footer(stdscr, "Tap to select")

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    screens = ["ifaces", "netdiag", "wifi", "dns_routes", "main"]
                    if clicked_item < len(screens):
                        return ScreenResult(next_screen=screens[clicked_item])
            except:
                pass
        
        return ScreenResult()


class InterfacesScreen(BaseScreen):
    name = "ifaces"
    title = "Network Interfaces"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        ifaces, warnings = get_interfaces()
        lines: List[str] = []
        
        for w in warnings:
            lines.append(f"⚠ {w}")
        
        if not ifaces:
            lines.append("❌ No interfaces found")
            self.lines = lines
            return
        
        for iface in ifaces:
            lines.append(f"┌─ {iface.name}")
            lines.append(f"│ State: {iface.state or '?'}")
            lines.append(f"│ MAC: {iface.mac or 'N/A'}")
            
            if iface.ipv4:
                for ip in iface.ipv4:
                    lines.append(f"│ IPv4: {ip}")
            
            if iface.ipv6:
                for ip in iface.ipv6:
                    lines.append(f"│ IPv6: {ip[:40]}")
            
            lines.append(f"└─")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="net_hub")
                elif button_clicked == 1:
                    self._load()
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
            except:
                pass
        
        return ScreenResult()


class NetDiagScreen(BaseScreen):
    name = "netdiag"
    title = "Network Diagnostics"

    def __init__(self):
        self.interfaces: List[str] = []
        self.menu_regions: List[ClickRegion] = []
        self.button_regions: List[ClickRegion] = []
        self.selected_index: int = -1
        self._load_interfaces()

    def _load_interfaces(self) -> None:
        ifaces, _ = get_interfaces()
        self.interfaces = [iface.name for iface in ifaces]
        if not self.interfaces:
            self.interfaces = ["(No interfaces)"]

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        
        safe_w = get_safe_width(stdscr)
        try:
            stdscr.addstr(3, 2, "Click interface:")
        except curses.error:
            pass
        
        self.menu_regions = menu(stdscr, 5, 2, safe_w - 4, self.interfaces, 0, touch_mode=True)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="net_hub")
                
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    self.selected_index = clicked_item
                    return ScreenResult(next_screen="netdiag_detail")
            except:
                pass
        
        return ScreenResult()


class NetDiagDetailScreen(BaseScreen):
    name = "netdiag_detail"
    title = "Diagnostics"

    def __init__(self, interface: str = ""):
        self.interface = interface
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        if not self.interface:
            self.lines = ["No interface selected"]
            return
        
        lines: List[str] = []
        stats, warnings = get_interface_stats(self.interface)
        
        if not stats:
            lines.append(f"❌ Could not load: {self.interface}")
            self.lines = lines
            return
        
        lines.append(f"🔌 {self.interface}")
        lines.append("─" * 30)
        lines.append(f"State: {stats.get('state', '?')}")
        lines.append(f"MAC: {stats.get('mac', 'N/A')}")
        
        ipv4_list = stats.get('ipv4', [])
        if ipv4_list:
            for ip in ipv4_list:
                lines.append(f"IPv4: {ip}")
        
        gw = stats.get('gateway')
        lines.append(f"GW: {gw or 'N/A'}")
        
        if 'ping_ok' in stats:
            ok = stats['ping_ok']
            lines.append(f"Ping: {'✓ OK' if ok else '✗ FAIL'}")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title, self.interface)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="netdiag")
                elif button_clicked == 1:
                    self._load()
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
            lines.append("📶 WLAN Configuration")
            lines.append("─" * 30)
            lines.append("")
            lines.append(f"Status: {err}")
            lines.append("")
            lines.append("Install: sudo apt install iw")
        else:
            lines.append("📶 WLAN Configuration")
            lines.append("─" * 30)
            lines.extend(out.splitlines()[:30])
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="net_hub")
                elif button_clicked == 1:
                    self._load()
            except:
                pass
        
        return ScreenResult()


class DnsRoutesScreen(BaseScreen):
    name = "dns_routes"
    title = "DNS & Routes"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        lines: List[str] = []
        
        # DNS
        lines.append("🔍 DNS SERVERS")
        lines.append("─" * 30)
        dns, dns_warn = get_dns()
        if dns:
            for d in dns:
                lines.append(f"  • {d}")
        else:
            lines.append("  (none found)")
        lines.append("")
        
        # Gateway
        lines.append("🌐 DEFAULT GATEWAY")
        lines.append("─" * 30)
        gw, gw_err = get_default_route()
        if gw:
            lines.append(f"  ✓ {gw}")
        else:
            lines.append(f"  ✗ {gw_err or 'N/A'}")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="net_hub")
                elif button_clicked == 1:
                    self._load()
            except:
                pass
        
        return ScreenResult()


# ============ BLUETOOTH HUB ============

class BluetoothHubScreen(BaseScreen):
    """Bluetooth Hub"""
    name = "bt_hub"
    title = "📱 Bluetooth Hub"

    def __init__(self):
        self.items = [
            "BT Devices",
            "BT Status",
            "← Back",
        ]
        self.menu_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        y_pos = 3
        
        safe_w = get_safe_width(stdscr)
        self.menu_regions = menu(stdscr, y_pos, 2, safe_w - 4, self.items, 0, touch_mode=True)
        
        draw_footer(stdscr, "Tap to select")

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    screens = ["bt_devices", "bt_status", "main"]
                    if clicked_item < len(screens):
                        return ScreenResult(next_screen=screens[clicked_item])
            except:
                pass
        
        return ScreenResult()


class BluetoothDevicesScreen(BaseScreen):
    name = "bt_devices"
    title = "Bluetooth Devices"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        devices, warnings = get_bluetooth_devices()
        lines: List[str] = []
        
        lines.append("📱 PAIRED DEVICES")
        lines.append("─" * 30)
        
        if warnings:
            for w in warnings:
                lines.append(f"⚠ {w}")
            lines.append("")
        
        if devices:
            for dev in devices:
                lines.append(dev[:50])
        else:
            lines.append("(No devices found)")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="bt_hub")
                elif button_clicked == 1:
                    self._load()
            except:
                pass
        
        return ScreenResult()


class BluetoothStatusScreen(BaseScreen):
    name = "bt_status"
    title = "Bluetooth Status"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        out, warnings = get_bluetooth_status()
        lines: List[str] = []
        
        lines.append("📡 BLUETOOTH STATUS")
        lines.append("─" * 30)
        
        if warnings:
            for w in warnings:
                lines.append(f"⚠ {w}")
        else:
            lines.extend(out.splitlines()[:25])
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="bt_hub")
                elif button_clicked == 1:
                    self._load()
            except:
                pass
        
        return ScreenResult()


# ============ SYSTEM INFO ============

class SystemInfoScreen(BaseScreen):
    name = "sys_info"
    title = "💻 System Info"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        lines: List[str] = []
        
        # System Info
        lines.append("📊 SYSTEM INFORMATION")
        lines.append("─" * 30)
        info, _ = get_system_info()
        if info:
            lines.append(f"Hostname: {info.get('hostname', 'N/A')}")
            lines.append(f"Uptime: {info.get('uptime', 'N/A')}")
            lines.append(f"Kernel: {info.get('kernel', 'N/A')}")
            lines.append(f"CPU Cores: {info.get('cpu_cores', 'N/A')}")
        lines.append("")
        
        # Memory
        lines.append("💾 MEMORY")
        lines.append("─" * 30)
        mem, _ = get_memory_info()
        if mem:
            lines.append(f"Total: {mem.get('total', 'N/A')}")
            lines.append(f"Available: {mem.get('available', 'N/A')}")
            lines.append(f"Free: {mem.get('free', 'N/A')}")
        lines.append("")
        
        # Disk
        lines.append("💿 DISK")
        lines.append("─" * 30)
        disk, _ = get_disk_usage()
        if disk:
            lines.append(f"Size: {disk.get('size', 'N/A')}")
            lines.append(f"Used: {disk.get('used', 'N/A')}")
            lines.append(f"Available: {disk.get('available', 'N/A')}")
            lines.append(f"Usage: {disk.get('percent', 'N/A')}")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="main")
                elif button_clicked == 1:
                    self._load()
            except:
                pass
        
        return ScreenResult()


# ============ HACKER TOOLS ============

class HackerToolsScreen(BaseScreen):
    """Hacker Tools menu"""
    name = "hacker"
    title = "🔧 Hacker Tools"

    def __init__(self):
        self.items = [
            "Port Scanner",
            "Network Sniffer",
            "Packet Tools",
            "← Back",
        ]
        self.menu_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        y_pos = 3
        
        safe_w = get_safe_width(stdscr)
        try:
            stdscr.addstr(y_pos, 2, "🔨 Select Tool:")
        except curses.error:
            pass
        
        self.menu_regions = menu(stdscr, y_pos + 2, 2, safe_w - 4, self.items, 0, touch_mode=True)
        
        draw_footer(stdscr, "Tap to select")

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                clicked_item = check_mouse_click(mouse_event, self.menu_regions)
                if clicked_item is not None:
                    screens = ["port_scan", "sniffer", "packets", "main"]
                    if clicked_item < len(screens):
                        return ScreenResult(next_screen=screens[clicked_item])
            except:
                pass
        
        return ScreenResult()


class PortScannerScreen(BaseScreen):
    name = "port_scan"
    title = "Port Scanner"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self._load()

    def _load(self) -> None:
        lines: List[str] = []
        
        lines.append("🔍 OPEN PORTS")
        lines.append("─" * 30)
        ports, warnings = check_open_ports()
        
        if warnings:
            for w in warnings:
                lines.append(f"⚠ {w}")
            lines.append("")
        
        if ports:
            for port in ports[:20]:
                lines.append(port)
        else:
            lines.append("(No listening ports found)")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
                elif button_clicked == 1:
                    self._load()
            except:
                pass
        
        return ScreenResult()


class SnifferScreen(BaseScreen):
    name = "sniffer"
    title = "Network Sniffer"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        
        lines = [
            "🚫 COMING SOON",
            "",
            "Network packet sniffing",
            "will be available in",
            "future versions.",
            "",
            "⚠️  Security notice:",
            "This tool follows ethical",
            "guidelines and Linux",
            "policies."
        ]
        
        draw_text_block(stdscr, 2, 2, w - 4, lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
            except:
                pass
        
        return ScreenResult()


class PacketsScreen(BaseScreen):
    name = "packets"
    title = "Packet Tools"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        
        lines = [
            "🚫 COMING SOON",
            "",
            "Advanced packet tools",
            "will be available in",
            "future versions.",
        ]
        
        draw_text_block(stdscr, 2, 2, w - 4, lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
            except:
                pass
        
        return ScreenResult()


# ============ SETTINGS ============

class SettingsScreen(BaseScreen):
    name = "settings"
    title = "⚙️  Settings"

    def __init__(self):
        self.button_regions: List[ClickRegion] = []
        self.lines = [
            "⚙️  SETTINGS",
            "─" * 30,
            "",
            "Future options:",
            "",
            "• Default Ping Host",
            "• Refresh Interval",
            "• UI Theme",
            "• Log Configuration",
            "",
            "Coming in v0.4.0+",
        ]

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="main")
            except:
                pass
        
        return ScreenResult()
