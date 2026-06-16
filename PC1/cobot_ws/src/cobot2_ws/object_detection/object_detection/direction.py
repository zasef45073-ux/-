from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple

import cv2
import numpy as np

DirectionLabel = Literal["horizontal", "vertical", "square", "unknown"]
VerticalPolarityLabel = Literal["up", "down", "unknown"]


@dataclass
class Direction2DResult:
    label: DirectionLabel
    aspect_ratio: float
    width: float
    height: float
    angle_deg: float
    center: Tuple[float, float]


@dataclass
class DirectionPolarityResult:
    label: VerticalPolarityLabel
    confidence: float
    top_area_ratio: float
    bottom_area_ratio: float


def estimate_direction_from_box(
    box: Sequence[float],
    horizontal_ratio: float = 1.20,
    vertical_ratio: float = 0.83,
) -> Direction2DResult:
    """Estimate object direction from bbox aspect ratio.

    Args:
        box: [x1, y1, x2, y2]
        horizontal_ratio: If width/height >= horizontal_ratio -> horizontal.
        vertical_ratio: If width/height <= vertical_ratio -> vertical.

    Returns:
        Direction2DResult with a coarse direction label.
    """
    if len(box) != 4:
        return Direction2DResult("unknown", 0.0, 0.0, 0.0, 0.0, (0.0, 0.0))

    x1, y1, x2, y2 = [float(v) for v in box]
    width = max(0.0, x2 - x1)
    height = max(0.0, y2 - y1)

    if width <= 0.0 or height <= 0.0:
        return Direction2DResult("unknown", 0.0, width, height, 0.0, (0.0, 0.0))

    ratio = width / height
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0

    if ratio >= horizontal_ratio:
        label: DirectionLabel = "horizontal"
    elif ratio <= vertical_ratio:
        label = "vertical"
    else:
        label = "square"

    return Direction2DResult(label, ratio, width, height, 0.0, (cx, cy))


def estimate_direction_from_roi(
    roi_bgr: np.ndarray,
    min_area: float = 400.0,
    horizontal_ratio: float = 1.20,
    vertical_ratio: float = 0.83,
) -> Direction2DResult:
    """Estimate object direction from ROI contour using minAreaRect.

    This is usually more stable than bbox-only direction because it uses
    the visible object shape inside ROI.
    """
    if roi_bgr is None or roi_bgr.size == 0:
        return Direction2DResult("unknown", 0.0, 0.0, 0.0, 0.0, (0.0, 0.0))

    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return Direction2DResult("unknown", 0.0, 0.0, 0.0, 0.0, (0.0, 0.0))

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < min_area:
        return Direction2DResult("unknown", 0.0, 0.0, 0.0, 0.0, (0.0, 0.0))

    (cx, cy), (w, h), angle = cv2.minAreaRect(contour)
    w = float(w)
    h = float(h)

    if w <= 1e-6 or h <= 1e-6:
        return Direction2DResult("unknown", 0.0, w, h, float(angle), (float(cx), float(cy)))

    ratio = w / h
    if ratio >= horizontal_ratio:
        label: DirectionLabel = "horizontal"
    elif ratio <= vertical_ratio:
        label = "vertical"
    else:
        label = "square"

    return Direction2DResult(label, ratio, w, h, float(angle), (float(cx), float(cy)))


def estimate_vertical_polarity_from_roi(
    roi_bgr: np.ndarray,
    min_area: float = 400.0,
    diff_threshold: float = 0.08,
) -> DirectionPolarityResult:
    """Estimate up/down polarity from ROI silhouette distribution.

    Strategy:
        1) Build foreground mask from ROI.
        2) Find the largest contour.
        3) Compare top-half and bottom-half occupied area ratio.

    Note:
        - This works when the object has asymmetric silhouette along Y axis.
        - Symmetric or heavily occluded shapes often return "unknown".
    """
    if roi_bgr is None or roi_bgr.size == 0:
        return DirectionPolarityResult("unknown", 0.0, 0.0, 0.0)

    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return DirectionPolarityResult("unknown", 0.0, 0.0, 0.0)

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < min_area:
        return DirectionPolarityResult("unknown", 0.0, 0.0, 0.0)

    h, w = binary.shape
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask, [contour], -1, 255, thickness=-1)

    mid = h // 2
    top_area = float(np.count_nonzero(mask[:mid, :]))
    bottom_area = float(np.count_nonzero(mask[mid:, :]))
    total_area = top_area + bottom_area
    if total_area <= 1e-6:
        return DirectionPolarityResult("unknown", 0.0, 0.0, 0.0)

    top_ratio = top_area / total_area
    bottom_ratio = bottom_area / total_area
    diff = top_ratio - bottom_ratio
    confidence = abs(diff)

    if confidence < diff_threshold:
        return DirectionPolarityResult("unknown", confidence, top_ratio, bottom_ratio)

    label: VerticalPolarityLabel = "up" if diff > 0 else "down"
    return DirectionPolarityResult(label, confidence, top_ratio, bottom_ratio)


class DirectionEstimator:
    """Unified estimator for 2D direction and vertical polarity."""

    def __init__(
        self,
        horizontal_ratio: float = 1.20,
        vertical_ratio: float = 0.83,
        min_area: float = 400.0,
        polarity_diff_threshold: float = 0.08,
    ):
        self.horizontal_ratio = horizontal_ratio
        self.vertical_ratio = vertical_ratio
        self.min_area = min_area
        self.polarity_diff_threshold = polarity_diff_threshold

    def from_box(self, box: Sequence[float]) -> Direction2DResult:
        return estimate_direction_from_box(
            box,
            horizontal_ratio=self.horizontal_ratio,
            vertical_ratio=self.vertical_ratio,
        )

    def from_roi(self, roi_bgr: np.ndarray) -> Direction2DResult:
        return estimate_direction_from_roi(
            roi_bgr,
            min_area=self.min_area,
            horizontal_ratio=self.horizontal_ratio,
            vertical_ratio=self.vertical_ratio,
        )

    def vertical_polarity(self, roi_bgr: np.ndarray) -> DirectionPolarityResult:
        return estimate_vertical_polarity_from_roi(
            roi_bgr,
            min_area=self.min_area,
            diff_threshold=self.polarity_diff_threshold,
        )

    def estimate_all(
        self,
        box: Sequence[float],
        roi_bgr: np.ndarray,
    ) -> Tuple[Direction2DResult, Direction2DResult, DirectionPolarityResult]:
        """Return (box_direction, roi_direction, vertical_polarity)."""
        box_dir = self.from_box(box)
        roi_dir = self.from_roi(roi_bgr)
        polarity = self.vertical_polarity(roi_bgr)
        return box_dir, roi_dir, polarity
