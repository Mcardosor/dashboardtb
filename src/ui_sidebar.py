"""
ui_sidebar.py
─────────────
Sidebar de filtros do dashboard TB SINAN.

Uso:
    from src.ui_sidebar import render_sidebar
    df, df_completo, anos_sel, ano_sel, total_filt, total_base = render_sidebar()
"""

import streamlit as st
import pandas as pd

from src.constantes import UF_SIGLAS, REGIOES, anos_disponiveis
from src.dados import carregar_dados, enriquecer_df

_NI_NORM = {"Nao informado": "Não informado"}


def render_sidebar() -> tuple[pd.DataFrame, pd.DataFrame, list, int, int, int]:
    """
    Renderiza a sidebar completa com filtros e retorna:
        df           — DataFrame filtrado e enriquecido
        df_completo  — DataFrame completo sem filtros (para KPIs de base)
        anos_sel     — lista de anos selecionados
        ano_sel      — ano de referência (mais recente selecionado)
        total_filt   — nº de registros após filtros
        total_base   — nº de registros antes dos filtros
    """
    with st.sidebar:
        st.markdown("## 🩺 TB · SINAN")

        anos = anos_disponiveis()
        MAX_ANOS = 3
        anos_sel = st.multiselect(
            "📅 Ano de notificação",
            options=anos,
            default=[anos[0]],
            max_selections=MAX_ANOS,
            help=f"Selecione até {MAX_ANOS} anos. Mais anos = mais tempo de carga.",
        )
        if not anos_sel:
            anos_sel = [anos[0]]
        if len(anos_sel) > 2:
            st.caption(f"⚡ {len(anos_sel)} anos selecionados — carregamento pode levar alguns segundos.")
        anos_key = tuple(sorted(anos_sel))
        df_completo = carregar_dados(anos_key)
        if df_completo.empty:
            anos_str = ", ".join(str(a) for a in anos_sel)
            st.error(
                f"Dados de {anos_str} não encontrados.\n\n"
                f"Execute:\n```\npython scripts/preparar_dados.py\n```"
            )
            st.stop()

        ano_sel = max(anos_sel)

        # ── Localização ───────────────────────────────────────────────────────
        with st.expander("📍 Localização", expanded=True):
            ufs_disp = sorted(df_completo["estado_notificacao"].dropna().unique())

            _regiao_sel = st.radio(
                "Região",
                options=["Todas"] + list(REGIOES.keys()),
                index=0,
                key="regiao_pills", horizontal=True,
                label_visibility="collapsed",
            )
            if not _regiao_sel:
                _regiao_sel = "Todas"

            if _regiao_sel == "Todas":
                _default_ufs = ufs_disp
            else:
                _siglas_regiao = set(REGIOES[_regiao_sel])
                _default_ufs = sorted([n for n in ufs_disp if UF_SIGLAS.get(n) in _siglas_regiao])
                if not _default_ufs:
                    _default_ufs = ufs_disp

            uf_sel = st.multiselect(
                "Estados",
                options=ufs_disp,
                default=_default_ufs,
                label_visibility="collapsed",
                help="Use os botões acima para seleção rápida, ou ajuste manualmente.",
                key=f"uf_sel_{_regiao_sel}",
            )
            if not uf_sel:
                uf_sel = ufs_disp

        # ── Perfil do Paciente ────────────────────────────────────────────────
        with st.expander("👤 Perfil do Paciente", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.caption("Sexo")
                sexo_m = st.checkbox("Masculino", value=True, key="sm")
                sexo_f = st.checkbox("Feminino",  value=True, key="sf")
            with col2:
                st.caption("Forma Clínica")
                forma_pulm  = st.checkbox("Pulmonar",      value=True, key="fp")
                forma_extra = st.checkbox("Extrapulmonar", value=True, key="fe")
                forma_ambos = st.checkbox("Pulm.+Extra",   value=True, key="fa")
            if "raca_cor" in df_completo.columns:
                _racas_vals = df_completo["raca_cor"].astype(str).replace("nan", "Não informado").replace(_NI_NORM)
                racas    = sorted(_racas_vals.unique())
                raca_sel = st.multiselect("Raça/Cor", racas, default=racas)
            else:
                racas = []; raca_sel = []

        # ── Perfil Clínico ────────────────────────────────────────────────────
        with st.expander("🏥 Perfil Clínico", expanded=False):
            if "tipo_entrada" in df_completo.columns:
                _ent_vals = df_completo["tipo_entrada"].astype(str).replace("nan", "Não informado").replace(_NI_NORM)
                entradas    = sorted(_ent_vals.unique())
                entrada_sel = st.multiselect("Tipo de Entrada", entradas, default=entradas)
            else:
                entradas = []; entrada_sel = []
            if "status_hiv" in df_completo.columns:
                st.caption("HIV")
                hiv_pos_cb = st.checkbox("Positivo",      value=True, key="hpos")
                hiv_neg_cb = st.checkbox("Negativo",      value=True, key="hneg")
                hiv_and_cb = st.checkbox("Em andamento",  value=True, key="hand")
                hiv_nr_cb  = st.checkbox("Não realizado", value=True, key="hnr")
                hiv_ign_cb = st.checkbox("Ignorado",      value=True, key="hign")
                tem_hiv = True
            else:
                tem_hiv = False

        # ── Populações Vulneráveis ────────────────────────────────────────────
        with st.expander("⚠️ Populações Vulneráveis", expanded=False):
            st.caption("Incluir apenas pacientes que sejam:")
            filt_liber = st.checkbox("Privado de liberdade",  value=False, key="liber")
            filt_rua   = st.checkbox("Em situação de rua",    value=False, key="rua")
            filt_saude = st.checkbox("Profissional de saúde", value=False, key="saude")
            filt_imig  = st.checkbox("Imigrante",             value=False, key="imig")
            st.caption("_(deixe desmarcado para não filtrar)_")

        # ── Comorbidades ──────────────────────────────────────────────────────
        with st.expander("💊 Comorbidades", expanded=False):
            st.caption("Incluir apenas pacientes com:")
            filt_aids   = st.checkbox("AIDS/HIV",          value=False, key="aids")
            filt_alcool = st.checkbox("Alcoolismo",         value=False, key="alc")
            filt_diab   = st.checkbox("Diabetes",           value=False, key="diab")
            filt_drogas = st.checkbox("Drogas ilícitas",    value=False, key="drog")
            filt_tabaco = st.checkbox("Tabagismo",          value=False, key="tab")
            st.caption("_(deixe desmarcado para não filtrar)_")

        if st.button("🔄 Limpar filtros", width='stretch'):
            st.rerun()

    # ── Aplicar filtros ───────────────────────────────────────────────────────
    df = df_completo.copy()

    if uf_sel != sorted(df_completo["estado_notificacao"].dropna().unique()):
        df = df[df["estado_notificacao"].isin(uf_sel)]

    sexo_vals = ([s for s, v in [("Masculino", sexo_m), ("Feminino", sexo_f)] if v]
                 or ["Masculino", "Feminino"])
    if "sexo" in df.columns:
        df = df[df["sexo"].isin(sexo_vals)]

    forma_vals = ([f for f, v in [
        ("Pulmonar", forma_pulm), ("Extrapulmonar", forma_extra),
        ("Pulmonar + Extrapulmonar", forma_ambos)] if v]
        or ["Pulmonar", "Extrapulmonar", "Pulmonar + Extrapulmonar"])
    if "forma" in df.columns:
        df = df[df["forma"].isin(forma_vals) | df["forma"].isna()]

    if racas and raca_sel and len(raca_sel) < len(racas):
        df = df[df["raca_cor"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).isin(raca_sel)]

    if entradas and entrada_sel and len(entrada_sel) < len(entradas) and "tipo_entrada" in df.columns:
        df = df[df["tipo_entrada"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).isin(entrada_sel)]

    if tem_hiv:
        hiv_vals = ([h for h, v in [
            ("Positivo", hiv_pos_cb), ("Negativo", hiv_neg_cb),
            ("Em andamento", hiv_and_cb), ("Não realizado", hiv_nr_cb),
            ("Ignorado", hiv_ign_cb)] if v]
            or list(df["status_hiv"].dropna().unique()))
        df = df[df["status_hiv"].isin(hiv_vals)]

    for flag, col in [(filt_liber, "populacao_privada_liberdade"),
                      (filt_rua,   "populacao_situacao_rua"),
                      (filt_saude, "profissional_saude"),
                      (filt_imig,  "populacao_imigrante")]:
        if flag and col in df.columns:
            df = df[df[col].astype(str).str.lower() == "sim"]

    for flag, col in [(filt_aids, "agravo_aids"), (filt_alcool, "agravo_alcoolismo"),
                      (filt_diab, "agravo_diabetes"), (filt_drogas, "agravo_drogas_ilicitas"),
                      (filt_tabaco, "agravo_tabagismo")]:
        if flag and col in df.columns:
            df = df[df[col].astype(str).str.lower() == "sim"]

    df = enriquecer_df(df)

    total_base = len(df_completo)
    total_filt = len(df)
    pct_filt   = round(total_filt / total_base * 100, 1) if total_base else 0

    st.sidebar.divider()
    st.sidebar.metric(
        "Registros filtrados",
        f"{total_filt:,}".replace(",", "."),
        f"de {total_base:,} ({pct_filt}%)".replace(",", "."),
    )
    st.sidebar.caption("Fonte: SINAN NET · Ministério da Saúde")

    if total_filt == 0:
        st.warning("Nenhum registro encontrado com os filtros selecionados.")
        st.stop()

    return df, df_completo, anos_sel, ano_sel, total_filt, total_base

