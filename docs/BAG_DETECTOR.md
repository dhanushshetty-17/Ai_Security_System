# Module 1: Suspicious Unattended Bag Detection

## What It Does

`detectors/bag_detector.py` detects and tracks:

- `person`
- `backpack`
- `handbag`
- `suitcase`

It uses YOLOv8 COCO detections and DeepSORT track IDs. Each tracked bag is
associated with the nearest person when the bag first appears. If the associated
owner moves beyond the configured distance, the detector starts an unattended
timer. When the timer passes the configured timeout, the bag is marked as:

```text
SUSPICIOUS BAG
```

The detector returns a `DetectorResult` containing:

- all person and bag detections;
- active suspicious-bag alerts;
- an annotated frame;
- per-frame processing time;
- saved snapshot paths when alerts are active.

## Bounding Box Colors

- Person: green
- Bag: orange
- Suspicious bag: red

## Important Parameters

Edit `BagDetectorConfig` when constructing the detector:

- `unattended_timeout_sec`: seconds before a separated bag becomes suspicious.
- `owner_assignment_max_distance_px`: max initial distance for owner assignment.
- `owner_absent_distance_px`: distance after which the owner is considered away.
- `stale_track_timeout_sec`: removes old bag state when tracks disappear.
- `snapshot_cooldown_sec`: limits duplicate evidence images.

## Unit Test

This test does not require YOLO, DeepSORT, OpenCV, or a camera. It tests the
ownership and timer rules directly:

```powershell
cd security_ai_system
python -m unittest discover -s tests
```

## Runtime Smoke Test

After installing requirements, a webcam test can be run from a short script:

```python
import cv2

from security_ai_system.detectors.bag_detector import SuspiciousBagDetector

detector = SuspiciousBagDetector(camera_id="webcam-0")
detector.load()

cap = cv2.VideoCapture(0)
while True:
    ok, frame = cap.read()
    if not ok:
        break
    result = detector.predict(frame)
    cv2.imshow("Bag Detector", result.annotated_frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
```

The first run may download official `yolov8n.pt` weights if they are not already
available.

## Demo Tips

- Place a backpack near a visible person first so ownership can be assigned.
- Have the person walk away from the bag and wait for the timeout.
- For presentations, reduce `unattended_timeout_sec` to `3` or `5`.
- Use `RuntimeConfig(save_snapshots=True)` to save evidence images under
  `outputs/snapshots/`.

