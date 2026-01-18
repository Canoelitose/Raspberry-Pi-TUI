from __future__ import annotations
import subprocess
from typing import List, Tuple


def run_cmd(cmd: List[str], timeout: int = 3) -> Tuple[int, str, str]:
    """
    Execute a system command and return (returncode, stdout, stderr).
    Uses no shell to prevent injection attacks.
    """
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except Exception as e:
        return 1, "", f"Error: {e}"