"""
app.py — Main entry point for the Agentic OCR System
Wires up all agents and runs the Streamlit UI via UserAgent
"""

import streamlit as st

# Page config must be first Streamlit call
st.set_page_config(
    page_title="OctoRead · Agentic OCR",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from agents.user_agent import UserAgent

# Boot the UserAgent which orchestrates the UI and kicks off DocAgent
if __name__ == "__main__" or True:
    ui = UserAgent()
    ui.run()
