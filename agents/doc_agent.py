"""
agents/doc_agent.py — DocAgent (Controller + Memory)

The brain of the operation. Runs the full observe→decide→act→evaluate→improve loop.
Stores session memory so it knows what worked and what flopped.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

from agents.image_agent import ImageAgent
from agents.strategy_agent import StrategyAgent
from agents.eval_agent import EvalAgent


@dataclass
class AttemptRecord:
    """One attempt in the retry loop."""
    attempt_num: int
    strategy_name: str
    confidence: float
    word_count: int
    error_flags: list
    text_preview: str
    timestamp: float = field(default_factory=time.time)


class SessionMemory:
    """Lightweight in-session memory. Tracks what strategies were tried and how they scored."""

    def __init__(self):
        self.attempts: list[AttemptRecord] = []
        self.best_attempt: Optional[AttemptRecord] = None
        self.best_text: str = ""
        self.decision_log: list[str] = []
        self.failed_strategies: list[str] = []

    def record(self, record: AttemptRecord, text: str):
        self.attempts.append(record)
        if self.best_attempt is None or record.confidence > self.best_attempt.confidence:
            self.best_attempt = record
            self.best_text = text

    def log(self, message: str):
        ts = time.strftime("%H:%M:%S")
        self.decision_log.append(f"[{ts}] {message}")

    def mark_strategy_failed(self, strategy_name: str):
        if strategy_name not in self.failed_strategies:
            self.failed_strategies.append(strategy_name)

    def tried_all_strategies(self, available: list[str]) -> bool:
        return all(s in self.failed_strategies for s in available)


class DocAgent:
    """
    Main controller. Runs the agentic loop:
    observe → decide → act → evaluate → improve (repeat if needed)
    """

    MAX_RETRIES = 4
    ACCEPTABLE_CONFIDENCE = 70.0  # Stop retrying above this threshold

    def __init__(self):
        self.image_agent = ImageAgent()
        self.strategy_agent = StrategyAgent()
        self.eval_agent = EvalAgent()
        self.memory = SessionMemory()

    def run(self, image_bytes: bytes) -> dict:
        """
        Main agentic loop. Returns a result dict with text, confidence,
        decision log, privacy warnings, etc.
        """
        self.memory = SessionMemory()  # fresh memory each run
        self.memory.log("DocAgent activated. Starting agentic OCR loop.")

        # ── OBSERVE ──────────────────────────────────────────────────────────
        self.memory.log("ImageAgent: Analyzing image quality and features...")
        image_features = self.image_agent.analyze(image_bytes)
        self.memory.log(
            f"ImageAgent report → blur={image_features['blur_score']:.1f}, "
            f"contrast={image_features['contrast_score']:.1f}, "
            f"noise={image_features['noise_level']}, "
            f"estimated_type={image_features['document_type']}"
        )

        current_strategy = None
        attempt = 0
        final_result = None

        # ── LOOP ─────────────────────────────────────────────────────────────
        while attempt < self.MAX_RETRIES:
            attempt += 1
            self.memory.log(f"--- Attempt {attempt} of {self.MAX_RETRIES} ---")

            # ── DECIDE ───────────────────────────────────────────────────────
            current_strategy = self.strategy_agent.choose_strategy(
                image_features=image_features,
                failed_strategies=self.memory.failed_strategies,
                attempt_num=attempt,
            )
            self.memory.log(
                f"StrategyAgent chose: '{current_strategy['name']}' — "
                f"reason: {current_strategy['reason']}"
            )

            # ── ACT ──────────────────────────────────────────────────────────
            self.memory.log("StrategyAgent: Preprocessing image...")
            processed_img = self.strategy_agent.preprocess(image_bytes, current_strategy)

            self.memory.log("StrategyAgent: Running OCR...")
            raw_text, ocr_data = self.strategy_agent.run_ocr(processed_img, current_strategy)

            # ── EVALUATE ─────────────────────────────────────────────────────
            self.memory.log("EvalAgent: Evaluating OCR output quality...")
            eval_result = self.eval_agent.evaluate(raw_text, ocr_data)
            confidence = eval_result["confidence"]
            self.memory.log(
                f"EvalAgent report → confidence={confidence:.1f}%, "
                f"word_count={eval_result['word_count']}, "
                f"errors_detected={len(eval_result['error_flags'])}"
            )

            # Record this attempt
            record = AttemptRecord(
                attempt_num=attempt,
                strategy_name=current_strategy["name"],
                confidence=confidence,
                word_count=eval_result["word_count"],
                error_flags=eval_result["error_flags"],
                text_preview=raw_text[:120].replace("\n", " "),
            )
            self.memory.record(record, raw_text)

            # ── IMPROVE ──────────────────────────────────────────────────────
            if confidence >= self.ACCEPTABLE_CONFIDENCE:
                self.memory.log(
                    f"EvalAgent: Quality acceptable ({confidence:.1f}% ≥ {self.ACCEPTABLE_CONFIDENCE}%). Stopping loop."
                )
                final_result = {"text": raw_text, "eval": eval_result, "strategy": current_strategy}
                break
            else:
                self.memory.log(
                    f"EvalAgent: Quality LOW ({confidence:.1f}%). Flagging strategy as failed."
                )
                self.memory.mark_strategy_failed(current_strategy["name"])

                # Check if we've exhausted all strategies
                available = self.strategy_agent.list_strategy_names()
                if self.memory.tried_all_strategies(available):
                    self.memory.log("DocAgent: All strategies exhausted. Using best attempt so far.")
                    break

                self.memory.log("DocAgent: Triggering retry with different strategy...")

        # If loop ended without acceptable result, fall back to best attempt
        if final_result is None:
            best = self.memory.best_attempt
            self.memory.log(
                f"DocAgent: Loop ended. Best result was attempt #{best.attempt_num} "
                f"with strategy '{best.strategy_name}' at {best.confidence:.1f}% confidence."
            )
            best_raw = self.memory.best_text
            best_eval = self.eval_agent.evaluate(best_raw, {})
            final_result = {
                "text": best_raw,
                "eval": best_eval,
                "strategy": {"name": best.strategy_name, "reason": "Best of all attempts"},
            }

        # Apply text cleanup on final output
        self.memory.log("EvalAgent: Applying final text cleanup and formatting...")
        cleaned_text = self.eval_agent.clean_text(final_result["text"])

        # Privacy scan
        self.memory.log("EvalAgent: Scanning for sensitive data (privacy check)...")
        privacy_warnings = self.eval_agent.detect_sensitive_data(cleaned_text)
        if privacy_warnings:
            self.memory.log(
                f"⚠️ Privacy: Found {len(privacy_warnings)} sensitive pattern(s): "
                + ", ".join([w["type"] for w in privacy_warnings])
            )
        else:
            self.memory.log("Privacy: No sensitive patterns detected.")

        self.memory.log("DocAgent: Storing session outcome in memory.")
        self.memory.log("DocAgent: Agentic loop complete. Handing off to UserAgent.")

        return {
            "text": cleaned_text,
            "raw_text": final_result["text"],
            "confidence": final_result["eval"]["confidence"],
            "word_count": final_result["eval"]["word_count"],
            "error_flags": final_result["eval"]["error_flags"],
            "strategy_used": final_result["strategy"]["name"],
            "strategy_reason": final_result["strategy"]["reason"],
            "attempts": len(self.memory.attempts),
            "all_attempts": self.memory.attempts,
            "privacy_warnings": privacy_warnings,
            "decision_log": self.memory.decision_log,
            "image_features": image_features,
        }
