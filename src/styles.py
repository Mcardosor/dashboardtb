"""
styles.py
─────────
CSS global do dashboard TB SINAN.
Injetar com: st.markdown(get_css(), unsafe_allow_html=True)
"""

import streamlit as st

_CSS = """
<style>
  [data-testid="stAppViewContainer"] { background-color: #f6f8fa; }
  [data-testid="stSidebar"]          { background-color: #ffffff; }
  [data-testid="stSidebar"] *        { color: #24292f !important; }

  /* ── Header Streamlit: toolbarMode=viewer cuida do menu, só esconde o deploy ── */
  .stDeployButton { display: none !important; }

  /* ── Botões primary — garante cor correta do tema ─────────── */
  [data-testid="stButton"] button[kind="primary"] {
    background-color: #2B7BB9 !important;
    border-color: #2B7BB9 !important;
    color: #ffffff !important;
  }
  [data-testid="stButton"] button[kind="primary"]:hover {
    background-color: #1a5c8a !important;
    border-color: #1a5c8a !important;
  }

  /* ── Pills (filtro de região na sidebar) ───────────────────── */
  [data-testid="stPills"] button {
    background-color: transparent !important;
    border: 1px solid #d0d7de !important;
    color: #24292f !important;
    border-radius: 999px !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    transition: background .15s, border-color .15s, color .15s !important;
  }
  [data-testid="stPills"] button:hover {
    background-color: rgba(43,123,185,.06) !important;
    border-color: rgba(43,123,185,.35) !important;
    color: #1a3a5c !important;
  }
  [data-testid="stPills"] button[aria-checked="true"],
  [data-testid="stPills"] button[aria-pressed="true"],
  [data-testid="stPills"] button[data-active="true"] {
    background-color: rgba(43,123,185,.12) !important;
    border-color: rgba(43,123,185,.35) !important;
    color: #1a3a5c !important;
    font-weight: 600 !important;
  }

  /* ── Multiselect tags — mais leves no tema claro ─────────── */
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background-color: rgba(43,123,185,.12) !important;
    border: 1px solid rgba(43,123,185,.35) !important;
    color: #1a3a5c !important;
    border-radius: 999px !important;
    font-size: 12px !important;
    font-weight: 600 !important;
  }
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] span,
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] button {
    color: #1a3a5c !important;
  }
  [data-testid="stMultiSelect"] span[data-baseweb="tag"]:hover {
    background-color: rgba(43,123,185,.2) !important;
  }
  h1, h2, h3                         { color: #1a3a5c; }
  p, span, label                     { color: #24292f; }
  [data-testid="stCaption"]          { color: #57606a; }
  hr                                 { border-color: #d0d7de; }
  .leaflet-control-attribution        { display: none !important; }

  /* ── KPI Cards ───────────────────────────────────────── */
  .kpi-card {
    --accent: #2B7BB9;
    border-radius: 14px;
    border: 1px solid #d0d7de;
    background: linear-gradient(160deg, #ffffff 0%, #f6f8fa 100%);
    box-shadow: 0 2px 8px rgba(0,0,0,.08);
    overflow: hidden;
    position: relative;
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
    margin-bottom: 4px;
  }
  .kpi-card.kpi-selected {
    border: 1.5px solid var(--accent);
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent),
                0 8px 28px rgba(0,0,0,.1);
    background: linear-gradient(160deg,
        color-mix(in srgb, var(--accent) 5%, #ffffff) 0%, #f6f8fa 100%);
  }
  .kpi-inner {
    display: flex; align-items: center; gap: 11px;
    padding: 13px 13px; position: relative; z-index:1;
  }
  .kpi-bar {
    width: 4px; height: 46px; border-radius: 999px;
    background: var(--accent); flex: 0 0 auto;
  }
  .kpi-body { flex: 1; min-width: 0; }
  .kpi-label {
    font-size: 10px; font-weight: 700; color: #57606a;
    text-transform: uppercase; letter-spacing: .6px;
    margin-bottom: 2px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
  }
  .kpi-value {
    font-size: 22px; font-weight: 900; color: #1a3a5c;
    letter-spacing: -.4px; line-height: 1.1;
  }
  .kpi-delta        { display:block; font-size: 11px; font-weight: 700; margin-top: 3px; }
  .kpi-delta.good   { color: #1a7f37; }
  .kpi-delta.bad    { color: #cf222e; }
  .kpi-delta.flat   { color: #57606a; }
  .kpi-icon {
    width: 34px; height: 34px; border-radius: 999px;
    background: rgba(0,0,0,.03);
    border: 1px solid #d0d7de;
    display: flex; align-items: center;
    justify-content: center; flex: 0 0 auto;
    font-size: 15px;
  }

  /* ── Hero ────────────────────────────────────────────── */
  .hero {
    position: relative; padding: 28px 32px 24px 32px;
    margin: -10px 0 22px 0; border-radius: 18px;
    background: linear-gradient(135deg, #ffffff 0%, #eaf2fb 60%, #d4e8f6 100%);
    border: 1px solid #d0d7de;
    box-shadow: 0 2px 8px rgba(0,0,0,.08); overflow: hidden;
  }
  .hero::before {
    content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #E07B54 0%, #2B7BB9 50%, #1a7f37 100%);
  }
  .hero-title {
    font-size: 32px; font-weight: 900; color: #1a3a5c;
    letter-spacing: -.8px; line-height: 1.15; margin: 0 0 6px 0;
    display: flex; align-items: center; gap: 12px;
  }
  .hero-emoji { font-size: 36px; filter: drop-shadow(0 2px 8px rgba(43,123,185,.25)); }
  .hero-subtitle {
    font-size: 14px; color: #57606a; margin: 0 0 16px 0;
    font-weight: 500; max-width: 720px; line-height: 1.5;
  }
  .hero-badges { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
  .hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 11px; border-radius: 999px; font-size: 11px;
    font-weight: 700; letter-spacing: .3px;
    background: rgba(0,0,0,.04); border: 1px solid #d0d7de;
    color: #24292f; text-transform: uppercase;
  }
  .hero-badge.accent  { background: rgba(43,123,185,.08); border-color: rgba(43,123,185,.3); color: #2B7BB9; }
  .hero-badge.success { background: rgba(26,127,55,.08); border-color: rgba(26,127,55,.3); color: #1a7f37; }
  .hero-badge .dot    { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .8; }

  /* ── Cenários+ navbar ────────────────────────────────── */
  .cenarios-bar {
    background: #2B7BB9; padding: 8px 24px;
    margin: 0.5rem -1rem 1.5rem -1rem;
    display: flex; align-items: center; gap: 8px;
  }
  .cenarios-bar-logo { font-size: 1.1rem; font-weight: 800; color: #ffffff; letter-spacing: -.3px; }
  .cenarios-bar-logo span { color: #E07B54; }
  .cenarios-bar-sep { color: rgba(255,255,255,.4); margin: 0 6px; }
  .cenarios-bar-title { font-size: .85rem; font-weight: 500; color: rgba(255,255,255,.85); }

  /* ── Layout ──────────────────────────────────────────── */
  .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; max-width: 1400px; }
  hr, [data-testid="stDivider"] {
    margin: 2rem 0 1.5rem 0 !important; border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, #d0d7de 20%, #d0d7de 80%, transparent 100%) !important;
  }
  h2 { font-size: 20px !important; font-weight: 700 !important; color: #1a3a5c !important;
       margin-top: .25rem !important; margin-bottom: 1rem !important; padding-bottom: .5rem !important; letter-spacing: -.3px !important; }
  h3 { font-size: 16px !important; font-weight: 600 !important; color: #24292f !important;
       margin-top: .5rem !important; margin-bottom: .75rem !important; letter-spacing: -.2px !important; }

  /* ── Tabs ────────────────────────────────────────────── */
  .stTabs { margin-top: 1rem; }
  .stTabs [data-baseweb="tab-list"] {
    gap: 4px; background: rgba(0,0,0,.02); padding: 6px;
    border-radius: 12px; border: 1px solid #d0d7de;
    flex-wrap: wrap !important;
    overflow-x: auto;
  }
  .stTabs [data-baseweb="tab"] {
    padding: 8px 14px !important; border-radius: 8px !important;
    font-weight: 600 !important; font-size: 13px !important;
    color: #57606a;
    white-space: nowrap;
    flex: 1 1 auto !important;
    text-align: center !important;
    cursor: pointer !important;
    border: 1px solid transparent !important;
    transition: background .15s ease, border-color .15s ease,
                color .15s ease, transform .1s ease !important;
  }
  .stTabs [data-baseweb="tab"]:hover {
    background: rgba(0,0,0,.04) !important;
    border-color: #d0d7de !important;
    color: #24292f !important;
    transform: translateY(-1px);
  }
  .stTabs [aria-selected="true"] {
    background: rgba(224,123,84,.1) !important;
    border-color: rgba(224,123,84,.3) !important;
    color: #1a3a5c !important;
    border-bottom-color: transparent !important;
    box-shadow: 0 2px 8px rgba(224,123,84,.1) !important;
  }
  .stTabs [data-baseweb="tab-panel"] { padding-top: 1.25rem; }

  /* ── Expanders ────────────────────────────────────────── */
  [data-testid="stExpander"] {
    border: 1px solid #d0d7de !important; border-radius: 12px !important;
    background: #ffffff !important; margin-top: 1rem;
  }
  [data-testid="stSidebar"] [data-testid="stExpander"] {
    background: transparent !important; border: 1px solid #d0d7de !important; margin-bottom: .5rem;
  }

  /* ── Folium ──────────────────────────────────────────── */
  iframe[title="streamlit_folium.st_folium"] {
    border-radius: 12px; border: 1px solid #d0d7de; overflow: hidden;
  }

  /* ── Responsividade — Tablet (≤1024px) ──────────────────── */
  @media (max-width: 1024px) {
    .hero-title    { font-size: 26px !important; }
    .hero-subtitle { font-size: 13px; }
    .block-container {
      padding-left: 1rem !important;
      padding-right: 1rem !important;
    }
  }

  /* ── Responsividade — Mobile (≤768px) ───────────────────── */
  @media (max-width: 768px) {
    .hero          { padding: 18px 16px 16px 16px !important; }
    .hero-title    { font-size: 20px !important; }
    .hero-emoji    { font-size: 24px !important; }
    .hero-subtitle { font-size: 12px; margin-bottom: 10px; }
    .hero-badge    { font-size: 10px !important; padding: 3px 8px !important; }

    [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
    [data-testid="column"] {
      min-width: calc(50% - 0.5rem) !important;
      flex: 0 0 calc(50% - 0.5rem) !important;
    }
    .kpi-value { font-size: 18px !important; }
    .kpi-label { font-size: 9px !important; }
    .kpi-icon  { width: 28px !important; height: 28px !important; font-size: 13px !important; }

    .stTabs [data-baseweb="tab-list"] {
      gap: 2px !important; padding: 4px !important;
      flex-wrap: wrap !important; overflow-x: auto !important;
    }
    .stTabs [data-baseweb="tab"] {
      font-size: 11px !important; padding: 6px 8px !important;
      flex: 1 1 auto !important; text-align: center !important;
    }
    .block-container {
      padding-left: 0.5rem !important;
      padding-right: 0.5rem !important;
    }
  }

  /* ── Responsividade — Mobile pequeno (≤480px) ────────────── */
  @media (max-width: 480px) {
    [data-testid="column"] {
      min-width: 100% !important;
      flex: 0 0 100% !important;
    }
    .hero-title  { font-size: 17px !important; }
    .hero-badges { flex-wrap: wrap; gap: 4px; }
    .hero-badge  { font-size: 9px !important; }
    .stTabs [data-baseweb="tab"] {
      font-size: 10px !important;
      padding: 5px 6px !important;
    }
  }
</style>
"""

# CSS minimalista para páginas secundárias (sem KPI cards e hero)
_CSS_PAGE = """
<style>
  [data-testid="stAppViewContainer"] { background-color: #f6f8fa; }
  [data-testid="stSidebar"]          { background-color: #ffffff; }
  [data-testid="stSidebar"] *        { color: #24292f !important; }
  h1, h2, h3                         { color: #1a3a5c; }
  p, span, label                     { color: #24292f; }
  [data-testid="stCaption"]          { color: #57606a; }
  .block-container { padding-top: 2rem !important; max-width: 1400px; }
</style>
"""


_DARK_CSS = """
  [data-theme="dark"] [data-testid="stAppViewContainer"] { background-color: #0d1117 !important; }
  [data-theme="dark"] [data-testid="stSidebar"]          { background-color: #161b22 !important; border-right: 1px solid #30363d !important; }
  [data-theme="dark"] [data-testid="stSidebar"] *        { color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stHeader"]           { background-color: #0d1117 !important; }
  [data-theme="dark"] [data-testid="stMain"]             { background-color: #0d1117 !important; }
  [data-theme="dark"] .block-container                   { background-color: #0d1117 !important; }
  [data-theme="dark"] h1, [data-theme="dark"] h2, [data-theme="dark"] h3 { color: #79c0ff !important; }
  [data-theme="dark"] p, [data-theme="dark"] span, [data-theme="dark"] label { color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stCaption"]          { color: #8b949e !important; }
  [data-theme="dark"] hr, [data-theme="dark"] [data-testid="stDivider"] { background: linear-gradient(90deg, transparent, #30363d, transparent) !important; }

  [data-theme="dark"] .kpi-card {
    background: linear-gradient(160deg, #161b22 0%, #1c2128 100%) !important;
    border-color: #30363d !important;
    box-shadow: 0 2px 8px rgba(0,0,0,.4) !important;
  }
  [data-theme="dark"] .kpi-card.kpi-selected {
    background: linear-gradient(160deg, #1c2840 0%, #1c2128 100%) !important;
  }
  [data-theme="dark"] .kpi-label { color: #8b949e !important; }
  [data-theme="dark"] .kpi-value { color: #79c0ff !important; }
  [data-theme="dark"] .kpi-icon  { background: rgba(255,255,255,.04) !important; border-color: #30363d !important; }

  [data-theme="dark"] .hero {
    background: linear-gradient(135deg, #161b22 0%, #1c2128 60%, #1c2840 100%) !important;
    border-color: #30363d !important;
  }
  [data-theme="dark"] .hero-title    { color: #e6edf3 !important; }
  [data-theme="dark"] .hero-subtitle { color: #8b949e !important; }
  [data-theme="dark"] .hero-badge    { background: rgba(255,255,255,.04) !important; border-color: #30363d !important; color: #8b949e !important; }
  [data-theme="dark"] .hero-badge.accent  { color: #58a6ff !important; }
  [data-theme="dark"] .hero-badge.success { color: #3fb950 !important; }

  [data-theme="dark"] .stTabs [data-baseweb="tab-list"]   { background: rgba(255,255,255,.03) !important; border-color: #30363d !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab"]        { color: #8b949e !important; }
  [data-theme="dark"] .stTabs [data-baseweb="tab"]:hover  { background: rgba(255,255,255,.06) !important; border-color: #30363d !important; color: #e6edf3 !important; }
  [data-theme="dark"] .stTabs [aria-selected="true"]      { background: rgba(224,123,84,.12) !important; border-color: rgba(224,123,84,.3) !important; color: #e6edf3 !important; }

  /* Expanders — header e body */
  [data-theme="dark"] [data-testid="stExpander"]                              { background: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-testid="stExpander"] details,
  [data-theme="dark"] [data-testid="stExpander"] details > div,
  [data-theme="dark"] [data-testid="stExpander"] details > div > div          { background: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] summary                                                  { background-color: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-testid="stSidebar"] summary                       { background-color: #1c2333 !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-testid="stSidebar"] [data-testid="stExpander"]    { border-color: #30363d !important; background: #161b22 !important; }

  [data-theme="dark"] [data-testid="stButton"] button     { background-color: #21262d !important; border-color: #30363d !important; color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stButton"] button[kind="primary"] { background-color: #2B7BB9 !important; border-color: #2B7BB9 !important; color: #fff !important; }
  /* Botão de download */
  [data-theme="dark"] [data-testid="stDownloadButton"] button { background-color: #21262d !important; border-color: #30363d !important; color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stDownloadButton"] button:hover { background-color: #2d333b !important; border-color: #58a6ff !important; }

  /* Pills — seletores reais do Streamlit */
  [data-theme="dark"] [data-testid="stBaseButton-pills"]                      { background: #21262d !important; border-color: #30363d !important; color: #c9d1d9 !important; }
  [data-theme="dark"] [data-testid="stBaseButton-pills"]:hover                { background: #2d333b !important; color: #e6edf3 !important; }
  [data-theme="dark"] [data-testid="stBaseButton-pillsActive"]                { background: rgba(43,123,185,.25) !important; border-color: rgba(43,123,185,.5) !important; color: #58a6ff !important; }

  /* Multiselect tags — especificidade maior que a regra light (span + atributo) */
  [data-theme="dark"] [data-testid="stMultiSelect"] span[data-baseweb="tag"] { background-color: #1f3b5a !important; border: 1px solid rgba(88,166,255,.4) !important; border-radius: 999px !important; }
  [data-theme="dark"] span[data-baseweb="tag"]                                { background-color: #1f3b5a !important; border: 1px solid rgba(88,166,255,.4) !important; }
  [data-theme="dark"] [data-testid="stMultiSelect"] span[data-baseweb="tag"] span,
  [data-theme="dark"] [data-testid="stMultiSelect"] span[data-baseweb="tag"] button { color: #cae0f5 !important; }
  [data-theme="dark"] span[data-baseweb="tag"] span,
  [data-theme="dark"] span[data-baseweb="tag"] button                         { color: #cae0f5 !important; }
  [data-theme="dark"] [data-baseweb="tag"] svg *                              { fill: #8b949e !important; }

  [data-theme="dark"] iframe[title="streamlit_folium.st_folium"] { border-color: #30363d !important; }

  /* ── Modal / Dialog ──────────────────────────────────────── */
  [data-theme="dark"] [data-testid="stDialog"]                                { background-color: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-testid="stDialog"] > div                          { background-color: #161b22 !important; }
  [data-theme="dark"] [data-testid="stDialogContent"],
  [data-theme="dark"] [data-testid="stModal"]                                 { background-color: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] div[role="dialog"]                                      { background-color: #161b22 !important; border-color: #30363d !important; }
  [data-theme="dark"] div[role="dialog"] > div                                { background-color: #161b22 !important; }
  [data-theme="dark"] .stModal, [data-theme="dark"] .stDialog                { background-color: #161b22 !important; }
  /* Botão X fechar modal */
  [data-theme="dark"] [data-testid="stDialog"] button[kind="header"],
  [data-theme="dark"] div[role="dialog"] button[aria-label="Close"],
  [data-theme="dark"] div[role="dialog"] button                               { background-color: #21262d !important; border: 1px solid #58a6ff !important; color: #e6edf3 !important; }
  [data-theme="dark"] div[role="dialog"] button svg,
  [data-theme="dark"] div[role="dialog"] button svg path                      { fill: #e6edf3 !important; stroke: #e6edf3 !important; }

  /* Botão tema — adapta ao modo escuro */
  [data-theme="dark"] #_tb_theme_btn { background: rgba(22,27,34,.9) !important; border-color: #30363d !important; color: #e6edf3 !important; }

  /* ── Inputs / Selects / Multiselect container ────────────── */
  [data-theme="dark"] [data-baseweb="select"] > div:first-child,
  [data-theme="dark"] [data-baseweb="input"] > div { background-color: #21262d !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-baseweb="select"] input,
  [data-theme="dark"] [data-baseweb="input"] input  { color: #e6edf3 !important; background-color: transparent !important; }
  [data-theme="dark"] [data-baseweb="select"] [data-testid="stWidgetLabel"],
  [data-theme="dark"] [data-baseweb="popover"]       { background-color: #21262d !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-testid="stSelectbox"] [data-baseweb="select"] > div,
  [data-theme="dark"] [data-testid="stMultiSelect"] [data-baseweb="select"] > div { background-color: #21262d !important; border-color: #30363d !important; }
  /* Dropdown menu */
  [data-theme="dark"] [data-baseweb="popover"] [role="listbox"],
  [data-theme="dark"] [data-baseweb="menu"]           { background-color: #21262d !important; border-color: #30363d !important; }
  [data-theme="dark"] [data-baseweb="menu"] li         { color: #e6edf3 !important; }
  [data-theme="dark"] [data-baseweb="menu"] li:hover   { background-color: #30363d !important; }
  /* Slider */
  [data-theme="dark"] [data-testid="stSlider"] [data-baseweb="slider"] { background-color: #30363d !important; }
  /* Number/text inputs */
  [data-theme="dark"] [data-testid="stNumberInput"] input,
  [data-theme="dark"] [data-testid="stTextInput"] input { background-color: #21262d !important; border-color: #30363d !important; color: #e6edf3 !important; }

  /* ── Plotly — legenda e textos SVG ───────────────────────── */
  [data-theme="dark"] .js-plotly-plot .plotly .legend .bg                  { fill: #161b22 !important; stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .legend text                 { fill: #e6edf3 !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .g-gtitle text               { fill: #c9d1d9 !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .xtick text,
  [data-theme="dark"] .js-plotly-plot .plotly .ytick text                  { fill: #8b949e !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .g-xtitle text,
  [data-theme="dark"] .js-plotly-plot .plotly .g-ytitle text               { fill: #8b949e !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .annotation-text             { fill: #e6edf3 !important; }
  /* Rótulos de texto dentro das barras */
  [data-theme="dark"] .js-plotly-plot .plotly .bars .textpoint text,
  [data-theme="dark"] .js-plotly-plot .plotly .points text                 { fill: #ffffff !important; }
  /* Fundo do paper/plot */
  [data-theme="dark"] .js-plotly-plot .plotly .bglayer rect                { fill: #0d1117 !important; }
  /* Gridlines */
  [data-theme="dark"] .js-plotly-plot .plotly .gridlayer path              { stroke: #21262d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .zerolinelayer path          { stroke: #30363d !important; }

  /* ── Plotly — Modebar (barra de ferramentas do gráfico) ──── */
  [data-theme="dark"] .js-plotly-plot .modebar                             { background: #21262d !important; border-radius: 6px !important; border: 1px solid #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .modebar-btn path                    { fill: #8b949e !important; }
  [data-theme="dark"] .js-plotly-plot .modebar-btn:hover path              { fill: #e6edf3 !important; }
  [data-theme="dark"] .js-plotly-plot .modebar-btn.active path             { fill: #58a6ff !important; }
  [data-theme="dark"] .js-plotly-plot .modebar-group                       { border-color: #30363d !important; }

  /* ── Plotly — Tooltip/Hover ───────────────────────────────── */
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer .hovertext rect  { fill: #21262d !important; stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer .hovertext path  { fill: #21262d !important; stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer .hovertext text  { fill: #e6edf3 !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer g path           { fill: #21262d !important; stroke: #30363d !important; }
  [data-theme="dark"] .js-plotly-plot .plotly .hoverlayer g text           { fill: #e6edf3 !important; }
"""

_THEME_TOGGLE_JS = """
<script>
(function() {
  var KEY = 'tb_dash_theme';
  var p = window.parent;

  function applyTheme(t) {
    p.document.documentElement.setAttribute('data-theme', t);
    p.localStorage.setItem(KEY, t);
    var btn = p.document.getElementById('_tb_theme_btn');
    if (btn) btn.innerHTML = t === 'dark' ? '☀️' : '🌙';
    if (btn) btn.title = t === 'dark' ? 'Modo claro' : 'Modo escuro';
  }

  function toggle() {
    var cur = p.document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(cur === 'dark' ? 'light' : 'dark');
  }

  function ensureStyle() {
    if (p.document.getElementById('_tb_dark_css')) return;
    var s = p.document.createElement('style');
    s.id = '_tb_dark_css';
    s.textContent = DARK_CSS_PLACEHOLDER;
    p.document.head.appendChild(s);
  }

  function ensureButton() {
    if (p.document.getElementById('_tb_theme_btn')) return;
    var btn = p.document.createElement('button');
    btn.id = '_tb_theme_btn';
    btn.onclick = toggle;
    var saved = p.localStorage.getItem(KEY) || 'light';
    btn.innerHTML = saved === 'dark' ? '☀️' : '🌙';
    btn.title = saved === 'dark' ? 'Modo claro' : 'Modo escuro';
    btn.style.cssText = [
      'position:fixed', 'top:8px', 'z-index:9999999',
      'width:32px', 'height:32px', 'border-radius:8px',
      'border:1px solid rgba(0,0,0,.15)', 'background:rgba(255,255,255,.92)',
      'backdrop-filter:blur(8px)', 'cursor:pointer',
      'font-size:18px', 'line-height:1', 'padding:0',
      'box-shadow:0 1px 4px rgba(0,0,0,.15)',
      'transition:transform .12s,background .2s',
      'display:flex', 'align-items:center', 'justify-content:center'
    ].join(';');
    function _pos() {
      var vw = p.document.documentElement.clientWidth || p.innerWidth;
      btn.style.left = Math.max(0, vw - 122) + 'px';
    }
    _pos();
    p.addEventListener('resize', _pos);
    btn.onmouseover = function() { btn.style.transform = 'scale(1.1)'; };
    btn.onmouseout  = function() { btn.style.transform = 'scale(1)'; };
    p.document.body.appendChild(btn);
  }

  function init() {
    ensureStyle();
    var saved = p.localStorage.getItem(KEY) || 'light';
    applyTheme(saved);
    ensureButton();
  }

  if (p.document.readyState === 'complete') { init(); }
  else { p.addEventListener('load', init); }

  // Recriar botão após rerenders do Streamlit
  var obs = new p.MutationObserver(function() {
    ensureButton();
  });
  obs.observe(p.document.body, { childList: true });
})();
</script>
"""


def inject_css() -> None:
    """Injeta o CSS completo do dashboard (usar no app.py principal)."""
    import streamlit.components.v1 as components
    st.markdown(_CSS, unsafe_allow_html=True)
    # Injeta dark mode CSS + botão lua/sol via iframe com acesso ao parent
    dark_css_escaped = _DARK_CSS.replace('\n', ' ').replace("'", "\\'").replace('"', '\\"')
    js = _THEME_TOGGLE_JS.replace('DARK_CSS_PLACEHOLDER', f"'{dark_css_escaped}'")
    components.html(js, height=1, scrolling=False)


def inject_css_page() -> None:
    """Injeta CSS minimalista para páginas secundárias (usar em pages/)."""
    st.markdown(_CSS_PAGE, unsafe_allow_html=True)
