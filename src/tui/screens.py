from __future__ import annotations
import curses
from dataclasses import dataclass
from typing import List, Optional, Dict

from config import APP_NAME, VERSION, KEY_HELP, MAX_WIDTH
from tui.widgets import draw_header, draw_footer, menu, draw_text_block, draw_separator, draw_section_header, draw_touch_button_bar, ClickRegion, check_mouse_click, get_safe_width
from netinfo import (
    get_interfaces, get_dns, get_default_route, ping, wifi_status, get_interface_stats,
    get_bluetooth_devices, get_bluetooth_status, get_bluetooth_powered,
    get_system_info, get_disk_usage, get_memory_info, check_open_ports,
    scan_ports_with_nmap, scan_network_with_nmap, get_local_network
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
        self.scan_mode = "local"  # local, localhost, nmap, network
        self.target = "localhost"
        self.custom_ports = "1-100"  # Default port range
        self._load()

    def _load(self) -> None:
        lines: List[str] = []
        
        lines.append("🔍 PORT SCANNER")
        lines.append("─" * 30)
        lines.append("")
        
        if self.scan_mode == "local":
            # Show local system ports
            lines.append("📊 LOCAL SYSTEM PORTS")
            lines.append("(via netstat/ss)")
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
        
        elif self.scan_mode == "nmap":
            # Show nmap scan
            lines.append("🎯 NMAP SCAN (localhost)")
            lines.append(f"Ports: {self.custom_ports}")
            lines.append("─" * 30)
            ports, warnings = scan_ports_with_nmap("localhost", self.custom_ports)
            
            if warnings:
                for w in warnings:
                    lines.append(f"⚠ {w}")
                lines.append("")
                lines.append("💡 To use nmap, install:")
                lines.append("  sudo apt install nmap")
                lines.append("")
            
            if ports:
                for port in ports[:25]:
                    lines.append(port)
            else:
                lines.append("(No open ports detected)")
        
        elif self.scan_mode == "network":
            # Show network scan
            lines.append("🌐 NETWORK HOST DISCOVERY")
            lines.append("(nmap -sn)")
            lines.append("─" * 30)
            network, net_warn = get_local_network()
            lines.append(f"Scanning: {network}")
            lines.append("")
            
            hosts, warnings = scan_network_with_nmap(network)
            
            if warnings:
                for w in warnings:
                    lines.append(f"⚠ {w}")
                lines.append("")
            
            if hosts:
                for host in hosts[:20]:
                    lines.append(host)
            else:
                lines.append("(No hosts found)")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title, self.scan_mode.upper())
        h, w = stdscr.getmaxyx()
        draw_text_block(stdscr, 2, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("Local", 0),
            ("nmap", 1),
            ("Network", 2),
            ("Custom", 3),
            ("← Back", 4),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    self.scan_mode = "local"
                    self._load()
                elif button_clicked == 1:
                    self.scan_mode = "nmap"
                    self._load()
                elif button_clicked == 2:
                    self.scan_mode = "network"
                    self._load()
                elif button_clicked == 3:
                    return ScreenResult(next_screen="custom_port_input")
                elif button_clicked == 4:
                    return ScreenResult(next_screen="hacker")
            except:
                pass
        
        return ScreenResult()


class CustomPortInputScreen(BaseScreen):
    """Virtual keyboard for custom port range input"""
    name = "custom_port_input"
    title = "Custom Port Range"

    def __init__(self):
        self.input_text = "1-100"
        self.keyboard_regions: List[ClickRegion] = []
        self.button_regions: List[ClickRegion] = []
        self.cursor_pos = len(self.input_text)

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        safe_w = get_safe_width(stdscr)
        
        y_pos = 3
        
        # Draw input field
        try:
            stdscr.addstr(y_pos, 2, "Port Range:")
            stdscr.attron(curses.A_REVERSE)
            input_line = f" {self.input_text:<30} "[:safe_w - 2]
            stdscr.addstr(y_pos + 1, 2, input_line)
            stdscr.attroff(curses.A_REVERSE)
        except curses.error:
            pass
        
        y_pos += 3
        
        # Draw keyboard - Numbers
        try:
            stdscr.addstr(y_pos, 2, "Numbers:", curses.A_BOLD)
        except curses.error:
            pass
        
        keyboard_numbers = [
            ["1", "2", "3", "4", "5"],
            ["6", "7", "8", "9", "0"],
        ]
        
        self.keyboard_regions = []
        button_width = max(4, (safe_w - 6) // 5)
        
        for row_idx, row in enumerate(keyboard_numbers):
            row_y = y_pos + 1 + row_idx
            for col_idx, char in enumerate(row):
                x_pos = 2 + (col_idx * button_width)
                
                try:
                    stdscr.attron(curses.A_REVERSE)
                    btn_text = f" {char} ".center(button_width)[:button_width]
                    stdscr.addstr(row_y, x_pos, btn_text)
                    stdscr.attroff(curses.A_REVERSE)
                except curses.error:
                    pass
                
                self.keyboard_regions.append(ClickRegion(
                    y_start=row_y,
                    y_end=row_y,
                    x_start=x_pos,
                    x_end=x_pos + button_width - 1,
                    action_id=int(char)  # 0-9
                ))
        
        y_pos += 3
        
        # Draw special keys
        try:
            stdscr.addstr(y_pos, 2, "Edit:", curses.A_BOLD)
        except curses.error:
            pass
        
        special_keys = ["-", "Backspace", "Clear"]
        special_width = max(8, (safe_w - 6) // len(special_keys))
        
        for key_idx, key in enumerate(special_keys):
            key_y = y_pos + 1
            x_pos = 2 + (key_idx * special_width)
            
            try:
                stdscr.attron(curses.A_REVERSE)
                key_text = f" {key} ".center(special_width)[:special_width]
                stdscr.addstr(key_y, x_pos, key_text)
                stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.keyboard_regions.append(ClickRegion(
                y_start=key_y,
                y_end=key_y,
                x_start=x_pos,
                x_end=x_pos + special_width - 1,
                action_id=100 + key_idx  # 100=dash, 101=backspace, 102=clear
            ))
        
        # Draw action buttons
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("Scan", 0),
            ("← Back", 1),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                
                # Check button bar first
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    # Start nmap with custom ports
                    from tui.screens import PortScannerScreen as PSS
                    pss = PortScannerScreen()
                    pss.scan_mode = "nmap"
                    pss.custom_ports = self.input_text
                    pss._load()
                    # We need to update the parent screen - return to port_scan with updated data
                    return ScreenResult(next_screen="port_scan")
                elif button_clicked == 1:
                    return ScreenResult(next_screen="port_scan")
                
                # Check keyboard
                keyboard_clicked = check_mouse_click(mouse_event, self.keyboard_regions)
                if keyboard_clicked is not None:
                    if keyboard_clicked < 10:  # 0-9
                        self.input_text += str(keyboard_clicked)
                    elif keyboard_clicked == 100:  # Dash
                        if self.input_text and self.input_text[-1] != "-":
                            self.input_text += "-"
                    elif keyboard_clicked == 101:  # Backspace
                        self.input_text = self.input_text[:-1]
                    elif keyboard_clicked == 102:  # Clear
                        self.input_text = ""
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
