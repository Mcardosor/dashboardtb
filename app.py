"""
app.py — Tuberculose no Brasil | SINAN NET
──────────────────────────────────────────
Dashboard completo: dark theme, hero, 8 KPI cards, 6 abas, Folium.
Revisão Raquel: 100 mil, reorder KPIs, pirâmide óbitos, desfecho HIV, indicadores.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

from src.constantes import (
    SPEC_PATH, COLUNAS_ANALISE, PLOTLY_CFG, POP_ESTADO, POP_BRASIL,
    UF_SIGLAS, TB_SEQ_INCIDENCIA, TB_SEQ_MORTAL,
    ANO_ATUAL, ANO_INICIO, HIST_INDICADORES,
    NORMALIZAR_DESFECHO, AGRAVOS, POPULACOES,
    H_SMALL, H_MEDIUM, H_LARGE,
    kpi_card_html, _delta_badge, pct,
    tb_color_map,
)
from src.graficos import tb_layout, grafico_vazio
from src.dados import (
    carregar_geojson, geojson_enriquecido,
    selecionar_colunas, render_pygwalker,
    load_historico, agregar_por_uf,
)
from src.ui_sidebar import render_sidebar
from src import graficos
from src import mapa_interativo
from src.banco import obitos_sim_por_uf, obitos_sim_brasil

# Tipos de entrada válidos para cálculo de incidência (Caderno de Indicadores MS)
_TIPOS_INCIDENCIA = {"Caso Novo", "Não Sabe", "Pós-óbito"}
from streamlit_folium import st_folium

# Valores inválidos a excluir dos gráficos (valores técnicos, não categorias epidemiológicas)
_INVAL = ["nan", "None", "undefined", ""]
_NI_NORM = {"Nao informado": "Não informado"}  # normaliza grafia sem acento


# ── Warmup: pré-aquece cache na inicialização ──────────────────────────────
@st.cache_resource(show_spinner=False)
def _iniciar_warmup():
    """Roda uma vez por processo — pré-carrega dados mais comuns em background."""
    import threading
    def _bg():
        try:
            from src.dados import carregar_dados, carregar_geojson
            from src.constantes import ANO_ATUAL
            carregar_geojson()
            carregar_dados((ANO_ATUAL,))
        except Exception:
            pass
    threading.Thread(target=_bg, daemon=True).start()
    return True
_iniciar_warmup()
# ───────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG & CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Dashboard TB | SINAN",
    page_icon="🩺",
    layout="wide",
)

from src.styles import inject_css  # noqa: E402
inject_css()

st.markdown("""
<div class="cenarios-bar">
  <span class="cenarios-bar-logo">Cenários<span>+</span></span>
  <span class="cenarios-bar-sep">|</span>
  <span class="cenarios-bar-title">Dashboard TB | SINAN</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — FILTROS
# ══════════════════════════════════════════════════════════════════════════════
df, df_completo, anos_sel, ano_sel, total_filt, total_base = render_sidebar()
pct_filt = round(total_filt / total_base * 100, 1) if total_base else 0

# ══════════════════════════════════════════════════════════════════════════════
#  HERO
# ══════════════════════════════════════════════════════════════════════════════
_label_anos  = f"Anos {min(anos_sel)}–{max(anos_sel)}" if len(anos_sel) > 1 else f"Ano {anos_sel[0]}"
_label_regs  = f"{total_filt:,}".replace(",", ".") + f" registros ({pct_filt}% da base)"
_badge_2026  = (
    '<span class="hero-badge" style="background:rgba(248,81,73,.15);'
    'border-color:rgba(248,81,73,.4);color:#f85149">'
    '<span class="dot"></span>2026 · dados parciais</span>'
) if 2026 in anos_sel else ""

st.markdown(f"""
<div class="hero">
  <h1 class="hero-title">
    <span class="hero-emoji">🩺</span>
    <span>Tuberculose no Brasil</span>
  </h1>
  <p class="hero-subtitle">
    Painel de vigilância epidemiológica baseado em notificações do SINAN —
    perfil dos casos, indicadores clínicos, distribuição geográfica e tendências
    temporais ({ANO_INICIO}–{ANO_ATUAL}).
  </p>
  <div class="hero-badges">
    <span class="hero-badge accent"><span class="dot"></span>{_label_anos}</span>{_badge_2026}<span class="hero-badge"><span class="dot"></span>SINAN NET · Dicionário v5.0</span><span class="hero-badge success"><span class="dot"></span>{_label_regs}</span><span class="hero-badge"><span class="dot"></span>Série histórica: {ANO_INICIO}–{ANO_ATUAL}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
#  KPIs — cálculo
# ══════════════════════════════════════════════════════════════════════════════
enc_norm = (df["situacao_enc_norm"] if "situacao_enc_norm" in df.columns
            else df.get("situacao_encerramento", pd.Series(dtype=str)).astype(str)
                   .map(lambda x: NORMALIZAR_DESFECHO.get(x, x)))

total      = len(df)
cura       = (enc_norm == "Cura").sum()
obito_tb   = (enc_norm == "Obito por TB").sum()
abandono   = enc_norm.isin(["Abandono", "Abandono Primario"]).sum()
hiv_pos    = (df["status_hiv"] == "Positivo").sum() if "status_hiv" in df.columns else 0
municipios = df["municipio_notificacao"].nunique() if "municipio_notificacao" in df.columns else 0

ufs_sel      = df["uf_sigla"].unique() if "uf_sigla" in df.columns else []
pop_filtrada = sum(POP_ESTADO.get(uf, 0) for uf in ufs_sel) or POP_BRASIL

# Número de anos selecionados — coeficientes (por 100 mil) são ANUAIS.
# Com múltiplos anos, anualizamos (média anual): divide por (população × nº de anos).
# Sem isso, somar N anos de casos sobre 1 ano de população infla a taxa ~N×.
_n_anos = max(len(anos_sel), 1)

# Incidência: apenas Caso Novo + Não Sabe + Pós-óbito (Caderno de Indicadores MS),
# excluindo casos sem UF mapeada (não têm denominador populacional).
if "tipo_entrada" in df.columns:
    _mask_inc = df["tipo_entrada"].astype(str).isin(_TIPOS_INCIDENCIA)
    if "uf_sigla" in df.columns:
        _mask_inc = _mask_inc & (df["uf_sigla"].astype(str) != "?")
    _total_inc = int(_mask_inc.sum())
else:
    _total_inc = total
incidencia  = round(_total_inc / (pop_filtrada * _n_anos) * 100_000, 1)

# Mortalidade: fonte SIM (Caderno de Indicadores MS — não usa SINAN SITUA_ENCE).
# Soma os óbitos SIM de TODOS os anos selecionados. Nacional usa obitos_sim_brasil
# (sem filtro de codmunres → não sub-conta óbitos com residência ignorada).
try:
    _por_uf = len(ufs_sel) > 0 and len(ufs_sel) < 27
    _obitos_sim = 0
    for _a in anos_sel:
        if _por_uf:
            _sim_uf = obitos_sim_por_uf(_a)
            _obitos_sim += int(_sim_uf[_sim_uf["uf_sigla"].isin(ufs_sel)]["obitos_sim"].sum())
        else:
            _obitos_sim += int(obitos_sim_brasil(_a) or 0)
    if _obitos_sim == 0:
        _obitos_sim = int(obito_tb)
except Exception:
    _obitos_sim = int(obito_tb)
mortalidade = round(_obitos_sim / (pop_filtrada * _n_anos) * 100_000, 1)

if "metric_mapa" not in st.session_state:
    st.session_state.metric_mapa = "incidencia"
if "selected_uf" not in st.session_state:
    st.session_state.selected_uf = None
if "mapa_key_counter" not in st.session_state:
    st.session_state.mapa_key_counter = 0

# ── KPI cards — ordem Raquel: incid | mort | óbitos | HIV / cura | abandono | total | municípios
_cards = [
    # Linha 1: indicadores de magnitude e mortalidade
    ("incidencia",  "Incidência por 100 mil hab.",
     f"{incidencia:.1f}".replace(".", ","),   None, None, False, "📈", "#58a6ff", "incidencia"),
    ("mortalidade", "Mortalidade por 100 mil hab.",
     f"{mortalidade:.1f}".replace(".", ","),  None, None, False, "💀", "#f85149", "mortalidade"),
    ("obito",       "Óbitos por TB (SIM)",
     f"{_obitos_sim:,}".replace(",", "."),    None, None, False, "⚠️", "#ffd700", None),
    ("hiv",         "Coinfecção HIV",
     f"{hiv_pos:,}".replace(",", "."),        None, None, False, "🔬", "#d2a8ff", None),
    # Linha 2: desfechos + total
    ("cura",        "Curas registradas",
     f"{cura:,}".replace(",", "."),           None, None, True,  "✅", "#7ee787", None),
    ("abandono",    "Abandonos",
     f"{abandono:,}".replace(",", "."),       None, None, False, "🚪", "#8b949e", None),
    ("total",       "Total de casos",
     f"{total:,}".replace(",", "."),          None, None, False, "🦠", "#ffa657", "casos"),
    ("municipios",  "Municípios prioritários",
     f"{municipios:,}".replace(",", "."),     None, None, False, "🏙️", "#79c0ff", None),
]

for row_cards in [_cards[:4], _cards[4:]]:
    cols = st.columns(4)
    for col, (key, title, valor, prev, cur, bom_subir, icon, accent, mapa_key) in zip(cols, row_cards):
        with col:
            sel   = (st.session_state.metric_mapa == mapa_key) if mapa_key else False
            delta = _delta_badge(cur, prev, good_when_up=bom_subir) if prev is not None else ""
            st.markdown(kpi_card_html(title, valor, delta, icon, accent, sel),
                        unsafe_allow_html=True)
            if mapa_key:
                lbl = "🗺️ No mapa ✓" if sel else "🗺️ Ver no mapa"
                if st.button(lbl, key=f"kpibtn_{key}",
                             type="primary" if sel else "secondary",
                             width='stretch'):
                    st.session_state.metric_mapa = mapa_key
                    st.rerun()

st.divider()

# ══════════════════════════════════════════════════════════════════════════════
#  ABAS
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False, max_entries=10)
def _modal_agregar(df_hash: int, uf: str, _df: pd.DataFrame) -> dict:
    """Agrega todos os dados do modal de uma vez — cacheado por (hash_df, uf)."""
    mask = _df["estado_notificacao"].astype(str).map(UF_SIGLAS) == uf
    df_uf = _df.loc[mask].copy()
    for col in df_uf.select_dtypes("category").columns:
        df_uf[col] = df_uf[col].astype(str)

    total_uf = int(mask.sum())
    total_mun = df_uf["municipio_notificacao"].astype(str).nunique()

    enc_col = "situacao_enc_norm" if "situacao_enc_norm" in df_uf.columns else "situacao_encerramento"

    # ── Desfechos: denominador = casos ENCERRADOS (exclui "Em acompanhamento") ──
    # Metodologia de coorte (MS/OMS): taxas calculadas sobre encerramentos definidos.
    cura_pct = aband_pct = obito_pct = 0.0
    n_encerrados = 0
    pct_acomp = 0.0
    if enc_col in df_uf.columns:
        enc = df_uf[enc_col].astype(str)
        em_acomp = enc.eq("Em acompanhamento")
        encerrados = enc[~em_acomp]
        n_encerrados = int(len(encerrados))
        denom = max(n_encerrados, 1)
        cura_pct  = round(encerrados.eq("Cura").sum() / denom * 100, 1)
        aband_pct = round(encerrados.isin(["Abandono", "Abandono Primario"]).sum() / denom * 100, 1)
        obito_pct = round(encerrados.eq("Obito por TB").sum() / denom * 100, 1)
        pct_acomp = round(em_acomp.sum() / max(len(enc), 1) * 100, 1)

    # ── Cura separada por tipo de entrada (tempos de tratamento diferentes) ──
    # Caso novo: esquema ~6 meses. Retratamento (recidiva/reingresso): mais longo.
    cura_novo_pct = cura_retrat_pct = 0.0
    n_enc_novo = n_enc_retrat = 0
    if enc_col in df_uf.columns and "tipo_entrada" in df_uf.columns:
        te = df_uf["tipo_entrada"].astype(str)
        enc_full = df_uf[enc_col].astype(str)
        nao_acomp = ~enc_full.eq("Em acompanhamento")
        m_novo = te.eq("Caso Novo") & nao_acomp
        m_retrat = te.isin(["Recidiva", "Reingresso após Abandono", "Reingresso Após Abandono"]) & nao_acomp
        n_enc_novo = int(m_novo.sum())
        n_enc_retrat = int(m_retrat.sum())
        if n_enc_novo:
            cura_novo_pct = round(enc_full[m_novo].eq("Cura").sum() / n_enc_novo * 100, 1)
        if n_enc_retrat:
            cura_retrat_pct = round(enc_full[m_retrat].eq("Cura").sum() / n_enc_retrat * 100, 1)

    # ── HIV: denominador = casos com testagem conhecida (exclui ignorado/não feito) ──
    hiv_pct = 0.0
    n_hiv_conhecido = 0
    pct_hiv_ign = 0.0
    if "status_hiv" in df_uf.columns:
        hiv = df_uf["status_hiv"].astype(str)
        conhecido = hiv.isin(["Positivo", "Negativo"])
        n_hiv_conhecido = int(conhecido.sum())
        hiv_pct = round(hiv.eq("Positivo").sum() / max(n_hiv_conhecido, 1) * 100, 1)
        pct_hiv_ign = round((~conhecido).sum() / max(len(hiv), 1) * 100, 1)

    top20 = (
        df_uf["municipio_notificacao"].astype(str)
        .value_counts().head(20).reset_index()
        .rename(columns={"municipio_notificacao": "municipio", "count": "casos"})
    )

    return dict(
        total_uf=total_uf, total_mun=total_mun,
        cura_pct=cura_pct, aband_pct=aband_pct, obito_pct=obito_pct, hiv_pct=hiv_pct,
        cura_novo_pct=cura_novo_pct, cura_retrat_pct=cura_retrat_pct,
        n_enc_novo=n_enc_novo, n_enc_retrat=n_enc_retrat,
        n_encerrados=n_encerrados, pct_acomp=pct_acomp,
        n_hiv_conhecido=n_hiv_conhecido, pct_hiv_ign=pct_hiv_ign,
        top20=top20,
    )


@st.cache_data(show_spinner=False, max_entries=10)
def _modal_mapa_html(df_hash: int, uf: str, _df: pd.DataFrame) -> str | None:
    """Renderiza o mapa Folium e retorna HTML puro — cacheado por (hash_df, uf)."""
    m = mapa_interativo.mapa_estado(_df, uf)
    if m is None:
        return None
    return mapa_interativo.render_html(m, height=420)


# Cache em memória do mapa Brasil — evita recriar objeto Folium a cada rerun.
# Folium Maps não são pickle-serializáveis, então não usamos @st.cache_data.
_MAPA_BRASIL_CACHE: dict = {}

def _get_mapa_brasil(casos_uf, df_hash: int, metrica: str, selected_uf: str | None):
    key = (df_hash, metrica, selected_uf)
    if key not in _MAPA_BRASIL_CACHE:
        if len(_MAPA_BRASIL_CACHE) > 15:
            _MAPA_BRASIL_CACHE.clear()
        _MAPA_BRASIL_CACHE[key] = mapa_interativo.mapa_brasil(
            casos_uf, metrica=metrica, selected_uf=selected_uf
        )
    return _MAPA_BRASIL_CACHE[key]


@st.dialog("Distribuição por Município", width="large")
def _modal_municipios(uf: str, df_modal: pd.DataFrame) -> None:
    import numpy as np
    nome = mapa_interativo.uf_para_nome(uf)

    # Chave de cache sensível ao CONTEÚDO (não só shape): evita colisão entre
    # filtros diferentes que resultem no mesmo nº de linhas → dados do estado errado.
    if len(df_modal):
        _sig = int(pd.util.hash_pandas_object(df_modal["municipio_notificacao"], index=False).sum())
    else:
        _sig = 0
    df_hash = hash((df_modal.shape, tuple(df_modal.columns), _sig))

    with st.spinner("Carregando..."):
        dados = _modal_agregar(df_hash, uf, df_modal)
        mapa_html = _modal_mapa_html(df_hash, uf, df_modal)

    total_uf  = dados["total_uf"]
    total_mun = dados["total_mun"]

    # ── Cabeçalho ──────────────────────────────────────────────────────────────
    st.markdown(f"### 📍 {nome} ({uf})")

    # ── Mapa ───────────────────────────────────────────────────────────────────
    if mapa_html:
        components.html(mapa_html, height=430, scrolling=False)
        if uf == "DF":
            st.caption("ℹ️ Dados do DF inteiro — SINAN não distingue Regiões Administrativas.")
    else:
        st.warning(f"GeoJSON de {uf} não encontrado.")

    st.divider()

    # ── KPIs + Gráfico lado a lado ─────────────────────────────────────────────
    col_chart, col_kpi = st.columns([2, 1])

    with col_kpi:
        st.metric("Notificações", f"{total_uf:,}", help="Total de casos notificados no SINAN (todos os desfechos).")
        # Cura separada por tipo de entrada — caso novo e retratamento têm
        # esquemas de tratamento com durações diferentes (não devem ser somados).
        cN, cR = st.columns(2)
        cN.metric(
            "Cura · caso novo", f"{dados['cura_novo_pct']:.1f}%",
            help=f"Fonte: SINAN. Sobre {dados['n_enc_novo']:,} casos novos encerrados. "
                 f"Esquema básico ~6 meses. Meta MS: ≥85%.",
        )
        cR.metric(
            "Cura · retratamento", f"{dados['cura_retrat_pct']:.1f}%",
            help=f"Fonte: SINAN. Sobre {dados['n_enc_retrat']:,} retratamentos encerrados "
                 f"(recidiva + reingresso). Tratamento mais longo e menor taxa de cura.",
        )
        # Abandono: alerta visual quando acima da meta da OMS (<5%)
        _ab = dados['aband_pct']
        _ab_label = "🔴 Abandono" if _ab >= 5.0 else "🟢 Abandono"
        st.metric(
            _ab_label, f"{_ab:.1f}%",
            help=f"Fonte: SINAN. Inclui abandono e abandono primário, sobre {dados['n_encerrados']:,} "
                 f"casos encerrados. Meta OMS: <5%."
                 + (f" ⚠️ Acima da meta — risco de TB resistente." if _ab >= 5.0 else ""),
        )
        st.metric(
            "Óbitos por TB", f"{dados['obito_pct']:.1f}%",
            help=f"Fonte: SINAN (desfecho de encerramento). Sobre {dados['n_encerrados']:,} casos "
                 f"encerrados. ⚠️ A mortalidade oficial vem do SIM, não deste percentual.",
        )
        st.metric(
            "HIV+", f"{dados['hiv_pct']:.1f}%",
            help=f"Fonte: SINAN. Denominador: {dados['n_hiv_conhecido']:,} casos com testagem conhecida "
                 f"(exclui {dados['pct_hiv_ign']:.0f}% ignorado/não realizado).",
        )

    with col_chart:
        top_n = st.select_slider("Top municípios:", options=[10, 15, 20], value=15, key=f"top_n_{uf}")
        top_mun = dados["top20"].head(top_n).sort_values("casos", ascending=True)
        st.caption(f"Top {top_n} de {total_mun} municípios com notificações")
        top_mun["cor"] = np.log1p(top_mun["casos"])
        fig_mun = px.bar(
            top_mun, x="casos", y="municipio", orientation="h",
            color="cor",
            color_continuous_scale=["#f4a261", "#e76f51", "#c0392b", "#7b0c0c"],
            labels={"casos": "Casos", "municipio": "", "cor": ""},
            text="casos",
        )
        max_casos = int(top_mun["casos"].max())
        margem_dir = max(70, len(f"{max_casos:,}") * 10)
        fig_mun.update_layout(
            height=max(350, top_n * 28), showlegend=False, coloraxis_showscale=False,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_color="#c9d1d9", margin=dict(l=0, r=margem_dir, t=5, b=35),
            xaxis=dict(title="Casos"),
            yaxis=dict(tickfont=dict(size=12)),
        )
        fig_mun.update_traces(
            marker_line_color="#0d1117", marker_line_width=1,
            texttemplate="%{text:,}", textposition="outside",
            cliponaxis=False, textfont=dict(size=13, color="#e6edf3"),
            hovertemplate="<b>%{y}</b><br>Casos: %{x:,}<extra></extra>",
        )
        st.plotly_chart(fig_mun, width="stretch", config={"displayModeBar": False})

    with st.expander(f"📋 Ver todos os {total_mun} municípios"):
        tabela = (
            df_modal.loc[df_modal["estado_notificacao"].astype(str).map(UF_SIGLAS) == uf,
                         "municipio_notificacao"].astype(str)
            .value_counts().reset_index()
            .rename(columns={"municipio_notificacao": "Município", "count": "Casos"})
        )
        tabela.index = range(1, len(tabela) + 1)
        st.dataframe(tabela, width="stretch", height=300)


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🗺️ Distribuição Geográfica",
    "👥 Perfil dos Pacientes",
    "🏥 Clínico & Diagnóstico",
    "⚠️ Comorbidades & Vulnerabilidades",
    "📈 Tendência Histórica",
    "🔬 Análise Livre",
])

# ── ABA 1: MAPA ───────────────────────────────────────────────────────────────
with tab1:
    _metric      = st.session_state.get("metric_mapa", "casos")
    _selected_uf = st.session_state.get("selected_uf")

    # Agrega casos/incidência/mortalidade por UF
    casos_uf = agregar_por_uf(df, enc_norm, anos=anos_sel)

    _cfg = {
        "casos":       ("casos",      "Total de Casos por Estado",                          "Total de Casos",             "YlOrRd"),
        "incidencia":  ("incidencia", "Coeficiente de Incidência por 100 mil hab. — Brasil", "Incidência por 100 mil hab.", "YlOrRd"),
        "mortalidade": ("mortalidade","Coeficiente de Mortalidade por 100 mil hab. — Brasil","Mortalidade por 100 mil hab.","OrRd"),
    }
    _col_mapa, _titulo_mapa, _leg_mapa, _pal_plotly = _cfg.get(_metric, _cfg["casos"])

    col_mapa, col_uf = st.columns([2, 1])

    with col_mapa:
        st.subheader(_titulo_mapa)
        st.caption("💡 Clique num estado no mapa ou selecione abaixo para ver os municípios.")
        # Lê estado atual do selectbox para destacar no mapa (persiste entre reruns)
        _sel_box = st.session_state.get("sel_estado_tab1", "")
        _highlighted_uf = (
            _sel_box.split(" — ")[0].strip()
            if _sel_box and _sel_box != "— selecione um estado —"
            else None
        )

        _df_hash = hash(tuple(casos_uf["uf_sigla"].tolist() + casos_uf.columns.tolist()))
        m_brasil = _get_mapa_brasil(casos_uf, _df_hash, _metric, _highlighted_uf)
        result = st_folium(
            m_brasil, height=500, width="100%",
            key=f"mapa_br_{st.session_state.mapa_key_counter}",
            returned_objects=["last_object_clicked_tooltip"],
        )

        # on_change: só dispara quando usuário realmente muda o valor
        def _sel_changed():
            sel = st.session_state.get("sel_estado_tab1", "")
            if sel and sel != "— selecione um estado —":
                st.session_state["_dialog_uf"] = sel.split(" — ")[0].strip()

        _ufs_disp = sorted(casos_uf["uf_sigla"].dropna().unique().tolist())
        _uf_nomes = {u: f"{u} — {mapa_interativo.uf_para_nome(u)}" for u in _ufs_disp}
        st.selectbox(
            "Explorar municípios:",
            ["— selecione um estado —"] + [_uf_nomes[u] for u in _ufs_disp],
            key="sel_estado_tab1",
            label_visibility="collapsed",
            on_change=_sel_changed,
        )

        # Clique no mapa — só dispara se for um estado diferente do último processado
        uf_clicado = mapa_interativo.extrair_uf_clicado(result)
        _ultimo_click = st.session_state.get("_last_map_click")
        if uf_clicado and uf_clicado != _ultimo_click and not st.session_state.get("_dialog_uf"):
            st.session_state["_dialog_uf"] = uf_clicado
            st.session_state["_last_map_click"] = uf_clicado

        # Abre o modal — reseta _last_map_click ao fechar para permitir reabrir o mesmo estado
        if st.session_state.get("_dialog_uf"):
            _uf = st.session_state.pop("_dialog_uf")
            st.session_state["_last_map_click"] = None
            _modal_municipios(_uf, df)

    with col_uf:
        st.subheader(_leg_mapa + " por Estado")
        if _metric == "incidencia":
            st.caption("📌 Incidência por 100 mil hab.: permite comparar estados de tamanhos diferentes.")
        elif _metric == "mortalidade":
            st.caption("📌 Mortalidade por 100 mil hab.: estados com valor mais alto precisam de atenção prioritária.")
        else:
            st.caption("📌 Total absoluto de casos notificados no estado.")
        por_uf = casos_uf.sort_values(_col_mapa, ascending=True)
        if not por_uf.empty:
            fig_uf = px.bar(por_uf, x=_col_mapa, y="uf_sigla", orientation="h",
                            color=_col_mapa, color_continuous_scale=_pal_plotly,
                            labels={_col_mapa: _leg_mapa, "uf_sigla": ""})
            tb_layout(fig_uf, altura=H_LARGE)
            fig_uf.update_layout(showlegend=False, coloraxis_showscale=False,
                                 xaxis=dict(title=_leg_mapa), yaxis=dict(title=""))
            fig_uf.update_traces(marker_line_color="#0d1117", marker_line_width=1,
                                 hovertemplate=f"<b>%{{y}}</b><br>{_leg_mapa}: %{{x}}<extra></extra>")
            st.plotly_chart(fig_uf, width='stretch', config=PLOTLY_CFG)

# ── ABA 2: PERFIL — pirâmide de casos + pirâmide de óbitos (Raquel ponto 5) ──

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Por Sexo")
        st.caption("Distribuição dos casos entre homens e mulheres. Historicamente, a TB afeta mais homens no Brasil.")
        if "sexo" in df.columns:
            d = df["sexo"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Sexo", "Casos"]
            d = d[~d["Sexo"].isin(_INVAL)]
            graficos.safe_pie(d, "Sexo", "Casos", height=H_SMALL)
            n_ign_sexo = int(df["sexo"].isna().sum() + df["sexo"].isin(["Ignorado", "Nao informado", "Não informado"]).sum())
            if n_ign_sexo > 0:
                st.caption(f"ℹ️ {n_ign_sexo:,} casos com sexo não informado/ignorado aparecem como categoria própria no gráfico.")
        else:
            grafico_vazio()
    with c2:
        st.subheader("Forma Clínica")
        st.caption("**Pulmonar**: TB nos pulmões — transmissível pelo ar. **Extrapulmonar**: TB em outros órgãos (gânglios, ossos, rins). A forma pulmonar representa maior risco de contágio.")
        if "forma" in df.columns:
            d = df["forma"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Forma", "Casos"]
            d = d[~d["Forma"].isin(_INVAL)]
            graficos.safe_pie(d, "Forma", "Casos", height=H_SMALL)
            n_ign_forma = int(df["forma"].isna().sum() + df["forma"].isin(["Ignorado", "Nao informado", "Não informado"]).sum())
            if n_ign_forma > 0:
                st.caption(f"ℹ️ {n_ign_forma:,} casos com forma clínica não informada/ignorada aparecem como categoria própria no gráfico.")
        else:
            grafico_vazio()

    _, c3mid, _ = st.columns([1, 2, 1])
    with c3mid:
        st.subheader("Tipo de Entrada")
        st.caption("**Caso Novo**: paciente diagnosticado com TB pela primeira vez. **Recidiva**: paciente que já teve TB e foi curado, mas voltou a adoecer. **Reingresso após abandono**: paciente que interrompeu o tratamento e retornou.")
        if "tipo_entrada" in df.columns:
            d = df["tipo_entrada"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Tipo", "Casos"]
            d = d[~d["Tipo"].isin(_INVAL)]
            # Barra horizontal em vez de pizza: 6 categorias com fatias pequenas
            # (ex.: "Não Sabe"/"Pós-óbito" com poucas dezenas de casos) ficam
            # ilegíveis em donut — barra ordenada compara melhor as categorias.
            graficos.safe_bar_h(d.sort_values("Casos", ascending=False), "Casos", "Tipo", height=H_SMALL)
        else:
            grafico_vazio()

    st.divider()
    c4, c5 = st.columns(2)
    with c4:
        st.subheader("Por Raça/Cor")
        st.caption("A TB afeta desproporcionalmente populações negras e indígenas no Brasil, refletindo desigualdades socioeconômicas no acesso à saúde.")
        if "raca_cor" in df.columns:
            d = df["raca_cor"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Raça", "Casos"]
            d = d[~d["Raça"].isin(["nan", "None"])]
            graficos.safe_bar_v(d, "Raça", "Casos", height=H_MEDIUM)
        else:
            grafico_vazio()
    with c5:
        st.subheader("Situação de Encerramento")
        st.caption("Como o caso foi concluído: **Cura** (tratamento completo), **Abandono** (interrompeu o tratamento), **Óbito por TB** (faleceu pela doença). Alta taxa de cura indica programa de controle eficaz.")
        col_enc = "situacao_enc_norm" if "situacao_enc_norm" in df.columns else "situacao_encerramento"
        if col_enc in df.columns:
            d = df[col_enc].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Situação", "Casos"]
            d = d[~d["Situação"].isin(_INVAL)]
            graficos.safe_bar_h(d.sort_values("Casos", ascending=False), "Casos", "Situação", height=H_MEDIUM)
        else:
            grafico_vazio()

    st.divider()

    # Desfecho agrupado + Desfecho × Raça/cor
    d1, d2 = st.columns(2)
    with d1:
        st.subheader("Desfecho de Tratamento — Agrupado")
        st.caption("Casos agrupados em 4 categorias: **Cura**, **Interrupção** (abandono), **Óbito** (por TB ou outras causas) e **Não avaliados** (transferências, TB-DR, em acompanhamento).")
        graficos.fig_desfecho_agrupado(df)
    with d2:
        st.subheader("Desfecho × Raça/Cor")
        st.caption("Distribuição dos desfechos de tratamento dentro de cada grupo racial. Diferenças entre grupos refletem desigualdades no acesso e na qualidade do cuidado.")
        graficos.fig_desfecho_por_raca(df)

    st.divider()

    # Raquel ponto 5: duas pirâmides — casos e óbitos
    p1, p2 = st.columns(2)
    with p1:
        st.subheader("Pirâmide Etária — Casos de TB")
        st.caption("Distribuição dos casos notificados por faixa etária e sexo")
        if "idade_anos" in df.columns and "sexo" in df.columns:
            st.plotly_chart(graficos.fig_piramide(df), width="stretch", config=PLOTLY_CFG)
            st.caption("🟠 Barras em laranja = faixas etárias **<15 anos** (público prioritário)")
        else:
            grafico_vazio()
    with p2:
        st.subheader("Pirâmide Etária — Óbitos por TB")
        st.caption("Distribuição dos óbitos por TB por faixa etária e sexo")
        fig_ob = graficos.fig_piramide_obitos(df)
        if fig_ob:
            st.plotly_chart(fig_ob, width="stretch", config=PLOTLY_CFG)
            st.caption("🟠 Barras em laranja = faixas etárias **<15 anos** (público prioritário)")
        else:
            st.info("Dados insuficientes de óbitos para a pirâmide.")

# ── ABA 3: CLÍNICO — Raquel ponto 6: Desfecho por status HIV ─────────────────
with tab3:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Status HIV")
        st.caption("Resultado do teste de HIV entre os pacientes com TB. Pacientes com HIV têm imunidade reduzida, tornando a TB mais grave e difícil de tratar.")
        if "status_hiv" in df.columns:
            d = df["status_hiv"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["HIV", "Casos"]
            d = d[~d["HIV"].isin(_INVAL)]
            graficos.safe_pie(d, "HIV", "Casos", height=H_SMALL)
        else:
            grafico_vazio()
    with c2:
        st.subheader("Baciloscopia — 1ª amostra")
        st.caption("Exame de escarro que detecta a bactéria da TB. **Positivo**: bactéria encontrada (caso confirmado e transmissível). **Negativo**: bactéria não detectada nesta amostra.")
        if "baciloscopia_primeira_amostra" in df.columns:
            d = df["baciloscopia_primeira_amostra"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Resultado", "Casos"]
            d = d[~d["Resultado"].isin(_INVAL)]
            graficos.safe_pie(d, "Resultado", "Casos", height=H_SMALL)
        else:
            grafico_vazio()

    _, c3mid2, _ = st.columns([1, 2, 1])
    with c3mid2:
        st.subheader("Teste Molecular Rápido (TMR-TB)")
        st.caption("Exame moderno que detecta a TB e já identifica resistência ao principal antibiótico (rifampicina) em poucas horas. Mais preciso e rápido que a baciloscopia tradicional.")
        if "teste_molecular" in df.columns:
            d = df["teste_molecular"].astype(str).replace("nan", "Não informado").replace(_NI_NORM).value_counts().reset_index()
            d.columns = ["Resultado", "Casos"]
            d = d[~d["Resultado"].isin(_INVAL)]
            graficos.safe_pie(d, "Resultado", "Casos", height=H_SMALL)
        else:
            grafico_vazio()

    st.divider()

    # Raquel ponto 6: Desfecho por status HIV
    st.subheader("Desfecho do Tratamento por Status HIV")
    st.caption("Compara como o tratamento de TB termina dependendo do status HIV do paciente. Cada coluna soma 100% — ou seja, mostra a proporção de cada desfecho **dentro** de cada grupo. Pacientes com HIV positivo tendem a ter menor taxa de cura e maior risco de óbito.")
    graficos.fig_desfecho_por_hiv(df)

    st.divider()
    st.subheader("Coinfecção TB-HIV por Estado")
    st.caption("De cada 100 pacientes com TB **testados para HIV** no estado, quantos têm resultado positivo. Denominador = casos com testagem conhecida (exclui não testados/ignorados). **Atenção**: é proporção (%), não quantidade absoluta.")
    graficos.fig_coinfeccao_hiv_uf(df)

    st.divider()
    st.subheader("⏱️ Oportunidade do Tratamento")
    st.caption("Quanto tempo o paciente espera entre o diagnóstico e o início do tratamento. O início precoce (idealmente ≤7 dias) interrompe a cadeia de transmissão e melhora o prognóstico.")
    _tt = graficos.tempo_tratamento_stats(df)
    if _tt is None:
        st.info("Dados de datas insuficientes para calcular o tempo de tratamento.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Início do tratamento (mediana)", f"{_tt['mediana_inicio']:.0f} dias",
                  help=f"Mediana de dias entre diagnóstico e início do tratamento, sobre {_tt['n']:,} casos com ambas as datas válidas.")
        m2.metric("Início em ≤7 dias", f"{_tt['pct_ate_7d']:.1f}%",
                  help="Proporção de casos que iniciaram o tratamento em até 7 dias do diagnóstico — início oportuno.")
        m3.metric("Início tardio (>30 dias)", f"{_tt['pct_acima_30d']:.1f}%",
                  help="Proporção com mais de 30 dias entre diagnóstico e início — atraso preocupante.")
        if _tt["duracao_mediana"] is not None:
            m4.metric("Duração do tratamento (mediana)", f"{_tt['duracao_mediana']:.0f} dias",
                      help="Mediana de dias entre notificação e encerramento, para casos encerrados. Esquema básico esperado: ~180 dias (6 meses).")
        graficos.fig_dist_tempo_tratamento(_tt)

# ── ABA 4: COMORBIDADES ───────────────────────────────────────────────────────
with tab4:
    col_comor, col_vuln = st.columns([3, 2])
    with col_comor:
        st.subheader("Comorbidades Associadas")
        st.caption("Doenças ou condições presentes junto com a TB. Alta prevalência de comorbidades indica pacientes mais vulneráveis e com tratamento mais complexo. Ex: diabéticos têm risco 3x maior de desenvolver TB.")
        graficos.fig_comorbidades(df, total)
    with col_vuln:
        st.subheader("Populações Vulneráveis")
        st.caption("Grupos com risco muito elevado de TB por condições de vida. Pessoas em situação de rua têm risco até 56x maior; privados de liberdade, até 28x maior que a população geral.")
        st.markdown("<br>", unsafe_allow_html=True)
        vuln = {
            "Privado de Liberdade":  (df.get("populacao_privada_liberdade", pd.Series(dtype=str)).astype(str).str.lower() == "sim").sum(),
            "Em Situação de Rua":    (df.get("populacao_situacao_rua",      pd.Series(dtype=str)).astype(str).str.lower() == "sim").sum(),
            "Profissional de Saúde": (df.get("profissional_saude",          pd.Series(dtype=str)).astype(str).str.lower() == "sim").sum(),
            "Imigrante":             (df.get("populacao_imigrante",         pd.Series(dtype=str)).astype(str).str.lower() == "sim").sum(),
        }
        for label, val in vuln.items():
            st.metric(label, f"{val:,}".replace(",", "."), pct(val, total))
            st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Desfecho de Tratamento × Populações Vulneráveis")
    st.caption("Como o tratamento termina para cada grupo vulnerável. Populações em situação de rua e privadas de liberdade tendem a ter maior taxa de interrupção e óbito.")
    graficos.fig_desfecho_por_vulneravel(df)

    st.divider()
    st.subheader("Comorbidades por Estado")
    st.caption("Proporção de casos com cada comorbidade em cada estado (% sobre o total de casos do estado). Permite identificar quais regiões concentram mais pacientes com condições agravantes.")
    graficos.fig_comorbidades_uf(df)

# ── ABA 5: TENDÊNCIA ─────────────────────────────────────────────────────────
with tab5:
    df_hist  = load_historico()
    ANOS_HIST = list(range(ANO_INICIO, ano_sel))

    if df_hist is None or not ANOS_HIST:
        st.warning(
            "Dados históricos não encontrados — apenas 1 ano disponível.\n\n"
            "Execute `python scripts/conectar_banco.py 2001 2024` para popular o histórico."
        )
        # Fallback: distribuição mensal do ano atual
        if "mes_num" in df.columns:
            st.subheader(f"Número de casos por mês — {ano_sel}")
            st.caption(f"Total de notificações de TB por mês de notificação — ano {ano_sel}")
            mes = (df.dropna(subset=["mes_num"])
                   .groupby("mes_num").size().reset_index(name="casos"))
            mes["mes_label"] = mes["mes_num"].map(graficos.MESES_PT)
            mes = mes.sort_values("mes_num")
            media_m = mes["casos"].mean()
            fig_mes = px.bar(mes, x="mes_label", y="casos",
                             labels={"mes_label": "Mês", "casos": "Nº de casos notificados"})
            fig_mes.add_hline(y=media_m, line_dash="dot", line_color="#58a6ff",
                              annotation_text=f"Média mensal: {media_m:,.0f}".replace(",", "."),
                              annotation_font=dict(color="#58a6ff", size=11))
            tb_layout(fig_mes, altura=H_LARGE)
            fig_mes.update_traces(marker_color="#d29922",
                                  marker_line_color="#0d1117", marker_line_width=1,
                                  hovertemplate="<b>%{x}</b><br>Nº de casos: %{y:,}<extra></extra>")
            st.plotly_chart(fig_mes, width='stretch', config=PLOTLY_CFG)
    else:
        # KPIs de tendência
        df_mensal = df_hist["mensal"]
        hist_anos = df_mensal[df_mensal["nu_ano"].astype(str).isin([str(a) for a in ANOS_HIST])]
        media_anual_hist = hist_anos.groupby("nu_ano")["casos"].sum().mean() if not hist_anos.empty else 0
        variacao_geral   = ((total - media_anual_hist) / media_anual_hist * 100) if media_anual_hist else 0
        tend_icon  = "⬆️" if variacao_geral > 5 else ("⬇️" if variacao_geral < -5 else "➡️")
        tend_label = "Para Mais" if variacao_geral > 5 else ("Para Menos" if variacao_geral < -5 else "Estável")

        ka, kb, kc = st.columns(3)
        ka.metric("Tendência vs histórico", f"{tend_icon} {tend_label}",
                  f"{variacao_geral:+.1f}% vs {ANO_INICIO}–{ano_sel-1}")
        kb.metric(f"Total {ano_sel}", f"{int(total):,}".replace(",", "."), "casos notificados")
        kc.metric("Média anual histórica", f"{int(media_anual_hist):,}".replace(",", "."),
                  f"casos/ano | {ANO_INICIO}–{ano_sel-1}")

        st.divider()

        # Raquel ponto 3: título explícito com unidade
        st.subheader(f"Casos por Mês — {ano_sel} vs Média Histórica")
        st.caption(f"Barras laranja = casos notificados mês a mês em {ano_sel} (com os filtros aplicados). Linha pontilhada = média mensal esperada com base nos anos {ANO_INICIO}–{ano_sel-1}. Barras acima da linha indicam meses com mais casos que o habitual.")
        graficos.fig_tendencia_mensal(df, df_hist, ano_sel, ANOS_HIST)

        st.divider()
        st.subheader(f"Evolução Anual do Total de Casos — {ANO_INICIO}–{ANO_ATUAL}")
        st.caption(f"Total de casos de TB notificados por ano no Brasil. A barra vermelha destaca o ano selecionado ({ano_sel}). Tendência de queda é positiva; tendência de alta exige investigação.")
        graficos.fig_tendencia_anual(df_hist, ano_sel)

        st.divider()
        st.subheader(f"Evolução Anual de Óbitos por TB (SIM) — {ANO_INICIO}–2024")
        st.caption("Número de óbitos por tuberculose por ano no Brasil, fonte oficial SIM (CID A15–A19). A barra vermelha destaca o ano selecionado — ou o mais recente disponível, já que o SIM vai até 2024.")
        try:
            from src.banco import historico_obitos_sim
            graficos.fig_obitos_anual(historico_obitos_sim(), ano_sel)
        except Exception as e:
            st.warning(f"Não foi possível carregar óbitos do SIM: {e}")

        st.divider()
        st.subheader(f"Variação por Estado — {ano_sel} vs Média Histórica")
        st.caption(f"Quanto cada estado variou em relação à sua própria média de casos ({ANO_INICIO}–{ano_sel-1}). 🔴 Vermelho = mais casos que o habitual (preocupante). 🟢 Verde = menos casos (melhora). 🟡 Amarelo = estável (±5%). Variações grandes podem indicar surtos ou melhorias no registro.")
        graficos.fig_tendencia_uf(df, df_hist, ano_sel, ANOS_HIST)

        # Raquel ponto 4: indicadores históricos com multiselect
        if HIST_INDICADORES.exists():
            st.divider()
            st.subheader(f"Evolução Histórica de Indicadores Clínicos — {ANO_INICIO}–{ANO_ATUAL}")
            st.caption("Acompanhe como os principais indicadores de TB evoluíram ao longo dos anos. Selecione os indicadores de interesse abaixo. A linha vertical marca o ano selecionado na sidebar.")
            try:
                from src.banco import historico_pulmonar_conf_lab, historico_contatos
                df_ind = pd.read_csv(str(HIST_INDICADORES))
                # Enriquecer com indicadores do PostgreSQL (fonte sinan_tube)
                _df_pulm = historico_pulmonar_conf_lab()
                if not _df_pulm.empty and "pct_pulm_conf_lab" in _df_pulm.columns:
                    df_ind = df_ind.merge(
                        _df_pulm[["nu_ano", "pct_pulm_conf_lab"]], on="nu_ano", how="left"
                    )
                _df_cont = historico_contatos()
                if not _df_cont.empty and "pct_contatos_exam" in _df_cont.columns:
                    df_ind = df_ind.merge(
                        _df_cont[["nu_ano", "pct_contatos_exam"]], on="nu_ano", how="left"
                    )
                # Apenas indicadores com coluna real no CSV/merge — sem opções "fantasma".
                # (Coef. de incidência/mortalidade exigiriam população por ano, que não
                #  temos na série histórica; TDO tem ~77% de "Não informado, omitido.)
                opcoes_multisel = [
                    "Taxa de cura (%)",
                    "Taxa de abandono (%)",
                    "Coinfecção HIV (%)",
                    "Forma pulmonar (%)",
                    "Testagem para HIV (%)",
                    "Óbito por TB (%)",
                    "Casos novos (%)",
                    "TB pulmonar conf. laboratorial (%)",
                    "Contatos examinados (%)",
                ]
                sel_ind = st.multiselect(
                    "Selecione os indicadores:",
                    options=opcoes_multisel,
                    default=["Coinfecção HIV (%)", "Taxa de cura (%)", "Taxa de abandono (%)"],
                )
                if sel_ind:
                    graficos.fig_indicadores_historicos(df_ind, sel_ind, ano_sel)
            except Exception as e:
                st.warning(f"Erro ao carregar indicadores históricos: {e}")

# ── ABA 6: ANÁLISE LIVRE ─────────────────────────────────────────────────────
with tab6:
    st.subheader("🔬 Análise Livre")
    st.caption(
        "Monte seus próprios gráficos arrastando campos para os eixos — "
        "sem precisar de código. Ideal para investigar hipóteses específicas."
    )

    df_analise = selecionar_colunas(df, COLUNAS_ANALISE)

    # Renomeia colunas para nomes amigáveis — facilita uso por leigos
    _NOMES_AMIGAVEIS = {
        "estado_notificacao":          "Estado",
        "municipio_notificacao":       "Municipio",
        "uf_residencia":               "UF Residencia",
        "ano_notificacao":             "Ano",
        "data_notificacao":            "Data Notificacao",
        "data_diagnostico":            "Data Diagnostico",
        "data_inicio_tratamento":      "Data Inicio Tratamento",
        "data_encerramento":           "Data Encerramento",
        "idade_anos":                  "Idade (anos)",
        "sexo":                        "Sexo",
        "raca_cor":                    "Raca/Cor",
        "escolaridade":                "Escolaridade",
        "tipo_entrada":                "Tipo de Entrada",
        "forma":                       "Forma Clinica",
        "situacao_encerramento":       "Situacao Encerramento",
        "status_hiv":                  "Status HIV",
        "uso_antirretroviral":         "Uso Antirretroviral",
        "raio_x_torax":                "Raio-X Torax",
        "baciloscopia_primeira_amostra": "Baciloscopia 1a Amostra",
        "cultura_escarro":             "Cultura Escarro",
        "histopatologia":              "Histopatologia",
        "teste_molecular":             "Teste Molecular (TMR-TB)",
        "teste_sensibilidade":         "Teste Sensibilidade",
        "tratamento_supervisionado":   "Tratamento Supervisionado",
        "baciloscopia_mes_1":          "Baciloscopia Mes 1",
        "baciloscopia_mes_2":          "Baciloscopia Mes 2",
        "baciloscopia_mes_3":          "Baciloscopia Mes 3",
        "baciloscopia_mes_4":          "Baciloscopia Mes 4",
        "baciloscopia_mes_5":          "Baciloscopia Mes 5",
        "baciloscopia_mes_6":          "Baciloscopia Mes 6",
        "baciloscopia_apos_6_meses":   "Baciloscopia Apos 6 Meses",
        "agravo_aids":                 "Agravo AIDS",
        "agravo_alcoolismo":           "Agravo Alcoolismo",
        "agravo_diabetes":             "Agravo Diabetes",
        "agravo_doenca_mental":        "Agravo Doenca Mental",
        "agravo_drogas_ilicitas":      "Agravo Drogas Ilicitas",
        "agravo_tabagismo":            "Agravo Tabagismo",
        "populacao_privada_liberdade": "Privado de Liberdade",
        "populacao_situacao_rua":      "Em Situacao de Rua",
        "profissional_saude":          "Profissional de Saude",
        "populacao_imigrante":         "Imigrante",
        "beneficiario_governo":        "Beneficiario Gov.",
        "numero_contatos":             "Numero de Contatos",
        "numero_contatos_examinados":  "Contatos Examinados",
        "tipo_notificacao":            "Tipo de Notificacao",
        "uf_sigla":                    "UF",
        "situacao_enc_norm":           "Desfecho",
        "mes_num":                     "Mes",
    }
    df_analise = df_analise.rename(columns={
        c: _NOMES_AMIGAVEIS[c] for c in df_analise.columns if c in _NOMES_AMIGAVEIS
    })

    n_registros = len(df_analise)
    n_colunas   = len(df_analise.columns)

    col_info, col_csv = st.columns([3, 1])
    with col_info:
        st.info(
            f"📊 **{n_registros:,}** registros  ·  **{n_colunas}** variáveis  "
            f"· filtros da sidebar já aplicados",
        )
    with col_csv:
        csv_bytes = df_analise.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Baixar CSV",
            data=csv_bytes,
            file_name=f"sinan_tb_{'-'.join(str(a) for a in anos_sel)}.csv",
            mime="text/csv",
            width='stretch',
        )

    st.divider()

    if not st.session_state.get("abrir_pygwalker"):
        col_l, col_cfg, col_r = st.columns([1, 2, 1])
        with col_cfg:
            st.markdown(
                "<div style='text-align:center;padding:24px 0 16px'>"
                "<div style='font-size:2.8rem'>🧪</div>"
                "<h3 style='color:#f0f6fc;margin:10px 0 6px'>Exploração Interativa</h3>"
                "<p style='color:#8b949e;margin:0 0 20px'>Arraste campos para os eixos, filtre e crie gráficos. "
                "Os dados ficam no servidor — sem travamento.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
            st.caption(f"Filtros da sidebar aplicados · {n_registros:,} registros disponíveis")
            if st.button("▶  Iniciar Análise", type="primary", use_container_width=True):
                st.session_state["abrir_pygwalker"] = True
                st.rerun()
    else:
        df_pyg = df_analise

        col_fechar, _ = st.columns([1, 4])
        with col_fechar:
            if st.button("✕ Fechar", key="fechar_pygwalker"):
                st.session_state["abrir_pygwalker"] = False
                st.rerun()

        spec = SPEC_PATH if Path(SPEC_PATH).exists() else None
        render_pygwalker(df_pyg, spec_path=spec)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background:#2B7BB9;
    border-radius:12px;
    padding:28px 36px;
    margin-top:8px;
">
    <div style="font-size:1.2rem;font-weight:800;color:#ffffff;letter-spacing:-0.3px;margin-bottom:4px;">
        Cenários<span style="color:#E07B54">+</span>
    </div>
    <div style="font-size:.82rem;color:rgba(255,255,255,.75);">Todos os direitos reservados.</div>
</div>
""", unsafe_allow_html=True)

