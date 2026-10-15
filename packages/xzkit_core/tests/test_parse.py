from pathlib import Path

from xzkit_core.parse import parse_text
from xzkit_core.provision import provision_status_from_snap

FIXTURES = Path(__file__).resolve().parents[3] / "examples" / "fixtures"


def test_provision_ap():
    text = (FIXTURES / "provision_ap.log").read_text(encoding="utf-8")
    _lines, snap = parse_text(text)
    assert snap.state == "configuring"
    assert snap.softap_ssid == "Zhp-A83D"
    assert snap.ap_url == "http://192.168.4.1"
    assert snap.provision == "configuring"
    status = provision_status_from_snap(snap)
    assert status["status"] == "configuring"


def test_mqtt_ready():
    text = (FIXTURES / "mqtt_ready.log").read_text(encoding="utf-8")
    _lines, snap = parse_text(text)
    assert snap.ip == "192.168.1.88"
    assert snap.mqtt == "connected"
    assert snap.ready is True
    assert snap.mqtt_endpoint == "botelv115200.com:1883"
    assert snap.ota_endpoint == "139.224.114.243:8002"
    assert snap.provision == "connected"


def test_dialog():
    text = (FIXTURES / "dialog.log").read_text(encoding="utf-8")
    _lines, snap = parse_text(text)
    assert any(">>" in d for d in snap.dialog)
    assert any("<<" in d for d in snap.dialog)


def test_wifi_crash():
    text = (FIXTURES / "wifi_crash.log").read_text(encoding="utf-8")
    _lines, snap = parse_text(text)
    assert snap.crash is True


def test_usb_reset_not_crash():
    text = (FIXTURES / "usb_reset_noise.log").read_text(encoding="utf-8")
    _lines, snap = parse_text(text)
    assert snap.usb_reset_noise is True
    assert snap.crash is False
    assert snap.version == "1.1.9"
