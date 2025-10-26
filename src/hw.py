from __future__ import annotations
import os, platform, subprocess, uuid, hashlib

def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True, timeout=2)
        return out.strip()
    except Exception:
        return ""

def _cpu_brand() -> str:
    p = platform.processor() or ""
    if p:
        return p
    sys = platform.system().lower()
    if sys == "linux":
        return _run(["bash", "-lc", "cat /proc/cpuinfo | grep 'model name' | head -1 | cut -d: -f2"]).strip()
    if sys == "darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    if sys == "windows":
        return _run(["wmic", "cpu", "get", "Name"]).splitlines()[1].strip() if "wmic" else ""
    return ""

def _board_uuid() -> str:
    sys = platform.system().lower()
    if sys == "linux":
        for p in ["/sys/class/dmi/id/product_uuid", "/sys/class/dmi/id/board_serial"]:
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8", errors="ignore") as f:
                        s = f.read().strip()
                        if s:
                            return s
                except Exception:
                    pass
    elif sys == "darwin":
        s = _run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
        for line in s.splitlines():
            if "IOPlatformUUID" in line:
                return line.split('"')[-2]
    elif sys == "windows":
        s = _run(["wmic", "csproduct", "get", "UUID"])
        parts = [x for x in s.splitlines() if x and "UUID" not in x]
        if parts:
            return parts[0].strip()
    return ""

def _disk_serial() -> str:
    sys = platform.system().lower()
    if sys == "linux":
        return _run(["bash","-lc","lsblk -dn -o SERIAL | head -1"])
    if sys == "darwin":
        # системный диск:
        return _run(["bash","-lc","system_profiler SPSerialATADataType | awk '/Serial Number/ {print $3; exit}'"])
    if sys == "windows":
        s = _run(["wmic", "diskdrive", "get", "SerialNumber"])
        parts = [x.strip() for x in s.splitlines()[1:] if x.strip()]
        if parts:
            return parts[0]
    return ""

def _mac_addr() -> str:
    try:
        return hex(uuid.getnode())
    except Exception:
        return ""

def get_hardware_fingerprint() -> str:
    """Стабильный отпечаток железа (без персональных данных)."""
    pieces = [
        platform.system(),
        platform.machine(),
        _cpu_brand(),
        _board_uuid(),
        _disk_serial(),
        _mac_addr(),
    ]
    norm = "|".join(x.strip().lower() for x in pieces if x)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def check_lic():
    lic = {'d8ef21763f1ffbbf6f211dc01e5ffd3fcf503543494493305eecdecd27541ab1': 'MA',
           'b70acc012f8c9457c5037e909ab8ccc8283c7d3caa54ed4afac015b6d997c4e0': 'TsAGI',
           '837158e975a72030d16911f20d6118a23cd001b8ce771263768b2dfd5a811682': 'TsAGI'}
    key = get_hardware_fingerprint()
    if key in  lic.keys():
        return lic[key]
    else:
        return False


if __name__ == '__main__':
    device, key = get_hardware_fingerprint()
    with open('configure.txt', 'w') as file:
        file.write(device)
        file.write('\n')
        file.write(key)