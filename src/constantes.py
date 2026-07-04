"""
constantes.py
─────────────
Mapeamentos, paletas de cores e configurações globais do dashboard.
Centraliza aqui tudo que é reutilizado em graficos.py e app.py.

SEM imports de streamlit/pandas — este módulo deve ser importável
sem efeitos colaterais pesados (reduz startup de ~1.3s para <0.05s).
"""

from pathlib import Path

# ── Caminhos ───────────────────────────────────────────────────────────────────
PASTA_DADOS  = Path("dados_dashboard")
PASTA        = PASTA_DADOS          # alias de compatibilidade
GEOJSON_PATH = PASTA_DADOS / "br_states.geojson"
SPEC_PATH    = "spec/dashboard_tb.json"

# Histórico pré-agregado (gerado por scripts/gerar_historico.py)
HIST_MENSAL      = PASTA_DADOS / "historico_mensal.csv"
HIST_ESTADUAL    = PASTA_DADOS / "historico_estadual.csv"
HIST_ANUAL       = PASTA_DADOS / "historico_anual.csv"
HIST_INDICADORES = PASTA_DADOS / "historico_indicadores.csv"
MUN_PARQUET      = PASTA_DADOS / "municipios.parquet"
MUN_URL = "https://raw.githubusercontent.com/kelvins/municipios-brasileiros/main/csv/municipios.csv"

ANO_ATUAL  = 2025
ANO_INICIO = 2001


def parquet_path(ano: int) -> Path:
    """Retorna o caminho do Parquet tratado para um dado ano."""
    return PASTA_DADOS / f"tuberculose_{ano}_tratado.parquet"


def anos_disponiveis() -> list[int]:
    """Detecta automaticamente quais anos têm Parquet tratado disponível."""
    arquivos = sorted(PASTA_DADOS.glob("tuberculose_*_tratado.parquet"), reverse=True)
    anos = []
    for f in arquivos:
        try:
            ano = int(f.stem.split("_")[1])
            if ano <= 2025:
                anos.append(ano)
        except (IndexError, ValueError):
            pass
    return anos if anos else [2025]


# -- Regioes do Brasil -> siglas dos estados ------------------------------------
REGIOES: dict[str, list[str]] = {
    "Norte":        ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste":     ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste":      ["ES", "MG", "RJ", "SP"],
    "Sul":          ["PR", "RS", "SC"],
}

# ── Mapeamento de estados → siglas ─────────────────────────────────────────────
UF_SIGLAS = {
    "Acre": "AC", "Alagoas": "AL", "Amapa": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceara": "CE", "Distrito Federal": "DF", "Espirito Santo": "ES",
    "Goias": "GO", "Maranhao": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Para": "PA", "Paraiba": "PB", "Parana": "PR",
    "Pernambuco": "PE", "Piaui": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondonia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "Sao Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
    # Com acentos
    "Amapá": "AP", "Ceará": "CE", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Pará": "PA", "Paraíba": "PB", "Piauí": "PI",
    "Rondônia": "RO", "São Paulo": "SP", "Paraná": "PR",
}

# ── Populações por estado — IBGE Censo 2022 ───────────────────────────────────
POP_ESTADO: dict[str, int] = {
    "AC":    906_876,  "AL":  3_127_683,  "AM":  4_269_995,
    "AP":    877_613,  "BA": 14_873_064,  "CE":  9_240_580,
    "DF":  3_094_325,  "ES":  4_108_508,  "GO":  7_206_589,
    "MA":  7_114_598,  "MG": 21_292_666,  "MS":  2_839_188,
    "MT":  3_658_813,  "PA":  8_777_124,  "PB":  4_059_905,
    "PE":  9_674_793,  "PI":  3_281_480,  "PR": 11_597_484,
    "RJ": 17_366_189,  "RN":  3_302_406,  "RO":  1_590_011,
    "RR":    652_713,  "RS": 11_466_630,  "SC":  7_786_786,
    "SE":  2_338_474,  "SP": 46_649_132,  "TO":  1_607_363,
}
POP_BRASIL: int = sum(POP_ESTADO.values())

# ── Agravos associados ─────────────────────────────────────────────────────────
AGRAVOS = {
    "agravo_aids":            "AIDS/HIV",
    "agravo_alcoolismo":      "Alcoolismo",
    "agravo_diabetes":        "Diabetes",
    "agravo_doenca_mental":   "Doenca Mental",
    "agravo_drogas_ilicitas": "Drogas Ilicitas",
    "agravo_tabagismo":       "Tabagismo",
}

# ── Populações vulneráveis ─────────────────────────────────────────────────────
POPULACOES = {
    "populacao_privada_liberdade": "Privada de Liberdade",
    "populacao_situacao_rua":      "Situacao de Rua",
    "populacao_imigrante":         "Imigrante",
    "profissional_saude":          "Profissional de Saude",
    "beneficiario_governo":        "Beneficiario Prog. Social",
}

# ── Normalização de desfechos ──────────────────────────────────────────────────
NORMALIZAR_DESFECHO = {
    "Nao informado":           "Em acompanhamento",
    "Não informado":           "Em acompanhamento",
    "Óbito por TB":            "Obito por TB",
    "Óbito por outras causas": "Obito por outras causas",
    "Mudança de Esquema":      "Mudanca de Esquema",
    "Abandono Primário":       "Abandono Primario",
    "Transferência":           "Transferencia",
    "Falência":                "Falencia",
}

# ── Paletas de cores ───────────────────────────────────────────────────────────
CORES_DESFECHOS = {
    "Cura":                    "#2ea043",
    "Em acompanhamento":       "#388bfd",
    "Transferencia":           "#58a6ff",
    "Mudanca de Esquema":      "#d29922",
    "Abandono Primario":       "#bb8009",
    "Abandono":                "#f0883e",
    "Falencia":                "#f85149",
    "TB-DR":                   "#a371f7",
    "Obito por outras causas": "#8957e5",
    "Obito por TB":            "#da3633",
}

CORES_FORMA = {
    "Pulmonar":                 "#58a6ff",
    "Extrapulmonar":            "#a371f7",
    "Pulmonar + Extrapulmonar": "#d2a8ff",
}

ESCALA_MAPA = [
    [0.0,  "#eaf4fc"], [0.15, "#a5d6ff"],
    [0.35, "#58a6ff"], [0.55, "#2B7BB9"],
    [0.75, "#1a4a80"], [1.0,  "#1a3a5c"],
]

# ── Paleta TB — semântica epidemiológica ──────────────────────────────────────
TB_COLORS = {
    "Cura":                     "#2ea043",
    "Óbito por TB":             "#da3633",
    "Obito por TB":             "#da3633",
    "Óbito outras causas":      "#8957e5",
    "Obito por outras causas":  "#8957e5",
    "Abandono":                 "#d29922",
    "Abandono Primario":        "#bb8009",
    "Abandono Primário":        "#bb8009",
    "Falencia":                 "#f85149",
    "Falência":                 "#f85149",
    "TB-DR":                    "#cf222e",
    "Transferencia":            "#1f6feb",
    "Transferência":            "#1f6feb",
    "Mudanca de Esquema":       "#ffa657",
    "Mudança de Esquema":       "#ffa657",
    "Mudança Diagnóstico":      "#f0b342",
    "Em acompanhamento":        "#388bfd",
    "Positivo":                 "#da3633",
    "Negativo":                 "#3fb950",
    "Em andamento":             "#d29922",
    "Não realizado":            "#a371f7",
    "Nao realizado":            "#a371f7",
    "Masculino":                "#58a6ff",
    "Feminino":                 "#f778ba",
    "Sim":                      "#da3633",
    "Não":                      "#3fb950",
    "Nao":                      "#3fb950",
    "Ignorado":                 "#d29922",
    "Positiva":                 "#da3633",
    "Negativa":                 "#3fb950",
    "Não realizada":            "#a371f7",
    "Nao realizada":            "#a371f7",
    "Não se aplica":            "#79c0ff",
    "Detectável sensível":      "#d29922",
    "Detectavel sensivel":      "#d29922",
    "Detectável resistente":    "#da3633",
    "Detectavel resistente":    "#da3633",
    "Não detectável":           "#3fb950",
    "Nao detectavel":           "#3fb950",
    "Inconclusivo":             "#d2a8ff",
    "Branca":                   "#79c0ff",
    "Preta":                    "#a371f7",
    "Parda":                    "#d2a8ff",
    "Amarela":                  "#f0b342",
    "Indígena":                 "#3fb950",
    "Indigena":                 "#3fb950",
    "Pulmonar":                       "#58a6ff",
    "Extrapulmonar":                  "#a371f7",
    "Pulmonar + Extrapulmonar":       "#d2a8ff",
    "Caso Novo":                "#3fb950",
    "Recidiva":                 "#d29922",
    "Reingresso Abandono":      "#f0883e",
    "Não Sabe":                 "#d29922",
    "Nao Sabe":                 "#d29922",
    "Pos-obito":                "#a40e26",
    "Pós-óbito":                "#a40e26",
}

# Paletas sequenciais para mapas
TB_SEQ_INCIDENCIA = ["#eaf4fc", "#a5d6ff", "#58a6ff", "#2B7BB9", "#1a4a80", "#1a3a5c"]
TB_SEQ_MORTAL     = ["#fff0ee", "#ffa198", "#f85149", "#da3633", "#a40e26", "#67060c"]

# Sequência para categorias sem cor semântica definida
CORES = ["#58a6ff", "#a371f7", "#3fb950", "#d29922", "#f778ba", "#79c0ff", "#d2a8ff"]


def tb_color_map(labels: list[str]) -> dict:
    """Mapeia lista de labels para cores TB (fallback determinístico)."""
    mapping = {}
    fallback_idx = 0
    for lbl in labels:
        if lbl in TB_COLORS:
            mapping[lbl] = TB_COLORS[lbl]
        else:
            mapping[lbl] = CORES[fallback_idx % len(CORES)]
            fallback_idx += 1
    return mapping


# ── Template Plotly padronizado ────────────────────────────────────────────────
PLOTLY_TEMPLATE = {
    "layout": {
        "font": {"family": "Inter, -apple-system, system-ui, sans-serif",
                 "color": "#24292f", "size": 12},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor":  "rgba(0,0,0,0)",
        "title": {"font": {"size": 15, "color": "#1a3a5c", "family": "Inter, sans-serif"},
                  "x": 0.02, "xanchor": "left", "pad": {"t": 10, "b": 5}},
        "xaxis": {"gridcolor": "#f0f2f5", "linecolor": "#d0d7de",
                  "tickfont": {"color": "#57606a", "size": 11},
                  "title_font": {"color": "#24292f", "size": 12}},
        "yaxis": {"gridcolor": "#f0f2f5", "linecolor": "#d0d7de",
                  "tickfont": {"color": "#57606a", "size": 11},
                  "title_font": {"color": "#24292f", "size": 12}},
        "legend": {"bgcolor": "rgba(255,255,255,.95)", "bordercolor": "#d0d7de",
                   "borderwidth": 1, "font": {"color": "#24292f", "size": 11}},
        "hoverlabel": {"bgcolor": "rgba(255,255,255,.98)", "bordercolor": "#d0d7de",
                       "font": {"color": "#24292f", "family": "Inter, sans-serif"}},
        "margin": {"l": 50, "r": 30, "t": 50, "b": 50},
    }
}

# Mantido para compatibilidade com graficos.py / mapa_interativo.py
BG = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor":  "rgba(0,0,0,0)",
}
HOVER_LABEL = dict(
    bgcolor="rgba(255,255,255,.98)",
    bordercolor="#d0d7de",
    font=dict(size=13, color="#24292f"),
)
PLOTLY_CFG = {"scrollZoom": False, "displayModeBar": False}


# ── Alturas padrão de gráficos ─────────────────────────────────────────────────
H_SMALL  = 300
H_MEDIUM = 380
H_LARGE  = 480



# ── Colunas carregadas do Parquet pelo dashboard ───────────────────────────────
# Subconjunto das 89 colunas do SINAN — exclui campos nunca usados nas abas
# (transferências internas, resistências individuais, campos de controle SINAN).
# Reduz carga de memória em ~44% vs SELECT *.
COLUNAS_DASHBOARD = (
    "ano_notificacao", "data_notificacao", "data_diagnostico",
    "data_inicio_tratamento", "data_encerramento",
    "estado_notificacao", "municipio_notificacao", "uf_residencia", "municipio_residencia",
    "sexo", "raca_cor", "idade_anos", "escolaridade", "ano_nascimento",
    "tipo_entrada", "forma", "extrapulmonar",
    "situacao_encerramento",
    "status_hiv", "uso_antirretroviral",
    "raio_x_torax", "teste_tuberculinico",
    "baciloscopia_primeira_amostra", "cultura_escarro", "histopatologia",
    "teste_molecular", "teste_sensibilidade",
    "tratamento_supervisionado",
    "baciloscopia_mes_1", "baciloscopia_mes_2", "baciloscopia_mes_3",
    "baciloscopia_mes_4", "baciloscopia_mes_5", "baciloscopia_mes_6",
    "baciloscopia_apos_6_meses",
    "agravo_aids", "agravo_alcoolismo", "agravo_diabetes",
    "agravo_doenca_mental", "agravo_drogas_ilicitas", "agravo_tabagismo", "agravo_outros",
    "populacao_privada_liberdade", "populacao_situacao_rua",
    "profissional_saude", "populacao_imigrante", "beneficiario_governo",
    "numero_contatos", "numero_contatos_examinados",
    "tipo_notificacao",
)

# ── Colunas expostas na Análise Livre ─────────────────────────────────────────
COLUNAS_ANALISE = (
    "estado_notificacao", "municipio_notificacao", "uf_residencia",
    "ano_notificacao", "data_notificacao", "data_diagnostico",
    "data_inicio_tratamento", "data_encerramento",
    "idade_anos", "sexo", "raca_cor", "escolaridade",
    "tipo_entrada", "forma", "situacao_encerramento",
    "status_hiv", "uso_antirretroviral", "raio_x_torax",
    "baciloscopia_primeira_amostra", "cultura_escarro",
    "histopatologia", "teste_molecular", "teste_sensibilidade",
    "tratamento_supervisionado",
    "baciloscopia_mes_1", "baciloscopia_mes_2", "baciloscopia_mes_3",
    "baciloscopia_mes_4", "baciloscopia_mes_5", "baciloscopia_mes_6",
    "baciloscopia_apos_6_meses",
    "agravo_aids", "agravo_alcoolismo", "agravo_diabetes",
    "agravo_doenca_mental", "agravo_drogas_ilicitas", "agravo_tabagismo",
    "populacao_privada_liberdade", "populacao_situacao_rua",
    "profissional_saude", "populacao_imigrante", "beneficiario_governo",
    "numero_contatos", "numero_contatos_examinados",
)


# ── Helpers puros (sem dependência de streamlit) ───────────────────────────────
def pct(valor, total):
    """Retorna percentual formatado (ex: '12.3%') ou '—' se total=0."""
    return f"{valor/total*100:.1f}%" if total and total > 0 else "—"


def _delta_badge(cur, prev, good_when_up=False):
    """Gera HTML do badge de variação para KPI cards."""
    try:
        cur, prev = float(cur), float(prev)
        if prev == 0:
            return ""
        diff_pct = (cur - prev) / prev * 100
        if abs(diff_pct) < 0.1:
            return '<span class="kpi-delta flat">≈ estável vs ano anterior</span>'
        arrow = "↑" if diff_pct > 0 else "↓"
        cls   = "good" if (diff_pct > 0) == good_when_up else "bad"
        return f'<span class="kpi-delta {cls}">{arrow} {abs(diff_pct):.1f}% vs ano anterior</span>'
    except Exception:
        return ""


def kpi_card_html(title, value, delta_html, icon, accent, selected):
    """Monta o HTML de um KPI card."""
    sel   = "kpi-selected" if selected else ""
    delta = delta_html.strip() if delta_html else ""
    return (
        f'<div class="kpi-card {sel}" style="--accent:{accent};">'
        f'<div class="kpi-inner">'
        f'<div class="kpi-bar"></div>'
        f'<div class="kpi-body">'
        f'<div class="kpi-label">{title}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'{delta}'
        f'</div>'
        f'<div class="kpi-icon">{icon}</div>'
        f'</div>'
        f'</div>'
    )


