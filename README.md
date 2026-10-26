# ✋ Gesture Blackboard

Draw, change colours and erase on your live webcam feed using only hand gestures
(Python + OpenCV + MediaPipe).

## Setup
Requires Python 3.9 – 3.11 (MediaPipe 0.10.14 wheels).

```bash
python -m venv venv
# Windows: venv\Scripts\activate      Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
python main.py
```
Options: `python main.py --camera 1 --width 1280 --height 720`

## Gestures
| Gesture | Action |
|---|---|
| ☝ Index finger only | **Draw** |
| ✌ Index + middle | **Select** – hover a toolbar button (colour / Undo / Clear / Save); a yellow bar shows the hold progress |
| 🖐 Open palm (4 fingers) | **Erase** – eraser circle follows your palm |
| ✊ Fist / other | Pause |

## Keyboard
`c` clear · `u` undo · `s` save PNG (to `saved/`) · `b` toggle camera/blackboard background ·
`h` show hand skeleton · `+`/`-` brush size · `[`/`]` eraser size · `q`/Esc quit

## Tips
- Good, even lighting and a plain background improve tracking.
- Keep your hand ~40–80 cm from the camera, palm facing it.
- Drawing is blocked inside the toolbar strip so you don't scribble on buttons.

## Files
- `main.py` – main loop, gesture → mode logic
- `hand_tracker.py` – MediaPipe wrapper, finger detection
- `whiteboard.py` – canvas, undo, toolbar, saving
