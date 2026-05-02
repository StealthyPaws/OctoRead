"""
agents/strategy_agent.py — StrategyAgent (Decision Maker)

Picks the right preprocessing approach and OCR config for the image.
Has a menu of strategies and avoids ones that already failed.
"""

import io
import numpy as np

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


# ── Strategy definitions ──────────────────────────────────────────────────────
# Each strategy specifies preprocessing steps + OCR config.
# The agent picks from this menu based on image features and past failures.

STRATEGIES = {
    "standard": {
        "name": "standard",
        "description": "Default grayscale + Otsu threshold. Good for clean typed docs.",
        "preprocess": ["grayscale", "otsu_threshold"],
        "ocr_config": "--oem 3 --psm 3",
        "priority": 1,
    },
    "adaptive_threshold": {
        "name": "adaptive_threshold",
        "description": "Adaptive thresholding. Better for uneven lighting.",
        "preprocess": ["grayscale", "adaptive_threshold"],
        "ocr_config": "--oem 3 --psm 6",
        "priority": 2,
    },
    "denoise_enhance": {
        "name": "denoise_enhance",
        "description": "Denoise + contrast enhancement. For noisy / low-quality images.",
        "preprocess": ["grayscale", "denoise", "contrast_enhance", "otsu_threshold"],
        "ocr_config": "--oem 3 --psm 6",
        "priority": 3,
    },
    "upscale_sharpen": {
        "name": "upscale_sharpen",
        "description": "Upscale small images + sharpening kernel. For tiny or blurry images.",
        "preprocess": ["grayscale", "upscale", "sharpen", "otsu_threshold"],
        "ocr_config": "--oem 3 --psm 6",
        "priority": 4,
    },
    "aggressive": {
        "name": "aggressive",
        "description": "Full pipeline: denoise, CLAHE, morphology. Last resort for bad images.",
        "preprocess": ["grayscale", "denoise", "clahe", "morph_open", "adaptive_threshold"],
        "ocr_config": "--oem 3 --psm 4",
        "priority": 5,
    },
}


class StrategyAgent:
    """Selects and applies image preprocessing strategy, then runs Tesseract OCR."""

    def list_strategy_names(self) -> list[str]:
        return list(STRATEGIES.keys())

    def choose_strategy(
        self,
        image_features: dict,
        failed_strategies: list[str],
        attempt_num: int,
    ) -> dict:
        """
        Picks best strategy given image features and what's already failed.
        First attempt uses image features to choose; subsequent attempts escalate.
        """
        # Gather candidates (not already failed)
        candidates = [
            s for name, s in STRATEGIES.items()
            if name not in failed_strategies
        ]

        if not candidates:
            # All failed — return the last resort anyway
            return STRATEGIES["aggressive"]

        # On first attempt, use image-feature-based heuristics
        if attempt_num == 1:
            return self._heuristic_pick(image_features, candidates)

        # On retries, just escalate priority order
        candidates_sorted = sorted(candidates, key=lambda s: s["priority"])
        chosen = candidates_sorted[0]
        chosen = dict(chosen)  # copy
        chosen["reason"] = f"Escalating after {attempt_num - 1} failed attempt(s)."
        return chosen

    def _heuristic_pick(self, features: dict, candidates: list[dict]) -> dict:
        """Use image features to pick best starting strategy."""
        noise = features.get("noise_level", "low")
        blur = features.get("blur_score", 200)
        contrast = features.get("contrast_score", 50)
        doc_type = features.get("document_type", "typed")

        chosen = None
        reason = ""

        if doc_type == "handwritten":
            chosen = STRATEGIES.get("adaptive_threshold")
            reason = "Handwritten doc detected — adaptive threshold handles uneven ink."
        elif noise in ("medium", "high"):
            chosen = STRATEGIES.get("denoise_enhance")
            reason = f"Noise level '{noise}' detected — denoising pipeline selected."
        elif blur < 50:
            chosen = STRATEGIES.get("upscale_sharpen")
            reason = f"Low sharpness (blur={blur:.0f}) — upscale + sharpen selected."
        elif contrast < 35:
            chosen = STRATEGIES.get("denoise_enhance")
            reason = f"Low contrast ({contrast:.1f}) — contrast enhancement selected."
        else:
            chosen = STRATEGIES.get("standard")
            reason = "Image quality looks clean — standard Otsu strategy selected."

        # Make sure chosen is in candidates
        if chosen is None or chosen["name"] not in [c["name"] for c in candidates]:
            candidates_sorted = sorted(candidates, key=lambda s: s["priority"])
            chosen = candidates_sorted[0]
            reason = "Fallback: picking lowest-priority unused strategy."

        chosen = dict(chosen)
        chosen["reason"] = reason
        return chosen

    def preprocess(self, image_bytes: bytes, strategy: dict) -> np.ndarray:
        """
        Apply the preprocessing steps from the strategy.
        Returns a numpy array ready for Tesseract.
        """
        img_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img = np.array(img_pil)

        steps = strategy.get("preprocess", ["grayscale"])

        for step in steps:
            img = self._apply_step(img, step)

        return img

    def _apply_step(self, img: np.ndarray, step: str) -> np.ndarray:
        """Apply a single preprocessing step."""
        if step == "grayscale":
            if CV2_AVAILABLE and len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
            else:
                # PIL fallback
                pil = Image.fromarray(img).convert("L")
                img = np.array(pil)

        elif step == "otsu_threshold":
            if CV2_AVAILABLE:
                _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                img = (img > 127).astype(np.uint8) * 255

        elif step == "adaptive_threshold":
            if CV2_AVAILABLE:
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                img = cv2.adaptiveThreshold(
                    img, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )
            else:
                img = (img > 127).astype(np.uint8) * 255

        elif step == "denoise":
            if CV2_AVAILABLE:
                if len(img.shape) == 3:
                    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
                else:
                    img = cv2.fastNlMeansDenoising(img, None, 10, 7, 21)
            # PIL fallback: nothing (skip step)

        elif step == "contrast_enhance":
            if CV2_AVAILABLE and len(img.shape) == 2:
                img = cv2.equalizeHist(img)
            else:
                pil = Image.fromarray(img)
                pil = ImageEnhance.Contrast(pil).enhance(2.0)
                img = np.array(pil)

        elif step == "clahe":
            if CV2_AVAILABLE:
                if len(img.shape) == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                img = clahe.apply(img)

        elif step == "upscale":
            h, w = img.shape[:2]
            if max(h, w) < 1000:
                scale = 2.0
                if CV2_AVAILABLE:
                    img = cv2.resize(img, (int(w * scale), int(h * scale)),
                                     interpolation=cv2.INTER_CUBIC)
                else:
                    pil = Image.fromarray(img).resize(
                        (int(w * scale), int(h * scale)), Image.BICUBIC
                    )
                    img = np.array(pil)

        elif step == "sharpen":
            if CV2_AVAILABLE:
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
                img = cv2.filter2D(img, -1, kernel)
            else:
                pil = Image.fromarray(img)
                img = np.array(pil.filter(ImageFilter.SHARPEN))

        elif step == "morph_open":
            if CV2_AVAILABLE:
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
                img = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

        return img

    def run_ocr(self, processed_img: np.ndarray, strategy: dict) -> tuple[str, dict]:
        """
        Run Tesseract on the processed image.
        Returns (raw_text, ocr_data_dict).
        """
        if not TESSERACT_AVAILABLE:
            return self._mock_ocr(processed_img)

        try:
            config = strategy.get("ocr_config", "--oem 3 --psm 3")
            pil_img = Image.fromarray(processed_img)

            # Get text
            text = pytesseract.image_to_string(pil_img, config=config)

            # Get per-word confidence data
            try:
                ocr_data = pytesseract.image_to_data(
                    pil_img,
                    config=config,
                    output_type=pytesseract.Output.DICT,
                )
            except Exception:
                ocr_data = {}

            return text, ocr_data

        except Exception as e:
            return f"[OCR Error: {e}]", {}

    def _mock_ocr(self, img: np.ndarray) -> tuple[str, dict]:
        """Fallback when Tesseract is unavailable (for local dev/testing)."""
        return (
            "Sample OCR Output\n\nThis is placeholder text.\n"
            "Tesseract is not installed in this environment.\n"
            "Please install tesseract-ocr to get real output.",
            {}
        )
