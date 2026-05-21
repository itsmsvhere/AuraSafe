"""
AuraSafe — main.py
Master orchestrator. Wires all modules, runs monitoring loops, watchdog.
Entry point: python main.py
"""

import json
import os
import sys
import time
import threading
import signal
import webbrowser
import queue

# ── Graceful import with clear error messages ─────────────────────────────────
try:
    import psutil
except ImportError:
    print("[AuraSafe] ERROR: psutil not installed. Run: pip install psutil")
    sys.exit(1)

try:
    from flask_cors import CORS  # noqa – just check
except ImportError:
    print("[AuraSafe] ERROR: flask-cors not installed. Run: pip install flask flask-cors")
    sys.exit(1)

# ── Platform-specific window detection ───────────────────────────────────────
_WIN_DETECTION = False
if sys.platform == "win32":
    try:
        import win32gui
        import win32process
        _WIN_DETECTION = True
    except ImportError:
        print("[AuraSafe] WARNING: pywin32 not installed. App monitoring disabled.")
        print("           Install: pip install pywin32")

# ── AuraSafe modules ──────────────────────────────────────────────────────────
from detector   import ContentDetector
from logger     import AuraLogger
from overlay    import OverlayManager
from lock_mode  import LockManager
from server     import APIServer


# ─────────────────────────────────────────────────────────────────────────────
# Config loader
# ─────────────────────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# Active window monitor (Windows only — degrades gracefully on others)
# ─────────────────────────────────────────────────────────────────────────────

class AppMonitor:
    def __init__(self, config: dict, overlay: OverlayManager, logger: AuraLogger, state: dict):
        self._restricted = [a.lower() for a in config.get("restricted_apps", [])]
        self._interval   = config.get("monitor_interval_ms", 500) / 1000
        self._overlay    = overlay
        self._logger     = logger
        self._state      = state
        self._running    = False
        self._last_blocked = ""

    def _get_active_exe(self) -> str:
        if not _WIN_DETECTION:
            return ""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            return proc.name().lower()
        except Exception:
            return ""

    def _monitor_loop(self):
        while self._running:
            exe = self._get_active_exe()
            if exe and exe in self._restricted:
                if self._last_blocked != exe:
                    self._last_blocked = exe
                    self._overlay.show_block(f"Restricted application: {exe}")
                    self._logger.log("APP_BLOCKED", content=exe, action="block_overlay")
                    self._state["blocked"] = True
                    self._state["last_event"] = f"app_blocked:{exe}"
            else:
                if self._last_blocked:
                    self._last_blocked = ""
            time.sleep(self._interval)

    def start(self):
        self._running = True
        t = threading.Thread(target=self._monitor_loop, name="AppMonitor", daemon=True)
        t.start()

    def stop(self):
        self._running = False


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────

class AuraSafe:
    def __init__(self):
        print("╔══════════════════════════════════╗")
        print("║        A U R A S A F E          ║")
        print("║   Local Safety Engine v2.5       ║")
        print("╚══════════════════════════════════╝")

        self._config  = load_config()
        self._running = False

        # Shared mutable state (thread-safe for primitive r/w)
        self._state: dict = {
            "blocked": False,
            "locked": False,
            "last_event": "startup"
        }

        # ── Instantiate modules ───────────────────────────────────────────
        self._logger   = AuraLogger(self._config)
        self._detector = ContentDetector(self._config)
        self._overlay  = OverlayManager(self._config)
        self._lock_mgr = LockManager(
            self._config,
            self._overlay._queue,  # share queue for Tkinter dispatch
            self._logger
        )
        self._app_mon  = AppMonitor(self._config, self._overlay, self._logger, self._state)
        self._server   = APIServer(
            self._config, self._state,
            self._overlay, self._lock_mgr, self._logger
        )

        # Patch OverlayManager to handle focus_lock commands
        self._patch_overlay_queue()

    def _patch_overlay_queue(self):
        """Extend OverlayManager._process_queue to handle focus_lock/focus_unlock."""
        original_process = self._overlay._process_queue.__func__

        lock_mgr = self._lock_mgr

        def patched_process(self_ov):
            try:
                while True:
                    cmd, kwargs = self_ov._queue.get_nowait()
                    if cmd == "block":
                        self_ov._do_block(kwargs["reason"])
                    elif cmd == "warning":
                        self_ov._do_warning(kwargs["message"])
                    elif cmd == "hide":
                        self_ov._do_hide()
                    elif cmd == "focus_lock":
                        self_ov._destroy_overlay()
                        self_ov._overlay_win = lock_mgr.build_lock_screen(
                            self_ov._root, kwargs.get("reason", "Focus Mode")
                        )
                    elif cmd == "focus_unlock":
                        self_ov._destroy_overlay()
                    elif cmd == "quit":
                        self_ov._root.quit()
                        return
            except queue.Empty:
                pass

            if self_ov._running:
                self_ov._root.after(100, lambda: patched_process(self_ov))

        import types
        self._overlay._process_queue = types.MethodType(patched_process, self._overlay)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def start(self):
        self._running = True
        self._logger.log("SYSTEM", action="startup", extra="AuraSafe v2.0 started")
        print("[AuraSafe] Starting modules...")

        # Start overlay (blocks this thread with mainloop — must be last)
        self._server.start()
        self._app_mon.start()
        print("[AuraSafe] All services running. Ctrl+C to stop.")
        # Open dashboard in browser after short delay
        import threading as _t
        def _open_dash():
            import time; time.sleep(1.2)
            port = self._config.get("api", {}).get("port", 5000)
            webbrowser.open(f"http://127.0.0.1:{port}/dashboard")
        _t.Thread(target=_open_dash, daemon=True).start()
        self._logger.log("SYSTEM", action="running", extra="all modules started")

        # Register shutdown signal
        signal.signal(signal.SIGINT,  self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

        # OverlayManager.start() → Tkinter mainloop (blocks here)
        self._overlay.start()  # ← blocks until overlay thread exits

    def _shutdown_handler(self, sig, frame):
        print("\n[AuraSafe] Shutting down...")
        self._running = False
        self._app_mon.stop()
        self._overlay.stop()
        self._logger.log("SYSTEM", action="shutdown")
        self._logger.close()
        print("[AuraSafe] Goodbye.")
        sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# Watchdog wrapper — auto-restarts on unexpected crash
# ─────────────────────────────────────────────────────────────────────────────

def run_with_watchdog():
    MAX_RESTARTS = 5
    restart_count = 0
    while restart_count < MAX_RESTARTS:
        try:
            app = AuraSafe()
            app.start()
            break  # clean exit
        except SystemExit:
            break
        except Exception as e:
            restart_count += 1
            print(f"[Watchdog] Crash detected ({restart_count}/{MAX_RESTARTS}): {e}")
            if restart_count >= MAX_RESTARTS:
                print("[Watchdog] Max restarts reached. Exiting.")
                break
            print(f"[Watchdog] Restarting in 3 seconds...")
            time.sleep(3)


if __name__ == "__main__":
    run_with_watchdog()
