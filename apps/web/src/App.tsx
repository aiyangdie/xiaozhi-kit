import { useCallback, useEffect, useMemo, useRef, useState } from "react";

type Port = {
  device: string;
  description: string;
  likely_esp: boolean;
};

type LogLine = {
  ts: string;
  tag: string | null;
  line: string;
};

type Provision = {
  status?: string;
  softap_ssid?: string | null;
  ap_url?: string | null;
  ip?: string | null;
  mqtt?: string | null;
  hints?: string[];
};

type Preset = { name: string; text: string };

export default function App() {
  const [ports, setPorts] = useState<Port[]>([]);
  const [port, setPort] = useState("");
  const [baud, setBaud] = useState(115200);
  const [connected, setConnected] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [logs, setLogs] = useState<LogLine[]>([]);
  const [sendText, setSendText] = useState("");
  const [presets, setPresets] = useState<Preset[]>([]);
  const [provision, setProvision] = useState<Provision>({});
  const [error, setError] = useState<string | null>(null);
  const [filterState, setFilterState] = useState(false);
  const [filterCrash, setFilterCrash] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  const refreshPorts = useCallback(async () => {
    const r = await fetch("/api/ports");
    const data = await r.json();
    setPorts(data.ports || []);
    if (!port && data.suggested) setPort(data.suggested);
  }, [port]);

  const refreshStatus = useCallback(async () => {
    const r = await fetch("/api/status");
    const data = await r.json();
    setProvision(data.provision || {});
    setStreaming(!!data.streaming);
  }, []);

  useEffect(() => {
    refreshPorts().catch((e) => setError(String(e)));
    fetch("/api/presets")
      .then((r) => r.json())
      .then((d) => setPresets(d.presets || []))
      .catch(() => undefined);
    const id = setInterval(() => {
      refreshStatus().catch(() => undefined);
    }, 2000);
    return () => clearInterval(id);
  }, [refreshPorts, refreshStatus]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const stopStream = () => {
    wsRef.current?.close();
    wsRef.current = null;
    setStreaming(false);
  };

  const startStream = () => {
    stopStream();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws/logs`);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "error") {
        setError(msg.error);
        setStreaming(false);
        return;
      }
      if (msg.type === "ready") {
        setStreaming(true);
        setError(null);
        return;
      }
      if (msg.type === "line") {
        setLogs((prev) => {
          const next = [...prev, { ts: msg.ts, tag: msg.tag, line: msg.line }];
          return next.length > 2000 ? next.slice(-2000) : next;
        });
        if (msg.provision) {
          setProvision((p) => ({ ...p, status: msg.provision }));
        }
      }
    };
    ws.onclose = () => setStreaming(false);
    ws.onerror = () => setError("WebSocket error — is serial free?");
  };

  const connect = async () => {
    setError(null);
    const r = await fetch("/api/connect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ port, baud }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      setError(data.detail || "Connect failed");
      setConnected(false);
      return;
    }
    setConnected(true);
    startStream();
  };

  const disconnect = async () => {
    stopStream();
    await fetch("/api/disconnect", { method: "POST" });
    setConnected(false);
  };

  const send = async (text: string) => {
    if (!text) return;
    setError(null);
    const r = await fetch("/api/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      setError(data.detail || "Send failed");
    }
  };

  const reset = async (bootloader = false) => {
    const r = await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bootloader }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      setError(data.detail || "Reset failed");
    }
  };

  const openPortal = async () => {
    const r = await fetch("/api/provision/open", { method: "POST", body: "{}" });
    const data = await r.json();
    if (!data.ok) setError(data.error || "Could not open portal");
  };

  const visibleLogs = useMemo(() => {
    return logs.filter((l) => {
      if (filterState && l.tag !== "state" && !/STATE:/i.test(l.line)) return false;
      if (filterCrash && l.tag !== "crash" && !/ESP_ERROR|abort|Backtrace/i.test(l.line))
        return false;
      return true;
    });
  }, [logs, filterState, filterCrash]);

  const provClass =
    provision.status === "connected"
      ? "ok"
      : provision.status === "configuring"
        ? "warn"
        : provision.status === "unprovisioned"
          ? "warn"
          : "";

  return (
    <>
      <header>
        <div>
          <h1>Xiaozhi Kit</h1>
          <p>Local serial console for ESP32 Xiaozhi — logs, reset, provision assist</p>
        </div>
      </header>

      <div className="grid">
        <aside>
          <div className="panel">
            <h2>Connection</h2>
            <label>Port</label>
            <select value={port} onChange={(e) => setPort(e.target.value)}>
              <option value="">Select…</option>
              {ports.map((p) => (
                <option key={p.device} value={p.device}>
                  {p.device} {p.likely_esp ? "★" : ""} — {p.description}
                </option>
              ))}
            </select>
            <label>Baud</label>
            <input
              type="number"
              value={baud}
              onChange={(e) => setBaud(Number(e.target.value))}
            />
            <div className="row">
              <button onClick={connect} disabled={!port}>
                Connect
              </button>
              <button className="secondary" onClick={disconnect}>
                Disconnect
              </button>
              <button className="secondary" onClick={() => refreshPorts()}>
                Refresh
              </button>
            </div>
            <div className="meta">
              {connected ? "Connected" : "Idle"}
              {streaming ? " · streaming" : ""}
            </div>
            {error && <div className="meta status bad">{error}</div>}
          </div>

          <div className="panel">
            <h2>Provision</h2>
            <div className="card">
              <div className={`status ${provClass}`}>{provision.status || "unknown"}</div>
              <div className="meta">SoftAP: {provision.softap_ssid || "—"}</div>
              <div className="meta">URL: {provision.ap_url || "—"}</div>
              <div className="meta">IP: {provision.ip || "—"}</div>
              <div className="meta">MQTT: {provision.mqtt || "—"}</div>
            </div>
            <div className="row">
              <button className="secondary" onClick={openPortal}>
                Open portal
              </button>
            </div>
            {(provision.hints || []).slice(0, 3).map((h, i) => (
              <div className="meta" key={i}>
                {h}
              </div>
            ))}
          </div>

          <div className="panel">
            <h2>Actions</h2>
            <div className="row">
              <button onClick={() => reset(false)}>Reset</button>
              <button className="secondary" onClick={() => reset(true)}>
                Bootloader
              </button>
              <button className="secondary" onClick={() => setLogs([])}>
                Clear logs
              </button>
            </div>
            <label>Send</label>
            <input
              type="text"
              value={sendText}
              onChange={(e) => setSendText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  send(sendText);
                  setSendText("");
                }
              }}
              placeholder="command…"
            />
            <div className="row">
              <button onClick={() => send(sendText)}>Send</button>
              {presets.map((p) => (
                <button key={p.name} className="secondary" onClick={() => send(p.text)}>
                  {p.name}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <main className="panel">
          <h2>Serial log</h2>
          <div className="filters">
            <label>
              <input
                type="checkbox"
                checked={filterState}
                onChange={(e) => setFilterState(e.target.checked)}
              />
              STATE only
            </label>
            <label>
              <input
                type="checkbox"
                checked={filterCrash}
                onChange={(e) => setFilterCrash(e.target.checked)}
              />
              Crash only
            </label>
          </div>
          <div className="logbox">
            {visibleLogs.map((l, i) => (
              <div key={i} className={l.tag === "crash" ? "crash" : undefined}>
                <span className="meta">[{l.ts}] </span>
                {l.tag && <span className="tag">[{l.tag}]</span>}
                {l.line}
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        </main>
      </div>
    </>
  );
}
