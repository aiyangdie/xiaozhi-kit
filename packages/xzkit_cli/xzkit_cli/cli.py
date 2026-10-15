#!/usr/bin/env python3
"""AI-operable CLI for Xiaozhi / ESP32 serial boards (xzkit).

Exit codes: 0 ok, 1 unhealthy/crash, 2 port error, 3 timeout, 4 dep, 5 usage.
Never run infinite serial monitors — always use bounded --seconds / --timeout.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xzkit_core.codes import (
    EXIT_DEP,
    EXIT_OK,
    EXIT_PORT,
    EXIT_TIMEOUT,
    EXIT_UNHEALTHY,
    EXIT_USAGE,
)
from xzkit_core.config import load_config
from xzkit_core.parse import parse_text
from xzkit_core.presets import get_preset, presets_payload
from xzkit_core.provision import open_portal, provision_status_from_snap, sample_provision
from xzkit_core.serial_io import (
    PortError,
    doctor,
    hard_reset,
    list_ports,
    pick_port,
    read_for,
    send_line,
    wait_for_pattern,
)
from xzkit_core.services import get_service, list_services

from . import __version__


def _ensure_utf8_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass


def emit(data: Any, as_json: bool) -> None:
    _ensure_utf8_stdout()
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                print(f"{k}:")
                print(json.dumps(v, ensure_ascii=False, indent=2))
            else:
                print(f"{k}: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                print(
                    f"{item.get('device', item.get('name', '?'))}\t"
                    f"{item.get('description', item.get('text', ''))}\t"
                    f"esp={item.get('likely_esp', '')}"
                )
            else:
                print(item)
    else:
        print(data)


def resolve_port(args: argparse.Namespace) -> str:
    cfg = load_config()
    port = getattr(args, "port", None) or cfg.get("port")
    auto = getattr(args, "auto", False)
    if port and not auto:
        return str(port)
    chosen = pick_port(preferred=port, esp_only=True) or pick_port(preferred=port)
    if not chosen:
        raise PortError("No serial ports found. Plug in the board.")
    return chosen


def cmd_list(args: argparse.Namespace) -> int:
    try:
        ports = [p.to_dict() for p in list_ports()]
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP
    emit(ports, args.json)
    if not args.json and not ports:
        print("No serial ports found.")
    return EXIT_OK


def cmd_doctor(args: argparse.Namespace) -> int:
    try:
        result = doctor(preferred_port=args.port, baud=args.baud)
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP
    emit(result, args.json)
    return EXIT_OK if result.get("ok") else EXIT_PORT


def cmd_status(args: argparse.Namespace) -> int:
    try:
        port = resolve_port(args)
        lines, snap = read_for(port, args.baud, args.seconds, max_lines=args.max_lines)
    except PortError as e:
        emit({"ok": False, "error": str(e), "hint": "Close other serial tools first."}, args.json)
        return EXIT_PORT
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP

    payload = {
        "ok": not snap.crash,
        "port": port,
        "baud": args.baud,
        "seconds": args.seconds,
        "device": snap.to_dict(),
        "provision": provision_status_from_snap(snap),
        "sample_tail": lines[-args.tail :],
    }
    emit(payload, args.json)
    if not args.json:
        print("--- summary ---")
        d = snap.to_dict()
        for key in (
            "project",
            "version",
            "ssid",
            "ip",
            "mqtt",
            "state",
            "ready",
            "crash",
            "provision",
            "softap_ssid",
        ):
            print(f"{key}: {d.get(key)}")
    return EXIT_UNHEALTHY if snap.crash else EXIT_OK


def cmd_read(args: argparse.Namespace) -> int:
    try:
        port = resolve_port(args)
        collected: list[dict[str, Any]] = []

        def on_line(line: str, tag: str | None) -> None:
            row = {"ts": datetime.now().isoformat(timespec="seconds"), "tag": tag, "line": line}
            collected.append(row)
            if not args.json:
                prefix = f"[{tag}] " if tag else ""
                print(f"[{row['ts']}] {prefix}{line}", flush=True)

        lines, snap = read_for(
            port,
            args.baud,
            args.seconds,
            on_line=on_line,
            max_lines=args.max_lines,
        )
    except PortError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_PORT
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP

    if args.output:
        Path(args.output).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    if args.json:
        emit(
            {
                "ok": not snap.crash,
                "port": port,
                "lines": collected,
                "device": snap.to_dict(),
                "output": args.output,
            },
            True,
        )
    return EXIT_UNHEALTHY if snap.crash else EXIT_OK


def cmd_wait(args: argparse.Namespace) -> int:
    try:
        port = resolve_port(args)
        matched, lines, snap, elapsed = wait_for_pattern(
            port, args.baud, args.pattern, args.timeout, ignore_case=not args.case_sensitive
        )
    except PortError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_PORT
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP

    payload = {
        "ok": matched,
        "matched": matched,
        "pattern": args.pattern,
        "elapsed": round(elapsed, 3),
        "port": port,
        "device": snap.to_dict(),
        "tail": lines[-args.tail :],
    }
    emit(payload, args.json)
    if not args.json:
        print("MATCHED" if matched else "TIMEOUT")
    if not matched:
        return EXIT_TIMEOUT
    return EXIT_UNHEALTHY if snap.crash else EXIT_OK


def cmd_send(args: argparse.Namespace) -> int:
    try:
        port = resolve_port(args)
        lines, snap = send_line(
            port, args.baud, args.text, wait=args.wait, newline=not args.no_newline
        )
    except PortError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_PORT
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP

    payload = {
        "ok": True,
        "port": port,
        "sent": args.text,
        "lines": lines,
        "device": snap.to_dict(),
    }
    emit(payload, args.json)
    if not args.json:
        for line in lines:
            print(line)
    return EXIT_OK


def cmd_reset(args: argparse.Namespace) -> int:
    try:
        port = resolve_port(args)
        hard_reset(port, args.baud, into_bootloader=args.bootloader)
    except PortError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_PORT
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP

    payload = {"ok": True, "port": port, "bootloader": args.bootloader}
    emit(payload, args.json)
    if not args.json:
        print(f"Reset pulse sent on {port}")
    return EXIT_OK


def cmd_provision(args: argparse.Namespace) -> int:
    try:
        if args.action == "open":
            url = args.url
            if not url and not args.skip_sample:
                try:
                    sample = sample_provision(
                        port=args.port, baud=args.baud, seconds=args.seconds
                    )
                    url = sample.get("ap_url")
                except PortError:
                    url = None
            result = open_portal(url)
            emit(result, args.json)
            return EXIT_OK if result.get("ok") else EXIT_USAGE
        result = sample_provision(port=args.port, baud=args.baud, seconds=args.seconds)
        emit(result, args.json)
        return EXIT_OK
    except PortError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_PORT
    except RuntimeError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_DEP


def cmd_preset(args: argparse.Namespace) -> int:
    if args.action == "list":
        emit(presets_payload(), args.json)
        return EXIT_OK
    text = get_preset(args.name)
    if not text:
        emit({"ok": False, "error": f"Unknown preset: {args.name}"}, args.json)
        return EXIT_USAGE
    args.text = text
    args.wait = getattr(args, "wait", 2.0)
    args.no_newline = False
    return cmd_send(args)


def cmd_parse(args: argparse.Namespace) -> int:
    path = Path(args.file)
    if not path.is_file():
        emit({"ok": False, "error": f"File not found: {path}"}, args.json)
        return EXIT_USAGE
    text = path.read_text(encoding="utf-8", errors="replace")
    lines, snap = parse_text(text)
    payload = {
        "ok": not snap.crash,
        "file": str(path),
        "device": snap.to_dict(),
        "provision": provision_status_from_snap(snap),
        "line_count": len(lines),
        "tail": lines[-args.tail :],
    }
    emit(payload, args.json)
    return EXIT_UNHEALTHY if snap.crash else EXIT_OK


def cmd_service(args: argparse.Namespace) -> int:
    if args.action == "list":
        emit({"ok": True, "services": list_services()}, args.json)
        return EXIT_OK
    try:
        svc = get_service(args.name)
        result = svc.run(
            port=args.port,
            baud=args.baud,
            seconds=getattr(args, "seconds", 6.0),
            endpoint=getattr(args, "endpoint", None),
            host=getattr(args, "host", None),
            timeout=getattr(args, "timeout", 3.0),
            action=getattr(args, "svc_action", "status"),
            url=getattr(args, "url", None),
        )
    except KeyError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_USAGE
    except PortError as e:
        emit({"ok": False, "error": str(e)}, args.json)
        return EXIT_PORT
    emit(result.to_dict(), args.json)
    return EXIT_OK if result.ok else EXIT_UNHEALTHY


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        from xzkit_server.app import run_server
    except ImportError as e:
        emit(
            {
                "ok": False,
                "error": f"Server deps missing: {e}",
                "hint": "pip install fastapi uvicorn websockets",
            },
            args.json,
        )
        return EXIT_DEP
    cfg = load_config()
    host = args.host or cfg.get("serve_host") or "127.0.0.1"
    port = args.serve_port or cfg.get("serve_port") or 8787
    if args.json:
        emit({"ok": True, "host": host, "port": port, "url": f"http://{host}:{port}"}, True)
    return run_server(
        host=str(host),
        port=int(port),
        serial_port=args.port,
        baud=args.baud,
    )


def build_parser() -> argparse.ArgumentParser:
    cfg = load_config()
    p = argparse.ArgumentParser(
        prog="xzkit",
        description="Open Xiaozhi Kit — AI-friendly serial CLI for ESP32 Xiaozhi",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON on stdout")
    p.add_argument("-p", "--port", default=None, help="Serial port, e.g. COM3")
    p.add_argument("-b", "--baud", type=int, default=int(cfg.get("baud") or 115200))
    p.add_argument("--auto", action="store_true", help="Auto-pick likely ESP port")

    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="List serial ports")
    sub.add_parser("doctor", help="Check deps, ports, openability")

    st = sub.add_parser("status", help="Sample logs and summarize device health")
    st.add_argument("-t", "--seconds", type=float, default=8.0)
    st.add_argument("-n", "--max-lines", type=int, default=None)
    st.add_argument("--tail", type=int, default=20)

    rd = sub.add_parser("read", help="Capture logs for N seconds then exit")
    rd.add_argument("-t", "--seconds", type=float, default=15.0)
    rd.add_argument("-n", "--max-lines", type=int, default=None)
    rd.add_argument("-o", "--output", default=None)

    wt = sub.add_parser("wait", help="Wait until regex matches a log line")
    wt.add_argument("pattern")
    wt.add_argument("-t", "--timeout", type=float, default=60.0)
    wt.add_argument("--case-sensitive", action="store_true")
    wt.add_argument("--tail", type=int, default=15)

    sd = sub.add_parser("send", help="Send one line, then capture reply")
    sd.add_argument("text")
    sd.add_argument("-w", "--wait", type=float, default=2.0)
    sd.add_argument("--no-newline", action="store_true")

    rs = sub.add_parser("reset", help="Pulse DTR/RTS to reset ESP")
    rs.add_argument("--bootloader", action="store_true")

    pv = sub.add_parser("provision", help="WiFi SoftAP provision assist")
    pv.add_argument("action", choices=["status", "open"])
    pv.add_argument("-t", "--seconds", type=float, default=10.0)
    pv.add_argument("--url", default=None)
    pv.add_argument("--skip-sample", action="store_true")

    pr = sub.add_parser("preset", help="List or run named presets")
    pr.add_argument("action", choices=["list", "run"])
    pr.add_argument("name", nargs="?", default=None)
    pr.add_argument("-w", "--wait", type=float, default=2.0)

    pa = sub.add_parser("parse", help="Parse a pasted log file (no serial)")
    pa.add_argument("file")
    pa.add_argument("--tail", type=int, default=30)

    sv = sub.add_parser("service", help="Run pluggable assist services")
    sv.add_argument("action", choices=["list", "run"])
    sv.add_argument("name", nargs="?", default=None)
    sv.add_argument("-t", "--seconds", type=float, default=6.0)
    sv.add_argument("--endpoint", default=None)
    sv.add_argument("--host", default=None)
    sv.add_argument("--timeout", type=float, default=3.0)
    sv.add_argument("--svc-action", default="status")
    sv.add_argument("--url", default=None)

    se = sub.add_parser("serve", help="Start local Web console")
    se.add_argument("--host", default=None)
    se.add_argument("--serve-port", type=int, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "preset" and args.action == "run" and not args.name:
        emit({"ok": False, "error": "preset run requires NAME"}, args.json)
        return EXIT_USAGE
    if args.cmd == "service" and args.action == "run" and not args.name:
        emit({"ok": False, "error": "service run requires NAME"}, args.json)
        return EXIT_USAGE
    handlers = {
        "list": cmd_list,
        "doctor": cmd_doctor,
        "status": cmd_status,
        "read": cmd_read,
        "wait": cmd_wait,
        "send": cmd_send,
        "reset": cmd_reset,
        "provision": cmd_provision,
        "preset": cmd_preset,
        "parse": cmd_parse,
        "service": cmd_service,
        "serve": cmd_serve,
    }
    try:
        return handlers[args.cmd](args)
    except BrokenPipeError:
        return EXIT_OK
    except KeyboardInterrupt:
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
