"""
AuraSafe — overlay.py
Tkinter overlay system: fullscreen block + warning overlays.
Always-on-top, thread-safe via queue-based dispatch.
FIX: start() now runs Tkinter mainloop on calling thread (main thread).
"""

import tkinter as tk
import threading
import queue
import time


class OverlayManager:
    def __init__(self, config: dict):
        cfg = config.get("overlay", {})
        self.warning_color = cfg.get("warning_color", "#FF4444")
        self.block_color   = cfg.get("block_color", "#0d0d0d")
        self.opacity       = cfg.get("opacity", 0.95)
        self.font_name     = cfg.get("font", "Segoe UI")

        self._root: tk.Tk | None = None
        self._overlay_win: tk.Toplevel | None = None
        self._queue: queue.Queue = queue.Queue()
        self._running = False

    # ── Public API (thread-safe) ─────────────────────────────────────────

    def start(self):
        """
        Start Tkinter mainloop on the CALLING thread.
        This BLOCKS — call it last in main.py after all other services start.
        """
        self._running = True
        self._root = tk.Tk()
        self._root.withdraw()
        self._root.after(100, self._process_queue)
        self._root.mainloop()  # blocks here

    def stop(self):
        self._running = False
        self._queue.put(("quit", {}))

    def show_block(self, reason: str = "Unsafe content detected"):
        self._queue.put(("block", {"reason": reason}))

    def show_warning(self, message: str = "Warning: Suspicious content detected"):
        self._queue.put(("warning", {"message": message}))

    def hide(self):
        self._queue.put(("hide", {}))

    # ── Internal Tkinter loop ────────────────────────────────────────────

    def _process_queue(self):
        try:
            while True:
                cmd, kwargs = self._queue.get_nowait()
                if cmd == "block":
                    self._do_block(kwargs["reason"])
                elif cmd == "warning":
                    self._do_warning(kwargs["message"])
                elif cmd == "hide":
                    self._do_hide()
                elif cmd == "quit":
                    self._root.quit()
                    return
        except queue.Empty:
            pass

        if self._running:
            self._root.after(100, self._process_queue)

    def _destroy_overlay(self):
        if self._overlay_win:
            try:
                self._overlay_win.destroy()
            except Exception:
                pass
            self._overlay_win = None

    def _do_block(self, reason: str):
        self._destroy_overlay()
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", self.opacity)
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{sw}x{sh}+0+0")
        win.configure(bg=self.block_color)

        tk.Label(
            win, text="🛡️", font=(self.font_name, 72),
            bg=self.block_color, fg="#FF4444"
        ).pack(expand=True, pady=(sh // 4, 10))

        tk.Label(
            win, text="BLOCKED BY AURASAFE",
            font=(self.font_name, 28, "bold"),
            bg=self.block_color, fg="#FF4444"
        ).pack()

        tk.Label(
            win, text=f"Reason: {reason}",
            font=(self.font_name, 14),
            bg=self.block_color, fg="#aaaaaa",
            wraplength=sw - 200
        ).pack(pady=12)

        tk.Label(
            win,
            text="Contact your administrator to unblock.",
            font=(self.font_name, 11),
            bg=self.block_color, fg="#666666"
        ).pack()

        win.protocol("WM_DELETE_WINDOW", lambda: None)
        win.bind("<Escape>", lambda e: None)
        self._overlay_win = win

    def _do_warning(self, message: str):
        self._destroy_overlay()
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.88)
        sw = win.winfo_screenwidth()
        bar_h = 70
        win.geometry(f"{sw}x{bar_h}+0+{win.winfo_screenheight() - bar_h - 48}")
        win.configure(bg=self.warning_color)

        tk.Label(
            win, text=f"⚠  {message}",
            font=(self.font_name, 13, "bold"),
            bg=self.warning_color, fg="white",
            padx=20
        ).pack(side="left", fill="y")

        win.after(4000, self._destroy_overlay)
        self._overlay_win = win

    def _do_hide(self):
        self._destroy_overlay()
