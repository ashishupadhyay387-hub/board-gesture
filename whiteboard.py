"""Drawing canvas, undo history and on-screen toolbar."""
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# name, BGR colour (None = action button), dwell seconds needed to trigger
BUTTONS = [
    ("White",  (255, 255, 255), 0.35),
    ("Red",    (60, 60, 255),   0.35),
    ("Green",  (80, 220, 80),   0.35),
    ("Blue",   (255, 150, 40),  0.35),
    ("Yellow", (0, 230, 255),   0.35),
    ("Undo",   None,            0.6),
    ("Clear",  None,            1.0),
    ("Save",   None,            0.8),
]

TOOLBAR_H = 80
BOARD_BG = (38, 48, 38)  # chalkboard green-grey


class Whiteboard:
    def __init__(self, width, height):
        self.w, self.h = width, height
        self.canvas = np.zeros((height, width, 3), np.uint8)  # black == transparent
        self.undo_stack = []
        self.color = (255, 255, 255)
        self.brush = 6
        self.eraser = 70
        self.overlay_on_camera = True  # False = pure blackboard

        self._hover = None
        self._hover_since = 0.0
        self._fired = False
        self.toast = ("", 0.0)

    # ---------- drawing ----------
    def begin_stroke(self):
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > 25:
            self.undo_stack.pop(0)

    def draw_line(self, p1, p2):
        cv2.line(self.canvas, p1, p2, self.color, self.brush, cv2.LINE_AA)

    def erase_at(self, p):
        cv2.circle(self.canvas, p, self.eraser // 2, (0, 0, 0), -1)

    def undo(self):
        if self.undo_stack:
            self.canvas = self.undo_stack.pop()
            self._say("Undo")
        else:
            self._say("Nothing to undo")

    def clear(self):
        self.begin_stroke()
        self.canvas[:] = 0
        self._say("Board cleared")

    def change_brush(self, delta):
        self.brush = int(np.clip(self.brush + delta, 2, 40))
        self._say(f"Brush size {self.brush}")

    # ---------- output ----------
    def compose(self, frame):
        mask = self.canvas.max(axis=2) > 0
        base = frame.copy() if self.overlay_on_camera else np.full_like(frame, BOARD_BG)
        base[mask] = self.canvas[mask]
        return base

    def save(self, composed):
        Path("saved").mkdir(exist_ok=True)
        name = datetime.now().strftime("saved/board_%Y%m%d_%H%M%S.png")
        cv2.imwrite(name, composed)
        self._say(f"Saved {name}")

    def _say(self, text):
        self.toast = (text, time.time() + 1.8)

    # ---------- toolbar ----------
    def _button_rect(self, i):
        bw = self.w // len(BUTTONS)
        return i * bw + 6, 8, (i + 1) * bw - 6, TOOLBAR_H - 8

    def button_at(self, x, y):
        if y > TOOLBAR_H:
            return None
        for i in range(len(BUTTONS)):
            x1, _, x2, _ = self._button_rect(i)
            if x1 - 6 <= x <= x2 + 6:
                return i
        return None

    def update_hover(self, point, composed):
        """Call while in selection mode. Triggers a button after dwelling on it."""
        idx = self.button_at(*point) if point else None
        now = time.time()
        if idx != self._hover:
            self._hover, self._hover_since, self._fired = idx, now, False
            return 0.0
        if idx is None or self._fired:
            return 0.0
        name, color, dwell = BUTTONS[idx]
        progress = min((now - self._hover_since) / dwell, 1.0)
        if progress >= 1.0:
            self._fired = True
            if color is not None:
                self.color = color
                self._say(f"Colour: {name}")
            elif name == "Undo":
                self.undo()
            elif name == "Clear":
                self.clear()
            elif name == "Save":
                self.save(composed)
        return progress

    def reset_hover(self):
        self._hover, self._fired = None, False

    def draw_toolbar(self, out, progress=0.0):
        cv2.rectangle(out, (0, 0), (self.w, TOOLBAR_H), (25, 25, 25), -1)
        for i, (name, color, _) in enumerate(BUTTONS):
            x1, y1, x2, y2 = self._button_rect(i)
            fill = color if color is not None else (70, 70, 70)
            cv2.rectangle(out, (x1, y1), (x2, y2), fill, -1)
            selected = color is not None and color == self.color
            border = (255, 255, 255) if selected else (110, 110, 110)
            cv2.rectangle(out, (x1, y1), (x2, y2), border, 3 if selected else 1)
            if color is None:
                (tw, th), _ = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.putText(out, name, ((x1 + x2 - tw) // 2, (y1 + y2 + th) // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            if i == self._hover and progress > 0 and not self._fired:
                cv2.rectangle(out, (x1, y2 - 8), (x1 + int((x2 - x1) * progress), y2),
                              (0, 255, 255), -1)

    def draw_toast(self, out):
        text, until = self.toast
        if time.time() < until:
            cv2.putText(out, text, (20, self.h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 255, 255), 2, cv2.LINE_AA)
