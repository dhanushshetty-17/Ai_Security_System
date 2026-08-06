# AI Smart Surveillance and Threat Detection System

Production-style Python project for real-time surveillance demos with YOLOv8,
DeepSORT, YOLOv8 pose, YAMNet audio analysis, multi-camera processing, alerting,
evidence snapshots, and a PyQt5 dashboard.

The project is being built module-by-module. The current code includes the
foundation, Module 1 suspicious unattended bag detection, Module 2 weapon
detection, Module 3 human behavior analysis, Module 4 audio threat detection,
Module 5 multi-camera threading, Module 6 threat alerts, and Module 7 PyQt5
dashboard.

## Current Structure

```text
security_ai_system/
|-- detectors/
|   |-- __init__.py
|   |-- audio_detector.py
|   |-- base.py
|   |-- bag_detector.py
|   |-- behavior_detector.py
|   `-- weapon_detector.py
|-- behavior/
|   |-- __init__.py
|   |-- motion_analysis.py
|   `-- pose_analysis.py
|-- audio/
|   |-- __init__.py
|   |-- audio_sources.py
|   `-- yamnet_classifier.py
|-- trackers/
|   |-- __init__.py
|   `-- tracker.py
|-- cameras/
|   |-- __init__.py
|   `-- camera_manager.py
|-- alerts/
|   |-- __init__.py
|   |-- alert_manager.py
|   `-- threat_engine.py
|-- ui/
|   |-- __init__.py
|   `-- dashboard.py
|-- web/
|   |-- __init__.py
|   |-- app.py
|   |-- auth.py
|   |-- streamer.py
|   |-- templates/
|   `-- static/
|-- utils/
|   |-- __init__.py
|   |-- drawing.py
|   |-- logger.py
|   `-- types.py
|-- outputs/
|   |-- snapshots/
|   `-- logs/
|-- models/
|-- docs/
|   |-- ALERTS_AND_THREATS.md
|   |-- ARCHITECTURE.md
|   |-- AUDIO_DETECTOR.md
|   |-- BAG_DETECTOR.md
|   |-- BEHAVIOR_DETECTOR.md
|   |-- CAMERA_MANAGER.md
|   |-- DASHBOARD.md
|   |-- SETUP.md
|   `-- WEAPON_DETECTOR.md
|-- tests/
|   |-- test_alerts.py
|   |-- test_audio_detection.py
|   |-- test_behavior_analysis.py
|   |-- test_bag_detector_state.py
|   |-- test_camera_manager.py
|   |-- test_dashboard_helpers.py
|   `-- test_weapon_detector.py
|-- main.py
|-- requirements.txt
`-- README.md
```

## Install

Use Python 3.10 on Windows.

```powershell
cd D:\chatgpt\security_ai_system
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Smoke Test

```powershell
python main.py
```

Expected:

```text
AI Smart Surveillance foundation is ready.
```

## Bag Detector Unit Test

This test verifies owner association and unattended timing without a camera or
model download:

```powershell
python -m unittest discover -s tests
```

## Weapon Detector Unit Test

This validates weapon label mapping, threat scoring, and weight-path validation
without loading YOLO:

```powershell
python -m unittest tests.test_weapon_detector
```

## Behavior Analysis Unit Test

This validates fall, fight, running, loitering, panic, and local ID matching
without loading YOLO:

```powershell
python -m unittest tests.test_behavior_analysis
```

## Audio Detection Unit Test

This validates waveform prep, YAMNet label mapping, detector alerts, and alert
cooldown without loading TensorFlow Hub:

```powershell
python -m unittest tests.test_audio_detection
```

## Multi-Camera Unit Test

This validates threaded workers, source inference, queue output, and detector
pipeline integration without opening real cameras:

```powershell
python -m unittest tests.test_camera_manager
```

## Alerts and Threat Scoring Unit Test

This validates score thresholds, fallback scoring, active-window expiry, JSONL
and CSV logging, cooldown, and snapshot-path preservation:

```powershell
python -m unittest tests.test_alerts
```

## Dashboard Helper Unit Test

This validates dashboard grid, formatting, event rows, colors, and source
builder helpers without starting PyQt5:

```powershell
python -m unittest tests.test_dashboard_helpers
```

## Implemented Modules

1. Foundation:
   shared types, detector base classes, logging, folder structure, setup docs.

2. Suspicious unattended bag detection:
   YOLOv8 COCO labels, DeepSORT track IDs, owner association, unattended timer,
   red suspicious-bag annotations, snapshots, and alert objects.

3. Weapon detection:
   configured YOLOv8-compatible gun/knife weights, dark-red boxes, confidence
   labels, high-priority alerts, threat scores, and snapshots.

4. Human behavior analysis:
   YOLOv8 pose wrapper, local centroid tracking, fall posture rules, fight
   interaction rules, running, loitering, crowd panic, and purple annotations.

5. Audio threat detection:
   YAMNet wrapper, microphone/file chunk helpers, scream/gunshot/glass/explosion
   label mapping, threat scores, and alert cooldown.

6. Multi-camera support:
   OpenCV source readers for webcam/video/RTSP/HTTP, independent camera worker
   threads, bounded queues, per-camera detector pipelines, latest-result access,
   FPS status, and alert draining.

7. Threat scoring and alert management:
   centralized score table, active threat window, LOW/MEDIUM/HIGH/CRITICAL
   levels, JSONL and CSV logs, evidence snapshot handling, event history, and
   optional Windows alarm beep.

8. PyQt5 dashboard:
   multi-camera grid, live frame rendering, FPS/status display, threat score,
   active alert count, event history table, and start/stop controls.

9. Web dashboard (FastAPI):
   Web-based secure interface with JWT authentication, MJPEG streaming, real-time threat
   polling, settings toggles (for AI models/heatmap), system health monitor,
   and Gemini Vision GenAI police-style incident reports with search capabilities.

## Planned Modules

All requested core modules are now implemented. Remaining work is integration
polish, optional packaged demo scripts, and real model/video asset setup.

## Demo Plan

The finished demo will support:

- webcam input;
- prerecorded video files;
- RTSP CCTV streams;
- multi-camera grid view;
- annotated bounding boxes;
- threat score escalation;
- event history;
- saved snapshots and logs.

Quick desktop dashboard demo:

```powershell
python main.py --dashboard --source 0
```

Web dashboard demo (Recommended):

```powershell
python main.py --web --source 0
```

## Important Model Note

COCO YOLOv8 weights include `person`, `backpack`, `handbag`, and `suitcase`,
which are enough for unattended bag detection. COCO does not provide reliable
gun, pistol, rifle, or knife classes. Weapon detection therefore requires a real
YOLOv8-compatible custom `.pt` model path supplied in `models/`.

Detailed setup and troubleshooting live in `docs/SETUP.md`.
