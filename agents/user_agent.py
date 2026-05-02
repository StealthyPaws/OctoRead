"""
agents/user_agent.py — UserAgent (Interaction + UI Layer)

Runs the Streamlit interface. Shows results, lets users edit,
displays agent decisions with transparency, and handles export.
"""

import io
import time
import streamlit as st


class UserAgent:
    """Owns the entire Streamlit UI. Kicks off DocAgent when an image is uploaded."""

    # ── Colour palette: warm academic meets playful lab ──────────────────────
    THEME_CSS = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap');

    :root {
        --cream:       #fdf6ec;
        --warm-white:  #fff9f2;
        --peach:       #f4a06e;
        --coral:       #e8623c;
        --goldenrod:   #d4922a;
        --sage:        #5a7a5e;
        --muted-sage:  #8aac8e;
        --ink:         #2b2118;
        --ink-light:   #5c4a38;
        --card-bg:     rgba(255,249,242,0.92);
        --border:      rgba(212,146,42,0.25);
        --success:     #5a7a5e;
        --warn:        #c9552a;
        --radius:      14px;
    }

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        color: var(--ink);
        background-color: var(--cream);
    }

    /* Noise texture overlay */
    body::before {
        content: '';
        position: fixed;
        inset: 0;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
        pointer-events: none;
        z-index: 9999;
    }

    /* Streamlit main wrapper */
    .main .block-container {
        max-width: 1400px;
        padding: 1.5rem 2rem 3rem;
    }

    /* ── Header ── */
    .octo-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 2rem 0 1.2rem;
        border-bottom: 2px solid var(--border);
        margin-bottom: 2rem;
    }
    .octo-logo {
        font-size: 3rem;
        line-height: 1;
    }
    .octo-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.4rem;
        font-weight: 700;
        color: var(--coral);
        line-height: 1.1;
        margin: 0;
    }
    .octo-subtitle {
        font-size: 0.88rem;
        color: var(--ink-light);
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-top: 0.2rem;
    }

    /* ── Panel cards ── */
    .panel-card {
        background: var(--card-bg);
        border: 1.5px solid var(--border);
        border-radius: var(--radius);
        padding: 1.4rem 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 2px 12px rgba(43,33,24,0.06);
    }
    .panel-label {
        font-family: 'Playfair Display', serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: var(--goldenrod);
        letter-spacing: 0.02em;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* ── Confidence meter ── */
    .conf-meter-wrap {
        margin: 0.6rem 0 1rem;
    }
    .conf-bar-bg {
        background: rgba(212,146,42,0.15);
        border-radius: 999px;
        height: 12px;
        overflow: hidden;
    }
    .conf-bar-fill {
        height: 100%;
        border-radius: 999px;
        transition: width 0.6s ease;
    }
    .conf-label {
        font-family: 'DM Mono', monospace;
        font-size: 1.6rem;
        font-weight: 500;
        margin-bottom: 0.3rem;
    }

    /* ── Quality badge ── */
    .quality-badge {
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .badge-excellent { background: #d4edda; color: #2d6a3f; }
    .badge-good      { background: #d4edd4; color: #3a6b3a; }
    .badge-fair      { background: #fef3cd; color: #856404; }
    .badge-poor      { background: #fde0d8; color: #8b2500; }
    .badge-empty     { background: #e9ecef; color: #495057; }

    /* ── Step log ── */
    .step-log {
        background: #2b2118;
        border-radius: var(--radius);
        padding: 1rem 1.2rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.78rem;
        color: #e8d5b5;
        max-height: 220px;
        overflow-y: auto;
        line-height: 1.7;
    }
    .step-log .log-line { margin: 0; }
    .step-log .log-warn { color: #f4a06e; }
    .step-log .log-ok   { color: #8aac8e; }
    .step-log .log-sep  { color: #5c4a38; }

    /* ── Privacy warning ── */
    .privacy-banner {
        background: #fff0eb;
        border: 2px solid var(--coral);
        border-radius: var(--radius);
        padding: 1rem 1.4rem;
        margin: 1rem 0;
    }
    .privacy-banner h4 {
        color: var(--coral);
        margin: 0 0 0.5rem;
        font-family: 'Playfair Display', serif;
    }
    .privacy-item {
        font-size: 0.85rem;
        display: flex;
        justify-content: space-between;
        padding: 0.25rem 0;
        border-bottom: 1px dashed rgba(212,100,60,0.2);
    }

    /* ── Stat pills ── */
    .stat-row {
        display: flex;
        gap: 0.8rem;
        flex-wrap: wrap;
        margin: 0.6rem 0;
    }
    .stat-pill {
        background: rgba(212,146,42,0.12);
        border: 1px solid var(--border);
        border-radius: 999px;
        padding: 0.3rem 0.9rem;
        font-size: 0.82rem;
        color: var(--ink-light);
        font-family: 'DM Mono', monospace;
    }
    .stat-pill span { color: var(--goldenrod); font-weight: 500; }

    /* ── Upload zone ── */
    [data-testid="stFileUploader"] {
        border: 2px dashed var(--peach) !important;
        border-radius: var(--radius) !important;
        background: rgba(244,160,110,0.05) !important;
        transition: border-color 0.2s;
    }
    [data-testid="stFileUploader"]:hover {
        border-color: var(--coral) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: var(--coral) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 500 !important;
        padding: 0.5rem 1.4rem !important;
        transition: background 0.2s !important;
    }
    .stButton > button:hover {
        background: var(--goldenrod) !important;
    }

    /* ── Text areas ── */
    .stTextArea textarea {
        font-family: 'DM Mono', monospace !important;
        font-size: 0.88rem !important;
        background: var(--warm-white) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 10px !important;
        color: var(--ink) !important;
    }

    /* ── Attempt table ── */
    .attempt-row {
        display: grid;
        grid-template-columns: 2rem 1fr 1fr 1fr;
        gap: 0.4rem;
        padding: 0.35rem 0;
        border-bottom: 1px dashed var(--border);
        font-size: 0.8rem;
        align-items: center;
    }
    .attempt-header {
        font-weight: 600;
        color: var(--goldenrod);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--peach); border-radius: 999px; }

    /* Hide Streamlit defaults */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .stDeployButton { display: none; }
    </style>
    """

    def run(self):
        """Main UI entrypoint called by app.py."""
        st.markdown(self.THEME_CSS, unsafe_allow_html=True)
        self._render_header()

        # Layout: left = upload/controls, right = output
        left, right = st.columns([1, 1.35], gap="large")

        with left:
            self._render_upload_panel()

        with right:
            self._render_output_panel()

    # ── Header ───────────────────────────────────────────────────────────────

    def _render_header(self):
        st.markdown("""
        <div class="octo-header">
            <div class="octo-logo">🐙</div>
            <div>
                <div class="octo-title">OctoRead</div>
                <div class="octo-subtitle">Agentic OCR · Intelligent Document Extraction</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Upload panel (left) ───────────────────────────────────────────────────

    def _render_upload_panel(self):
        st.markdown('<div class="panel-label">📎 Upload Image</div>', unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Drop an image here or click to browse",
            type=["png", "jpg", "jpeg", "bmp", "tiff", "webp"],
            label_visibility="collapsed",
        )

        if uploaded:
            st.image(uploaded, caption="Uploaded Image", use_container_width=True)
            image_bytes = uploaded.read()

            st.markdown('<div class="panel-label" style="margin-top:1.2rem">⚙️ Options</div>',
                        unsafe_allow_html=True)

            use_llm = st.toggle("✨ Use LLM Enhancement (optional)", value=False,
                                help="Applies lightweight AI text correction. Requires Anthropic API key.")

            if use_llm:
                api_key = st.text_input("Anthropic API Key", type="password",
                                        placeholder="sk-ant-...")
                if api_key:
                    st.session_state["anthropic_api_key"] = api_key

            run_btn = st.button("🚀  Extract Text", use_container_width=True)

            if run_btn:
                self._run_agents(image_bytes, use_llm=use_llm)

        else:
            st.markdown("""
            <div style="
                text-align:center;
                padding: 3rem 1rem;
                color: var(--ink-light, #5c4a38);
                font-size: 0.9rem;
            ">
                <div style="font-size:3rem;margin-bottom:0.8rem">🖼️</div>
                <div>Upload a PNG, JPG, or TIFF image<br>of typed or handwritten text</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Output panel (right) ─────────────────────────────────────────────────

    def _render_output_panel(self):
        if "ocr_result" not in st.session_state:
            st.markdown("""
            <div style="
                text-align:center;
                padding: 4rem 2rem;
                color: var(--ink-light, #5c4a38);
            ">
                <div style="font-size:3.5rem;margin-bottom:1rem">📄</div>
                <div style="font-family:'Playfair Display',serif;font-size:1.3rem;color:#d4922a">
                    Awaiting Image
                </div>
                <div style="font-size:0.85rem;margin-top:0.5rem">
                    Upload an image on the left to begin the agentic extraction loop.
                </div>
            </div>
            """, unsafe_allow_html=True)
            return

        result = st.session_state["ocr_result"]
        self._render_confidence_card(result)
        self._render_privacy_warnings(result.get("privacy_warnings", []))
        self._render_text_editor(result)
        self._render_stats_row(result)
        self._render_decision_log(result.get("decision_log", []))
        self._render_attempt_history(result.get("all_attempts", []))
        self._render_export_section(result)

    # ── Agent runner ─────────────────────────────────────────────────────────

    def _run_agents(self, image_bytes: bytes, use_llm: bool = False):
        """Kick off DocAgent with a progress indicator."""
        from agents.doc_agent import DocAgent

        progress_placeholder = st.empty()

        steps = [
            ("🧠 DocAgent booting up...", 0.08),
            ("🔍 ImageAgent analyzing image quality...", 0.22),
            ("⚡ StrategyAgent selecting preprocessing...", 0.42),
            ("📝 Running OCR...", 0.65),
            ("⚖️ EvalAgent evaluating output...", 0.82),
            ("🔒 Privacy scan in progress...", 0.93),
            ("✅ Finalising output...", 1.0),
        ]

        with progress_placeholder.container():
            pbar = st.progress(0, text="Starting agentic loop...")
            for msg, pct in steps:
                pbar.progress(pct, text=msg)
                time.sleep(0.25)

        try:
            agent = DocAgent()
            result = agent.run(image_bytes)

            # Optional LLM enhancement
            if use_llm and st.session_state.get("anthropic_api_key"):
                result = self._apply_llm_correction(result)

            st.session_state["ocr_result"] = result
            st.session_state["edited_text"] = result["text"]
            progress_placeholder.empty()
            st.rerun()

        except Exception as e:
            progress_placeholder.empty()
            st.error(f"Agent encountered an error: {e}")
            import traceback
            st.code(traceback.format_exc(), language="text")

    def _apply_llm_correction(self, result: dict) -> dict:
        """Optional: use Claude API to clean up extracted text."""
        try:
            import anthropic
            api_key = st.session_state.get("anthropic_api_key", "")
            if not api_key:
                return result

            client = anthropic.Anthropic(api_key=api_key)
            text = result["text"][:3000]  # cap tokens

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{
                    "role": "user",
                    "content": (
                        "Clean up the following OCR-extracted text. "
                        "Fix obvious spelling errors from OCR artifacts, "
                        "normalise spacing and punctuation, but preserve the original meaning exactly. "
                        "Return only the corrected text with no commentary.\n\n"
                        f"TEXT:\n{text}"
                    )
                }]
            )
            corrected = message.content[0].text
            result["text"] = corrected
            result["decision_log"].append(
                f"[LLM] Claude applied text correction. Original length={len(text)}, "
                f"corrected length={len(corrected)}."
            )
        except Exception as e:
            result["decision_log"].append(f"[LLM] Enhancement skipped: {e}")

        return result

    # ── Confidence card ───────────────────────────────────────────────────────

    def _render_confidence_card(self, result: dict):
        conf = result.get("confidence", 0)
        label = result.get("error_flags", [])
        quality = "EXCELLENT" if conf >= 80 else "GOOD" if conf >= 65 else "FAIR" if conf >= 45 else "POOR"

        # bar colour
        bar_color = (
            "#5a7a5e" if quality == "EXCELLENT" else
            "#8aac8e" if quality == "GOOD" else
            "#d4922a" if quality == "FAIR" else
            "#e8623c"
        )

        badge_class = f"badge-{quality.lower()}"

        st.markdown(f"""
        <div class="panel-card">
            <div class="panel-label">📊 OCR Confidence</div>
            <div class="conf-label" style="color:{bar_color}">{conf:.1f}%</div>
            <span class="quality-badge {badge_class}">{quality}</span>
            <div class="conf-meter-wrap">
                <div class="conf-bar-bg">
                    <div class="conf-bar-fill" style="width:{conf}%;background:{bar_color}"></div>
                </div>
            </div>
            <div style="font-size:0.82rem;color:var(--ink-light)">
                Strategy: <strong>{result.get('strategy_used','—')}</strong> ·
                Attempts: <strong>{result.get('attempts',1)}</strong> ·
                Words: <strong>{result.get('word_count',0)}</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Privacy warnings ──────────────────────────────────────────────────────

    def _render_privacy_warnings(self, warnings: list):
        if not warnings:
            return

        items_html = ""
        for w in warnings:
            items_html += f"""
            <div class="privacy-item">
                <span>⚠️ {w['type']}</span>
                <span style="font-family:'DM Mono',monospace;color:#c9552a">{w['preview']} ×{w['count']}</span>
            </div>
            """

        st.markdown(f"""
        <div class="privacy-banner">
            <h4>🔐 Sensitive Data Detected</h4>
            <p style="font-size:0.83rem;color:#5c4a38;margin:0 0 0.6rem">
                The extracted text may contain personal or private information. 
                Please review before sharing or downloading.
            </p>
            {items_html}
        </div>
        """, unsafe_allow_html=True)

    # ── Text editor ───────────────────────────────────────────────────────────

    def _render_text_editor(self, result: dict):
        st.markdown('<div class="panel-label">✏️ Extracted Text (editable)</div>',
                    unsafe_allow_html=True)

        initial = st.session_state.get("edited_text", result["text"])
        edited = st.text_area(
            "Edit the extracted text below:",
            value=initial,
            height=280,
            label_visibility="collapsed",
            key="text_editor_area",
        )
        st.session_state["edited_text"] = edited

    # ── Stats row ─────────────────────────────────────────────────────────────

    def _render_stats_row(self, result: dict):
        feats = result.get("image_features", {})
        blur = feats.get("blur_score", "—")
        noise = feats.get("noise_level", "—")
        doc_type = feats.get("document_type", "—")

        blur_display = f"{blur:.0f}" if isinstance(blur, float) else str(blur)

        st.markdown(f"""
        <div class="stat-row">
            <div class="stat-pill">Blur Score <span>{blur_display}</span></div>
            <div class="stat-pill">Noise <span>{noise}</span></div>
            <div class="stat-pill">Doc Type <span>{doc_type}</span></div>
            <div class="stat-pill">Tess Conf <span>{result.get('confidence',0):.0f}%</span></div>
            <div class="stat-pill">Words <span>{result.get('word_count',0)}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # ── Decision log ──────────────────────────────────────────────────────────

    def _render_decision_log(self, log: list[str]):
        with st.expander("🤖 Agent Decision Log", expanded=False):
            if not log:
                st.caption("No log entries.")
                return

            log_html = ""
            for line in log:
                if "⚠️" in line or "Privacy" in line or "sensitive" in line.lower():
                    cls = "log-warn"
                elif "acceptable" in line.lower() or "complete" in line.lower() or "✅" in line:
                    cls = "log-ok"
                elif "---" in line:
                    cls = "log-sep"
                else:
                    cls = ""
                escaped = line.replace("<", "&lt;").replace(">", "&gt;")
                log_html += f'<p class="log-line {cls}">{escaped}</p>'

            st.markdown(f'<div class="step-log">{log_html}</div>', unsafe_allow_html=True)

    # ── Attempt history ───────────────────────────────────────────────────────

    def _render_attempt_history(self, attempts: list):
        if len(attempts) <= 1:
            return

        with st.expander(f"🔁 Retry History ({len(attempts)} attempts)", expanded=False):
            header = """
            <div class="attempt-row attempt-header">
                <div>#</div><div>Strategy</div><div>Confidence</div><div>Words</div>
            </div>
            """
            rows = ""
            for a in attempts:
                conf_color = "#5a7a5e" if a.confidence >= 65 else "#d4922a" if a.confidence >= 45 else "#e8623c"
                rows += f"""
                <div class="attempt-row">
                    <div>{a.attempt_num}</div>
                    <div>{a.strategy_name}</div>
                    <div style="color:{conf_color};font-family:'DM Mono',monospace">{a.confidence:.1f}%</div>
                    <div>{a.word_count}</div>
                </div>
                """
            st.markdown(
                f'<div style="font-size:0.82rem">{header}{rows}</div>',
                unsafe_allow_html=True
            )

    # ── Export section ────────────────────────────────────────────────────────

    def _render_export_section(self, result: dict):
        st.markdown('<div class="panel-label" style="margin-top:0.8rem">⬇️ Export</div>',
                    unsafe_allow_html=True)

        text_to_export = st.session_state.get("edited_text", result["text"])
        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="📄 Download .txt",
                data=text_to_export.encode("utf-8"),
                file_name="octoread_output.txt",
                mime="text/plain",
                use_container_width=True,
            )

        with col2:
            try:
                docx_bytes = self._make_docx(text_to_export, result)
                st.download_button(
                    label="📝 Download .docx",
                    data=docx_bytes,
                    file_name="octoread_output.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
            except Exception:
                st.caption("Install python-docx for Word export.")

    def _make_docx(self, text: str, result: dict) -> bytes:
        """Build a simple .docx file from the extracted text."""
        from docx import Document
        from docx.shared import Pt, RGBColor

        doc = Document()
        doc.core_properties.title = "OctoRead OCR Output"

        # Title
        title = doc.add_heading("OctoRead — Extracted Text", level=1)
        title.runs[0].font.color.rgb = RGBColor(0xE8, 0x62, 0x3C)

        # Metadata paragraph
        meta = doc.add_paragraph()
        meta.add_run(
            f"Strategy: {result.get('strategy_used','—')} | "
            f"Confidence: {result.get('confidence',0):.1f}% | "
            f"Words: {result.get('word_count',0)}"
        ).font.size = Pt(9)
        meta.runs[0].font.color.rgb = RGBColor(0x5C, 0x4A, 0x38)

        doc.add_paragraph()  # spacer

        # Body text
        for line in text.split("\n"):
            doc.add_paragraph(line)

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
