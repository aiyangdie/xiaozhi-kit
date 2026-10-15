"""Local FastAPI + WebSocket console for Xiaozhi Kit."""

from __future__ import annotations

import asyncio
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from xzkit_core.parse import decode_line, update_snapshot, DeviceSnapshot
from xzkit_core.presets import presets_payload
from xzkit_core.provision import open_portal, provision_status_from_snap
from xzkit_core.serial_io import (
    PortBusyError,
    PortError,
    claim_port,
    hard_reset,
    list_ports,
    open_serial,
    pick_port,
    release_port,
    send_line,
)

OWNER = "xzkit-serve"
STATIC_DIR = Path(__file__).resolve().parent / "static"

_state: dict[str, Any] = {
    "serial_port": None,
    "baud": 115200,
    "snap": DeviceSnapshot(),
    "streaming": False,
    "lock": threading.Lock(),
}


def create_app(serial_port: str | None = None, baud: int = 115200) -> FastAPI:
    _state["serial_port"] = serial_port
    _state["baud"] = baud
    app = FastAPI(title="Xiaozhi Kit Console", version="0.1.0")

    @app.get("/api/health")
    def api_health() -> dict[str, Any]:
        return {"ok": True, "owner": OWNER, "streaming": _state["streaming"]}

    @app.get("/api/ports")
    def api_ports() -> dict[str, Any]:
        try:
            ports = [p.to_dict() for p in list_ports()]
        except RuntimeError as e:
            raise HTTPException(status_code=500, detail=str(e)) from e
        return {
            "ok": True,
            "ports": ports,
            "suggested": pick_port(esp_only=True) or pick_port(),
            "selected": _state["serial_port"],
        }

    @app.post("/api/connect")
    def api_connect(body: dict[str, Any]) -> dict[str, Any]:
        port = body.get("port") or _state["serial_port"] or pick_port(esp_only=True)
        baud_v = int(body.get("baud") or _state["baud"] or 115200)
        if not port:
            raise HTTPException(status_code=400, detail="No port")
        try:
            claim_port(OWNER)
            ser = open_serial(str(port), baud_v)
            ser.close()
        except PortBusyError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        except PortError as e:
            release_port(OWNER)
            raise HTTPException(status_code=400, detail=str(e)) from e
        _state["serial_port"] = str(port)
        _state["baud"] = baud_v
        return {"ok": True, "port": port, "baud": baud_v}

    @app.post("/api/disconnect")
    def api_disconnect() -> dict[str, Any]:
        release_port(OWNER)
        _state["streaming"] = False
        return {"ok": True}

    @app.get("/api/status")
    def api_status() -> dict[str, Any]:
        snap: DeviceSnapshot = _state["snap"]
        return {
            "ok": not snap.crash,
            "port": _state["serial_port"],
            "baud": _state["baud"],
            "streaming": _state["streaming"],
            "device": snap.to_dict(),
            "provision": provision_status_from_snap(snap),
        }

    @app.post("/api/send")
    def api_send(body: dict[str, Any]) -> dict[str, Any]:
        port = _state["serial_port"]
        if not port:
            raise HTTPException(status_code=400, detail="Not connected")
        text = body.get("text") or ""
        try:
            lines, snap = send_line(str(port), int(_state["baud"]), text, wait=float(body.get("wait") or 1.5))
            _state["snap"] = snap
        except PortError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        return {"ok": True, "lines": lines, "device": snap.to_dict()}

    @app.post("/api/reset")
    def api_reset(body: dict[str, Any] | None = None) -> dict[str, Any]:
        body = body or {}
        port = _state["serial_port"] or pick_port(esp_only=True)
        if not port:
            raise HTTPException(status_code=400, detail="No port")
        try:
            hard_reset(str(port), int(_state["baud"]), into_bootloader=bool(body.get("bootloader")))
        except PortError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e
        return {"ok": True, "port": port, "bootloader": bool(body.get("bootloader"))}

    @app.get("/api/presets")
    def api_presets() -> dict[str, Any]:
        return presets_payload()

    @app.get("/api/provision")
    def api_provision() -> dict[str, Any]:
        return provision_status_from_snap(_state["snap"])

    @app.post("/api/provision/open")
    def api_provision_open(body: dict[str, Any] | None = None) -> dict[str, Any]:
        body = body or {}
        url = body.get("url") or provision_status_from_snap(_state["snap"]).get("ap_url")
        return open_portal(url)

    @app.websocket("/ws/logs")
    async def ws_logs(ws: WebSocket) -> None:
        await ws.accept()
        port = _state["serial_port"] or pick_port(esp_only=True)
        baud = int(_state["baud"])
        if not port:
            await ws.send_json({"type": "error", "error": "No serial port selected"})
            await ws.close()
            return
        try:
            claim_port(OWNER)
        except PortBusyError as e:
            await ws.send_json({"type": "error", "error": str(e)})
            await ws.close(code=1013)
            return

        _state["serial_port"] = port
        _state["streaming"] = True
        snap = DeviceSnapshot()
        _state["snap"] = snap
        loop = asyncio.get_event_loop()
        stop = threading.Event()

        def reader() -> None:
            try:
                ser = open_serial(str(port), baud, timeout=0.2)
            except PortError as e:
                asyncio.run_coroutine_threadsafe(
                    ws.send_json({"type": "error", "error": str(e)}),
                    loop,
                )
                return
            try:
                while not stop.is_set():
                    raw = ser.readline()
                    if not raw:
                        continue
                    line = decode_line(raw)
                    tag = update_snapshot(snap, line)
                    _state["snap"] = snap
                    msg = {
                        "type": "line",
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "tag": tag,
                        "line": line,
                        "provision": snap.provision,
                    }
                    fut = asyncio.run_coroutine_threadsafe(ws.send_json(msg), loop)
                    try:
                        fut.result(timeout=2)
                    except Exception:  # noqa: BLE001
                        break
            finally:
                ser.close()

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        try:
            await ws.send_json({"type": "ready", "port": port, "baud": baud})
            while True:
                data = await ws.receive_text()
                if data == "ping":
                    await ws.send_json({"type": "pong"})
        except WebSocketDisconnect:
            pass
        finally:
            stop.set()
            _state["streaming"] = False
            release_port(OWNER)
            t.join(timeout=1.0)

    if STATIC_DIR.is_dir():
        assets = STATIC_DIR / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        def index() -> FileResponse:
            return FileResponse(STATIC_DIR / "index.html")

    return app


def run_server(
    host: str = "127.0.0.1",
    port: int = 8787,
    serial_port: str | None = None,
    baud: int = 115200,
) -> int:
    import uvicorn

    app = create_app(serial_port=serial_port, baud=baud)
    print(f"Xiaozhi Kit console: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
