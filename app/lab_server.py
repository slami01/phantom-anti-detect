"""
Local defensive lab server.

This module starts a closed, local-only target site for classroom testing. The
site collects browser signals, simulates network reputation, calculates a risk
score, and saves JSON reports. It does not target or bypass third-party sites.
"""
import json
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


LAB_PROFILES = {
    "clean": {
        "name": "Clean residential profile",
        "declared_os": "Windows",
        "declared_timezone": "Asia/Tashkent",
        "declared_language": "ru-RU",
        "network": "residential",
        "ip_reputation": "trusted",
        "asn_type": "isp",
        "notes": "Low-risk baseline profile for the lab target."
    },
    "datacenter": {
        "name": "Datacenter proxy profile",
        "declared_os": "Windows",
        "declared_timezone": "Europe/London",
        "declared_language": "ru-RU",
        "network": "proxy",
        "ip_reputation": "poor",
        "asn_type": "hosting",
        "notes": "Simulates a hosting ASN / proxy reputation problem."
    },
    "inconsistent": {
        "name": "Inconsistent fingerprint profile",
        "declared_os": "Mac",
        "declared_timezone": "America/New_York",
        "declared_language": "en-US",
        "network": "residential",
        "ip_reputation": "trusted",
        "asn_type": "isp",
        "notes": "Simulates mismatched OS, language, timezone, and browser signals."
    },
    "fresh": {
        "name": "Fresh session profile",
        "declared_os": "Windows",
        "declared_timezone": "Asia/Tashkent",
        "declared_language": "ru-RU",
        "network": "residential",
        "ip_reputation": "neutral",
        "asn_type": "isp",
        "notes": "Simulates a new browser identity with little storage history."
    }
}


LAB_HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Phantom Defensive Lab</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #647084;
      --line: #d9dfeb;
      --blue: #1d6fdc;
      --green: #168a4a;
      --amber: #b36b00;
      --red: #c93535;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 14px/1.45 "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      background: #172033;
      color: #fff;
      padding: 16px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
    }
    header h1 {
      font-size: 18px;
      margin: 0;
      font-weight: 650;
    }
    header select, header button {
      height: 34px;
      border: 1px solid #31405d;
      border-radius: 6px;
      background: #fff;
      color: #172033;
      padding: 0 10px;
    }
    main {
      max-width: 1180px;
      margin: 18px auto 40px;
      padding: 0 18px;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
    }
    .wide { grid-column: 1 / -1; }
    h2 {
      font-size: 15px;
      margin: 0 0 10px;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      background: #f0f3f8;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      max-height: 320px;
      overflow: auto;
    }
    .score {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .scoreValue {
      width: 96px;
      height: 96px;
      border-radius: 50%;
      display: grid;
      place-items: center;
      color: #fff;
      font-size: 26px;
      font-weight: 700;
      background: var(--green);
    }
    .scoreValue.medium { background: var(--amber); }
    .scoreValue.high { background: var(--red); }
    ul { margin: 8px 0 0 18px; padding: 0; }
    li { margin: 4px 0; }
    .muted { color: var(--muted); }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }
    .kv {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 8px;
      min-height: 56px;
    }
    .kv b { display: block; font-size: 12px; color: var(--muted); }
    @media (max-width: 850px) {
      main { grid-template-columns: 1fr; }
      .wide { grid-column: auto; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Phantom Defensive Lab</h1>
    <div>
      <select id="profileSelect">
        <option value="clean">Clean residential profile</option>
        <option value="datacenter">Datacenter proxy profile</option>
        <option value="inconsistent">Inconsistent fingerprint profile</option>
        <option value="fresh">Fresh session profile</option>
      </select>
      <button id="rerun">Run check</button>
    </div>
  </header>
  <main>
    <section class="wide">
      <h2>Risk Score</h2>
      <div class="score">
        <div id="scoreValue" class="scoreValue">...</div>
        <div>
          <div id="verdict">Waiting for browser signals...</div>
          <div class="muted" id="profileNotes"></div>
          <ul id="reasons"></ul>
        </div>
      </div>
    </section>
    <section>
      <h2>Declared Profile</h2>
      <div class="grid" id="declared"></div>
    </section>
    <section>
      <h2>Observed Browser</h2>
      <div class="grid" id="observed"></div>
    </section>
    <section class="wide">
      <h2>Behavior Layer</h2>
      <p class="muted">Move the mouse, scroll, click, type in the page, then run the check again.</p>
      <pre id="behavior"></pre>
    </section>
    <section class="wide">
      <h2>Raw Report</h2>
      <pre id="raw"></pre>
    </section>
  </main>
  <script>
    const LAB_PROFILES = __LAB_PROFILES__;
    const params = new URLSearchParams(location.search);
    const initialProfile = params.get("profile") || "clean";
    const select = document.getElementById("profileSelect");
    select.value = LAB_PROFILES[initialProfile] ? initialProfile : "clean";

    const behavior = {
      startedAt: Date.now(),
      events: { mousemove: 0, click: 0, wheel: 0, scroll: 0, keydown: 0, focus: 0, blur: 0 },
      mousePath: [],
      clicks: [],
      keys: [],
      scrolls: []
    };

    function sample(list, value, limit = 350) {
      list.push(value);
      if (list.length > limit) list.shift();
    }

    function t() { return Math.round(performance.now()); }

    addEventListener("mousemove", (event) => {
      behavior.events.mousemove += 1;
      if (behavior.events.mousemove % 3 === 0) {
        sample(behavior.mousePath, { t: t(), x: Math.round(event.clientX), y: Math.round(event.clientY) });
      }
    }, { passive: true });
    addEventListener("click", (event) => {
      behavior.events.click += 1;
      sample(behavior.clicks, { t: t(), x: Math.round(event.clientX), y: Math.round(event.clientY) });
    }, { passive: true });
    addEventListener("wheel", (event) => {
      behavior.events.wheel += 1;
      sample(behavior.scrolls, { t: t(), dy: Math.round(event.deltaY), type: "wheel" });
    }, { passive: true });
    addEventListener("scroll", () => {
      behavior.events.scroll += 1;
      sample(behavior.scrolls, { t: t(), y: Math.round(scrollY), type: "scroll" });
    }, { passive: true });
    addEventListener("keydown", (event) => {
      behavior.events.keydown += 1;
      sample(behavior.keys, { t: t(), code: event.code || "", keyLength: String(event.key || "").length });
    }, { passive: true });
    addEventListener("focus", () => behavior.events.focus += 1);
    addEventListener("blur", () => behavior.events.blur += 1);

    function hashString(value) {
      let hash = 2166136261;
      for (let i = 0; i < value.length; i++) {
        hash ^= value.charCodeAt(i);
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(16).padStart(8, "0");
    }

    function canvasHash() {
      try {
        const canvas = document.createElement("canvas");
        canvas.width = 300;
        canvas.height = 90;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#f60";
        ctx.fillRect(0, 0, 300, 90);
        ctx.font = "18px Arial";
        ctx.fillStyle = "#063";
        ctx.fillText("Phantom lab canvas 123", 10, 14);
        return hashString(canvas.toDataURL());
      } catch (error) {
        return "error:" + error.message;
      }
    }

    function webglInfo() {
      try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
        if (!gl) return { supported: false };
        const ext = gl.getExtension("WEBGL_debug_renderer_info");
        return {
          supported: true,
          vendor: gl.getParameter(gl.VENDOR),
          renderer: gl.getParameter(gl.RENDERER),
          unmaskedVendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : null,
          unmaskedRenderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null
        };
      } catch (error) {
        return { supported: false, error: error.message };
      }
    }

    function summarizePath(points) {
      if (!points || points.length < 2) return { points: points ? points.length : 0, distance: 0, durationMs: 0 };
      let distance = 0;
      for (let i = 1; i < points.length; i++) {
        const dx = points[i].x - points[i - 1].x;
        const dy = points[i].y - points[i - 1].y;
        distance += Math.sqrt(dx * dx + dy * dy);
      }
      return {
        points: points.length,
        distance: Math.round(distance),
        durationMs: points[points.length - 1].t - points[0].t
      };
    }

    function collectSignals() {
      const profile = LAB_PROFILES[select.value] || LAB_PROFILES.clean;
      if (select.value !== "fresh") {
        localStorage.setItem("phantom_lab_seen", localStorage.getItem("phantom_lab_seen") || new Date().toISOString());
      } else {
        localStorage.removeItem("phantom_lab_seen");
      }
      document.cookie = "phantom_lab_cookie=1; path=/; SameSite=Lax";

      return {
        collectedAt: new Date().toISOString(),
        profileKey: select.value,
        declaredProfile: profile,
        browser: {
          url: location.href,
          userAgent: navigator.userAgent,
          platform: navigator.platform,
          webdriver: navigator.webdriver,
          languages: navigator.languages,
          language: navigator.language,
          hardwareConcurrency: navigator.hardwareConcurrency,
          deviceMemory: navigator.deviceMemory,
          maxTouchPoints: navigator.maxTouchPoints,
          cookieEnabled: navigator.cookieEnabled,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
          timezoneOffset: new Date().getTimezoneOffset(),
          screen: {
            width: screen.width,
            height: screen.height,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight,
            dpr: devicePixelRatio,
            innerWidth,
            innerHeight
          },
          webgl: webglInfo(),
          canvasHash: canvasHash(),
          storage: {
            cookieLength: document.cookie.length,
            localStorageKeys: Object.keys(localStorage).length,
            sessionStorageKeys: Object.keys(sessionStorage).length,
            indexedDB: Boolean(window.indexedDB),
            serviceWorker: Boolean(navigator.serviceWorker),
            cacheStorage: Boolean(window.caches)
          }
        },
        behavior: {
          durationMs: Date.now() - behavior.startedAt,
          events: behavior.events,
          mouseSummary: summarizePath(behavior.mousePath),
          clickSamples: behavior.clicks.slice(-30),
          keySamples: behavior.keys.slice(-30),
          scrollSamples: behavior.scrolls.slice(-30)
        }
      };
    }

    function kv(container, data) {
      container.innerHTML = "";
      for (const [key, value] of Object.entries(data)) {
        const div = document.createElement("div");
        div.className = "kv";
        div.innerHTML = `<b>${key}</b>${typeof value === "object" ? JSON.stringify(value) : String(value)}`;
        container.appendChild(div);
      }
    }

    async function runCheck() {
      const report = collectSignals();
      const response = await fetch("/api/audit", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(report)
      });
      const result = await response.json();

      const score = document.getElementById("scoreValue");
      score.textContent = result.score;
      score.className = "scoreValue" + (result.score >= 70 ? " high" : result.score >= 35 ? " medium" : "");
      document.getElementById("verdict").textContent = result.verdict;
      document.getElementById("profileNotes").textContent = report.declaredProfile.notes;
      document.getElementById("reasons").innerHTML = result.reasons.map((item) => `<li>${item}</li>`).join("");

      kv(document.getElementById("declared"), report.declaredProfile);
      kv(document.getElementById("observed"), {
        platform: report.browser.platform,
        language: report.browser.language,
        timezone: report.browser.timezone,
        webdriver: report.browser.webdriver,
        webgl: report.browser.webgl.unmaskedRenderer || report.browser.webgl.renderer,
        canvasHash: report.browser.canvasHash,
        storage: report.browser.storage
      });
      document.getElementById("behavior").textContent = JSON.stringify(report.behavior, null, 2);
      document.getElementById("raw").textContent = JSON.stringify({ report, result }, null, 2);
    }

    document.getElementById("rerun").addEventListener("click", runCheck);
    select.addEventListener("change", () => {
      const url = new URL(location.href);
      url.searchParams.set("profile", select.value);
      history.replaceState(null, "", url);
      runCheck();
    });
    runCheck();
  </script>
</body>
</html>
"""


class LabRequestHandler(BaseHTTPRequestHandler):
    server_version = "PhantomLab/1.0"

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("/", "/index.html"):
            self.send_error(404)
            return

        html = LAB_HTML.replace("__LAB_PROFILES__", json.dumps(LAB_PROFILES, ensure_ascii=False))
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "text/html; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/audit":
            self.send_error(404)
            return

        length = int(self.headers.get("content-length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            report = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "invalid JSON")
            return

        result = self.score_report(report)
        report_path = self.save_report(report, result)
        result["reportPath"] = str(report_path.resolve())

        body = json.dumps(result, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def score_report(self, report):
        reasons = []
        score = 0
        profile = report.get("declaredProfile", {})
        browser = report.get("browser", {})
        behavior = report.get("behavior", {})
        storage = browser.get("storage", {})

        if browser.get("webdriver") is True:
            score += 35
            reasons.append("navigator.webdriver is true")

        declared_os = str(profile.get("declared_os", "")).lower()
        platform = str(browser.get("platform", "")).lower()
        user_agent = str(browser.get("userAgent", "")).lower()
        if declared_os == "mac" and "mac" not in platform and "mac" not in user_agent:
            score += 20
            reasons.append("Declared OS is Mac, but observed browser does not look like Mac")
        if declared_os == "windows" and "win" not in platform and "windows" not in user_agent:
            score += 20
            reasons.append("Declared OS is Windows, but observed browser does not look like Windows")

        declared_lang = str(profile.get("declared_language", "")).split("-")[0].lower()
        observed_lang = str(browser.get("language", "")).split("-")[0].lower()
        if declared_lang and observed_lang and declared_lang != observed_lang:
            score += 12
            reasons.append("Declared language does not match browser language")

        declared_tz = profile.get("declared_timezone")
        observed_tz = browser.get("timezone")
        if declared_tz and observed_tz and declared_tz != observed_tz:
            score += 12
            reasons.append("Declared timezone does not match observed timezone")

        if profile.get("ip_reputation") == "poor":
            score += 35
            reasons.append("Simulated IP reputation is poor")
        elif profile.get("ip_reputation") == "neutral":
            score += 10
            reasons.append("Simulated IP reputation is neutral/new")

        if profile.get("asn_type") == "hosting":
            score += 18
            reasons.append("Simulated ASN is hosting/datacenter")

        if not browser.get("cookieEnabled"):
            score += 10
            reasons.append("Cookies are disabled")
        if storage.get("cookieLength", 0) <= 0:
            score += 8
            reasons.append("No visible first-party cookie state")
        if storage.get("localStorageKeys", 0) <= 0:
            score += 8
            reasons.append("No first-party localStorage history")

        events = behavior.get("events", {})
        if behavior.get("durationMs", 0) > 2500:
            if events.get("mousemove", 0) < 3 and events.get("scroll", 0) < 1 and events.get("click", 0) < 1:
                score += 12
                reasons.append("Very little user interaction during the observation window")

        if not reasons:
            reasons.append("No high-risk lab signals detected")

        score = max(0, min(100, score))
        if score >= 70:
            verdict = "High risk: challenge or block in this lab model"
        elif score >= 35:
            verdict = "Medium risk: step-up verification in this lab model"
        else:
            verdict = "Low risk: allow in this lab model"

        return {
            "score": score,
            "verdict": verdict,
            "reasons": reasons,
            "scoredAt": datetime.now().isoformat()
        }

    def save_report(self, report, result):
        output_dir = Path("exports") / "lab_reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = output_dir / f"lab_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"report": report, "result": result}, f, ensure_ascii=False, indent=2)
        return path


class LabServer:
    """Small local-only HTTP server wrapper."""

    def __init__(self, host="127.0.0.1", port=8765):
        self.host = host
        self.port = port
        self._server = None
        self._thread = None

    @property
    def is_running(self):
        return self._server is not None

    def start(self):
        if self._server:
            return self.url()

        self._server = ThreadingHTTPServer((self.host, self.port), LabRequestHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.url()

    def stop(self):
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    def url(self, profile="clean"):
        return f"http://{self.host}:{self.port}/?profile={profile}"
