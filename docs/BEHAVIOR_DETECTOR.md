# Module 3: Human Behavior Analysis

## What It Does

`detectors/behavior_detector.py` uses YOLOv8 pose estimation plus transparent
motion heuristics to detect:

- `RUNNING`
- `FIGHT DETECTED`
- `FALL DETECTED`
- `SUSPICIOUS MOVEMENT`

`SUSPICIOUS MOVEMENT` is used for loitering, repeated abrupt direction changes,
and crowd-panic style movement.

## How It Works

1. YOLOv8 pose detects people and COCO 17-keypoint skeletons.
2. A lightweight centroid matcher assigns stable local IDs between frames.
3. `PoseAnalyzer` checks body posture and person-to-person interaction cues.
4. `MotionAnalyzer` keeps per-person motion history for running, loitering, and
   crowd-level fast movement.
5. Findings are returned as `Detection` alert objects and drawn with purple
   bounding boxes.

## Labels and Scores

- `RUNNING`: `20`
- `FIGHT DETECTED`: `50`
- `FALL DETECTED`: `50`
- `SUSPICIOUS MOVEMENT`: `20` or `30` depending on rule

## Webcam Demo Snippet

```python
import cv2

from security_ai_system.detectors.behavior_detector import BehaviorDetector

detector = BehaviorDetector(camera_id="webcam-0")
detector.load()

cap = cv2.VideoCapture(0)
while True:
    ok, frame = cap.read()
    if not ok:
        break

    result = detector.predict(frame)
    cv2.imshow("Behavior Detector", result.annotated_frame)

    for alert in result.alerts:
        print(alert.label, alert.track_id, alert.threat_score, alert.metadata["reason"])

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
```

The first run may download official `yolov8n-pose.pt` weights if they are not
already available.

## Unit Tests

The rule tests do not require YOLO, OpenCV, or a camera:

```powershell
cd security_ai_system
python -m unittest tests.test_behavior_analysis
```

## Demo Tips

- Use `yolov8n-pose.pt` for CPU demos and low latency.
- Use a short clip with a clear fall posture or fast movement for repeatability.
- Pose heuristics are lighting and camera-angle sensitive. Use a stable camera
  angle where the full body is visible.
- Treat behavior alerts as operator triage cues, not final judgments of intent.

