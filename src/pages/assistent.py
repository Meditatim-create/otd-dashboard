"""Chat assistent pagina."""

import pandas as pd
import streamlit as st

from src.components.chat import (
    init_chat,
    render_chat_geschiedenis,
    render_voorbeeldvragen,
    voeg_bericht_toe,
)
from src.utils.llm_service import is_beschikbaar, bereid_context_voor, stel_vraag


def render_assistent(df: pd.DataFrame):
    """Render de chat assistent pagina."""
    st.header("🤖 OTD Assistent")

    if not is_beschikbaar():
        st.warning(
            "De chat assistent is nog niet geconfigureerd. "
            "Voeg LLM credentials toe aan `.streamlit/secrets.toml`. "
            "Zie de README voor instructies."
        )
        st.code(
            '[llm]\nprovider = "openrouter"\napi_key = "sk-or-..."\nmodel = "anthropic/claude-sonnet-4"',
            language="toml",
        )
        return

    init_chat()

    # Data-context voorbereiden
    context = bereid_context_voor(df)

    # Info over de dataset
    with st.expander("📊 Data-context (wat de assistent weet)"):
        st.text(context)

    # Chatgeschiedenis tonen
    render_chat_geschiedenis()

    # Voorbeeldvragen (alleen als er nog geen berichten zijn)
    geselecteerde_vraag = render_voorbeeldvragen()

    # Chat input
    vraag = st.chat_input("Stel een vraag over de OTD-data...")

    # Gebruik voorbeeldvraag als er geen directe input is
    actieve_vraag = vraag or geselecteerde_vraag

    if actieve_vraag:
        # Gebruikersbericht tonen en opslaan
        voeg_bericht_toe("user", actieve_vraag)
        with st.chat_message("user"):
            st.markdown(actieve_vraag)

        # LLM antwoord ophalen
        with st.chat_message("assistant"):
            with st.spinner("Denken..."):
                antwoord = stel_vraag(
                    actieve_vraag,
                    context,
                    st.session_state.chat_berichten[:-1],  # Exclusief huidige vraag
                )
                st.markdown(antwoord)

        voeg_bericht_toe("assistant", antwoord)

    # Wis-knop
    if st.session_state.chat_berichten:
        if st.button("🗑️ Wis gesprek"):
            st.session_state.chat_berichten = []
            st.rerun()
