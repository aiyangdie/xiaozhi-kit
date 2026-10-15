import json
import subprocess
import sys


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    import os

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "xzkit_cli.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )


def test_list_json():
    r = _run("--json", "list")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert isinstance(data, list)


def test_doctor_json():
    r = _run("--json", "doctor")
    assert r.returncode in (0, 2)
    data = json.loads(r.stdout)
    assert "pyserial" in data
    assert "ports" in data


def test_preset_list():
    r = _run("--json", "preset", "list")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["ok"] is True
    names = {p["name"] for p in data["presets"]}
    assert "ping" in names


def test_service_list():
    r = _run("--json", "service", "list")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    names = {s["name"] for s in data["services"]}
    assert "health" in names
    assert "mqtt_probe" in names


def test_parse_fixture():
    from pathlib import Path

    fixture = Path(__file__).resolve().parents[3] / "examples" / "fixtures" / "provision_ap.log"
    r = _run("--json", "parse", str(fixture))
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["device"]["softap_ssid"] == "Zhp-A83D"
