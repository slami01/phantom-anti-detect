"""
Defensive browser security audit helpers.

The module collects observable browser, storage, tracker, and behavior signals
from the currently loaded page. It does not bypass CAPTCHA, Cloudflare,
Turnstile, or any other site protection.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class SecurityAudit:
    """Builds JavaScript probes and exports browser audit reports."""

    def browser_signal_script(self) -> str:
        return r"""
(() => {
    const now = new Date();

    function safe(fn, fallback = null) {
        try {
            return fn();
        } catch (error) {
            return { error: String(error && error.message ? error.message : error) };
        }
    }

    function hashString(value) {
        let hash = 2166136261;
        for (let i = 0; i < value.length; i++) {
            hash ^= value.charCodeAt(i);
            hash = Math.imul(hash, 16777619);
        }
        return (hash >>> 0).toString(16).padStart(8, "0");
    }

    function canvasProbe() {
        return safe(() => {
            const canvas = document.createElement("canvas");
            canvas.width = 280;
            canvas.height = 80;
            const ctx = canvas.getContext("2d");
            ctx.textBaseline = "top";
            ctx.font = "16px Arial";
            ctx.fillStyle = "#f60";
            ctx.fillRect(0, 0, 280, 80);
            ctx.fillStyle = "#069";
            ctx.fillText("Phantom audit canvas 123", 8, 8);
            ctx.fillStyle = "rgba(102, 204, 0, 0.7)";
            ctx.fillText("Fingerprint sample", 10, 34);
            const data = canvas.toDataURL();
            return { hash: hashString(data), length: data.length };
        });
    }

    function webglProbe() {
        return safe(() => {
            const canvas = document.createElement("canvas");
            const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
            if (!gl) return { supported: false };
            const ext = gl.getExtension("WEBGL_debug_renderer_info");
            return {
                supported: true,
                vendor: gl.getParameter(gl.VENDOR),
                renderer: gl.getParameter(gl.RENDERER),
                version: gl.getParameter(gl.VERSION),
                shadingLanguageVersion: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
                unmaskedVendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : null,
                unmaskedRenderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null,
                maxTextureSize: gl.getParameter(gl.MAX_TEXTURE_SIZE),
                maxViewportDims: Array.from(gl.getParameter(gl.MAX_VIEWPORT_DIMS) || [])
            };
        });
    }

    function permissionsProbe() {
        return {
            permissionsApi: Boolean(navigator.permissions && navigator.permissions.query),
            notificationPermission: typeof Notification !== "undefined" ? Notification.permission : "unsupported",
            geolocationApi: Boolean(navigator.geolocation),
            mediaDevicesApi: Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
            clipboardApi: Boolean(navigator.clipboard)
        };
    }

    function storageProbe() {
        const result = safe(() => ({
            cookiesEnabled: navigator.cookieEnabled,
            cookieLength: document.cookie ? document.cookie.length : 0,
            localStorageKeys: window.localStorage ? Object.keys(localStorage).length : null,
            sessionStorageKeys: window.sessionStorage ? Object.keys(sessionStorage).length : null
        }), {});

        result.indexedDBApi = Boolean(window.indexedDB);
        result.indexedDBDatabaseListingApi = Boolean(window.indexedDB && indexedDB.databases);
        result.serviceWorkers = {
            supported: Boolean(navigator.serviceWorker),
            controller: Boolean(navigator.serviceWorker && navigator.serviceWorker.controller)
        };
        result.cacheStorageApi = Boolean(window.caches && caches.keys);

        return result;
    }

    function trackerProbe() {
        const patterns = {
            googleAnalytics: ["google-analytics.com", "googletagmanager.com", "/gtag/js"],
            metaPixel: ["connect.facebook.net", "facebook.com/tr"],
            tiktokPixel: ["analytics.tiktok.com", "tiktok.com/i18n/pixel"],
            hotjar: ["hotjar.com", "static.hotjar.com"],
            amplitude: ["amplitude.com", "api2.amplitude.com"],
            remarketing: ["doubleclick.net", "adservice.google.com", "googleadservices.com"]
        };
        const urls = [];
        const nodes = Array.from(document.querySelectorAll("script[src], img[src], iframe[src], link[href]"));
        for (const node of nodes) {
            urls.push(node.src || node.href || "");
        }
        const resources = performance.getEntriesByType("resource").map((entry) => entry.name);
        urls.push(...resources);

        const matches = {};
        for (const [name, needles] of Object.entries(patterns)) {
            const found = [...new Set(urls.filter((url) => needles.some((needle) => url.includes(needle))))];
            matches[name] = found.slice(0, 20);
        }

        const linkParams = {};
        for (const [key, value] of new URL(location.href).searchParams.entries()) {
            if (/^(utm_|gclid|fbclid|ttclid|mc_|yclid|msclkid)/i.test(key)) {
                linkParams[key] = value;
            }
        }

        return { matches, linkDecorationParams: linkParams };
    }

    function resourceProbe() {
        const entries = performance.getEntriesByType("resource").slice(-250);
        const byOrigin = {};
        for (const entry of entries) {
            let origin = "unknown";
            try {
                origin = new URL(entry.name).origin;
            } catch (_) {}
            if (!byOrigin[origin]) {
                byOrigin[origin] = { count: 0, transferSize: 0, initiatorTypes: {} };
            }
            byOrigin[origin].count += 1;
            byOrigin[origin].transferSize += entry.transferSize || 0;
            byOrigin[origin].initiatorTypes[entry.initiatorType || "unknown"] =
                (byOrigin[origin].initiatorTypes[entry.initiatorType || "unknown"] || 0) + 1;
        }
        return byOrigin;
    }

    return {
        collectedAt: now.toISOString(),
        page: {
            url: location.href,
            origin: location.origin,
            title: document.title,
            referrer: document.referrer,
            protocol: location.protocol
        },
        navigator: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            webdriver: navigator.webdriver,
            languages: navigator.languages,
            language: navigator.language,
            hardwareConcurrency: navigator.hardwareConcurrency,
            deviceMemory: navigator.deviceMemory,
            maxTouchPoints: navigator.maxTouchPoints,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            vendor: navigator.vendor,
            productSub: navigator.productSub,
            pdfViewerEnabled: navigator.pdfViewerEnabled
        },
        screen: {
            width: screen.width,
            height: screen.height,
            availWidth: screen.availWidth,
            availHeight: screen.availHeight,
            colorDepth: screen.colorDepth,
            pixelDepth: screen.pixelDepth,
            devicePixelRatio: window.devicePixelRatio,
            innerWidth: window.innerWidth,
            innerHeight: window.innerHeight,
            outerWidth: window.outerWidth,
            outerHeight: window.outerHeight
        },
        timezone: {
            intl: Intl.DateTimeFormat().resolvedOptions().timeZone,
            offsetMinutes: new Date().getTimezoneOffset(),
            locale: Intl.DateTimeFormat().resolvedOptions().locale
        },
        webgl: webglProbe(),
        canvas: canvasProbe(),
        permissions: permissionsProbe(),
        storage: storageProbe(),
        trackers: trackerProbe(),
        resourcesByOrigin: resourceProbe()
    };
})()
"""

    def install_behavior_recorder_script(self) -> str:
        return r"""
(() => {
    if (window.__phantomAuditBehavior && window.__phantomAuditBehavior.installed) {
        return "already_installed";
    }

    const state = {
        installed: true,
        startedAt: Date.now(),
        events: {
            mousemove: 0,
            click: 0,
            wheel: 0,
            scroll: 0,
            keydown: 0,
            focus: 0,
            blur: 0,
            visibilitychange: 0
        },
        mousePath: [],
        clicks: [],
        keys: [],
        scrolls: [],
        focusTransitions: []
    };

    function now() {
        return Math.round(performance.now());
    }

    function sample(list, value, limit = 600) {
        list.push(value);
        if (list.length > limit) list.shift();
    }

    window.addEventListener("mousemove", (event) => {
        state.events.mousemove += 1;
        if (state.events.mousemove % 3 === 0) {
            sample(state.mousePath, { t: now(), x: Math.round(event.clientX), y: Math.round(event.clientY) });
        }
    }, { passive: true });

    window.addEventListener("click", (event) => {
        state.events.click += 1;
        sample(state.clicks, { t: now(), x: Math.round(event.clientX), y: Math.round(event.clientY), button: event.button });
    }, { passive: true });

    window.addEventListener("wheel", (event) => {
        state.events.wheel += 1;
        sample(state.scrolls, { t: now(), type: "wheel", dx: Math.round(event.deltaX), dy: Math.round(event.deltaY) });
    }, { passive: true });

    window.addEventListener("scroll", () => {
        state.events.scroll += 1;
        sample(state.scrolls, { t: now(), type: "scroll", x: Math.round(scrollX), y: Math.round(scrollY) });
    }, { passive: true });

    window.addEventListener("keydown", (event) => {
        state.events.keydown += 1;
        sample(state.keys, { t: now(), keyLength: String(event.key || "").length, code: event.code || "" });
    }, { passive: true });

    window.addEventListener("focus", () => {
        state.events.focus += 1;
        sample(state.focusTransitions, { t: now(), type: "focus" });
    }, { passive: true });

    window.addEventListener("blur", () => {
        state.events.blur += 1;
        sample(state.focusTransitions, { t: now(), type: "blur" });
    }, { passive: true });

    document.addEventListener("visibilitychange", () => {
        state.events.visibilitychange += 1;
        sample(state.focusTransitions, { t: now(), type: document.visibilityState });
    }, { passive: true });

    window.__phantomAuditBehavior = state;
    return "installed";
})()
"""

    def collect_behavior_script(self) -> str:
        return r"""
(() => {
    const state = window.__phantomAuditBehavior;
    if (!state) return { installed: false };

    function summarizePath(points) {
        if (!points || points.length < 2) {
            return { points: points ? points.length : 0, distance: 0, durationMs: 0, avgSpeedPxPerSec: 0 };
        }
        let distance = 0;
        for (let i = 1; i < points.length; i++) {
            const dx = points[i].x - points[i - 1].x;
            const dy = points[i].y - points[i - 1].y;
            distance += Math.sqrt(dx * dx + dy * dy);
        }
        const durationMs = Math.max(1, points[points.length - 1].t - points[0].t);
        return {
            points: points.length,
            distance: Math.round(distance),
            durationMs,
            avgSpeedPxPerSec: Math.round(distance / durationMs * 1000)
        };
    }

    function intervals(items) {
        if (!items || items.length < 2) return [];
        const values = [];
        for (let i = 1; i < items.length; i++) values.push(items[i].t - items[i - 1].t);
        return values.slice(-100);
    }

    return {
        installed: true,
        startedAt: new Date(state.startedAt).toISOString(),
        durationMs: Date.now() - state.startedAt,
        events: state.events,
        mouseSummary: summarizePath(state.mousePath),
        clickIntervalsMs: intervals(state.clicks),
        keyIntervalsMs: intervals(state.keys),
        scrollSamples: state.scrolls.slice(-100),
        focusTransitions: state.focusTransitions.slice(-100)
    };
})()
"""

    def save_report(self, report: Dict[str, Any], export_dir: str = "exports") -> Path:
        output_dir = Path(export_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"audit_{timestamp}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path

    def format_report(self, report: Dict[str, Any]) -> str:
        nav = report.get("navigator", {})
        screen = report.get("screen", {})
        timezone = report.get("timezone", {})
        webgl = report.get("webgl", {})
        storage = report.get("storage", {})
        trackers = report.get("trackers", {}).get("matches", {})
        behavior = report.get("behavior", {})

        tracker_lines = []
        for name, matches in trackers.items():
            tracker_lines.append(f"{name}: {len(matches)}")

        return "\n".join([
            f"URL: {report.get('page', {}).get('url', '')}",
            f"Collected: {report.get('collectedAt', '')}",
            "",
            "Navigator",
            f"  User-Agent: {nav.get('userAgent')}",
            f"  Platform: {nav.get('platform')}",
            f"  webdriver: {nav.get('webdriver')}",
            f"  Languages: {nav.get('languages')}",
            f"  Hardware: cores={nav.get('hardwareConcurrency')} memory={nav.get('deviceMemory')}",
            "",
            "Screen / Timezone",
            f"  Screen: {screen.get('width')}x{screen.get('height')} DPR={screen.get('devicePixelRatio')}",
            f"  Window: {screen.get('innerWidth')}x{screen.get('innerHeight')}",
            f"  Timezone: {timezone.get('intl')} offset={timezone.get('offsetMinutes')}",
            "",
            "WebGL / Canvas",
            f"  WebGL: {webgl.get('unmaskedVendor') or webgl.get('vendor')} / {webgl.get('unmaskedRenderer') or webgl.get('renderer')}",
            f"  Canvas hash: {report.get('canvas', {}).get('hash')}",
            "",
            "Storage",
            f"  Cookie length: {storage.get('cookieLength')}",
            f"  LocalStorage keys: {storage.get('localStorageKeys')}",
            f"  SessionStorage keys: {storage.get('sessionStorageKeys')}",
            f"  IndexedDB: {storage.get('indexedDBDatabases')}",
            f"  Service workers: {storage.get('serviceWorkers')}",
            "",
            "Trackers",
            "  " + "\n  ".join(tracker_lines),
            "",
            "Behavior Recorder",
            f"  Installed: {behavior.get('installed', False)}",
            f"  Events: {behavior.get('events', {})}",
            f"  Mouse summary: {behavior.get('mouseSummary', {})}",
        ])
