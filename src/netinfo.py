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