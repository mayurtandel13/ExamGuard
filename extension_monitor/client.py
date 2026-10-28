"""
Client-side JavaScript Injection Generator for Browser Extension & DOM Integrity Monitoring
"""

import json


def get_integrity_client_js(exam_session_id: str, student_id: str) -> str:
    """
    Returns HTML + JavaScript snippet to embed in Streamlit via st.components.v1.html.
    Implements MutationObserver, window focus/blur tracking, extension ping-pong handshake,
    and overlay detection.
    """
    return f"""
    <div id="integrity-telemetry-hud" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 10px 14px;
        margin-top: 8px;
        font-size: 12px;
        color: #334155;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span id="integrity-pulse" style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #10b981;"></span>
                <span style="font-weight: 600; color: #0f172a;">Browser Environment & DOM Integrity Guard</span>
            </div>
            <div id="ext-status-badge" style="background: #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 600; font-size: 11px;">
                Scanning Environment...
            </div>
        </div>
        <div id="integrity-metrics" style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-top: 8px; font-size: 11px;">
            <div style="background: #ffffff; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0;">
                <span style="color: #64748b;">Browser:</span> <strong id="val-browser">Detecting...</strong>
            </div>
            <div style="background: #ffffff; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0;">
                <span style="color: #64748b;">Observer:</span> <strong id="val-observer" style="color: #10b981;">Active</strong>
            </div>
            <div style="background: #ffffff; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0;">
                <span style="color: #64748b;">Tab Switches:</span> <strong id="val-blurs" style="color: #0f172a;">0</strong>
            </div>
            <div style="background: #ffffff; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0;">
                <span style="color: #64748b;">Tab Risk:</span> <strong id="val-tab-risk" style="color: #10b981;">NORMAL</strong>
            </div>
            <div style="background: #ffffff; padding: 6px; border-radius: 4px; border: 1px solid #e2e8f0;">
                <span style="color: #64748b;">Shortcuts:</span> <strong id="val-shortcuts" style="color: #0f172a;">0</strong>
            </div>
        </div>
        <div id="integrity-log" style="margin-top: 6px; font-size: 11px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            Status: Initialized environment checks. No interference observed.
        </div>
        <div id="tab-warning-alert" style="display: none; margin-top: 8px; padding: 8px 12px; background: #fff1f2; border: 1.5px solid #e11d48; border-radius: 6px; color: #9f1239; font-weight: 600; font-size: 11px;">
            🚨 <strong>HIGH-RISK PROCTORING ALERT: Tab Switch Detected!</strong> Navigating away from the examination window is recorded at <strong>HIGH RISK</strong> (<span id="tab-warn-count">1</span> incident). Tab detection risk elevated to <strong>HIGH</strong>.
        </div>
        <div id="keyboard-warning-alert" style="display: none; margin-top: 8px; padding: 8px 12px; background: #fff1f2; border: 1.5px solid #e11d48; border-radius: 6px; color: #9f1239; font-weight: 600; font-size: 11px;">
            🚨 <strong>PROCTORING ALERT: Forbidden Key Detected (<span id="kb-warn-key">CTRL+C</span>)!</strong> Keystroke recorded and cheating score penalized (<span id="kb-warn-count">1</span> violation).
        </div>
    </div>

    <script>
    (function() {{
        const SESSION_ID = "{exam_session_id}";
        const STUDENT_ID = "{student_id}";

        let blurCount = 0;
        let mutationCount = 0;
        let extensionConnected = false;

        // 1. Detect Browser & Features
        function detectBrowser() {{
            const ua = navigator.userAgent;
            let browser = "Unknown";
            let ver = "0";

            if (ua.indexOf("Edg/") > -1) {{
                browser = "Edge";
                ver = (ua.match(/Edg\\/([0-9]+)/) || [])[1] || "";
            }} else if (ua.indexOf("Chrome/") > -1) {{
                browser = "Chrome";
                ver = (ua.match(/Chrome\\/([0-9]+)/) || [])[1] || "";
            }} else if (ua.indexOf("Firefox/") > -1) {{
                browser = "Firefox";
                ver = (ua.match(/Firefox\\/([0-9]+)/) || [])[1] || "";
            }} else if (ua.indexOf("Safari/") > -1) {{
                browser = "Safari";
                ver = (ua.match(/Version\\/([0-9]+)/) || [])[1] || "";
            }}

            const el = document.getElementById("val-browser");
            if (el) el.innerText = browser + " v" + ver;
            return {{ browser, ver, ua }};
        }}

        detectBrowser();

        // 2. Ping Companion & Detect Extension Presence
        function pingInstitutionalExtension() {{
            const pingMsg = {{
                type: "EXAM_INTEGRITY_PING",
                sessionId: SESSION_ID,
                timestamp: Date.now()
            }};

            try {{ window.postMessage(pingMsg, "*"); }} catch(e) {{}}
            try {{ if (window.parent && window.parent !== window) window.parent.postMessage(pingMsg, "*"); }} catch(e) {{}}
            try {{ if (window.top && window.top !== window) window.top.postMessage(pingMsg, "*"); }} catch(e) {{}}

            // Check DOM marker directly
            try {{
                const targetDoc = window.parent ? window.parent.document : document;
                const marker = targetDoc.getElementById("examguard-extension-marker") || document.getElementById("examguard-extension-marker");
                if (marker) {{
                    setExtensionConnected(marker.getAttribute("data-extension-name") || "Exam Integrity Extension");
                }}
            }} catch(e) {{}}

            setTimeout(() => {{
                const badge = document.getElementById("ext-status-badge");
                if (!extensionConnected && badge) {{
                    badge.innerText = "Extension: Optional (Unmanaged)";
                    badge.style.background = "#f1f5f9";
                    badge.style.color = "#475569";
                }}
            }}, 1500);
        }}

        function setExtensionConnected(extName) {{
            extensionConnected = true;
            const badge = document.getElementById("ext-status-badge");
            if (badge) {{
                badge.innerText = "Extension: Connected (v1.0.0)";
                badge.style.background = "#dcfce7";
                badge.style.color = "#166534";
            }}
            const log = document.getElementById("integrity-log");
            if (log) log.innerText = "Institutional extension (" + extName + ") verified and securely connected.";
        }}

        function onPongMsg(event) {{
            if (event.data && (event.data.type === "EXAM_INTEGRITY_PONG" || event.data.type === "PONG_EXTENSION")) {{
                setExtensionConnected(event.data.name || event.data.extensionId || "Exam Integrity Extension");
            }}
        }}

        window.addEventListener("message", onPongMsg);
        try {{ if (window.parent) window.parent.addEventListener("message", onPongMsg); }} catch(e) {{}}

        pingInstitutionalExtension();
        setInterval(pingInstitutionalExtension, 2500);

        // 3. MutationObserver on document
        try {{
            const targetDoc = window.parent ? window.parent.document : document;
            const targetRoot = targetDoc.body || targetDoc.documentElement;

            const observer = new MutationObserver((mutations) => {{
                for (let mutation of mutations) {{
                    for (let node of mutation.addedNodes) {{
                        if (node.nodeType === 1) {{
                            const tag = node.tagName.toLowerCase();
                            const src = node.getAttribute("src") || "";
                            const href = node.getAttribute("href") || "";

                            // Check for extension protocol injection
                            if (src.includes("chrome-extension://") || href.includes("chrome-extension://") ||
                                src.includes("moz-extension://") || href.includes("moz-extension://")) {{
                                mutationCount++;
                                updateLog("WARNING: Foreign extension asset injected: " + tag);
                            }}
                        }}
                    }}
                }}
            }});

            observer.observe(targetRoot, {{ childList: true, subtree: true, attributes: false }});
        }} catch(e) {{
            console.log("[Integrity] MutationObserver sandbox notice:", e);
        }}

        // 4. Focus, Blur & Tab Visibility Listeners
        const targetWin = window.parent ? window.parent : window;
        const targetDoc = window.parent ? window.parent.document : document;

        function handleTabSwitch() {{
            blurCount++;
            const blursEl = document.getElementById("val-blurs");
            if (blursEl) {{
                blursEl.innerText = blurCount;
                blursEl.style.color = "#dc2626";
            }}
            const tabRiskEl = document.getElementById("val-tab-risk");
            if (tabRiskEl) {{
                tabRiskEl.innerHTML = "<span style='color: #e11d48; font-weight: bold;'>HIGH</span>";
            }}
            updateLog("🚨 HIGH-RISK VIOLATION: Candidate switched window or backgrounded tab (" + blurCount + ") - Risk: HIGH");

            // 1. Show warning alert inside the integrity HUD
            const warnBanner = document.getElementById("tab-warning-alert");
            if (warnBanner) {{
                warnBanner.style.display = "block";
                const countSpan = document.getElementById("tab-warn-count");
                if (countSpan) countSpan.innerText = blurCount;
            }}

            // 2. Inject high-visibility floating proctoring warning in main window
            try {{
                if (window.parent && window.parent.document) {{
                    let parentBanner = window.parent.document.getElementById("exam-live-tab-warning");
                    if (!parentBanner) {{
                        parentBanner = window.parent.document.createElement("div");
                        parentBanner.id = "exam-live-tab-warning";
                        parentBanner.style.cssText = "position:fixed; top:20px; left:50%; transform:translateX(-50%); z-index:999999; background:#fff1f2; border:2.5px solid #e11d48; color:#9f1239; padding:14px 28px; border-radius:10px; box-shadow:0 10px 30px rgba(225,29,72,0.4); font-family:sans-serif; font-size:15px; font-weight:bold; display:flex; align-items:center; gap:12px; transition: all 0.3s ease;";
                        window.parent.document.body.appendChild(parentBanner);
                    }}
                    parentBanner.innerHTML = "<span>🚨</span> <span><strong>HIGH-RISK PROCTORING VIOLATION:</strong> Tab switch detected! Navigating away from the examination window is recorded at <strong>HIGH RISK</strong>. Tab detection risk elevated to <strong>HIGH</strong>. (Incident #" + blurCount + ")</span>";
                    parentBanner.style.display = "flex";
                    setTimeout(() => {{
                        if (parentBanner) parentBanner.style.display = "none";
                    }}, 7000);
                }}
            }} catch(e) {{
                console.log("[Integrity] Parent banner exception:", e);
            }}

            // 3. Send beacon to local proctoring server
            try {{
                fetch("http://127.0.0.1:8585/api/tab_switch", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        session_id: SESSION_ID,
                        student_id: STUDENT_ID,
                        count: blurCount,
                        risk_level: "HIGH"
                    }})
                }}).catch(() => {{}});
            }} catch(e) {{}}
        }}

        targetWin.addEventListener("blur", handleTabSwitch);
        targetDoc.addEventListener("visibilitychange", () => {{
            if (targetDoc.hidden) {{
                handleTabSwitch();
            }}
        }});

        // 5. Browser-Side Keyboard Shortcut & Clipboard Violation Monitor
        let kbViolationCount = 0;
        let lastViolationTime = 0;

        function handleKeyboardViolation(shortcutName, keyName) {{
            const now = Date.now();
            if (now - lastViolationTime < 350) return;
            lastViolationTime = now;

            kbViolationCount++;
            const shortcutsEl = document.getElementById("val-shortcuts");
            if (shortcutsEl) {{
                shortcutsEl.innerText = kbViolationCount;
                shortcutsEl.style.color = "#dc2626";
            }}
            updateLog("WARNING: Forbidden key detected: " + shortcutName.toUpperCase() + " (" + kbViolationCount + ")");

            const kbAlert = document.getElementById("keyboard-warning-alert");
            if (kbAlert) {{
                kbAlert.style.display = "block";
                const keySpan = document.getElementById("kb-warn-key");
                if (keySpan) keySpan.innerText = shortcutName.toUpperCase();
                const countSpan = document.getElementById("kb-warn-count");
                if (countSpan) countSpan.innerText = kbViolationCount;
            }}

            try {{
                if (window.parent && window.parent.document) {{
                    let parentBanner = window.parent.document.getElementById("exam-live-kb-warning");
                    if (!parentBanner) {{
                        parentBanner = window.parent.document.createElement("div");
                        parentBanner.id = "exam-live-kb-warning";
                        parentBanner.style.cssText = "position:fixed; top:20px; left:50%; transform:translateX(-50%); z-index:999999; background:#fff1f2; border:2.5px solid #e11d48; color:#9f1239; padding:14px 28px; border-radius:10px; box-shadow:0 10px 30px rgba(225,29,72,0.4); font-family:sans-serif; font-size:15px; font-weight:bold; display:flex; align-items:center; gap:12px; transition: all 0.3s ease;";
                        window.parent.document.body.appendChild(parentBanner);
                    }}
                    parentBanner.innerHTML = "<span>🚨</span> <span><strong>PROCTORING WARNING:</strong> Forbidden Shortcut Detected: <code>" + shortcutName.toUpperCase() + "</code>! Keystroke recorded and cheating score penalized. (Incident #" + kbViolationCount + ")</span>";
                    parentBanner.style.display = "flex";
                    setTimeout(() => {{
                        if (parentBanner) parentBanner.style.display = "none";
                    }}, 6000);
                }}
            }} catch(e) {{
                console.log("[Integrity] Keyboard parent banner exception:", e);
            }}

            try {{
                fetch("http://127.0.0.1:8585/api/keyboard_event", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        session_id: SESSION_ID,
                        student_id: STUDENT_ID,
                        shortcut: shortcutName,
                        key: keyName,
                        count: kbViolationCount,
                        timestamp: now
                    }})
                }}).catch(() => {{}});
            }} catch(e) {{}}
        }}

        function onKeyDownHandler(e) {{
            const key = e.key ? e.key.toLowerCase() : "";
            const isCtrl = e.ctrlKey || e.metaKey;
            const isAlt = e.altKey;

            if (isCtrl) {{
                if (key === "c") handleKeyboardViolation("ctrl+c", "c");
                else if (key === "v") handleKeyboardViolation("ctrl+v", "v");
                else if (key === "x") handleKeyboardViolation("ctrl+x", "x");
                else if (key === "a") handleKeyboardViolation("ctrl+a", "a");
                else if (key === "w") handleKeyboardViolation("ctrl+w", "w");
                else if (key === "t") handleKeyboardViolation("ctrl+t", "t");
                else if (e.shiftKey && (key === "i" || key === "j")) handleKeyboardViolation("devtools", "devtools");
            }} else if (isAlt) {{
                if (key === "tab") handleKeyboardViolation("alt+tab", "tab");
                else if (key === "f4") handleKeyboardViolation("alt+f4", "f4");
            }} else if (key === "printscreen" || e.keyCode === 44) {{
                handleKeyboardViolation("print_screen", "PrintScreen");
            }} else if (key === "f12") {{
                handleKeyboardViolation("devtools", "f12");
            }}
        }}

        targetWin.addEventListener("keydown", onKeyDownHandler);
        targetDoc.addEventListener("keydown", onKeyDownHandler);
        targetWin.addEventListener("keyup", (e) => {{
            if (e.key === "PrintScreen" || e.keyCode === 44) {{
                handleKeyboardViolation("print_screen", "PrintScreen");
            }}
        }});
        targetDoc.addEventListener("copy", () => handleKeyboardViolation("ctrl+c", "CopyEvent"));
        targetDoc.addEventListener("paste", () => handleKeyboardViolation("ctrl+v", "PasteEvent"));
        targetDoc.addEventListener("cut", () => handleKeyboardViolation("ctrl+x", "CutEvent"));

        function updateLog(msg) {{
            const log = document.getElementById("integrity-log");
            if (log) {{
                log.innerText = "[" + new Date().toLocaleTimeString() + "] " + msg;
                log.style.color = "#b45309";
            }}
        }}
    }})();
    </script>
    """


def get_pre_exam_extension_detector_js(
    exam_session_id: str,
    student_id: str,
    is_extension_active: bool = False,
    extension_name: str = "Exam Integrity Extension"
) -> str:
    """
    Returns HTML + JavaScript telemetry script embedded in the Student Dashboard before starting the exam.
    Performs real-time, multi-vector browser extension diagnostic scanning:
    - Injected DOM markers and extension elements
    - Active ping-pong handshake with Chrome companion extension
    - Global window hooks, attributes, and shadow root injections
    - Protocol URL assets (chrome-extension://)
    - Automatic two-way synchronization with Streamlit parent portal
    """
    active_flag = "true" if is_extension_active else "false"
    safe_ext_name = extension_name.replace('"', '\\"')

    return f"""
    <div id="pre-exam-extension-hud" style="
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        background: {'#fef2f2' if is_extension_active else '#f8fafc'};
        border: 1.5px solid {'#ef4444' if is_extension_active else '#e2e8f0'};
        border-radius: 8px;
        padding: 12px 16px;
        margin-top: 6px;
        font-size: 12px;
        color: #1e293b;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span id="pre-ext-pulse" style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: {'#ef4444' if is_extension_active else '#10b981'};"></span>
                <strong id="pre-ext-title" style="color: {'#991b1b' if is_extension_active else '#0f172a'}; font-size: 13px;">
                    🔍 Pre-Exam Extension & Environment Diagnostic Scanner
                </strong>
            </div>
            <div id="pre-ext-badge" style="
                background: {'#fee2e2' if is_extension_active else '#dcfce7'};
                color: {'#991b1b' if is_extension_active else '#166534'};
                border: 1px solid {'#fca5a5' if is_extension_active else '#86efac'};
                padding: 3px 10px;
                border-radius: 4px;
                font-weight: 700;
                font-size: 11px;
            ">
                {'🚨 EXTENSION DETECTED' if is_extension_active else '🟢 INTEGRITY PASS: NO EXTENSIONS'}
            </div>
        </div>

        <div id="pre-ext-warning-box" style="
            display: {'block' if is_extension_active else 'none'};
            margin-top: 10px;
            padding: 10px 14px;
            background: #ffffff;
            border: 2px solid #ef4444;
            border-radius: 6px;
            color: #991b1b;
        ">
            <div style="display: flex; align-items: flex-start; gap: 8px;">
                <span style="font-size: 18px;">⚠️</span>
                <div>
                    <div style="font-weight: 700; font-size: 13px; margin-bottom: 2px;">
                        WARNING: YOU ARE USING A BROWSER EXTENSION!
                    </div>
                    <div style="font-size: 11.5px; line-height: 1.4; color: #7f1d1d;">
                        Active Extension Detected: <strong><span id="detected-ext-label">{safe_ext_name}</span></strong>.<br/>
                        Institutional Examination Policy strictly forbids third-party extensions, AI helpers, or script injectors.
                        <strong>This telemetry has been transmitted to the Faculty Dashboard.</strong> Please disable all extensions before proceeding.
                    </div>
                </div>
            </div>
        </div>

        <div id="pre-ext-clean-box" style="
            display: {'none' if is_extension_active else 'block'};
            margin-top: 8px;
            font-size: 11.5px;
            color: #475569;
        ">
            <span>🛡️ <strong>Environment Scan Result:</strong> Clean. Zero unauthorized extensions or suspicious DOM injections detected. Ready for proctored examination.</span>
        </div>
    </div>

    <script>
    (function() {{
        const SESSION_ID = "{exam_session_id}";
        const STUDENT_ID = "{student_id}";
        const SIMULATED_ACTIVE = {active_flag};
        const EXT_NAME = "{safe_ext_name}";

        let alreadyAlerted = false;

        function triggerExtensionViolationAlert(name) {{
            if (alreadyAlerted && document.getElementById("detected-ext-label") && document.getElementById("detected-ext-label").innerText === name) {{
                return;
            }}
            alreadyAlerted = true;

            // 1. Update UI Elements inside the HUD iframe
            const warnBox = document.getElementById("pre-ext-warning-box");
            if (warnBox) warnBox.style.display = "block";
            const cleanBox = document.getElementById("pre-ext-clean-box");
            if (cleanBox) cleanBox.style.display = "none";
            const badge = document.getElementById("pre-ext-badge");
            if (badge) {{
                badge.innerText = "🚨 EXTENSION DETECTED: " + name;
                badge.style.background = "#fee2e2";
                badge.style.color = "#991b1b";
                badge.style.borderColor = "#fca5a5";
            }}
            const pulse = document.getElementById("pre-ext-pulse");
            if (pulse) pulse.style.background = "#ef4444";
            const title = document.getElementById("pre-ext-title");
            if (title) title.style.color = "#991b1b";
            const label = document.getElementById("detected-ext-label");
            if (label) label.innerText = name;

            const targetWin = window.parent ? window.parent : window;
            const targetDoc = window.parent ? window.parent.document : document;

            // 2. High-visibility floating warning in parent exam portal
            try {{
                if (targetDoc && targetDoc.body) {{
                    let parentBanner = targetDoc.getElementById("exam-precheck-ext-warning");
                    if (!parentBanner) {{
                        parentBanner = targetDoc.createElement("div");
                        parentBanner.id = "exam-precheck-ext-warning";
                        parentBanner.style.cssText = "position:fixed; top:20px; left:50%; transform:translateX(-50%); z-index:999999; background:#fff1f2; border:2.5px solid #e11d48; color:#9f1239; padding:14px 28px; border-radius:10px; box-shadow:0 10px 30px rgba(225,29,72,0.35); font-family:sans-serif; font-size:14px; font-weight:bold; display:flex; align-items:center; gap:12px; transition: all 0.3s ease;";
                        targetDoc.body.appendChild(parentBanner);
                    }}
                    parentBanner.innerHTML = "<span>🚨</span> <span><strong>PROCTORING WARNING:</strong> Active browser extension detected: <code>" + name + "</code>! Disable all extensions before starting. Incident forwarded to Faculty Dashboard.</span>";
                    parentBanner.style.display = "flex";
                }}
            }} catch(e) {{
                console.log("[Extension Guard] Parent banner notice:", e);
            }}

            // 3. Dynamically update the Checklist inside parent document
            try {{
                if (targetDoc) {{
                    // Update checklist item chip for Third-Party Extension Guard
                    const allCards = targetDoc.querySelectorAll("div");
                    for (let c of allCards) {{
                        if (c.innerText && c.innerText.includes("Third-Party Extension Guard")) {{
                            const pill = c.querySelector(".pill-pass, .pill-warn, .pill");
                            if (pill) {{
                                pill.className = "pill pill-fail";
                                pill.innerHTML = "❌ FAIL";
                            }}
                            const detail = c.querySelector("div[style*='font-size: 0.78rem']");
                            if (detail) {{
                                detail.innerText = "Active: " + name + " (Forbidden)";
                                detail.style.color = "#dc2626";
                            }}
                            c.style.borderColor = "#ef4444";
                            break;
                        }}
                    }}
                }}
            }} catch(e) {{}}

            // 4. Dispatch alert to local proctoring beacon server to notify faculty dashboard
            try {{
                fetch("http://127.0.0.1:8585/api/extension_event", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        session_id: SESSION_ID,
                        student_id: STUDENT_ID,
                        extension_name: name,
                        stage: "PRE_EXAM",
                        timestamp: Date.now()
                    }})
                }}).catch(() => {{}});
            }} catch(e) {{}}

            // 5. Synchronize with Streamlit Python via URL query params
            try {{
                const pLoc = targetWin.location;
                if (pLoc && pLoc.href) {{
                    const url = new URL(pLoc.href);
                    if (url.searchParams.get("ext_detected") !== "1" || url.searchParams.get("ext_name") !== name) {{
                        url.searchParams.set("ext_detected", "1");
                        url.searchParams.set("ext_name", name);
                        pLoc.replace(url.href);
                    }}
                }}
            }} catch(e) {{}}
        }}

        // If explicitly active/simulated, immediately trigger alert
        if (SIMULATED_ACTIVE) {{
            triggerExtensionViolationAlert(EXT_NAME);
            return;
        }}

        // Multi-Vector Real-Time Browser Extension Diagnostic Scanner
        function performDiagnosticScan() {{
            try {{
                const targetDoc = window.parent ? window.parent.document : document;
                const targetWin = window.parent ? window.parent : window;

                let detected = null;

                // 1. Direct Extension DOM Marker Check
                const marker = (targetDoc ? targetDoc.getElementById("examguard-extension-marker") : null) || document.getElementById("examguard-extension-marker");
                if (marker) {{
                    detected = marker.getAttribute("data-extension-name") || "Exam Integrity Extension";
                }}

                // 2. Global Window & Storage Properties Check
                if (!detected) {{
                    if (targetWin.__EXAMGUARD_EXTENSION_ACTIVE__ || window.__EXAMGUARD_EXTENSION_ACTIVE__) {{
                        detected = targetWin.__EXAMGUARD_EXTENSION_NAME__ || window.__EXAMGUARD_EXTENSION_NAME__ || "Exam Integrity Extension";
                    }}
                }}
                if (!detected) {{
                    try {{
                        const sVal = targetWin.sessionStorage.getItem("examguard_ext_detected") || window.sessionStorage.getItem("examguard_ext_detected");
                        if (sVal) detected = sVal;
                    }} catch(e) {{}}
                }}
                if (!detected) {{
                    try {{
                        const lVal = targetWin.localStorage.getItem("examguard_ext_detected") || window.localStorage.getItem("examguard_ext_detected");
                        if (lVal) detected = lVal;
                    }} catch(e) {{}}
                }}

                // 3. Known Popular Extension DOM Injections
                if (!detected && targetDoc) {{
                    // Grammarly
                    if (targetDoc.querySelector("grammarly-desktop-integration, grammarly-extension, [data-grammarly-shadow-root]")) {{
                        detected = "Grammarly Writing Assistant";
                    }}
                    // Dark Reader
                    else if (targetDoc.querySelector("style.darkreader, meta[name='darkreader'], [data-darkreader-mode]")) {{
                        detected = "Dark Reader Extension";
                    }}
                    // Google Translate
                    else if (targetDoc.querySelector("#google_translate_element, [class*='goog-te-'], .VIpgJd-ZVi9od-ORHb")) {{
                        detected = "Google Translate Extension";
                    }}
                    // ChatGPT / OpenAI / Copilot / Gemini / AI Tools
                    else if (targetDoc.querySelector("[id*='chatgpt'], [class*='chatgpt'], chatgpt-sidebar, [id*='monica'], [id*='sider'], [id*='harpa'], [id*='merlin'], [id*='gemini'], [class*='gemini']")) {{
                        detected = "AI Assistant / Translator Extension";
                    }}
                    // Tampermonkey / Script Injectors
                    else if (targetDoc.querySelector("[id*='tampermonkey'], [id*='violentmonkey']")) {{
                        detected = "Tampermonkey / Script Injector";
                    }}
                    // Password Managers
                    else if (targetDoc.querySelector("[id*='bitwarden'], [data-lastpass-root], [data-1p-ignore]")) {{
                        detected = "Password Manager Extension";
                    }}
                    // Loom Screen Recorder
                    else if (targetDoc.querySelector("loom-container, [id*='loom-companion']")) {{
                        detected = "Loom Screen Recorder Extension";
                    }}
                    // AdBlockers
                    else if (targetDoc.querySelector("[id*='ublock'], [id*='adguard'], [data-adblockkey]")) {{
                        detected = "AdBlock / Content Filter Extension";
                    }}
                    // Generic Extension Elements or Protocols
                    else {{
                        const extNode = targetDoc.querySelector("[data-extension-id], [data-extension-name], [data-extension-detected], [class*='chrome-extension']");
                        if (extNode) {{
                            detected = extNode.getAttribute("data-extension-name") || extNode.getAttribute("data-extension-id") || "Active Chrome Extension";
                        }}
                    }}
                }}

                // 4. Injected Extension Protocol Assets (chrome-extension://)
                if (!detected && targetDoc) {{
                    const extAsset = targetDoc.querySelector("script[src*='chrome-extension://'], link[href*='chrome-extension://'], img[src*='chrome-extension://'], iframe[src*='chrome-extension://']");
                    if (extAsset) {{
                        detected = "Injected Extension Protocol Asset";
                    }}
                }}

                // 5. Global Window Hooks
                if (!detected && targetWin) {{
                    if (targetWin.__REACT_DEVTOOLS_GLOBAL_HOOK__) detected = "React Developer Tools";
                    else if (targetWin.__REDUX_DEVTOOLS_EXTENSION__) detected = "Redux DevTools";
                    else if (targetWin.ethereum || targetWin.solana) detected = "Crypto Wallet Extension";
                    else if (targetWin.GM || targetWin.GM_info) detected = "Tampermonkey / Userscript Engine";
                }}

                if (detected) {{
                    triggerExtensionViolationAlert(detected);
                }}
            }} catch(e) {{
                console.log("[Extension Guard] Diagnostic scan exception:", e);
            }}
        }}

        // Bi-directional Ping/Pong Handshake with Companion Extension
        function sendPing() {{
            const pingMsg = {{
                type: "EXAM_INTEGRITY_PING",
                sessionId: SESSION_ID,
                timestamp: Date.now()
            }};
            try {{ window.postMessage(pingMsg, "*"); }} catch(e) {{}}
            try {{
                const targetWin = window.parent ? window.parent : window;
                if (targetWin && targetWin !== window) {{
                    targetWin.postMessage(pingMsg, "*");
                }}
            }} catch(e) {{}}
        }}

        function onPong(event) {{
            if (event.data && (event.data.type === "EXAM_INTEGRITY_PONG" || event.data.type === "PONG_EXTENSION")) {{
                const name = event.data.name || event.data.extensionId || "Exam Integrity Extension";
                triggerExtensionViolationAlert(name);
            }}
        }}

        window.addEventListener("message", onPong);
        try {{
            if (window.parent) window.parent.addEventListener("message", onPong);
        }} catch(e) {{}}

        // Run scans continuously
        performDiagnosticScan();
        sendPing();

        setTimeout(performDiagnosticScan, 300);
        setTimeout(sendPing, 400);
        setTimeout(performDiagnosticScan, 900);
        setTimeout(sendPing, 1000);

        setInterval(performDiagnosticScan, 2000);
        setInterval(sendPing, 2500);
    }})();
    </script>
    """
