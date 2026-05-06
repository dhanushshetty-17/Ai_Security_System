"""OpenCV drawing helpers for annotated surveillance frames."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from security_ai_system.utils.types import BoundingBox


Color = tuple[int, int, int]


@dataclass(frozen=True)
class DrawStyle:
    """Bounding box and label styling."""

    color: Color
    thickness: int = 2
    font_scale: float = 0.55
    text_thickness: int = 1


PERSON_STYLE = DrawStyle(color=(0, 180, 0))
BAG_STYLE = DrawStyle(color=(0, 165, 255))
SUSPICIOUS_STYLE = DrawStyle(color=(0, 0, 255), thickness=3)
WEAPON_STYLE = DrawStyle(color=(0, 0, 139), thickness=3)
BEHAVIOR_STYLE = DrawStyle(color=(160, 32, 240), thickness=2)


def draw_labeled_box(
    frame: Any,
    bbox: BoundingBox,
    label: str,
    style: DrawStyle,
) -> None:
    """Draw a bounding box with a filled label background on a BGR frame."""

    import cv2

    x1, y1, x2, y2 = bbox.as_xyxy()
    frame_h, frame_w = frame.shape[:2]
    x1 = max(0, min(x1, frame_w - 1))
    x2 = max(0, min(x2, frame_w - 1))
    y1 = max(0, min(y1, frame_h - 1))
    y2 = max(0, min(y2, frame_h - 1))

    cv2.rectangle(frame, (x1, y1), (x2, y2), style.color, style.thickness)

    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_w, text_h), baseline = cv2.getTextSize(
        label,
        font,
        style.font_scale,
        style.text_thickness,
    )
    label_y1 = max(0, y1 - text_h - baseline - 6)
    label_y2 = label_y1 + text_h + baseline + 6
    label_x2 = min(frame_w - 1, x1 + text_w + 8)

    cv2.rectangle(frame, (x1, label_y1), (label_x2, label_y2), style.color, -1)
    cv2.putText(
        frame,
        label,
        (x1 + 4, label_y2 - baseline - 3),
        font,
        style.font_scale,
        (255, 255, 255),
        style.text_thickness,
        cv2.LINE_AA,
    )


def draw_connection(
    frame: Any,
    start: tuple[int, int],
    end: tuple[int, int],
    color: Color = (255, 255, 0),
) -> None:
    """Draw a light owner-to-bag association line."""

    import cv2

    cv2.line(frame, start, end, color, 1, cv2.LINE_AA)


def draw_status_text(
    frame: Any,
    text: str,
    origin: tuple[int, int],
    color: Color = (255, 255, 255),
) -> None:
    """Draw readable overlay status text."""

    import cv2

    x, y = origin
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, text, (x + 1, y + 1), font, 0.55, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(frame, text, (x, y), font, 0.55, color, 1, cv2.LINE_AA)

