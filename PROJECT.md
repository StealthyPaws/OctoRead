# 📐 OctoRead — Project Architecture

## System Goal

> "Convert an input image into the most accurate and well-formatted document possible."

The system is not a pipeline. It is a **goal-directed agent** that pursues this objective through a loop, using feedback to improve its approach at each step.

---

## The Agent Loop

```
┌──────────────────────────────────────────────────────────┐
│                       DocAgent                           │
│                                                          │
│  ┌─────────┐    ┌──────────┐    ┌──────────────────┐    │
│  │ OBSERVE │───▶│  DECIDE  │───▶│       ACT        │    │
│  │         │    │          │    │                  │    │
│  │ImageAgent│   │Strategy  │    │ Preprocess +     │    │
│  │analyzes  │   │Agent     │    │ Run Tesseract    │    │
│  │features  │   │picks     │    │                  │    │
│  └─────────┘    │strategy  │    └────────┬─────────┘    │
│                 └──────────┘             │               │
│                       ▲                 ▼               │
│                       │          ┌──────────────┐       │
│                       │          │   EVALUATE   │       │
│                       │          │              │       │
│                 ┌─────┴────┐     │  EvalAgent   │       │
│                 │ IMPROVE  │◀────│  scores      │       │
│                 │          │     │  output      │       │
│                 │ DocAgent │     └──────────────┘       │
│                 │ retries  │                             │
│                 └──────────┘                             │
└──────────────────────────────────────────────────────────┘
                          │ (when quality ≥ 70% OR
                          │  all strategies exhausted)
                          ▼
                    ┌───────────┐
                    │ UserAgent │
                    │ shows UI  │
                    └───────────┘
```

---

## Agent Roles

### 1. DocAgent — Controller + Memory
**File:** `agents/doc_agent.py`

The orchestrator. Runs the `while attempt < MAX_RETRIES` loop. After each attempt it checks EvalAgent's score: if confidence ≥ 70% it stops; otherwise it marks the current strategy as failed and loops again. It also maintains `SessionMemory` which stores:
- All attempt records (strategy name, confidence, word count)
- List of failed strategies (so StrategyAgent won't repeat them)
- The best text seen so far (fallback if all retries fail)
- The decision log (list of timestamped strings)

### 2. ImageAgent — Perception
**File:** `agents/image_agent.py`

Runs once at the start. Uses OpenCV (with PIL fallback) to extract:
- **Blur score** via Laplacian variance
- **Contrast score** via pixel standard deviation
- **Noise level** (low/medium/high) via Gaussian difference
- **Brightness** (dark/normal/bright)
- **Skew angle** via Hough line detection
- **Document type** heuristic (typed/handwritten/receipt)

These features feed into StrategyAgent's decision-making.

### 3. StrategyAgent — Decision Maker
**File:** `agents/strategy_agent.py`

Has 5 registered strategies in priority order:
1. `standard` — grayscale + Otsu threshold
2. `adaptive_threshold` — adaptive thresholding for uneven lighting
3. `denoise_enhance` — denoise + histogram equalisation
4. `upscale_sharpen` — 2× upscale + sharpening kernel
5. `aggressive` — full pipeline with CLAHE and morphology

On attempt 1, it uses `_heuristic_pick()` to match image features to the best strategy. On retries, it escalates by priority. It never repeats a strategy marked as failed by DocAgent.

### 4. EvalAgent — Judge
**File:** `agents/eval_agent.py`

Computes a **composite confidence score** (0–100) from four sub-scores:
- Tesseract's internal word confidence (weight 0.45)
- Common English word ratio (weight 0.25)
- Garbage character detection (weight 0.20)
- Output length sanity check (weight 0.10)

Also handles:
- Text cleanup (strip artefacts, normalise whitespace)
- Sensitive data detection via regex patterns

### 5. UserAgent — UI
**File:** `agents/user_agent.py`

Runs Streamlit. Provides:
- Image upload panel (left column)
- Live progress bar during agent execution
- Confidence meter with animated fill bar
- Privacy warning banner (red, prominent)
- Editable text area (human-in-the-loop)
- Stat pills for image features
- Expandable decision log (timestamped agent messages)
- Retry history table
- .txt and .docx download buttons

---

## Memory Architecture

Memory is **session-scoped** (cleared each new image run). It is stored as a `SessionMemory` dataclass instance inside `DocAgent`, and summary results are stored in `st.session_state` for the UI to read.

There is no persistent database. This is intentional: OCR sessions are ephemeral and privacy-sensitive.

---

## Strategy Selection Logic

```
attempt 1:
  if document_type == "handwritten"  → adaptive_threshold
  elif noise in (medium, high)        → denoise_enhance
  elif blur_score < 50                → upscale_sharpen
  elif contrast_score < 35            → denoise_enhance
  else                                → standard

attempt 2+:
  pick lowest-priority strategy not yet in failed_strategies
```

---

## Confidence Thresholds

| Label     | Score    |
|-----------|----------|
| EXCELLENT | ≥ 80%    |
| GOOD      | 65–80%   |
| FAIR      | 45–65%   |
| POOR      | < 45%    |

The agent stops retrying at ≥ 70% (GOOD/EXCELLENT). If it hits the retry limit, it returns the best-scoring attempt.
