from __future__ import annotations
import curses
from typing import Dict, Type, Optional

from tui.screens import (
    BaseScreen,
    MainMenuScreen,
    NetworkHubScreen,
    InterfacesScreen,
    NetDiagScreen,
    NetDiagDetailScreen,
    WifiScreen,
    DnsRoutesScreen,
    BluetoothHubScreen,
    BluetoothDevicesScreen,
    BluetoothStatusScreen,
    SystemInfoScreen,
    HackerToolsScreen,
    PortScannerScreen,
    CustomPortInputScreen,
    SnifferScreen,
    KeyloggerScreen,
    USBKeyboardInterceptorScreen,
    PacketsScreen,
    SettingsScreen,
)


class TuiApp:
    def __init__(self):
        self.screen_map: Dict[str, Type[BaseScreen]] = {
            "main": MainMenuScreen,
            "net_hub": NetworkHubScreen,
            "ifaces": InterfacesScreen,
            "netdiag": NetDiagScreen,
            "netdiag_detail": NetDiagDetailScreen,
            "wifi": WifiScreen,
            "dns_routes": DnsRoutesScreen,
            "bt_hub": BluetoothHubScreen,
            "bt_devices": BluetoothDevicesScreen,
            "bt_status": BluetoothStatusScreen,
            "sys_info": SystemInfoScreen,
            "hacker": HackerToolsScreen,
            "port_scan": PortScannerScreen,
            "custom_port_input": CustomPortInputScreen,
            "sniffer": SnifferScreen,
            "keylogger": KeyloggerScreen,
            "usb_interceptor": USBKeyboardInterceptorScreen,
            "packets": PacketsScreen,
            "settings": SettingsScreen,
        }
        self.current_name = "main"
        self.current: BaseScreen = self.screen_map[self.current_name]()
        self.selected_interface: Optional[str] = None
        # Always enable touch mode
        if hasattr(self.current, 'set_touch_mode'):
            self.current.set_touch_mode(True)

    def switch(self, name: str) -> None:
        self.current_name = name
        
        # Handle special case for netdiag_detail screen
        if name == "netdiag_detail":
            # Get the selected interface from the current NetDiagScreen
            if isinstance(self.current, NetDiagScreen):
                if self.current.selected_index >= 0 and self.current.selected_index < len(self.current.interfaces):
                    self.selected_interface = self.current.interfaces[self.current.selected_index]
            self.current = NetDiagDetailScreen(self.selected_interface or "")
        else:
            self.current = self.screen_map[name]()
        
        # Always enable touch mode
        if hasattr(self.current, 'set_touch_mode'):
            self.current.set_touch_mode(True)

    def run(self, stdscr) -> None:
        curses.curs_set(0)
        stdscr.keypad(True)
        curses.use_default_colors()
        
        # Enable mouse events for touchscreen and mouse support
        curses.mousemask(curses.BUTTON1_CLICKED | curses.BUTTON3_CLICKED)

        while True:
            self.current.render(stdscr)
            stdscr.refresh()

            # Use short timeout (500ms) only for SnifferScreen for live updates
            if self.current_name == "sniffer":
                stdscr.nodelay(True)
                stdscr.timeout(500)  # 500ms timeout for live packet updates
            else:
                stdscr.nodelay(False)
                stdscr.timeout(-1)   # Blocking mode for normal screens

            key = stdscr.getch()
            if key != -1 or self.current_name == "sniffer":  # Always render sniffer even on timeout
                result = self.current.handle_key(key) if key != -1 else self.current.handle_key(-1)

                if result.next_screen == "quit":
                    break
                if result.next_screen and result.next_screen != self.current_name:
                    self.switch(result.next_screen)


def start() -> None:
    """Start the TUI application with mouse-only interaction mode."""
    curses.wrapper(TuiApp().run)