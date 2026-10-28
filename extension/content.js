/**
 * ExamGuard AI - Browser Extension Content Script
 * Automatically detected by ExamGuard pre-exam environment scan and live proctoring HUD.
 */

(function () {
    const EXT_NAME = "Exam Integrity Extension";
    const EXT_ID = "examguard-extension-v1";
    const EXT_VERSION = "1.0.0";

    console.log(`[ExamGuard Extension] Initialized: ${EXT_NAME} v${EXT_VERSION}`);

    // 1. Mark DOM Elements for Heuristic & Direct Detection
    function injectDOMMarkers() {
        try {
            const root = document.documentElement || document.body;
            if (root) {
                root.setAttribute("data-extension-id", EXT_ID);
                root.setAttribute("data-extension-name", EXT_NAME);
                root.setAttribute("data-extension-detected", "true");
                root.setAttribute("data-extension-version", EXT_VERSION);
                root.classList.add("chrome-extension-active");
            }

            let marker = document.getElementById("examguard-extension-marker");
            if (!marker && (document.body || document.documentElement)) {
                marker = document.createElement("div");
                marker.id = "examguard-extension-marker";
                marker.setAttribute("data-extension-id", EXT_ID);
                marker.setAttribute("data-extension-name", EXT_NAME);
                marker.setAttribute("data-extension-version", EXT_VERSION);
                marker.setAttribute("data-extension-detected", "true");
                marker.style.cssText = "display: none !important; position: absolute; width: 0; height: 0;";
                (document.body || document.documentElement).appendChild(marker);
            }
        } catch (e) {
            console.log("[ExamGuard Extension] DOM marker exception:", e);
        }
    }

    injectDOMMarkers();
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", injectDOMMarkers);
    }

    // 2. Set Global Window Properties & Storage Markers
    try {
        window.__EXAMGUARD_EXTENSION_ACTIVE__ = true;
        window.__EXAMGUARD_EXTENSION_NAME__ = EXT_NAME;
        window.__EXAMGUARD_EXTENSION_ID__ = EXT_ID;
        window.__EXAMGUARD_EXTENSION_VERSION__ = EXT_VERSION;

        window.sessionStorage.setItem("examguard_ext_detected", EXT_NAME);
        window.sessionStorage.setItem("examguard_ext_active", "true");
        window.localStorage.setItem("examguard_ext_detected", EXT_NAME);
    } catch (e) {}

    // 3. Dispatch HTTP Beacon Directly to Local Proctoring Server
    function sendBeacon(eventType) {
        try {
            fetch("http://127.0.0.1:8585/api/extension_event", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_id: "PORTAL_ACTIVE_SESSION",
                    student_id: "STU-2026-081",
                    extension_name: EXT_NAME,
                    extension_id: EXT_ID,
                    version: EXT_VERSION,
                    stage: "PRE_EXAM",
                    source: "CHROME_EXTENSION_LOADED",
                    timestamp: Date.now()
                })
            }).catch(() => {});
        } catch (e) {}
    }

    sendBeacon("CHROME_EXTENSION_LOADED");
    setTimeout(() => sendBeacon("CHROME_EXTENSION_LOADED"), 1500);

    // 4. Bi-directional Ping/Pong Handshake with Main Page & Any Nested Iframes
    function sendPong(targetWindow) {
        const pong = {
            type: "EXAM_INTEGRITY_PONG",
            extensionId: EXT_ID,
            name: EXT_NAME,
            version: EXT_VERSION,
            status: "ACTIVE",
            managedMode: true,
            timestamp: Date.now()
        };

        try { window.postMessage(pong, "*"); } catch (e) {}
        if (targetWindow && targetWindow !== window) {
            try { targetWindow.postMessage(pong, "*"); } catch (e) {}
        }

        // Also broadcast to all iframes on the current page
        try {
            const iframes = document.querySelectorAll("iframe");
            iframes.forEach((f) => {
                try {
                    if (f.contentWindow) {
                        f.contentWindow.postMessage(pong, "*");
                    }
                } catch (err) {}
            });
        } catch (e) {}
    }

    // Listen for PING messages from the examination application or nested components
    window.addEventListener("message", (event) => {
        if (!event.data) return;
        if (event.data.type === "EXAM_INTEGRITY_PING" || event.data.type === "PING_EXTENSION") {
            sendPong(event.source);
        }
    });

    // Periodic announce every 1.5 seconds
    setInterval(() => {
        injectDOMMarkers();
        sendPong(null);
    }, 1500);

    // Initial broadcast
    sendPong(null);
})();
