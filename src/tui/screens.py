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
    scan_ports_with_nmap, scan_network_with_nmap, get_local_network, sniff_packets,
    sniff_packets_with_tshark, check_tshark_available,
    open_wireshark, check_wireshark_available,
    monitor_keyboard_events, get_keyboard_devices, capture_keyboard_events,
    list_usb_devices, monitor_usb_keyboard_events, intercept_usb_keyboard
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
            ("🔄 Sync", 1),
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
            ("🔄 Sync", 1),
            ("Home", 2),
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
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
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
            ("🔄 Sync", 1),
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
            ("🔄 Sync", 1),
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
            ("🔄 Sync", 1),
            ("Home", 2),
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
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
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
            ("🔄 Sync", 1),
            ("Home", 2),
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
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
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
            ("🔄 Sync", 1),
            ("Home", 2),
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
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
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
            "Keystroke Logger",
            "USB Keyboard Interceptor",
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
                    screens = ["port_scan", "sniffer", "keylogger", "usb_interceptor", "packets", "main"]
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
        self.scan_mode_buttons: List[ClickRegion] = []
        self.interface_buttons: List[ClickRegion] = []
        self.scan_mode = "local"  # local, nmap, network
        self.custom_ports = "1-1000"  # Default port range (not too many)
        self.selected_interface = None
        self.interfaces: List[str] = []
        self._load_interfaces()
        self._load()

    def _load_interfaces(self) -> None:
        """Load available network interfaces"""
        ifaces, _ = get_interfaces()
        self.interfaces = [iface.name for iface in ifaces]
        if not self.interfaces:
            self.interfaces = ["all"]
        if not self.selected_interface:
            self.selected_interface = self.interfaces[0]

    def _load(self) -> None:
        lines: List[str] = []
        
        # Check if we came from CustomPortInputScreen with custom ports
        if CustomPortInputScreen.custom_ports_to_scan != "1-1000":
            self.scan_mode = "nmap"
            self.custom_ports = CustomPortInputScreen.custom_ports_to_scan
            self.selected_interface = CustomPortInputScreen.current_interface
            CustomPortInputScreen.custom_ports_to_scan = "1-1000"  # Reset
        
        # Show interface info
        lines.append(f"┌─ INTERFACE: {self.selected_interface}")
        
        # Get interface details
        ifaces, _ = get_interfaces()
        for iface in ifaces:
            if iface.name == self.selected_interface:
                lines.append(f"│ State: {iface.state or '?'}")
                lines.append(f"│ MAC: {iface.mac or 'N/A'}")
                if iface.ipv4:
                    for ip in iface.ipv4:
                        lines.append(f"│ IPv4: {ip}")
                break
        
        lines.append("└─")
        lines.append("")
        
        if self.scan_mode == "local":
            # Show local system ports
            lines.append("┌─ LOCAL PORTS (netstat)")
            ports, warnings = check_open_ports()
            
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
                lines.append("│")
            
            if ports:
                for port in ports[:20]:
                    lines.append(f"│ {port}")
            else:
                lines.append("│ (No listening ports)")
            
            lines.append("└─")
        
        elif self.scan_mode == "nmap":
            # Show nmap scan with custom ports on selected interface
            lines.append(f"┌─ NMAP SCAN | {self.selected_interface} | Range: {self.custom_ports}")
            
            # Get the network range for the selected interface
            if self.selected_interface == "all" or self.selected_interface == "localhost":
                # Scan localhost
                target = "localhost"
                interface = None
            else:
                # Get the local network range for this interface
                network, net_warn = get_local_network()
                target = network if network else "localhost"
                interface = self.selected_interface
            
            ports, warnings = scan_ports_with_nmap(target, self.custom_ports, interface)
            
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
                lines.append("│")
                lines.append("│ 💡 Install nmap:")
                lines.append("│ sudo apt install nmap")
                lines.append("│")
            
            if ports:
                for port in ports[:25]:
                    lines.append(f"│ {port}")
            else:
                lines.append("│ (No open ports detected)")
            
            lines.append("└─")
        
        elif self.scan_mode == "network":
            # Show network scan
            network, net_warn = get_local_network()
            lines.append(f"┌─ NETWORK DISCOVERY | {self.selected_interface} | {network}")
            lines.append("│")
            
            # Pass interface to nmap
            interface = None if self.selected_interface in ["all", "localhost"] else self.selected_interface
            hosts, warnings = scan_network_with_nmap(network, interface)
            
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
                lines.append("│")
            
            if hosts:
                for host in hosts[:20]:
                    lines.append(f"│ {host}")
            else:
                lines.append("│ (No hosts found)")
            
            lines.append("└─")
        
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        safe_w = get_safe_width(stdscr)
        
        y_pos = 2
        
        # Draw interface selector
        try:
            stdscr.addstr(y_pos, 2, "┌─ SELECT INTERFACE", curses.A_BOLD)
            y_pos += 1
        except curses.error:
            pass
        
        self.interface_buttons = []
        button_width = max(8, (safe_w - 6) // len(self.interfaces))
        
        for idx, iface in enumerate(self.interfaces):
            x_pos = 2 + (idx * (button_width + 1))
            marker = "✓" if iface == self.selected_interface else " "
            
            try:
                if iface == self.selected_interface:
                    stdscr.attron(curses.A_REVERSE)
                btn_text = f" {marker}{iface} ".center(button_width)[:button_width]
                stdscr.addstr(y_pos, x_pos, btn_text)
                if iface == self.selected_interface:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.interface_buttons.append(ClickRegion(
                y_start=y_pos,
                y_end=y_pos,
                x_start=x_pos,
                x_end=x_pos + button_width - 1,
                action_id=idx
            ))
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        y_pos += 3
        
        # Draw scan mode selector
        try:
            stdscr.addstr(y_pos, 2, "┌─ SELECT SCAN MODE", curses.A_BOLD)
            y_pos += 1
        except curses.error:
            pass
        
        modes = [("Local", "local"), ("nmap", "nmap"), ("Network", "network"), ("Custom", None)]
        self.scan_mode_buttons = []
        mode_width = max(8, (safe_w - 6) // len(modes))
        
        for idx, (label, mode_val) in enumerate(modes):
            x_pos = 2 + (idx * (mode_width + 1))
            is_selected = (mode_val == self.scan_mode) if mode_val else False
            marker = "✓" if is_selected else " "
            
            try:
                if is_selected:
                    stdscr.attron(curses.A_REVERSE)
                btn_text = f" {marker}{label} ".center(mode_width)[:mode_width]
                stdscr.addstr(y_pos, x_pos, btn_text)
                if is_selected:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.scan_mode_buttons.append(ClickRegion(
                y_start=y_pos,
                y_end=y_pos,
                x_start=x_pos,
                x_end=x_pos + mode_width - 1,
                action_id=idx
            ))
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        y_pos += 2
        draw_text_block(stdscr, y_pos, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Sync", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                
                # Check interface buttons
                iface_clicked = check_mouse_click(mouse_event, self.interface_buttons)
                if iface_clicked is not None:
                    self.selected_interface = self.interfaces[iface_clicked]
                    self._load()
                    return ScreenResult()
                
                # Check scan mode buttons
                mode_clicked = check_mouse_click(mouse_event, self.scan_mode_buttons)
                if mode_clicked is not None:
                    if mode_clicked == 3:  # Custom
                        # Pass selected_interface to CustomPortInputScreen
                        from tui.app import TuiApp
                        # Store in a class variable for retrieval
                        CustomPortInputScreen.current_interface = self.selected_interface
                        return ScreenResult(next_screen="custom_port_input")
                    else:
                        modes = ["local", "nmap", "network"]
                        self.scan_mode = modes[mode_clicked]
                        self._load()
                    return ScreenResult()
                
                # Check bottom buttons
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
                elif button_clicked == 1:
                    self._load_interfaces()
                    self._load()
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
            except:
                pass
        
        return ScreenResult()


class CustomPortInputScreen(BaseScreen):
    """Virtual keyboard for custom port range input"""
    name = "custom_port_input"
    title = "Custom Port Range"
    
    # Class variable to store interface from PortScannerScreen
    current_interface = "localhost"
    custom_ports_to_scan = "1-1000"

    def __init__(self):
        # Always use the class variable current_interface (set by PortScannerScreen)
        self.input_text = CustomPortInputScreen.custom_ports_to_scan
        self.keyboard_regions: List[ClickRegion] = []
        self.button_regions: List[ClickRegion] = []
        self.selected_interface = CustomPortInputScreen.current_interface

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title, f"({self.selected_interface})")
        h, w = stdscr.getmaxyx()
        safe_w = get_safe_width(stdscr)
        
        y_pos = 3
        self.keyboard_regions = []
        
        # Draw interface info
        try:
            stdscr.addstr(y_pos, 2, f"┌─ INTERFACE: {self.selected_interface}")
            y_pos += 1
        except curses.error:
            pass
        
        # Draw input field with box
        try:
            stdscr.addstr(y_pos, 2, "┌─ PORT RANGE")
            stdscr.addstr(y_pos + 1, 2, f"│ ")
            stdscr.attron(curses.A_REVERSE)
            input_display = f" {self.input_text:<40} "[:(safe_w - 6)]
            stdscr.addstr(y_pos + 1, 4, input_display)
            stdscr.attroff(curses.A_REVERSE)
            stdscr.addstr(y_pos + 2, 2, f"└─ Examples: 1-100, 22,80,443")
        except curses.error:
            pass
        
        y_pos += 5
        
        # Draw keyboard grid - Numbers 0-9
        keyboard_numbers = [
            ["1", "2", "3", "4", "5"],
            ["6", "7", "8", "9", "0"],
        ]
        
        button_width = 6
        
        try:
            stdscr.addstr(y_pos, 2, "┌─ KEYBOARD")
            y_pos += 1
        except curses.error:
            pass
        
        # Numbers rows
        for row_idx, row in enumerate(keyboard_numbers):
            try:
                stdscr.addstr(y_pos + row_idx, 2, "│")
            except curses.error:
                pass
            
            for col_idx, char in enumerate(row):
                x_pos = 4 + (col_idx * (button_width + 1))
                row_y = y_pos + row_idx
                
                try:
                    stdscr.attron(curses.A_REVERSE)
                    btn_text = f" {char} ".center(button_width)
                    stdscr.addstr(row_y, x_pos, btn_text)
                    stdscr.attroff(curses.A_REVERSE)
                except curses.error:
                    pass
                
                self.keyboard_regions.append(ClickRegion(
                    y_start=row_y,
                    y_end=row_y,
                    x_start=x_pos,
                    x_end=x_pos + button_width - 1,
                    action_id=int(char)
                ))
        
        y_pos += 2
        
        # Special keys row
        special_keys = [("─", 100), ("⌫", 101), ("C", 102)]
        
        try:
            stdscr.addstr(y_pos, 2, "│")
        except curses.error:
            pass
        
        for key_idx, (key_char, key_id) in enumerate(special_keys):
            x_pos = 4 + (key_idx * (button_width + 1))
            
            try:
                stdscr.attron(curses.A_REVERSE)
                if key_char == "⌫":
                    btn_text = "BACK".center(button_width)
                elif key_char == "C":
                    btn_text = "CLR".center(button_width)
                else:
                    btn_text = f" {key_char} ".center(button_width)
                stdscr.addstr(y_pos, x_pos, btn_text)
                stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.keyboard_regions.append(ClickRegion(
                y_start=y_pos,
                y_end=y_pos,
                x_start=x_pos,
                x_end=x_pos + button_width - 1,
                action_id=key_id
            ))
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        # Draw action buttons
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("✓ Go", 0),
            ("← Back", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                
                # Check button bar first
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    # Go - save ports and interface, return to port_scan
                    CustomPortInputScreen.custom_ports_to_scan = self.input_text
                    CustomPortInputScreen.current_interface = self.selected_interface
                    return ScreenResult(next_screen="port_scan")
                elif button_clicked == 1:
                    return ScreenResult(next_screen="port_scan")
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
                
                # Check keyboard
                keyboard_clicked = check_mouse_click(mouse_event, self.keyboard_regions)
                if keyboard_clicked is not None:
                    if keyboard_clicked < 10:  # 0-9
                        self.input_text += str(keyboard_clicked)
                    elif keyboard_clicked == 100:  # Dash
                        if self.input_text and self.input_text[-1] != "-" and self.input_text[-1] != ",":
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
        import threading
        import queue
        
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self.interface_buttons: List[ClickRegion] = []
        self.action_buttons: List[ClickRegion] = []
        self.packet_count = 20
        self.selected_interface = None
        self.selected_mode = 0  # 0=tcpdump, 1=tshark, 2=wireshark
        self.interfaces: List[str] = []
        self.tshark_available = check_tshark_available()
        self.wireshark_available = check_wireshark_available()
        
        # Live packet capture for TShark
        self.live_packets: List[str] = []
        self.live_capture_active = False
        self.packet_queue = queue.Queue()
        self.capture_thread = None
        
        self._load_interfaces()
        self._load()

    def _load_interfaces(self) -> None:
        """Load available network interfaces"""
        ifaces, _ = get_interfaces()
        self.interfaces = [iface.name for iface in ifaces]
        if not self.interfaces:
            self.interfaces = ["eth0"]
        if not self.selected_interface:
            self.selected_interface = self.interfaces[0]

    def _start_live_capture(self) -> None:
        """Start background thread for live packet capture"""
        import threading
        
        if self.live_capture_active or self.selected_mode != 1:
            return
        
        self.live_capture_active = True
        self.capture_thread = threading.Thread(target=self._live_capture_worker, daemon=True)
        self.capture_thread.start()

    def _stop_live_capture(self) -> None:
        """Stop background live capture thread"""
        self.live_capture_active = False

    def _live_capture_worker(self) -> None:
        """Background worker that continuously captures packets"""
        import time
        
        while self.live_capture_active:
            try:
                # Capture 5 packets every 1 second for live updates
                packets, warnings = sniff_packets_with_tshark(
                    self.selected_interface, 
                    packet_count=5
                )
                
                if packets and packets[0] != "(No packets captured)":
                    # Add new packets to queue
                    for packet in packets:
                        self.packet_queue.put(packet)
                
                # Keep only last 50 packets
                while self.packet_queue.qsize() > 50:
                    try:
                        self.packet_queue.get_nowait()
                    except:
                        break
                
                time.sleep(1)  # Update every second
            except Exception as e:
                time.sleep(1)

    def _update_live_packets(self) -> None:
        """Update live_packets from queue"""
        import queue as queue_module
        
        # Drain all packets from queue
        packets_list = []
        try:
            while True:
                packets_list.append(self.packet_queue.get_nowait())
        except queue_module.Empty:
            pass
        
        # Keep newest 25 packets
        self.live_packets = (self.live_packets + packets_list)[-25:]

    def _load(self) -> None:
        lines: List[str] = []
        
        # Show interface and settings
        mode_name = ["TcpDump", "TShark", "Wireshark"][self.selected_mode]
        
        if self.selected_mode == 1:
            # TShark Live mode
            self._update_live_packets()
            lines.append(f"┌─ SNIFFER | {self.selected_interface} | LIVE | TShark")
            lines.append("│ (Updates every second)")
            lines.append("│")
            
            if self.live_packets:
                for packet in self.live_packets[-20:]:
                    lines.append(f"│ {packet}")
            else:
                lines.append("│ (Waiting for packets...)")
        else:
            # Static capture modes
            lines.append(f"┌─ SNIFFER | {self.selected_interface} | {self.packet_count} packets | {mode_name}")
            lines.append("│")
            
            # Run sniffer based on selected mode
            if self.selected_mode == 0:
                # TcpDump mode
                packets, warnings = sniff_packets(self.selected_interface, self.packet_count)
            elif self.selected_mode == 1:
                # TShark mode (this shouldn't happen now, but keep for safety)
                packets, warnings = sniff_packets_with_tshark(self.selected_interface, self.packet_count)
            else:
                packets, warnings = [], []
            
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
                lines.append("│")
            
            if packets:
                for packet in packets[:25]:
                    lines.append(f"│ {packet}")
            else:
                lines.append("│ (No packets captured)")
        
        lines.append("└─")
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        safe_w = get_safe_width(stdscr)
        
        y_pos = 2
        
        # Draw interface selector
        try:
            stdscr.addstr(y_pos, 2, "┌─ SELECT INTERFACE", curses.A_BOLD)
            y_pos += 1
        except curses.error:
            pass
        
        self.interface_buttons = []
        button_width = max(8, (safe_w - 6) // len(self.interfaces))
        
        for idx, iface in enumerate(self.interfaces):
            x_pos = 2 + (idx * (button_width + 1))
            marker = "✓" if iface == self.selected_interface else " "
            
            try:
                if iface == self.selected_interface:
                    stdscr.attron(curses.A_REVERSE)
                btn_text = f" {marker}{iface} ".center(button_width)[:button_width]
                stdscr.addstr(y_pos, x_pos, btn_text)
                if iface == self.selected_interface:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.interface_buttons.append(ClickRegion(
                y_start=y_pos,
                y_end=y_pos,
                x_start=x_pos,
                x_end=x_pos + button_width - 1,
                action_id=idx
            ))
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        y_pos += 3
        
        # Draw capture mode buttons
        try:
            stdscr.addstr(y_pos, 2, "┌─ CAPTURE MODE", curses.A_BOLD)
            y_pos += 1
        except curses.error:
            pass
        
        self.action_buttons = []
        action_x = 2
        button_idx = 0  # Track actual clickable buttons
        
        # Mode buttons
        modes = [
            ("📊 TcpDump", True),      # Always available
            ("🔍 TShark", self.tshark_available),
            ("🖥️ Wireshark", self.wireshark_available),
        ]
        
        for mode_idx, (label, available) in enumerate(modes):
            if available:
                is_selected = (mode_idx == self.selected_mode)
                button_width = 14
                try:
                    if is_selected:
                        stdscr.attron(curses.A_REVERSE)
                    # Center the label in fixed width button
                    btn_text = label.center(button_width)[:button_width]
                    stdscr.addstr(y_pos, action_x, btn_text)
                    if is_selected:
                        stdscr.attroff(curses.A_REVERSE)
                except curses.error:
                    pass
                
                self.action_buttons.append(ClickRegion(
                    y_start=y_pos,
                    y_end=y_pos,
                    x_start=action_x,
                    x_end=action_x + button_width - 1,
                    action_id=mode_idx  # Store the mode index
                ))
                action_x += button_width + 1
            else:
                # Unavailable mode shown in gray
                button_width = 14
                try:
                    stdscr.attron(curses.A_DIM)
                    btn_text = label.center(button_width)[:button_width]
                    stdscr.addstr(y_pos, action_x, btn_text)
                    stdscr.attroff(curses.A_DIM)
                except curses.error:
                    pass
                action_x += button_width + 1
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        y_pos += 3
        draw_text_block(stdscr, y_pos, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Sync", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                
                # Check interface buttons
                iface_clicked = check_mouse_click(mouse_event, self.interface_buttons)
                if iface_clicked is not None:
                    self._stop_live_capture()
                    self.selected_interface = self.interfaces[iface_clicked]
                    self._load()
                    self._start_live_capture()
                    return ScreenResult()
                
                # Check action buttons
                action_clicked = check_mouse_click(mouse_event, self.action_buttons)
                if action_clicked is not None:
                    if action_clicked == 0:
                        # TcpDump mode
                        self._stop_live_capture()
                        self.selected_mode = 0
                        self._load()
                        return ScreenResult()
                    elif action_clicked == 1 and self.tshark_available:
                        # TShark mode (with LIVE capture)
                        self.selected_mode = 1
                        self.live_packets = []  # Reset packets
                        self._load()
                        self._start_live_capture()  # Start background thread
                        return ScreenResult()
                    elif action_clicked == 2 and self.wireshark_available:
                        # Wireshark GUI mode
                        self._stop_live_capture()
                        rc = open_wireshark(self.selected_interface)
                        if rc == 0:
                            return ScreenResult()
                        else:
                            return ScreenResult(message="Wireshark launch failed")
                
                # Check bottom buttons
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    self._stop_live_capture()
                    return ScreenResult(next_screen="hacker")
                elif button_clicked == 1:
                    # Sync - reload data
                    if self.selected_mode == 1:
                        # TShark live: just update display
                        self._load()
                    else:
                        # Static modes: reload
                        self._load()
                elif button_clicked == 2:
                    self._stop_live_capture()
                    return ScreenResult(next_screen="main")
            except:
                pass
        
        return ScreenResult()


class KeyloggerScreen(BaseScreen):
    name = "keylogger"
    title = "⌨️ Keystroke Logger"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self.mode_buttons: List[ClickRegion] = []
        self.device_buttons: List[ClickRegion] = []
        self.mode = 0  # 0=info, 1=devices, 2=capture
        self.devices: List[str] = []
        self.selected_device = None
        self._load()

    def _load(self) -> None:
        lines: List[str] = []
        lines.append("┌─ KEYSTROKE LOGGER")
        lines.append("│")
        lines.append("│ ⚠️  SECURITY NOTICE:")
        lines.append("│ This tool captures keyboard events for authorized")
        lines.append("│ security testing on YOUR OWN system only.")
        lines.append("│")
        lines.append("│ ✓ Educational/Testing purposes")
        lines.append("│ ✓ System monitoring")
        lines.append("│ ✗ Unauthorized surveillance is ILLEGAL")
        lines.append("│")
        
        if self.mode == 0:
            # Info mode
            lines.append("│ Steps:")
            lines.append("│ 1. Click 'List Devices' to see input devices")
            lines.append("│ 2. Select a device to monitor")
            lines.append("│ 3. Click 'Start Capture' to record events")
            lines.append("│")
            lines.append("│ Uses: evtest (kernel input event monitoring)")
        
        elif self.mode == 1:
            # Device list mode
            devices, warnings = get_keyboard_devices()
            
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
            
            lines.append("│")
            lines.append("│ Available Devices:")
            
            if devices:
                self.devices = devices
                for i, dev in enumerate(devices[:10]):
                    marker = "→" if dev == self.selected_device else " "
                    lines.append(f"│ {marker} {dev[:70]}")
            else:
                lines.append("│ (No devices found)")
                lines.append("│ Try: sudo evtest")
        
        elif self.mode == 2:
            # Capture mode
            if self.selected_device:
                lines.append(f"│ Device: {self.selected_device[:60]}")
                lines.append("│")
                lines.append("│ Capturing keyboard events (5 sec)...")
                
                # Extract device path from selected_device
                device_path = self.selected_device.split(":")[0].strip()
                events, warnings = capture_keyboard_events(device_path, duration=5)
                
                if warnings:
                    lines.append("│")
                    for w in warnings:
                        lines.append(f"│ ⚠ {w}")
                
                if events:
                    lines.append("│")
                    for event in events[:15]:
                        lines.append(f"│ {event}")
                else:
                    lines.append("│ (No events captured)")
            else:
                lines.append("│ No device selected")
        
        lines.append("└─")
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        safe_w = get_safe_width(stdscr)
        
        y_pos = 2
        
        # Draw mode buttons
        try:
            stdscr.addstr(y_pos, 2, "┌─ MODE", curses.A_BOLD)
            y_pos += 1
        except curses.error:
            pass
        
        self.mode_buttons = []
        modes = [
            ("ℹ️ Info", 0),
            ("📋 List", 1),
            ("⏹️ Capture", 2),
        ]
        
        action_x = 2
        for label, mode_idx in modes:
            is_selected = (mode_idx == self.mode)
            button_width = 12
            try:
                if is_selected:
                    stdscr.attron(curses.A_REVERSE)
                btn_text = label.center(button_width)[:button_width]
                stdscr.addstr(y_pos, action_x, btn_text)
                if is_selected:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.mode_buttons.append(ClickRegion(
                y_start=y_pos,
                y_end=y_pos,
                x_start=action_x,
                x_end=action_x + button_width - 1,
                action_id=mode_idx
            ))
            action_x += button_width + 1
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        y_pos += 3
        draw_text_block(stdscr, y_pos, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                
                # Check mode buttons
                mode_clicked = check_mouse_click(mouse_event, self.mode_buttons)
                if mode_clicked is not None:
                    self.mode = mode_clicked
                    self._load()
                    return ScreenResult()
                
                # Check device buttons
                dev_clicked = check_mouse_click(mouse_event, self.device_buttons)
                if dev_clicked is not None and dev_clicked < len(self.devices):
                    self.selected_device = self.devices[dev_clicked]
                    return ScreenResult()
                
                # Check bottom buttons
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
                elif button_clicked == 1:
                    self._load()
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
            except:
                pass
        
        return ScreenResult()


class USBKeyboardInterceptorScreen(BaseScreen):
    name = "usb_interceptor"
    title = "🔌 USB Keyboard Interceptor"

    def __init__(self):
        self.lines: List[str] = []
        self.button_regions: List[ClickRegion] = []
        self.mode_buttons: List[ClickRegion] = []
        self.device_buttons: List[ClickRegion] = []
        self.mode = 0  # 0=info, 1=detect, 2=monitor, 3=intercept
        self.devices: List[str] = []
        self.selected_device = None
        self._load()

    def _load(self) -> None:
        lines: List[str] = []
        lines.append("┌─ USB KEYBOARD INTERCEPTOR")
        lines.append("│")
        lines.append("│ ⚠️  ADVANCED SECURITY TOOL:")
        lines.append("│ USB Keyboard Traffic Interception")
        lines.append("│")
        lines.append("│ ⚠️  LEGAL WARNING:")
        lines.append("│ - Unauthorized interception is ILLEGAL")
        lines.append("│ - Use only on systems you own/control")
        lines.append("│ - Educational/authorized testing ONLY")
        lines.append("│")
        
        if self.mode == 0:
            # Info mode
            lines.append("│ FEATURES:")
            lines.append("│ • Auto-detect USB keyboards")
            lines.append("│ • Live keystroke monitoring")
            lines.append("│ • USB device enumeration")
            lines.append("│ • HID event capture")
            lines.append("│")
            lines.append("│ STEPS:")
            lines.append("│ 1. Click 'Detect' to find USB keyboards")
            lines.append("│ 2. Click 'Monitor' to watch keystrokes")
            lines.append("│ 3. View all captured keys live")
        
        elif self.mode == 1:
            # Detect mode
            devices, warnings = list_usb_devices()
            
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
                lines.append("│")
            
            lines.append("│ USB DEVICES:")
            
            if devices:
                self.devices = devices
                for dev in devices[:15]:
                    lines.append(f"│ {dev[:70]}")
            else:
                lines.append("│ (No USB devices found)")
                lines.append("│ Connect a USB keyboard")
        
        elif self.mode == 2:
            # Monitor mode
            results, warnings = monitor_usb_keyboard_events()
            
            lines.append("│")
            if warnings:
                for w in warnings:
                    lines.append(f"│ ⚠ {w}")
                lines.append("│")
            
            for line in results:
                lines.append(f"│ {line[:70]}")
        
        elif self.mode == 3:
            # Intercept mode
            if self.selected_device:
                lines.append(f"│ Intercepting: {self.selected_device[:60]}")
                lines.append("│")
                
                # Extract device path
                device_path = self.selected_device.split(":")[0].strip() if ":" in self.selected_device else "/dev/input/event0"
                
                results, warnings = intercept_usb_keyboard(device_path)
                
                if warnings:
                    lines.append("│")
                    for w in warnings:
                        lines.append(f"│ ⚠ {w}")
                
                lines.append("│")
                for line in results:
                    lines.append(f"│ {line[:70]}")
            else:
                lines.append("│ No device selected for interception")
        
        lines.append("└─")
        self.lines = lines

    def render(self, stdscr) -> None:
        stdscr.clear()
        draw_header(stdscr, self.title)
        h, w = stdscr.getmaxyx()
        safe_w = get_safe_width(stdscr)
        
        y_pos = 2
        
        # Draw mode buttons
        try:
            stdscr.addstr(y_pos, 2, "┌─ MODE", curses.A_BOLD)
            y_pos += 1
        except curses.error:
            pass
        
        self.mode_buttons = []
        modes = [
            ("ℹ️ Info", 0),
            ("🔎 Detect", 1),
            ("👁️ Monitor", 2),
            ("⏹️ Intercept", 3),
        ]
        
        action_x = 2
        for label, mode_idx in modes:
            is_selected = (mode_idx == self.mode)
            button_width = 13
            try:
                if is_selected:
                    stdscr.attron(curses.A_REVERSE)
                btn_text = label.center(button_width)[:button_width]
                stdscr.addstr(y_pos, action_x, btn_text)
                if is_selected:
                    stdscr.attroff(curses.A_REVERSE)
            except curses.error:
                pass
            
            self.mode_buttons.append(ClickRegion(
                y_start=y_pos,
                y_end=y_pos,
                x_start=action_x,
                x_end=action_x + button_width - 1,
                action_id=mode_idx
            ))
            action_x += button_width + 1
        
        try:
            stdscr.addstr(y_pos + 1, 2, "└─")
        except curses.error:
            pass
        
        y_pos += 3
        draw_text_block(stdscr, y_pos, 2, w - 4, self.lines)
        
        self.button_regions = draw_touch_button_bar(stdscr, [
            ("← Back", 0),
            ("🔄 Refresh", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                
                # Check mode buttons
                mode_clicked = check_mouse_click(mouse_event, self.mode_buttons)
                if mode_clicked is not None:
                    self.mode = mode_clicked
                    self._load()
                    return ScreenResult()
                
                # Check bottom buttons
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
                elif button_clicked == 1:
                    self._load()
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
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
            ("🔄 Sync", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="hacker")
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
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
            ("🔄 Sync", 1),
            ("Home", 2),
        ])

    def handle_key(self, key: int) -> ScreenResult:
        if key == curses.KEY_MOUSE:
            try:
                mouse_event = curses.getmouse()
                button_clicked = check_mouse_click(mouse_event, self.button_regions)
                if button_clicked == 0:
                    return ScreenResult(next_screen="main")
                elif button_clicked == 2:
                    return ScreenResult(next_screen="main")
            except:
                pass
        
        return ScreenResult()
