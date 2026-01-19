from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re

from utils import run_cmd


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
    
    # Run nmap
    rc, out, err = run_cmd(cmd, timeout=30)
    
    if rc != 0:
        if "not allowed" in err.lower() or "permission" in err.lower():
            warnings.append("nmap requires sudo: sudo nmap <target>")
        else:
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
    rc, out, err = run_cmd(cmd, timeout=30)
    
    if rc != 0:
        if "permission" in err.lower():
            warnings.append("nmap requires sudo for network scans")
        else:
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

