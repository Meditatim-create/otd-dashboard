"""Chat UI componenten."""

from __future__ import annotations

import streamlit as st


VOORBEELDVRAGEN = [
    "Wat is de huidige OTD-score?",
    "Welke KPI-stap faalt het meest?",
    "Welke klanten hebben de meeste te late leveringen?",
    "Wat zijn de belangrijkste root causes?",
    "Hoe kan de OTD verbeterd worden?",
]


def init_chat():
    """Initialiseer chat session state."""
    if "chat_berichten" not in st.session_state:
        st.session_state.chat_berichten = []


def render_chat_geschiedenis():
    """Toon chatberichten."""
    for bericht in st.session_state.chat_berichten:
        with st.chat_message(bericht["role"]):
            st.markdown(bericht["content"])


def voeg_bericht_toe(role: str, content: str):
    """Voeg een bericht toe aan de chatgeschiedenis."""
    st.session_state.chat_berichten.append({"role": role, "content": content})


def render_voorbeeldvragen() -> str | None:
    """Toon voorbeeldvragen als knoppen. Retourneert geselecteerde vraag of None."""
    if st.session_state.chat_berichten:
        return None

    st.markdown("**Voorbeeldvragen:**")
    cols = st.columns(len(VOORBEELDVRAGEN))
    for i, vraag in enumerate(VOORBEELDVRAGEN):
        if cols[i % len(cols)].button(vraag, key=f"voorbeeld_{i}", use_container_width=True):
            return vraag
    return None
