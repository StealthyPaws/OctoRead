"""
agents/eval_agent.py — EvalAgent (Evaluation + Correction)

Judges OCR output quality, cleans up text, and scans for sensitive data.
The judge of the operation — decides whether the loop continues or stops.
"""

import re
import statistics
from typing import Optional


# Sensitive data patterns for privacy scanning
SENSITIVE_PATTERNS = {
    "Email Address": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "Phone Number (PK)": r"(\+92|0092|0)[- ]?(3[0-9]{2})[- ]?[0-9]{7}",
    "Phone Number (Generic)": r"\b(\+?1?[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",
    "CNIC (Pakistan)": r"\b\d{5}[-\s]?\d{7}[-\s]?\d{1}\b",
    "Credit/Debit Card": r"\b(?:\d[ -]?){13,16}\b",
    "National ID (Generic)": r"\b[A-Z]{1,2}\d{6,9}[A-Z]?\b",
    "Date of Birth": r"\b(DOB|Date of Birth|Born)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    "Passport Number": r"\b[A-Z]{1,2}[0-9]{6,9}\b",
    "URL / Link": r"https?://[^\s]+",
    "IP Address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
}

# Common garbage characters that indicate bad OCR
GARBAGE_PATTERNS = [
    r"[|]{3,}",          # runs of pipes
    r"[~^]{3,}",         # runs of tildes/carets
    r"[^\x00-\x7F]{5,}", # long non-ASCII runs
    r"\d{20,}",          # absurdly long number runs
]

# Typical English stop-words presence increases confidence
COMMON_WORDS = {"the", "and", "is", "are", "of", "to", "a", "in", "that", "it",
                "for", "on", "with", "as", "at", "by", "from", "or", "an", "be"}


class EvalAgent:
    """
    Evaluates OCR output quality and applies corrections.
    Confidence is a composite score — not just Tesseract's raw confidence.
    """

    def evaluate(self, text: str, ocr_data: dict) -> dict:
        """
        Compute composite confidence score and identify issues.
        Returns an evaluation dict.
        """
        if not text or not text.strip():
            return {
                "confidence": 0.0,
                "word_count": 0,
                "error_flags": ["empty_output"],
                "tesseract_mean_conf": 0.0,
                "quality_label": "EMPTY",
            }

        word_count = len(text.split())
        error_flags = []
        score_components = []

        # 1. Tesseract confidence score (if available)
        tess_conf = self._extract_tesseract_confidence(ocr_data)
        if tess_conf is not None:
            score_components.append(("tesseract_conf", tess_conf, 0.45))
            if tess_conf < 40:
                error_flags.append("low_tesseract_confidence")
        else:
            # No Tesseract data — use a neutral placeholder
            tess_conf = 60.0

        # 2. Common word ratio — real English text has common words
        common_ratio = self._common_word_ratio(text)
        common_score = min(common_ratio * 200, 100)  # scale to 0-100
        score_components.append(("common_words", common_score, 0.25))

        # 3. Garbage character detection
        garbage_score = self._garbage_score(text)
        score_components.append(("garbage_check", garbage_score, 0.20))
        if garbage_score < 50:
            error_flags.append("garbage_characters_detected")

        # 4. Length sanity — very short output on a real image is suspicious
        length_score = min(word_count * 5, 100)
        score_components.append(("length_check", length_score, 0.10))
        if word_count < 5:
            error_flags.append("very_short_output")

        # Weighted composite
        total_weight = sum(w for _, _, w in score_components)
        confidence = sum(s * w for _, s, w in score_components) / total_weight

        quality_label = (
            "EXCELLENT" if confidence >= 80 else
            "GOOD" if confidence >= 65 else
            "FAIR" if confidence >= 45 else
            "POOR"
        )

        return {
            "confidence": round(confidence, 2),
            "word_count": word_count,
            "error_flags": error_flags,
            "tesseract_mean_conf": round(tess_conf, 2),
            "quality_label": quality_label,
            "score_breakdown": {k: round(s, 1) for k, s, _ in score_components},
        }

    def _extract_tesseract_confidence(self, ocr_data: dict) -> Optional[float]:
        """Pull mean word confidence from Tesseract's data dict."""
        if not ocr_data or "conf" not in ocr_data:
            return None
        confs = [int(c) for c in ocr_data.get("conf", []) if str(c).lstrip("-").isdigit() and int(c) >= 0]
        if not confs:
            return None
        return statistics.mean(confs)

    def _common_word_ratio(self, text: str) -> float:
        """What fraction of words are common English words?"""
        words = re.findall(r"[a-zA-Z]+", text.lower())
        if not words:
            return 0.0
        hits = sum(1 for w in words if w in COMMON_WORDS)
        return hits / len(words)

    def _garbage_score(self, text: str) -> float:
        """Returns 0-100; lower = more garbage detected."""
        for pattern in GARBAGE_PATTERNS:
            if re.search(pattern, text):
                return 20.0
        # Check ratio of printable to total characters
        printable = sum(1 for c in text if c.isprintable() or c in "\n\t")
        ratio = printable / max(len(text), 1)
        return round(ratio * 100, 1)

    def clean_text(self, text: str) -> str:
        """
        Apply basic text cleanup:
        - Remove multiple blank lines
        - Strip leading/trailing whitespace per line
        - Remove common OCR artefacts
        - Normalise spaces
        """
        if not text:
            return ""

        lines = text.split("\n")
        cleaned = []

        for line in lines:
            line = line.strip()
            # Remove lines that are pure garbage (only symbols, no letters/digits)
            if line and re.match(r"^[^a-zA-Z0-9\s]{3,}$", line):
                continue
            # Replace multiple spaces with single space
            line = re.sub(r" {2,}", " ", line)
            cleaned.append(line)

        # Remove runs of more than 2 blank lines
        result_lines = []
        blank_count = 0
        for line in cleaned:
            if line == "":
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        return "\n".join(result_lines).strip()

    def detect_sensitive_data(self, text: str) -> list[dict]:
        """
        Scan for patterns that might be sensitive personal data.
        Returns list of warning dicts.
        """
        warnings = []
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Redact full match for safety in warning preview
                preview = str(matches[0])
                if len(preview) > 8:
                    preview = preview[:4] + "****" + preview[-2:]
                warnings.append({
                    "type": pattern_name,
                    "count": len(matches),
                    "preview": preview,
                })
        return warnings
