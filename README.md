# 🐙 OctoRead — Agentic OCR System

> *"Not just a scanner — an agent with a goal."*

OctoRead is an intelligent, goal-driven document extraction system built on a real agent loop. Unlike traditional OCR pipelines that run the same steps every time, OctoRead **observes, decides, acts, evaluates, and improves** — retrying with smarter strategies until the output quality is acceptable.

---

## ✨ Features

- **Real Agentic Loop** — `observe → decide → act → evaluate → improve` with up to 4 retry attempts
- **Adaptive Preprocessing** — 5 distinct strategies chosen dynamically based on image quality
- **Composite Confidence Scoring** — not just Tesseract's raw number; a weighted multi-factor score
- **Privacy Scanner** — detects emails, phone numbers, CNICs, card numbers, and more
- **Human-in-the-Loop Editing** — edit the extracted text before downloading
- **Transparent Decision Log** — every agent decision is logged and viewable in the UI
- **Export to .txt and .docx** — clean download with metadata
- **Optional LLM Enhancement** — Claude API for text correction (disabled by default, no cost)
- **Cutesy Academic UI** — warm peach/coral/sage palette with Playfair Display typography

---

## 🤖 What Makes It Agentic?

| Feature | Linear Pipeline | OctoRead Agent |
|---|---|---|
| Preprocessing | Fixed steps | Chosen dynamically per image |
| Retries | Never retries | Up to 4 retries with strategy switching |
| Decision making | None | StrategyAgent picks approach; DocAgent controls loop |
| Memory | None | Session memory tracks failed strategies |
| Goal-driven | No | Stops only when confidence ≥ 70% or all strategies exhausted |
| Transparency | Hidden | Full decision log exposed in UI |

---

## 🏗️ Architecture

```
app.py
├── agents/
│   ├── doc_agent.py       ← Controller + Memory (runs the loop)
│   ├── image_agent.py     ← Perception (analyzes image quality)
│   ├── strategy_agent.py  ← Decision Maker (picks + runs preprocessing + OCR)
│   ├── eval_agent.py      ← Judge (scores output, detects privacy issues)
│   └── user_agent.py      ← UI Layer (Streamlit interface)
├── requirements.txt
├── packages.txt
└── docs/
    ├── README.md
    ├── PROJECT.md
    └── DEPLOYMENT.md
```

---

## 🚀 Quick Start (Local)

```bash
# 1. Install Tesseract (macOS)
brew install tesseract

# 1. Install Tesseract (Ubuntu/Debian)
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# 2. Clone and install Python deps
git clone <repo-url>
cd octoread
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

---

## 🔐 Privacy & Ethics

OctoRead scans extracted text for:
- Email addresses
- Pakistani phone numbers (+92 / 03xx format)
- CNIC numbers (xxxxx-xxxxxxx-x)
- Credit/debit card patterns
- Passport numbers
- Dates of birth
- IP addresses and URLs

If any are found, a **red warning banner** appears before the user downloads the output.

---

## 🌐 Deploy to Streamlit Cloud

See [DEPLOYMENT.md](DEPLOYMENT.md) for step-by-step instructions.

---

## ⚙️ LLM Enhancement (Optional)

Set `use_llm = True` in the UI toggle and provide your Anthropic API key. The system will call `claude-sonnet-4-20250514` to clean up OCR artefacts in the extracted text. The system works fully without this.
