# Setup Guide

## 1. Create a Python Environment

Use Python 3.10 on Windows for the most reliable TensorFlow/YAMNet setup.

```powershell
cd security_ai_system
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Verify the Foundation

```powershell
python main.py
```

Expected output:

```text
AI Smart Surveillance foundation is ready.
```

## 3. Run Module Tests

The bag detector state test does not require YOLO, DeepSORT, OpenCV, or a
camera. It validates owner association and unattended timing logic.

```powershell
python -m unittest discover -s tests
```

## 4. Bag Detector Webcam Demo

After requirements are installed, create a small script or use the snippet in
`docs/BAG_DETECTOR.md` to test webcam input. The first YOLO run may download
official `yolov8n.pt` weights if they are not present.

For presentations, instantiate the detector with a short timeout:

```python
from security_ai_system.detectors.bag_detector import BagDetectorConfig

config = BagDetectorConfig(unattended_timeout_sec=3.0)
```

## 5. Weapon Detector Setup

Place a real YOLOv8-compatible weapon model in `models/`, for example:

```text
models/weapon_yolov8.pt
```

Then configure:

```python
from pathlib import Path

from security_ai_system.utils.types import ModelPathConfig

model_paths = ModelPathConfig(
    yolo_weapon_weights=Path("models/weapon_yolov8.pt")
)
```

See `docs/WEAPON_DETECTOR.md` for a webcam demo snippet.

## 6. Behavior Detector Webcam Demo

The behavior detector uses official Ultralytics pose weights:

```text
yolov8n-pose.pt
```

The first run may auto-download the weights when network access is available.
Use the snippet in `docs/BEHAVIOR_DETECTOR.md` for a webcam demo.

## 7. Audio Threat Detection Setup

YAMNet uses TensorFlow Hub and expects mono 16 kHz audio. The first run downloads
the model from:

```text
https://tfhub.dev/google/yamnet/1
```

For microphone demos, confirm Windows microphone permissions are enabled. For
video-file demos, extract audio to WAV for the most stable presentation flow, or
use `librosa` directly when your local backend supports the video container.

See `docs/AUDIO_DETECTOR.md` for microphone and file snippets.

## 8. Multi-Camera Setup

The multi-camera layer uses OpenCV `VideoCapture`, so these sources are valid:

```python
0
"demo.mp4"
"rtsp://user:pass@camera-ip/live"
"https://example.com/stream"
```

Use `docs/CAMERA_MANAGER.md` for examples showing one detector pipeline per
camera.

## 9. Alert Logs and Threat Scoring

Alert events are saved to:

```text
outputs/logs/threat_events.jsonl
outputs/logs/threat_events.csv
```

Evidence images are saved to:

```text
outputs/snapshots/
```

See `docs/ALERTS_AND_THREATS.md` for score thresholds and integration examples.

## 10. Dashboard Demo

Start the PyQt5 dashboard with a webcam:

```powershell
python main.py --dashboard --source 0
```

Use multiple sources for the grid:

```powershell
python main.py --dashboard --source 0 --source demo_video.mp4
```

See `docs/DASHBOARD.md` for full detector dashboard wiring.

## 11. GPU Notes

Ultralytics YOLOv8 can use CUDA when a compatible PyTorch build is installed.
The base `requirements.txt` leaves PyTorch to the Ultralytics dependency chain
for CPU-friendly installation. For GPU demos, install the correct PyTorch CUDA
wheel from the official PyTorch selector before running the detectors.

TensorFlow 2.10.1 is pinned because it is the most practical Windows-native
choice for Python 3.10 in this project. Native Windows GPU support for newer
TensorFlow versions is limited, so this project treats TensorFlow audio
classification as CPU-first on Windows.

## 12. Model Files

The `models/` folder is reserved for local weights.

- `yolov8n.pt`: general COCO object detector.
- `yolov8n-pose.pt`: pose detector.
- `weapon_yolov8.pt`: user-provided YOLOv8-compatible gun/knife detector.

Ultralytics can auto-download official YOLOv8 weights on first use when network
access is available. Weapon weights must be supplied separately.

## Troubleshooting

- If `tensorflow==2.10.1` fails to install, confirm the virtual environment is
  Python 3.10 and 64-bit.
- If OpenCV cannot access a webcam, close other camera applications and try
  camera index `0` or `1`.
- If RTSP playback is unstable, test the stream URL in VLC first.
- If YOLO runs slowly on CPU, use smaller weights such as `yolov8n.pt`, reduce
  input resolution, or install a CUDA-enabled PyTorch build.
- If `sounddevice` cannot open the microphone, check Windows privacy settings
  and default input device selection.
