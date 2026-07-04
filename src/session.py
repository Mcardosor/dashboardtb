"""
session.py
──────────
Helpers para ler o DataFrame filtrado do session_state.
Todas as pages chamam get_df() para obter os dados carregados pelo app.py.
"""

import streamlit as st
import pandas as pd


def get_df() -> pd.DataFrame:
    """Retorna o DataFrame filtrado salvo pelo app.py no session_state."""
    df = st.session_state.get("df")
    if df is None or df.empty:
        st.warning("⚠️ Nenhum dado carregado. Volte para a página principal **app**.")
        st.stop()
    return df


def get_context() -> dict:
    """Retorna o contexto completo salvo pelo app.py."""
    ctx = st.session_state.get("ctx")
    if ctx is None:
        st.warning("⚠️ Contexto não encontrado. Volte para a página principal **app**.")
        st.stop()
    return ctx
