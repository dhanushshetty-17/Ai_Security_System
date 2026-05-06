# Architecture Design

## Goal

The system is designed as a modular real-time surveillance pipeline:

1. Camera workers read frames from webcam, RTSP, or video files.
2. Detector modules process frames or audio chunks independently.
3. Tracker modules provide persistent IDs for people, bags, and other objects.
4. Behavior modules analyze pose, speed, posture, and movement history.
5. The threat engine assigns scores and threat levels.
6. The alert manager persists events, snapshots, timestamps, and source metadata.
7. The dashboard renders annotated feeds, FPS, active alerts, history, and score.

## Module Responsibilities

- `detectors/`
  - `base.py`: shared detector contracts.
  - `bag_detector.py`: YOLOv8 object detection plus DeepSORT ownership logic.
  - `weapon_detector.py`: YOLOv8 custom weapon weights.
  - `behavior_detector.py`: YOLOv8 pose plus motion analysis.
  - `audio_detector.py`: audio threat detector wrapper.

- `trackers/`
  - `tracker.py`: DeepSORT adapter returning stable track IDs.

- `behavior/`
  - `pose_analysis.py`: posture rules such as falling and fighting candidates.
  - `motion_analysis.py`: speed, loitering, running, and panic metrics.

- `audio/`
  - `yamnet_classifier.py`: TensorFlow Hub YAMNet loading and class mapping.

- `cameras/`
  - `camera_manager.py`: threaded multi-source frame capture.

- `alerts/`
  - `threat_engine.py`: centralized score aggregation and level calculation.
  - `alert_manager.py`: logs, snapshot writing, and notification queue.

- `ui/`
  - `dashboard.py`: PyQt5 real-time grid dashboard.

- `utils/`
  - `drawing.py`: consistent bounding boxes, labels, and overlays.
  - `logger.py`: shared logging setup.
  - `types.py`: dataclasses and enums shared across modules.

## Model Strategy

- General object detection uses official Ultralytics YOLOv8 COCO weights such as
  `yolov8n.pt`, which supports `person`, `backpack`, `handbag`, and `suitcase`.
- Pose behavior detection uses official Ultralytics pose weights such as
  `yolov8n-pose.pt`.
- Weapon detection requires a separate YOLOv8-compatible weapon model trained on
  gun/knife classes. There is no official Ultralytics COCO weapon class for guns
  or knives, so the system will accept a configured `.pt` path instead of
  pretending one exists.
- Audio detection uses Google YAMNet from TensorFlow Hub.

## Threading Model

Each camera source will run in its own worker thread:

- frame capture thread reads frames and pushes them into a bounded queue;
- processing loop consumes the most recent frame to avoid latency build-up;
- detector results are pushed to the dashboard and alert queues.

This keeps a slow detector on one source from freezing every camera feed.

## Implemented: Bag Detection Pipeline

The bag detector follows this frame-level flow:

1. YOLOv8 detects COCO classes `person`, `backpack`, `handbag`, and `suitcase`.
2. Detections are converted to DeepSORT inputs.
3. DeepSORT returns confirmed person and bag tracks with stable IDs.
4. Each new bag is associated with the nearest person within the configured
   assignment distance.
5. If the owner is missing or farther than the absent-distance threshold, the
   unattended timer starts.
6. After `unattended_timeout_sec`, the detector emits a `SUSPICIOUS BAG` alert
   with threat score `40` and saves a snapshot when snapshot saving is enabled.

The detector can be unit-tested without loading YOLO or DeepSORT by exercising
the state update methods with synthetic `TrackedObject` instances.

## Implemented: Weapon Detection Pipeline

The weapon detector follows this frame-level flow:

1. A user-supplied YOLOv8 `.pt` weapon model is loaded.
2. YOLO detections are checked against configured class aliases.
3. `gun`, `pistol`, and `rifle` detections are normalized to `GUN DETECTED`.
4. `knife` detections are normalized to `KNIFE DETECTED`.
5. A dark-red bounding box is drawn with confidence.
6. Each weapon detection is emitted as a high-priority alert and an evidence
   snapshot is saved when snapshot saving is enabled.

This detector intentionally refuses to run without explicit weapon weights.
COCO object weights are not silently reused for weapons.

## Implemented: Behavior Detection Pipeline

The behavior detector follows this frame-level flow:

1. YOLOv8 pose detects people and COCO keypoints.
2. A lightweight centroid matcher assigns local IDs between frames.
3. Pose rules detect fall-like posture and close aggressive-contact cues.
4. Motion rules detect running, loitering, repeated direction changes, and
   crowd-level fast movement.
5. Purple labels are drawn above people with active behavior findings.

The behavior logic lives in `behavior/pose_analysis.py` and
`behavior/motion_analysis.py`, so rules can be unit-tested without YOLO.

## Implemented: Audio Detection Pipeline

The audio detector follows this chunk-level flow:

1. Audio is loaded from microphone chunks or file chunks as mono 16 kHz samples.
2. YAMNet from TensorFlow Hub produces AudioSet class scores.
3. AudioSet labels are matched against configured aliases for scream, gunshot,
   glass breaking, and explosion.
4. Matches become shared `Detection` alert objects with threat scores.
5. Per-label cooldown suppresses duplicate alert popups during continuous audio.

The YAMNet wrapper and audio detector can be unit-tested without loading the
TensorFlow Hub model by exercising label mapping and detector conversion.

## Implemented: Multi-Camera Pipeline

The camera manager follows this source-level flow:

1. Each `CameraSourceConfig` is registered with a `CameraWorker`.
2. Each worker opens one OpenCV source in its own thread.
3. Frames are published as `FramePacket` objects into a bounded queue.
4. Optional per-camera detectors run sequentially on the latest frame.
5. Processed output is published as `CameraPipelineResult` with annotated frame,
   detector results, alerts, processing time, and FPS.
6. `CameraManager.latest_results()` gives dashboard code the newest processed
   frame for every active camera.

The worker accepts an injectable `FrameReader`, so source handling is unit-tested
without requiring physical cameras or video files.

## Implemented: Threat and Alert Pipeline

The alert layer follows this event-level flow:

1. Detector alerts are collected from `DetectorResult` or `CameraPipelineResult`.
2. `ThreatScoringEngine` assigns scores using detector-provided values or the
   fallback project score table.
3. Active contributions inside the scoring window are summed into one total
   threat score.
4. Scores map to LOW, MEDIUM, HIGH, or CRITICAL.
5. `AlertManager` writes JSONL and CSV event logs, preserves or saves evidence
   snapshots, and applies duplicate-event cooldown.

This layer is independent from the UI, so the future dashboard can subscribe to
events and threat state without owning persistence logic.

## Implemented: Dashboard Pipeline

The dashboard follows this UI-level flow:

1. `CameraManager` workers produce latest processed results per camera.
2. The PyQt5 dashboard refreshes on a timer and renders each latest frame in a
   responsive camera grid.
3. New frame alerts are passed to `AlertManager` exactly once per frame.
4. The threat panel reads `ThreatState` for total score, active alert count, and
   level color.
5. Persisted alert events are appended to the event-history table.

PyQt5 imports are lazy, so dashboard helper tests run in non-GUI environments.
