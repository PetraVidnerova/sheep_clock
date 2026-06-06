#!/usr/bin/env python3
"""Desktop widget that shows the current time as a phrase.

Renders Conky-style on the desktop layer where the window manager supports
_NET_WM_WINDOW_TYPE_DESKTOP. Drag with left mouse, right-click to quit.
"""

from __future__ import annotations

import sys
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True)
class Phase:
    start: time
    label: str


# Ordered by start time. The phase that applies is the latest one whose
# `start` is <= now; the day wraps so the last entry covers up to midnight.
# "midnight" appears at both ends intentionally so the label spans 23:50–00:10.
PHASES: tuple[Phase, ...] = (
    Phase(time(0, 0),  "midnight"),
    Phase(time(0, 10), "late night"),
    Phase(time(3, 0),  "dawn"),
    Phase(time(5, 30), "early morning"),
    Phase(time(8, 0),  "late morning"),
    Phase(time(10, 30), "before noon"),
    Phase(time(11, 50), "noon"),
    Phase(time(12, 30), "early afternoon"),
    Phase(time(15, 0),  "late afternoon"),
    Phase(time(17, 0),  "dusk"),
    Phase(time(18, 30), "evening"),
    Phase(time(20, 30), "late evening"),
    Phase(time(22, 30), "night"),
    Phase(time(23, 50), "midnight"),
)


def phrase_for(now: datetime) -> str:
    """Return the phrase for a given datetime."""
    current = now.time()
    selected = PHASES[0].label
    for phase in PHASES:
        if phase.start <= current:
            selected = phase.label
        else:
            break
    return selected


# ---------- GUI ----------

POLL_MS = 30_000
MARGIN = 32
FONT_SPEC = ("Serif", 32, "italic")
FG_COLOR = "#f5f0e6"
BG_COLOR = "#101014"
ALPHA = 0.78


class WordsClock:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("time-in-words")
        self.root.overrideredirect(True)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self._drag_origin: tuple[int, int] | None = None

        # Best-effort: behave as a desktop-layer widget on X11. Silently
        # fall back to a regular borderless window if the WM doesn't support
        # the attribute (e.g. Wayland, macOS, Windows).
        for attr, value in (("-type", "desktop"), ("-alpha", ALPHA)):
            try:
                self.root.wm_attributes(attr, value)
            except tk.TclError:
                pass

        self.root.configure(bg=BG_COLOR)

        self._current_phrase = phrase_for(datetime.now())
        self.label = tk.Label(
            self.root,
            text=self._current_phrase,
            font=FONT_SPEC,
            fg=FG_COLOR,
            bg=BG_COLOR,
            padx=24,
            pady=12,
        )
        self.label.pack()

        self._place_top_right()
        self._bind_controls()
        self.root.lower()

    def _place_top_right(self) -> None:
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        screen_w = self.root.winfo_screenwidth()
        x = screen_w - w - MARGIN
        y = MARGIN
        self.root.geometry(f"+{x}+{y}")

    def _bind_controls(self) -> None:
        for widget in (self.root, self.label):
            widget.bind("<Button-1>", self._on_drag_start)
            widget.bind("<B1-Motion>", self._on_drag_move)
            widget.bind("<Button-3>", lambda _e: self.root.destroy())
        # Keyboard kill switches as recovery if the widget is dragged off-screen
        # or its right-click target is otherwise unreachable.
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.root.bind("<Control-q>", lambda _e: self.root.destroy())

    def _on_drag_start(self, event: tk.Event) -> None:
        self._drag_origin = (event.x_root - self.root.winfo_x(),
                             event.y_root - self.root.winfo_y())

    def _on_drag_move(self, event: tk.Event) -> None:
        if self._drag_origin is None:
            return
        ox, oy = self._drag_origin
        x = event.x_root - ox
        y = event.y_root - oy
        # Clamp so the widget can't be dragged entirely off-screen and lost.
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        min_visible = 40
        x = max(min_visible - w, min(x, screen_w - min_visible))
        y = max(0, min(y, screen_h - min_visible))
        self.root.geometry(f"+{x}+{y}")

    def _tick(self) -> None:
        if not self.root.winfo_exists():
            return
        new_phrase = phrase_for(datetime.now())
        if new_phrase != self._current_phrase:
            self._current_phrase = new_phrase
            self.label.config(text=new_phrase)
        # Re-lower on each tick so the widget stays behind other windows on WMs
        # that don't honor _NET_WM_WINDOW_TYPE_DESKTOP.
        self.root.lower()
        self.root.after(POLL_MS, self._tick)

    def run(self) -> None:
        self.root.after(POLL_MS, self._tick)
        self.root.mainloop()


def main() -> None:
    try:
        widget = WordsClock()
    except tk.TclError as exc:
        print(f"time-in-words: cannot open display ({exc}). "
              "Is $DISPLAY set?", file=sys.stderr)
        sys.exit(1)
    widget.run()


if __name__ == "__main__":
    main()
