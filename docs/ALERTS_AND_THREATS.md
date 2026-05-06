# Module 6: Threat Scoring and Alert Management

## What It Does

`alerts/threat_engine.py` and `alerts/alert_manager.py` centralize:

- threat score calculation;
- threat level escalation;
- alert event creation;
- JSONL and CSV event logs;
- evidence snapshot saving;
- duplicate-alert cooldown;
- optional Windows alarm beep.

## Required Score Table

| Event | Score |
| --- | ---: |
| Suspicious unattended bag | 40 |
| Suspicious running / running | 20 |
| Fight | 50 |
| Knife | 80 |
| Gun | 100 |
| Scream | 60 |
| Gunshot | 120 |
| Glass break | 70 |
| Explosion | 100 |

Detector-provided `Detection.threat_score` is used first. If it is missing, the
engine falls back to its label-to-score table.

## Threat Levels

| Total Score | Level |
| ---: | --- |
| 0-39 | LOW |
| 40-79 | MEDIUM |
| 80-100 | HIGH |
| >100 | CRITICAL |

The `>100` critical rule matches the project requirement.

## Output Files

By default, alert logs are saved under:

```text
outputs/logs/threat_events.jsonl
outputs/logs/threat_events.csv
```

Evidence images are saved under:

```text
outputs/snapshots/
```

Some detectors already save snapshots and pass `snapshot_path` in metadata. The
alert manager preserves that path instead of writing a duplicate image.

## Camera Integration Example

```python
from security_ai_system.alerts import AlertManager
from security_ai_system.cameras import CameraManager

camera_manager = CameraManager()
alert_manager = AlertManager()

# Add cameras and detectors here, then:
camera_manager.start_all()

try:
    while True:
        for result in camera_manager.latest_results().values():
            events = alert_manager.handle_camera_result(result)
            threat_state = alert_manager.current_threat_state()

            for event in events:
                print(event.iso_time, event.camera_id, event.label, event.threat_level)

            print(threat_state.total_score, threat_state.level.value)
finally:
    camera_manager.stop_all()
```

## Direct Alert Example

```python
from security_ai_system.alerts import AlertManager
from security_ai_system.utils.types import Detection

manager = AlertManager()
events = manager.handle_alerts(
    [Detection(label="GUNSHOT DETECTED", confidence=0.92)],
    camera_id="microphone-0",
    source="microphone",
)
```

## Unit Tests

```powershell
cd security_ai_system
python -m unittest tests.test_alerts
```

## Troubleshooting

- If no events are written, confirm detections have a positive `threat_score` or
  a label in the fallback score map.
- If repeated events appear too often, increase `event_cooldown_sec`.
- If snapshots are missing, confirm a valid image frame is passed to
  `handle_alerts()` or `handle_camera_result()`.
- If the alarm does not sound, confirm `alarm_enabled=True`; the built-in beep is
  Windows-only and intentionally non-fatal if unavailable.

