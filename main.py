"""
Gesture Blackboard - draw in the air with your webcam.

Gestures (one hand):
  ☝  Index finger only .......... DRAW
  ✌  Index + middle fingers ..... SELECT (hover a toolbar button)
  🖐  Open palm (4 fingers) ...... ERASE (eraser follows your palm)
  ✊  Fist / anything else ....... PAUSE

Keys: c clear | u undo | s save | b board/camera | h skeleton
      + / - brush size | [ / ] eraser size | q or Esc quit
"""
import argparse
import time

import cv2

from hand_tracker import HandTracker
from whiteboard import TOOLBAR_H, Whiteboard

DRAW, SELECT, ERASE, IDLE = "DRAW", "SELECT", "ERASE", "PAUSE"


def classify(fingers):
    index, middle, ring, pinky = fingers
    if index and not middle and not ring and not pinky:
        return DRAW
    if index and middle and not ring and not pinky:
        return SELECT
    if index and middle and ring and pinky:
        return ERASE
    return IDLE


class Smoother:
    """Exponential moving average to remove jitter."""
    def __init__(self, alpha=0.45):
        self.alpha, self.p = alpha, None

    def __call__(self, pt):
        if self.p is None:
            self.p = pt
        else:
            self.p = (self.alpha * pt[0] + (1 - self.alpha) * self.p[0],
                      self.alpha * pt[1] + (1 - self.alpha) * self.p[1])
        return int(self.p[0]), int(self.p[1])

    def reset(self):
        self.p = None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--height", type=int, default=720)
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
    if not cap.isOpened():
        raise SystemExit("Could not open the camera. Try --camera 1")

    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    tracker = HandTracker()
    board = Whiteboard(W, H)
    smooth = Smoother()
    prev_pt, prev_mode = None, IDLE
    show_skeleton, last_t, fps = False, time.time(), 0.0
    win = "Gesture Blackboard"
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)  # mirror view

        landmarks = tracker.process(frame)
        mode, cursor, progress = IDLE, None, 0.0
        composed = board.compose(frame)

        if landmarks is not None:
            pts = tracker.to_pixels(landmarks, W, H)
            mode = classify(tracker.fingers_up(pts))

            if mode == ERASE:
                cursor = smooth(pts[9])           # palm centre
            elif mode in (DRAW, SELECT):
                cursor = smooth(pts[8])           # index fingertip
            else:
                smooth.reset()

            if mode in (DRAW, ERASE) and prev_mode != mode:
                board.begin_stroke()
                prev_pt = None

            if mode == DRAW:
                if cursor[1] > TOOLBAR_H:
                    if prev_pt is not None:
                        board.draw_line(prev_pt, cursor)
                    prev_pt = cursor
                else:
                    prev_pt = None
            elif mode == ERASE:
                board.erase_at(cursor)
                prev_pt = None
            else:
                prev_pt = None

            if mode == SELECT:
                progress = board.update_hover(cursor, composed)
            else:
                board.reset_hover()

            if show_skeleton:
                tracker.draw_skeleton(frame, landmarks)
                composed = board.compose(frame)
        else:
            smooth.reset()
            prev_pt = None
            board.reset_hover()

        prev_mode = mode

        # ---- HUD (drawn after compose so it never ends up on the canvas) ----
        out = board.compose(frame) if landmarks is not None else composed
        if show_skeleton and landmarks is not None:
            tracker.draw_skeleton(out, landmarks)
        board.draw_toolbar(out, progress)

        if cursor is not None:
            if mode == DRAW:
                cv2.circle(out, cursor, board.brush // 2 + 4, board.color, 2, cv2.LINE_AA)
            elif mode == ERASE:
                cv2.circle(out, cursor, board.eraser // 2, (255, 255, 255), 2, cv2.LINE_AA)
            elif mode == SELECT:
                cv2.circle(out, cursor, 14, (0, 255, 255), 2, cv2.LINE_AA)

        now = time.time()
        fps = 0.9 * fps + 0.1 * (1.0 / max(now - last_t, 1e-6))
        last_t = now
        cv2.putText(out, f"Mode: {mode}   FPS: {fps:.0f}", (20, TOOLBAR_H + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        board.draw_toast(out)

        cv2.imshow(win, out)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), 27):
            break
        elif key == ord("c"):
            board.clear()
        elif key == ord("u"):
            board.undo()
        elif key == ord("s"):
            board.save(board.compose(frame))
        elif key == ord("b"):
            board.overlay_on_camera = not board.overlay_on_camera
        elif key == ord("h"):
            show_skeleton = not show_skeleton
        elif key in (ord("+"), ord("=")):
            board.change_brush(2)
        elif key in (ord("-"), ord("_")):
            board.change_brush(-2)
        elif key == ord("]"):
            board.eraser = min(board.eraser + 10, 200)
        elif key == ord("["):
            board.eraser = max(board.eraser - 10, 20)

    tracker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
