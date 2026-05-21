"""
AuraSafe — lock_mode.py
Focus-Wellness fullscreen lock. PIN-protected, Tkinter-based.
Dispatches via queue to run on OverlayManager's Tkinter thread.
"""

import tkinter as tk
import threading
import queue
import time
import hashlib


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


class LockManager:
    """
    Manages the focus/wellness lock mode.
    When locked, fullscreen overlay prevents all interaction until correct PIN.
    """

    def __init__(self, config: dict, overlay_queue: queue.Queue, logger=None):
        self._pin_hash = _hash_pin(str(config.get("pin", "1234")))
        self._overlay_queue = overlay_queue  # shared with OverlayManager
        self._logger = logger
        self._locked = False
        self._lock_obj = threading.Lock()
        self._lock_win: tk.Toplevel | None = None
        self._root_ref: tk.Tk | None = None  # set externally after OverlayManager starts

    # ------------------------------------------------------------------ #
    # Public API (thread-safe)
    # ------------------------------------------------------------------ #

    @property
    def is_locked(self) -> bool:
        return self._locked

    def lock(self, reason: str = "Focus Mode Active"):
        with self._lock_obj:
            if self._locked:
                return
            self._locked = True
        self._overlay_queue.put(("focus_lock", {"reason": reason}))
        if self._logger:
            self._logger.log("FOCUS_LOCK", action="locked", extra=reason)

    def unlock_attempt(self, pin: str) -> bool:
        """Returns True if PIN correct and lock released."""
        if _hash_pin(pin) == self._pin_hash:
            with self._lock_obj:
                self._locked = False
            self._overlay_queue.put(("focus_unlock", {}))
            if self._logger:
                self._logger.log("FOCUS_UNLOCK", action="unlocked")
            return True
        return False

    # ------------------------------------------------------------------ #
    # Called by OverlayManager's _process_queue (same Tkinter thread)
    # ------------------------------------------------------------------ #

    def build_lock_screen(self, root: tk.Tk, reason: str) -> tk.Toplevel:
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.97)

        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f"{sw}x{sh}+0+0")
        win.configure(bg="#0a0a14")

        # Block close
        win.protocol("WM_DELETE_WINDOW", lambda: None)
        win.bind("<Escape>", lambda e: None)

        # Layout
        frame = tk.Frame(win, bg="#0a0a14")
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(
            frame, text="🔒", font=("Segoe UI", 64),
            bg="#0a0a14", fg="#4FC3F7"
        ).pack(pady=(0, 10))

        tk.Label(
            frame, text="FOCUS MODE",
            font=("Segoe UI", 32, "bold"),
            bg="#0a0a14", fg="#4FC3F7"
        ).pack()

        tk.Label(
            frame, text=reason,
            font=("Segoe UI", 13),
            bg="#0a0a14", fg="#546E7A"
        ).pack(pady=(8, 24))

        tk.Label(
            frame, text="Enter PIN to unlock",
            font=("Segoe UI", 12),
            bg="#0a0a14", fg="#78909C"
        ).pack()

        pin_var = tk.StringVar()
        pin_entry = tk.Entry(
            frame, textvariable=pin_var, show="●",
            font=("Segoe UI", 16), width=12,
            bg="#1a1a2e", fg="white",
            insertbackground="white",
            relief="flat", bd=0
        )
        pin_entry.pack(pady=8, ipady=8)
        pin_entry.focus_set()

        status_var = tk.StringVar(value="")
        status_lbl = tk.Label(
            frame, textvariable=status_var,
            font=("Segoe UI", 11),
            bg="#0a0a14", fg="#EF5350"
        )
        status_lbl.pack()

        def attempt_unlock(event=None):
            pin = pin_var.get()
            if self.unlock_attempt(pin):
                win.destroy()
            else:
                status_var.set("Incorrect PIN. Try again.")
                pin_var.set("")

        pin_entry.bind("<Return>", attempt_unlock)

        tk.Button(
            frame, text="Unlock",
            command=attempt_unlock,
            font=("Segoe UI", 12, "bold"),
            bg="#4FC3F7", fg="#0a0a14",
            relief="flat", cursor="hand2",
            padx=24, pady=8
        ).pack(pady=12)

        return win
