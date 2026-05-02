"""
agents/image_agent.py — ImageAgent (Perception)

Looks at the raw image and figures out what we're dealing with:
blur level, contrast, noise, estimated document type.
Sends these features upstream so StrategyAgent can make smart choices.
"""

import io
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageStat
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageAgent:
    """Analyzes image quality and extracts features for strategy selection."""

    def analyze(self, image_bytes: bytes) -> dict:
        """
        Main analysis method. Returns a feature dict.
        Falls back gracefully if OpenCV isn't available.
        """
        features = {
            "blur_score": 100.0,       # Higher = sharper
            "contrast_score": 100.0,   # Higher = more contrast
            "noise_level": "low",      # low / medium / high
            "brightness": "normal",    # dark / normal / bright
            "is_grayscale": False,
            "width": 0,
            "height": 0,
            "document_type": "unknown",  # typed / handwritten / mixed / receipt / table
            "needs_deskew": False,
            "needs_denoise": False,
            "needs_contrast_boost": False,
        }

        try:
            img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            features["width"], features["height"] = img_pil.size

            img_array = np.array(img_pil)

            if CV2_AVAILABLE:
                features = self._analyze_with_cv2(img_array, features)
            else:
                features = self._analyze_with_pil(img_pil, features)

            features["document_type"] = self._estimate_doc_type(features)
            features["needs_denoise"] = features["noise_level"] in ("medium", "high")
            features["needs_contrast_boost"] = features["contrast_score"] < 40
            features["needs_deskew"] = features.get("skew_angle", 0) > 2.0

        except Exception as e:
            features["analysis_error"] = str(e)

        return features

    def _analyze_with_cv2(self, img_array: np.ndarray, features: dict) -> dict:
        """Full analysis using OpenCV."""
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)

        # Blur detection via Laplacian variance — low variance = blurry
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        features["blur_score"] = min(laplacian_var, 1000.0)  # cap for display

        # Contrast via standard deviation of pixel values
        features["contrast_score"] = float(gray.std())

        # Noise estimation via difference from gaussian blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise_diff = np.abs(gray.astype(float) - blurred.astype(float)).mean()
        if noise_diff < 3:
            features["noise_level"] = "low"
        elif noise_diff < 8:
            features["noise_level"] = "medium"
        else:
            features["noise_level"] = "high"

        # Brightness
        mean_brightness = gray.mean()
        if mean_brightness < 80:
            features["brightness"] = "dark"
        elif mean_brightness > 200:
            features["brightness"] = "bright"
        else:
            features["brightness"] = "normal"

        # Grayscale check
        b, g, r = img_array[:,:,2], img_array[:,:,1], img_array[:,:,0]
        color_diff = np.abs(r.astype(int) - g.astype(int)).mean() + \
                     np.abs(g.astype(int) - b.astype(int)).mean()
        features["is_grayscale"] = bool(color_diff < 10)

        # Skew detection (simplified)
        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 100)
            if lines is not None:
                angles = []
                for rho, theta in lines[:, 0]:
                    angle = (theta * 180 / np.pi) - 90
                    if abs(angle) < 45:
                        angles.append(angle)
                if angles:
                    features["skew_angle"] = float(np.median(angles))
                else:
                    features["skew_angle"] = 0.0
            else:
                features["skew_angle"] = 0.0
        except Exception:
            features["skew_angle"] = 0.0

        return features

    def _analyze_with_pil(self, img_pil: "Image.Image", features: dict) -> dict:
        """Fallback analysis using PIL only."""
        stat = ImageStat.Stat(img_pil.convert("L"))
        features["contrast_score"] = stat.stddev[0]
        features["blur_score"] = 200.0  # Can't measure without CV2, assume medium
        features["brightness"] = (
            "dark" if stat.mean[0] < 80 else
            "bright" if stat.mean[0] > 200 else
            "normal"
        )
        return features

    def _estimate_doc_type(self, features: dict) -> str:
        """
        Heuristic guess at document type based on image properties.
        This shapes the OCR strategy.
        """
        blur = features.get("blur_score", 100)
        contrast = features.get("contrast_score", 50)

        # Very low contrast often = handwritten or faded document
        if contrast < 25:
            return "handwritten"

        # Very high blur with decent contrast = receipt / low-res scan
        if blur < 30:
            return "receipt"

        # Default typed
        return "typed"
