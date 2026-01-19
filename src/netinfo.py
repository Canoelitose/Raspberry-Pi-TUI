from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re

from utils import run_cmd, run_cmd_with_sudo


@dataclass
class InterfaceInfo:
    name: str
    state: Optional[str] = None
    mac: Optional[str] = None
    ipv4: List[str] = field(default_factory=list)
    ipv6: List[str] = field(default_factory=list)
    mtu: Optional[str] = None


def _parse_ip_addr(output: str) -> Dict[str, InterfaceInfo]:
    infos: Dict[str, InterfaceInfo] = {}
    current: Optional[InterfaceInfo] = None

    header_re = re.compile(r"^\d+:\s+([^:]+):.*mtu\s+(\d+)")
    link_re = re.compile(r"^\s+link/\S+\s+([0-9a-f:]{17})")
    inet4_re = re.compile(r"^\s+inet\s+(\d+\.\d+\.\d+\.\d+/\d+)")
    inet6_re = re.compile(r"^\s+inet6\s+([0-9a-f:]+/\d+)")
    state_re = re.compile(r"\bstate\s+(\S+)")

    for line in output.splitlines():
        m = header_re.match(line)
        if m:
            name = m.group(1)
            mtu = m.group(2)
            current = infos.get(name) or InterfaceInfo(name=name)
            current.mtu = mtu

            sm = state_re.search(line)
            if sm:
                current.state = sm.group(1)
            infos[name] = current
            continue

        if current is None:
            continue

        m = link_re.match(line)
        if m:
            current.mac = m.group(1)
            continue

        m = inet4_re.match(line)
        if m:
            current.ipv4.append(m.group(1))
            continue

        m = inet6_re.match(line)
        if m:
            current.ipv6.append(m.group(1))
            continue

    return infos


def get_interfaces() -> Tuple[List[InterfaceInfo], List[str]]:
    warnings: List[str] = []

    rc, _, err = run_cmd(["ip", "-brief", "link"], timeout=3)
    if rc != 0:
        warnings.append(f"ip -brief link: {err or 'unknown error'}")

    rc2, out2, err2 = run_cmd(["ip", "addr"], timeout=3)
    if rc2 != 0:
        warnings.append(f"ip addr: {err2 or 'unknown error'}")
        return [], warnings

    infos = _parse_ip_addr(out2)
    names = sorted([n for n in infos.keys() if n != "lo"]) + (["lo"] if "lo" in infos else [])
    return [infos[n] for n in names], warnings


def get_dns() -> Tuple[List[str], List[str]]:
    warnings: List[str] = []
    dns: List[str] = []

    path = "/etc/resolv.conf"
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("nameserver"):
                    parts = line.split()
                    if len(parts) >= 2:
                        dns.append(parts[1])
    except Exception as e:
        warnings.append(f"{path} could not be read: {e}")

    return dns, warnings


def get_default_route() -> Tuple[Optional[str], Optional[str]]:
    rc, out, err = run_cmd(["ip", "route", "show", "default"], timeout=3)
    if rc != 0 or not out:
        return None, err or "no default route found"

    m = re.search(r"\bvia\s+(\d+\.\d+\.\d+\.\d+)", out)
    gw = m.group(1) if m else None
    return gw, None


def ping(host: str = "1.1.1.1") -> Tuple[bool, str]:
    rc, out, err = run_cmd(["ping", "-c", "1", "-W", "2", host], timeout=4)
    if rc == 0:
        return True, out
    return False, err or out or "Ping failed"


def wifi_status() -> Tuple[str, str]:
    rc, out, err = run_cmd(["iw", "dev"], timeout=3)
    if rc != 0:
        return "", "iw is not available (run: sudo apt install iw) or no WLAN device found."
    return out, ""


def ping_via_interface(interface: str, host: str = "1.1.1.1") -> Tuple[bool, str]:
    """Ping a host via a specific interface"""
    rc, out, err = run_cmd(["ping", "-I", interface, "-c", "1", "-W", "2", host], timeout=4)
    if rc == 0:
        return True, out
    return False, err or out or "Ping failed"


def get_route_via_interface(interface: str) -> Tuple[Optional[str], Optional[str]]:
    """Get the gateway for a specific interface"""
    rc, out, err = run_cmd(["ip", "route", "show", "dev", interface], timeout=3)
    if rc != 0 or not out:
        return None, err or "no route found"
    
    # Try to find the gateway
    m = re.search(r"\bvia\s+(\d+\.\d+\.\d+\.\d+)", out)
    gw = m.group(1) if m else None
    return gw, None


def get_interface_stats(interface: str) -> Tuple[Dict, List[str]]:
    """Get detailed statistics for a specific interface"""
    warnings: List[str] = []
    stats: Dict = {}
    
    # Get interface info
    ifaces, iface_warns = get_interfaces()
    warnings.extend(iface_warns)
    
    iface_obj = None
    for iface in ifaces:
        if iface.name == interface:
            iface_obj = iface
            break
    
    if not iface_obj:
        warnings.append(f"Interface {interface} not found")
        return {}, warnings
    
    stats["name"] = iface_obj.name
    stats["state"] = iface_obj.state
    stats["mtu"] = iface_obj.mtu
    stats["mac"] = iface_obj.mac
    stats["ipv4"] = iface_obj.ipv4
    stats["ipv6"] = iface_obj.ipv6
    
    # Get gateway for this interface
    gw, gw_err = get_route_via_interface(interface)
    stats["gateway"] = gw
    if gw_err:
        warnings.append(f"Gateway: {gw_err}")
    
    # Get ping result via this interface (only if it has IP)
    if iface_obj.ipv4 or iface_obj.ipv6:
        ok, out = ping_via_interface(interface)
        stats["ping_ok"] = ok
        stats["ping_output"] = out
    
    return stats, warnings


# ============== BLUETOOTH FUNCTIONS ==============

def get_bluetooth_devices() -> Tuple[List[str], List[str]]:
    """Get list of paired Bluetooth devices"""
    warnings: List[str] = []
    devices: List[str] = []
    
    rc, out, err = run_cmd(["bluetoothctl", "paired-devices"], timeout=3)
    if rc != 0:
        warnings.append("Bluetooth not available or bluetoothctl not found")
        return devices, warnings
    
    for line in out.splitlines():
        line = line.strip()
        if line:
            devices.append(line)
    
    return devices, warnings


def get_bluetooth_status() -> Tuple[str, List[str]]:
    """Get Bluetooth controller status"""
    warnings: List[str] = []
    
    rc, out, err = run_cmd(["bluetoothctl", "show"], timeout=3)
    if rc != 0:
        return "Bluetooth not available", ["bluetoothctl not found"]
    
    return out, warnings


def get_bluetooth_powered() -> Tuple[bool, List[str]]:
    """Check if Bluetooth is powered on"""
    warnings: List[str] = []
    
    rc, out, err = run_cmd(["bluetoothctl", "show"], timeout=3)
    if rc != 0:
        return False, ["bluetoothctl not found"]
    
    for line in out.splitlines():
        if "Powered: yes" in line:
            return True, []
        elif "Powered: no" in line:
            return False, []
    
    return False, ["Could not determine power status"]


# ============== SYSTEM INFO FUNCTIONS ==============

def get_system_info() -> Tuple[Dict[str, str], List[str]]:
    """Get basic system information"""
    warnings: List[str] = []
    info: Dict[str, str] = {}
    
    # Hostname
    rc, out, _ = run_cmd(["hostname"], timeout=2)
    info["hostname"] = out if rc == 0 else "N/A"
    
    # Uptime
    rc, out, _ = run_cmd(["uptime", "-p"], timeout=2)
    info["uptime"] = out if rc == 0 else "N/A"
    
    # Kernel
    rc, out, _ = run_cmd(["uname", "-r"], timeout=2)
    info["kernel"] = out if rc == 0 else "N/A"
    
    # CPU
    rc, out, _ = run_cmd(["nproc"], timeout=2)
    info["cpu_cores"] = out if rc == 0 else "N/A"
    
    return info, warnings


def get_disk_usage() -> Tuple[Dict[str, str], List[str]]:
    """Get disk usage information"""
    warnings: List[str] = []
    usage: Dict[str, str] = {}
    
    rc, out, err = run_cmd(["df", "-h"], timeout=3)
    if rc != 0:
        warnings.append("Could not get disk usage")
        return usage, warnings
    
    lines = out.splitlines()
    if len(lines) > 1:
        root_line = lines[1]
        parts = root_line.split()
        if len(parts) >= 5:
            usage["filesystem"] = parts[0]
            usage["size"] = parts[1]
            usage["used"] = parts[2]
            usage["available"] = parts[3]
            usage["percent"] = parts[4]
    
    return usage, warnings


def get_memory_info() -> Tuple[Dict[str, str], List[str]]:
    """Get memory information from /proc/meminfo"""
    warnings: List[str] = []
    mem_info: Dict[str, str] = {}
    
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        total_kb = int(parts[1])
                        mem_info["total"] = f"{total_kb // 1024} MB"
                elif line.startswith("MemAvailable:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        avail_kb = int(parts[1])
                        mem_info["available"] = f"{avail_kb // 1024} MB"
                elif line.startswith("MemFree:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        free_kb = int(parts[1])
                        mem_info["free"] = f"{free_kb // 1024} MB"
    except Exception as e:
        warnings.append(f"Could not read memory info: {e}")
    
    return mem_info, warnings


# ============== PORT SCANNING FUNCTIONS ==============

def check_open_ports(host: str = "localhost") -> Tuple[List[str], List[str]]:
    """Check common open ports using netstat"""
    warnings: List[str] = []
    open_ports: List[str] = []
    
    rc, out, err = run_cmd(["netstat", "-tuln"], timeout=3)
    if rc != 0:
        warnings.append("netstat not available or failed")
        # Try ss as fallback
        rc, out, err = run_cmd(["ss", "-tuln"], timeout=3)
        if rc != 0:
            warnings.append("ss not available either")
            return open_ports, warnings
    
    for line in out.splitlines():
        if "LISTEN" in line:
            open_ports.append(line.strip()[:60])  # Limit line length
    
    return open_ports, warnings


# ============== NMAP PORT SCANNING ==============

def scan_ports_with_nmap(target: str = "localhost", ports: str = "1-1000", interface: str = None) -> Tuple[List[str], List[str]]:
    """
    Scan specific ports using nmap.
    target: target IP or network range
    ports: port range like "1-1000" or "22,80,443" or "1-100" 
    interface: network interface to use (e.g. "eth0", "wlan0")
    """
    warnings: List[str] = []
    results: List[str] = []
    
    # Check if nmap is available
    rc, _, err = run_cmd(["which", "nmap"], timeout=2)
    if rc != 0:
        return results, ["nmap not installed. Install with: sudo apt install nmap"]
    
    # Validate port range
    if not ports:
        ports = "1-1000"
    
    # Build nmap command
    cmd = ["nmap", "-p", ports]
    
    # Add interface if specified
    if interface and interface not in ["all", "localhost"]:
        cmd.extend(["-e", interface])
    
    cmd.append(target)
    
    # Run nmap with automatic sudo if needed
    rc, out, err = run_cmd_with_sudo(cmd, timeout=30)
    
    if rc != 0:
        warnings.append(f"nmap failed: {err[:50]}")
        return results, warnings
    
    # Parse nmap output
    lines = out.splitlines()
    in_port_section = False
    
    for line in lines:
        line_stripped = line.strip()
        
        # Look for port information
        if "/tcp" in line or "/udp" in line:
            in_port_section = True
            results.append(line_stripped[:70])
        elif in_port_section and line_stripped and not line_stripped.startswith("Nmap"):
            if "Host is up" in line or "Nmap scan report" in line:
                break
            if line_stripped:
                results.append(line_stripped[:70])
    
    if not results:
        # Try to extract summary info if no ports found
        for line in lines:
            if "All" in line and "ports" in line:
                results.append(line.strip()[:70])
    
    return results, warnings


def scan_network_with_nmap(network: str = "192.168.1.0/24", interface: str = None) -> Tuple[List[str], List[str]]:
    """
    Scan a network for active hosts using nmap -sn (ping scan).
    network: CIDR notation like "192.168.1.0/24"
    interface: network interface to use (e.g. "eth0", "wlan0")
    """
    warnings: List[str] = []
    results: List[str] = []
    
    # Check if nmap is available
    rc, _, err = run_cmd(["which", "nmap"], timeout=2)
    if rc != 0:
        return results, ["nmap not installed. Install with: sudo apt install nmap"]
    
    # Run nmap network discovery
    cmd = ["nmap", "-sn"]
    
    # Add interface if specified
    if interface and interface not in ["all", "localhost"]:
        cmd.extend(["-e", interface])
    
    cmd.append(network)
    
    # Run nmap with automatic sudo if needed
    rc, out, err = run_cmd_with_sudo(cmd, timeout=30)
    
    if rc != 0:
        warnings.append(f"nmap failed: {err[:50]}")
        return results, warnings
    
    # Parse nmap output
    for line in out.splitlines():
        if "Nmap scan report for" in line or "Host is up" in line:
            results.append(line.strip()[:70])
    
    return results, warnings


def get_local_network() -> Tuple[str, List[str]]:
    """Get local network CIDR from current interfaces"""
    warnings: List[str] = []
    
    ifaces, _ = get_interfaces()
    
    for iface in ifaces:
        if iface.name not in ["lo", "docker0"]:
            if iface.ipv4:
                # Extract network from first IPv4
                ip_str = iface.ipv4[0]  # e.g., "192.168.1.100/24"
                if "/" in ip_str:
                    ip_part, mask = ip_str.split("/")
                    # Reconstruct network address
                    parts = ip_part.split(".")
                    if len(parts) == 4:
                        network = f"{parts[0]}.{parts[1]}.{parts[2]}.0/{mask}"
                        return network, warnings
    
    # Fallback
    return "192.168.1.0/24", ["Could not determine local network"]


def sniff_packets(interface: str = "eth0", packet_count: int = 20, filter_str: str = "") -> Tuple[List[str], List[str]]:
    """
    Sniff network packets using tcpdump.
    interface: network interface to sniff on (e.g. "eth0", "wlan0")
    packet_count: number of packets to capture
    filter_str: tcpdump filter (e.g. "tcp port 80" or "icmp")
    """
    warnings: List[str] = []
    results: List[str] = []
    
    # Check if tcpdump is available
    rc, _, err = run_cmd(["which", "tcpdump"], timeout=2)
    if rc != 0:
        return results, ["tcpdump not installed. Install with: sudo apt install tcpdump"]
    
    # Build tcpdump command
    cmd = ["tcpdump", "-i", interface, "-c", str(packet_count)]
    
    # Add filter if specified
    if filter_str:
        cmd.append(filter_str)
    
    # Run tcpdump with automatic sudo if needed
    rc, out, err = run_cmd_with_sudo(cmd, timeout=10)
    
    if rc != 0:
        warnings.append(f"tcpdump failed: {err[:50]}")
        return results, warnings
    
    # Parse tcpdump output
    lines = out.splitlines()
    
    # Skip header lines and extract packet info
    for line in lines:
        line = line.strip()
        # Skip empty lines and summary lines
        if line and not line.startswith("tcpdump:") and "packets captured" not in line:
            # Truncate long lines for display
            results.append(line[:80])
    
    if not results:
        results.append("(No packets captured)")
    
    return results, warnings


def sniff_packets_with_tshark(interface: str = "eth0", packet_count: int = 20, filter_str: str = "") -> Tuple[List[str], List[str]]:
    """
    Sniff network packets using tshark (Wireshark terminal version).
    Provides better formatting and analysis than tcpdump.
    interface: network interface to sniff on (e.g. "eth0", "wlan0")
    packet_count: number of packets to capture
    filter_str: tshark filter (e.g. "tcp.port == 80" or "icmp")
    """
    warnings: List[str] = []
    results: List[str] = []
    
    # Check if tshark is available
    rc, _, err = run_cmd(["which", "tshark"], timeout=2)
    if rc != 0:
        return results, ["tshark not installed. Install with: sudo apt install tshark"]
    
    # Build tshark command with nice formatting
    cmd = ["tshark", "-i", interface, "-c", str(packet_count)]
    
    # Add tshark format options for better display
    cmd.extend(["-o", "gui.column.format:\"No.\",\"%m\",\"Time\",\"%t\",\"Source\",\"%s\",\"Protocol\",\"%p\",\"Info\",\"%i\""])
    
    # Add filter if specified
    if filter_str:
        cmd.extend(["-f", filter_str])
    
    # Run tshark with automatic sudo if needed
    rc, out, err = run_cmd_with_sudo(cmd, timeout=10)
    
    if rc != 0:
        warnings.append(f"tshark failed: {err[:50]}")
        return results, warnings
    
    # Parse tshark output
    lines = out.splitlines()
    
    for line in lines:
        line = line.strip()
        # Skip empty lines
        if line and not line.startswith("tshark:"):
            # Truncate long lines for display
            results.append(line[:80])
    
    if not results:
        results.append("(No packets captured)")
    
    return results, warnings


def check_tshark_available() -> bool:
    """Check if tshark is installed and available"""
    rc, _, _ = run_cmd(["which", "tshark"], timeout=2)
    return rc == 0


def open_wireshark(interface: str = None) -> int:
    """
    Open Wireshark GUI for interactive packet capture and analysis.
    If interface is specified, Wireshark will capture on that interface.
    Returns 0 on success, non-zero on failure.
    """
    import subprocess
    import os
    
    try:
        # Check if Wireshark is installed
        rc, _, _ = run_cmd(["which", "wireshark"], timeout=2)
        if rc != 0:
            return 1  # Wireshark not installed
        
        # Check if display is available (X11 or Wayland)
        if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
            return 2  # No display server available
        
        # Build Wireshark command
        cmd = []
        
        # Try to use wireshark with sudo if needed
        try:
            cmd = ["wireshark"]
            if interface:
                cmd.extend(["-i", interface])
            
            # Try to run Wireshark, may require sudo
            subprocess.Popen(cmd)
            return 0
        except PermissionError:
            # Retry with sudo
            cmd = ["sudo", "wireshark"]
            if interface:
                cmd.extend(["-i", interface])
            
            subprocess.Popen(cmd)
            return 0
    
    except Exception as e:
        return 1


def check_wireshark_available() -> bool:
    """Check if Wireshark is installed and available with a display server"""
    import os
    
    rc, _, _ = run_cmd(["which", "wireshark"], timeout=2)
    if rc != 0:
        return False
    
    # Also check if display is available
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False
    
    return True


def monitor_keyboard_events(duration_seconds: int = 10, device_pattern: str = "") -> Tuple[List[str], List[str]]:
    """
    Monitor keyboard/input events using libinput or evtest.
    duration_seconds: how long to monitor (approximately)
    device_pattern: filter devices (e.g. "keyboard", "")
    Returns list of events captured
    """
    warnings: List[str] = []
    results: List[str] = []
    
    # Try libinput first (newer, preferred method)
    rc, _, _ = run_cmd(["which", "libinput"], timeout=2)
    if rc == 0:
        try:
            # List input devices
            cmd = ["libinput", "list-devices"]
            rc, out, err = run_cmd_with_sudo(cmd, timeout=5)
            
            if rc == 0:
                for line in out.splitlines()[:20]:
                    if "Keyboard" in line or "keyboard" in line or line.strip():
                        results.append(line.strip()[:80])
                
                if not results:
                    results.append("(No keyboard devices found)")
            else:
                warnings.append("libinput list-devices failed")
        except Exception as e:
            warnings.append(f"libinput error: {str(e)[:40]}")
    else:
        # Fallback: try evtest
        rc, _, _ = run_cmd(["which", "evtest"], timeout=2)
        if rc == 0:
            results.append("evtest available for event monitoring")
            results.append("(Interactive mode - press device to monitor)")
        else:
            warnings.append("Neither libinput nor evtest found")
            warnings.append("Install: sudo apt-get install libinput-tools evtest")
    
    return results, warnings


def get_keyboard_devices() -> Tuple[List[str], List[str]]:
    """
    List available keyboard input devices.
    """
    warnings: List[str] = []
    devices: List[str] = []
    
    # Try to list input devices
    import os
    import glob
    
    # Check /dev/input/event* files (requires root)
    try:
        event_files = sorted(glob.glob("/dev/input/event*"))
        for event_file in event_files:
            # Try to get device name
            name_cmd = ["cat", f"/sys/class/input/{os.path.basename(event_file)}/device/name"]
            rc, name, _ = run_cmd(name_cmd, timeout=2)
            if rc == 0 and name:
                devices.append(f"{event_file}: {name.strip()}")
            else:
                devices.append(event_file)
    except:
        pass
    
    if not devices:
        warnings.append("Could not enumerate input devices")
        warnings.append("Try: sudo evtest")
    
    return devices, warnings


def capture_keyboard_events(event_device: str = "", duration: int = 5) -> Tuple[List[str], List[str]]:
    """
    Capture keyboard events from specified device using evtest.
    event_device: e.g., "/dev/input/event0"
    duration: capture duration in seconds
    """
    import time
    
    warnings: List[str] = []
    results: List[str] = []
    
    # Check if evtest is available
    rc, _, _ = run_cmd(["which", "evtest"], timeout=2)
    if rc != 0:
        return results, ["evtest not installed. Install with: sudo apt-get install evtest"]
    
    if not event_device:
        return results, ["No event device specified"]
    
    try:
        # Run evtest with timeout
        cmd = ["timeout", str(duration), "evtest", event_device]
        rc, out, err = run_cmd_with_sudo(cmd, timeout=duration + 5)
        
        # Parse evtest output
        lines = out.splitlines()
        
        for line in lines:
            line = line.strip()
            # Filter for key events
            if "EV_KEY" in line or "EV_REL" in line or "KEY_" in line:
                results.append(line[:80])
        
        if not results:
            results.append("(No events captured)")
            if err:
                warnings.append(f"Error: {err[:50]}")
    except Exception as e:
        warnings.append(f"Capture error: {str(e)[:50]}")
    
    return results, warnings


def list_usb_devices() -> Tuple[List[str], List[str]]:
    """
    List all connected USB devices (including keyboards).
    Uses lsusb command for detection.
    """
    warnings: List[str] = []
    devices: List[str] = []
    
    # Check if lsusb is available
    rc, _, _ = run_cmd(["which", "lsusb"], timeout=2)
    if rc != 0:
        return devices, ["lsusb not installed. Install with: sudo apt-get install usbutils"]
    
    # List all USB devices
    rc, out, err = run_cmd(["lsusb"], timeout=5)
    
    if rc == 0:
        lines = out.splitlines()
        for line in lines:
            # Parse lsusb output: "Bus 001 Device 002: ID 1234:5678 Keyboard Name"
            if "Keyboard" in line or "keyboard" in line or "HID" in line or "hid" in line:
                devices.append(f"⌨️  {line.strip()}")
            else:
                devices.append(f"📱 {line.strip()}")
    else:
        warnings.append(f"lsusb error: {err[:50]}")
    
    return devices, warnings


def monitor_usb_keyboard_events(bus: int = -1, device: int = -1) -> Tuple[List[str], List[str]]:
    """
    Monitor USB keyboard events using pyusb or evtest.
    Intercepts keystrokes and displays them live.
    """
    import threading
    
    warnings: List[str] = []
    results: List[str] = []
    
    # Try to import pyusb for direct USB monitoring
    try:
        import usb
        results.append("✓ pyusb available - Direct USB monitoring")
        results.append("")
        
        # List all USB devices
        devices_found = 0
        keyboard_devices = []
        
        for dev in usb.core.find(find_all=True):
            # Check if device is keyboard-like (HID class 3)
            try:
                if dev.bDeviceClass == 0 or dev.bDeviceClass == usb.CLASS_HID or "Keyboard" in str(dev):
                    devices_found += 1
                    dev_name = f"Bus {dev.bus:03d} Device {dev.address:03d}"
                    try:
                        dev_name += f": {dev.manufacturer} - {dev.product}"
                    except:
                        pass
                    results.append(dev_name)
                    keyboard_devices.append((dev.bus, dev.address))
            except:
                pass
        
        if devices_found == 0:
            results.append("No USB keyboards detected")
            results.append("Make sure USB keyboard is connected")
        else:
            results.append(f"\n✓ Found {devices_found} USB device(s)")
    
    except ImportError:
        warnings.append("pyusb not installed")
        results.append("Install: pip3 install pyusb")
        
        # Fallback to evtest
        rc, _, _ = run_cmd(["which", "evtest"], timeout=2)
        if rc == 0:
            results.append("\nFallback: Using evtest for monitoring")
            results.append("Connect keyboard and select device in evtest")
        else:
            warnings.append("Neither pyusb nor evtest available")
    
    return results, warnings


def intercept_usb_keyboard(input_device: str) -> Tuple[List[str], List[str]]:
    """
    Intercept USB keyboard input and display keystrokes live.
    input_device: Source device path (e.g., /dev/input/event5)
    """
    warnings: List[str] = []
    results: List[str] = []
    
    # Check input device exists
    import os
    if not os.path.exists(input_device):
        return results, [f"Input device not found: {input_device}"]
    
    results.append(f"✓ Input device: {input_device}")
    results.append("")
    results.append("Capturing keyboard events (5 sec)...")
    results.append("Press some keys on the USB keyboard:")
    results.append("")
    
    # Use evtest to capture events with grab (exclusive access)
    cmd = ["timeout", "5", "evtest", "--grab", input_device]
    rc, out, err = run_cmd_with_sudo(cmd, timeout=10)
    
    if rc == 0 or rc == 124:  # 124 = timeout (expected)
        lines = out.splitlines()
        key_count = 0
        for line in lines:
            if "EV_KEY" in line or "KEY_" in line:
                # Parse keystroke: extract the key name
                if "press" in line.lower() or "release" in line.lower():
                    results.append(f"⌨️  {line.strip()[:75]}")
                    key_count += 1
        
        if key_count > 0:
            results.append(f"\n✓ Captured {key_count} keystrokes")
        else:
            results.append("(No keystrokes captured)")
    else:
        if "Permission denied" in err:
            warnings.append("Permission denied - try with sudo")
        else:
            warnings.append(f"evtest error: {err[:50]}")
    
    return results, warnings


