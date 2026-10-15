"""Serial port helpers with AI-friendly error codes."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .parse import DeviceSnapshot, decode_line, update_snapshot

# Re-export exit codes for convenience
from .codes import (  # noqa: F401
    EXIT_DEP,
    EXIT_OK,
    EXIT_PORT,
    EXIT_TIMEOUT,
    EXIT_UNHEALTHY,
    EXIT_USAGE,
)


@dataclass
class PortInfo:
    device: str
    description: str
    hwid: str
    vid: int | None = None
    pid: int | None = None
    manufacturer: str | None = None
    likely_esp: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PortError(RuntimeError):
    """Port cannot be opened (busy, missing, permission)."""


class PortBusyError(PortError):
    """Another process owns the serial port."""


# Global lock hint for CLI / serve mutual exclusion (cooperative)
_owner: str | None = None


def claim_port(owner: str) -> None:
    global _owner
    if _owner and _owner != owner:
        raise PortBusyError(
            f"Serial owned by '{_owner}'. Stop that session first "
            "(close Web console or other xzkit process)."
        )
    _owner = owner


def release_port(owner: str) -> None:
    global _owner
    if _owner == owner:
        _owner = None


def current_owner() -> str | None:
    return _owner


def require_serial() -> None:
    try:
        import serial  # noqa: F401
        from serial.tools import list_ports  # noqa: F401
    except ImportError as e:
        raise RuntimeError("pyserial not installed. Run: pip install pyserial") from e


def list_ports() -> list[PortInfo]:
    require_serial()
    from serial.tools import list_ports

    out: list[PortInfo] = []
    for p in list_ports.comports():
        text = f"{p.description} {p.hwid} {p.manufacturer or ''}".lower()
        likely = any(
            k in text
            for k in (
                "esp",
                "silicon labs",
                "cp210",
                "ch340",
                "ch910",
                "usb jtag",
                "usb serial",
                "uart",
                "ftdi",
            )
        )
        out.append(
            PortInfo(
                device=p.device,
                description=p.description or "",
                hwid=p.hwid or "",
                vid=p.vid,
                pid=p.pid,
                manufacturer=p.manufacturer,
                likely_esp=likely,
            )
        )
    return out


def pick_port(preferred: str | None = None, esp_only: bool = False) -> str | None:
    ports = list_ports()
    if preferred:
        for p in ports:
            if p.device.upper() == preferred.upper():
                return p.device
        return preferred
    candidates = [p for p in ports if p.likely_esp] if esp_only else ports
    if not candidates:
        candidates = ports
    return candidates[0].device if candidates else None


def open_serial(port: str, baud: int, timeout: float = 0.2):
    require_serial()
    import serial

    try:
        return serial.Serial(port, baud, timeout=timeout)
    except serial.SerialException as e:
        msg = str(e)
        if "PermissionError" in msg or "Access is denied" in msg or "busy" in msg.lower():
            raise PortBusyError(
                f"{msg}. Close 安信可串口调试助手 / Arduino Serial Monitor / other xzkit sessions."
            ) from e
        raise PortError(msg) from e


def hard_reset(port: str, baud: int = 115200, into_bootloader: bool = False) -> None:
    """Toggle DTR/RTS like esptool to reset ESP32."""
    ser = open_serial(port, baud, timeout=0.1)
    try:
        if into_bootloader:
            ser.dtr = False
            ser.rts = True
            time.sleep(0.1)
            ser.dtr = True
            time.sleep(0.1)
            ser.rts = False
            ser.dtr = False
        else:
            ser.dtr = False
            ser.rts = True
            time.sleep(0.1)
            ser.rts = False
            time.sleep(0.05)
    finally:
        ser.close()


def read_for(
    port: str,
    baud: int,
    duration: float,
    on_line: Callable[[str, str | None], None] | None = None,
    max_lines: int | None = None,
) -> tuple[list[str], DeviceSnapshot]:
    ser = open_serial(port, baud)
    lines: list[str] = []
    snap = DeviceSnapshot()
    end = time.time() + duration
    try:
        while time.time() < end:
            if max_lines is not None and len(lines) >= max_lines:
                break
            raw = ser.readline()
            if not raw:
                continue
            line = decode_line(raw)
            tag = update_snapshot(snap, line)
            lines.append(line)
            if on_line:
                on_line(line, tag)
    finally:
        ser.close()
    return lines, snap


def wait_for_pattern(
    port: str,
    baud: int,
    pattern: str,
    timeout: float,
    ignore_case: bool = True,
) -> tuple[bool, list[str], DeviceSnapshot, float]:
    import re

    flags = re.I if ignore_case else 0
    rx = re.compile(pattern, flags)
    ser = open_serial(port, baud)
    lines: list[str] = []
    snap = DeviceSnapshot()
    start = time.time()
    matched = False
    try:
        while (time.time() - start) < timeout:
            raw = ser.readline()
            if not raw:
                continue
            line = decode_line(raw)
            update_snapshot(snap, line)
            lines.append(line)
            if rx.search(line):
                matched = True
                break
    finally:
        ser.close()
    return matched, lines, snap, time.time() - start


def send_line(
    port: str,
    baud: int,
    text: str,
    wait: float = 2.0,
    newline: bool = True,
) -> tuple[list[str], DeviceSnapshot]:
    ser = open_serial(port, baud)
    payload = text.encode("utf-8")
    if newline and not payload.endswith(b"\n"):
        payload += b"\n"
    ser.write(payload)
    ser.flush()
    lines: list[str] = []
    snap = DeviceSnapshot()
    end = time.time() + wait
    try:
        while time.time() < end:
            raw = ser.readline()
            if not raw:
                continue
            line = decode_line(raw)
            update_snapshot(snap, line)
            lines.append(line)
    finally:
        ser.close()
    return lines, snap


def doctor(preferred_port: str | None = None, baud: int = 115200) -> dict[str, Any]:
    result: dict[str, Any] = {
        "pyserial": False,
        "pyserial_version": None,
        "ports": [],
        "suggested_port": None,
        "preferred_port": preferred_port,
        "preferred_available": None,
        "preferred_openable": None,
        "serial_owner": current_owner(),
        "hints": [],
        "ok": False,
    }
    try:
        import serial

        result["pyserial"] = True
        result["pyserial_version"] = getattr(serial, "__version__", "?")
    except ImportError:
        result["hints"].append("pip install 'xiaozhi-kit' or: pip install pyserial")
        return result

    ports = list_ports()
    result["ports"] = [p.to_dict() for p in ports]
    result["suggested_port"] = pick_port(esp_only=True) or pick_port()

    if not ports:
        result["hints"].append("No COM ports found. Plug in USB and install CH340/CP210x driver.")
        return result

    if preferred_port:
        names = {p.device.upper() for p in ports}
        result["preferred_available"] = preferred_port.upper() in names
        if not result["preferred_available"]:
            result["hints"].append(
                f"{preferred_port} not in port list. Try suggested_port={result['suggested_port']}"
            )
        else:
            try:
                ser = open_serial(preferred_port, baud)
                ser.close()
                result["preferred_openable"] = True
            except PortError as e:
                result["preferred_openable"] = False
                result["hints"].append(str(e))
    else:
        sug = result["suggested_port"]
        if sug:
            try:
                ser = open_serial(sug, baud)
                ser.close()
                result["preferred_openable"] = True
                result["preferred_available"] = True
            except PortError as e:
                result["preferred_openable"] = False
                result["hints"].append(str(e))

    result["ok"] = bool(
        result["pyserial"]
        and result["ports"]
        and (result["preferred_openable"] is True or result["preferred_openable"] is None)
    )
    if result["preferred_openable"] is False:
        result["ok"] = False
    if result["ok"] and not result["hints"]:
        result["hints"].append("Ready. Use: xzkit status --json")
    return result
