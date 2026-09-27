"""
A module to receive and correct detections coordinate made from a CV model before being sent to the turret

The received detection's coordinate will be processed to take into account lens distortion and camera offset to the turret center using camera calibration data and a translation matrix.

The detection will also go through a filter module, retaining the detection fitting within a class set and with the highest confidence.

Exports a function that contains the preprocessing pipeline, that will be called by a socketio listener

Design Principles:
- huh ??

"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

DEFAULT_CALIBRATION_PATH = Path(__file__).resolve().parents[1] / "calibration.yaml"


@dataclass
class Detection:
    classname: str
    conf: float
    cls: int
    bbox: List[int]
    center: Tuple[float, float]


@dataclass
class Detections:
    frame: int
    timestamp: float
    detections: List[Detection]

    @classmethod
    def from_payload(cls, payload: Any) -> "Detections":
        """Build a Detections from a Detections instance or a socketio JSON payload."""
        if isinstance(payload, cls):
            return payload

        detections = [
            Detection(
                classname=d.get("classname", ""),
                conf=d.get("conf", 0.0),
                cls=d.get("cls", -1),
                bbox=d.get("bbox", []),
                center=(d.get("center", [0, 0])[0], d.get("center", [0, 0])[1]),
            )
            for d in payload.get("detections", [])
        ]

        return cls(
            frame=payload.get("frame", -1),
            timestamp=payload.get("timestamp", 0.0),
            detections=detections,
        )


# Global optical preproc instance
optical_preproc = None


def get_optical_preproc():
    global optical_preproc
    if optical_preproc is None:
        optical_preproc = Optical_Preproc(allowed_classes={"bird", "person"})

    return optical_preproc


def _load_opencv_calibration(path: Path) -> Dict[str, Any]:
    """Parse an OpenCV-generated calibration YAML (%YAML:1.0 files, not loadable by PyYAML)."""
    text = path.read_text()

    def parse_matrix(key: str) -> np.ndarray:
        match = re.search(
            rf"{key}:.*?rows:\s*(\d+).*?cols:\s*(\d+).*?data:\s*\[(.*?)\]",
            text,
            re.DOTALL,
        )
        if match is None:
            raise ValueError(f"Missing '{key}' in calibration file {path}")
        rows, cols, data = int(match.group(1)), int(match.group(2)), match.group(3)
        values = [float(v) for v in data.replace(",", " ").split()]
        if len(values) != rows * cols:
            raise ValueError(f"'{key}' in {path} declares {rows}x{cols} but holds {len(values)} values")
        return np.array(values).reshape(rows, cols)

    def parse_scalar(key: str) -> float:
        match = re.search(rf"^{key}:\s*([-0-9.eE+]+)\s*$", text, re.MULTILINE)
        if match is None:
            raise ValueError(f"Missing '{key}' in calibration file {path}")
        return float(match.group(1))

    return {
        "camera_matrix": parse_matrix("camera_matrix"),
        "dist_coeffs": parse_matrix("dist_coeffs").flatten(),
        "image_width": int(parse_scalar("image_width")),
        "image_height": int(parse_scalar("image_height")),
    }


class Optical_Preproc:

    _BOUNDARY_SAMPLES = 720  # directions sampled for the reachable-radius boundary
    _SOLVE_MARGIN = 0.98      # keep targets this fraction of the boundary: roots too close
                              # to it are ill-conditioned (the model folds there)

    def __init__(self, allowed_classes: Optional[Set[str]] = None,
                 calibration_path: Optional[Path] = DEFAULT_CALIBRATION_PATH):
        """
        Args:
            allowed_classes: set of classnames to keep (e.g. {"plane", "bird"}).
                None keeps every class.
            calibration_path: path to the camera calibration YAML written by OpenCV.
                None skips calibration loading (angles fall back to the raw pixel offsets).
        """
        self.allowed_classes = allowed_classes

        self.camera_matrix: Optional[np.ndarray] = None
        self.dist_coeffs: Optional[np.ndarray] = None
        self._dist5: Optional[np.ndarray] = None
        self._r_undist_max: float = np.inf
        self._r_dist_max: float = np.inf

        if calibration_path is not None:
            calibration = _load_opencv_calibration(Path(calibration_path))
            self.camera_matrix = calibration["camera_matrix"]
            self.dist_coeffs = calibration["dist_coeffs"]

            self._dist5 = np.zeros(5)
            self._dist5[:len(self.dist_coeffs)] = self.dist_coeffs[:5]
            self._r_undist_max, self._r_dist_max = self._invertible_domain()

    def set_allowed_classes(self, allowed_classes: Optional[Set[str]]) -> None:
        self.allowed_classes = allowed_classes

    def _is_allowed(self, detection: Detection) -> bool:
        return self.allowed_classes is None or detection.classname in self.allowed_classes

    def _invertible_domain(self) -> Tuple[float, float]:
        """Bounds of the distortion model's invertible region: (undistorted, distorted) radii.

        The 6th-degree radial polynomial is only monotonic up to a fold point;
        beyond it (image corners of a wide lens, outside the calibrated data)
        the model has no physical preimage, so undistortion clamps to this radius.
        """
        k1, k2, _, _, k3 = self._dist5
        r2 = np.linspace(0.0, 4.0, 4001)[1:]
        radial = 1 + k1 * r2 + k2 * r2**2 + k3 * r2**3
        mapped_radius = np.sqrt(r2) * radial
        i = int(np.argmax(mapped_radius))
        return float(np.sqrt(r2[i])), float(mapped_radius[i])

    def _solve_normalized(self, x_target: float, y_target: float,
                          x: float, y: float, iterations: int) -> Tuple[float, float]:
        """Newton's method for the preimage of (x_target, y_target), starting from (x, y).

        Iterates are projected back inside the model's fold radius, so a bad
        step cannot run off.
        """
        k1, k2, p1, p2, k3 = self._dist5

        for _ in range(iterations):
            r2 = x * x + y * y
            radial = 1 + k1 * r2 + k2 * r2 * r2 + k3 * r2 * r2 * r2
            f1 = x * radial + 2 * p1 * x * y + p2 * (r2 + 2 * x * x) - x_target
            f2 = y * radial + p1 * (r2 + 2 * y * y) + 2 * p2 * x * y - y_target

            d_radial_dx = 2 * x * (k1 + 2 * k2 * r2 + 3 * k3 * r2 * r2)
            d_radial_dy = 2 * y * (k1 + 2 * k2 * r2 + 3 * k3 * r2 * r2)
            j11 = radial + x * d_radial_dx + 2 * p1 * y + 6 * p2 * x
            j12 = x * d_radial_dy + 2 * p1 * x + 2 * p2 * y
            j21 = y * d_radial_dx + 2 * p1 * x + 2 * p2 * y
            j22 = radial + y * d_radial_dy + 6 * p1 * y + 2 * p2 * x

            det = j11 * j22 - j12 * j21
            x -= (j22 * f1 - j12 * f2) / det
            y -= (-j21 * f1 + j11 * f2) / det

            r = float(np.hypot(x, y))
            if r > self._r_undist_max:
                x, y = x * self._r_undist_max / r, y * self._r_undist_max / r

        return x, y

    def _undistort_normalized(self, x_dist: float, y_dist: float) -> Tuple[float, float]:
        """Invert the lens distortion of normalized image coordinates.

        Targets beyond the model's reachable radius (no preimage exists, e.g.
        image corners of a wide lens) are clamped onto its boundary, keeping
        their direction. Near the model's fold point the inverse problem is
        ill-conditioned and plain Newton diverges, so the target is walked out
        from the center in steps, warm-starting Newton on the previous root
        (continuation); elsewhere Newton converges directly.
        """
        r_dist = float(np.hypot(x_dist, y_dist))
        if r_dist == 0.0:
            return 0.0, 0.0

        if r_dist > self._r_dist_max:
            x_dist, y_dist = x_dist * self._r_dist_max / r_dist, y_dist * self._r_dist_max / r_dist
            r_dist = self._r_dist_max

        if r_dist < 0.9 * self._r_dist_max:
            return self._solve_normalized(x_dist, y_dist, x_dist, y_dist, 20)

        x, y = 0.0, 0.0
        for i in range(1, 65):
            t = i / 64
            x, y = self._solve_normalized(t * x_dist, t * y_dist, x, y, 4)

        return x, y

    def _detection_vec_to_degs(self, detection: Detection) -> List[float]:
        """Convert a detection center to [azimuth, elevation] in degrees relative to the camera optical axis.

        Azimuth is positive to the right of the image center, elevation is positive above it.
        """
        x, y = detection.center

        if self.camera_matrix is None:
            return [float(x), float(y)]

        fx, fy = self.camera_matrix[0, 0], self.camera_matrix[1, 1]
        cx, cy = self.camera_matrix[0, 2], self.camera_matrix[1, 2]

        x_norm, y_norm = (x - cx) / fx, (y - cy) / fy
        x_und, y_und = self._undistort_normalized(x_norm, y_norm)

        azimuth = float(np.degrees(np.arctan(x_und)))
        elevation = float(np.degrees(np.arctan(-y_und)))

        return [azimuth, elevation]

    def _score_detections(self, detection: Detection) -> float:
        return detection.conf

    def process_detections(self, payload: Any) -> Optional[List[float]]:
        """Preprocessing pipeline: keep allowed classes, pick the highest confidence detection, convert to degrees."""
        detections = [
            d for d in Detections.from_payload(payload).detections
            if self._is_allowed(d)
        ]

        if not detections:
            return None

        best = max(detections, key=self._score_detections)
        return self._detection_vec_to_degs(best)
