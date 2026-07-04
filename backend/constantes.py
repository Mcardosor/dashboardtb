"""
constantes.py — Constantes do backend (portadas de src/constantes.py).

Sem dependências pesadas: apenas pathlib. Importável em <10ms.
"""

from pathlib import Path

# ── Caminhos ──────────────────────────────────────────────────────────────────
RAIZ         = Path(__file__).resolve().parents[1]
PASTA_DADOS  = RAIZ / "dados_dashboard"
GEO_CACHE    = PASTA_DADOS / "_geo_cache"

HIST_MENSAL      = PASTA_DADOS / "historico_mensal.csv"
HIST_ESTADUAL    = PASTA_DADOS / "historico_estadual.csv"
HIST_ANUAL       = PASTA_DADOS / "historico_anual.csv"
HIST_INDICADORES = PASTA_DADOS / "historico_indicadores.csv"

ANO_INICIO = 2001

# ── Regiões do Brasil → siglas ────────────────────────────────────────────────
REGIOES: dict[str, list[str]] = {
    "Norte":        ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste":     ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Sudeste":      ["ES", "MG", "RJ", "SP"],
    "Sul":          ["PR", "RS", "SC"],
}

# ── Nome do estado (como aparece no SINAN) → sigla ────────────────────────────
UF_SIGLAS = {
    "Acre": "AC", "Alagoas": "AL", "Amapa": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceara": "CE", "Distrito Federal": "DF", "Espirito Santo": "ES",
    "Goias": "GO", "Maranhao": "MA", "Mato Grosso": "MT", "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG", "Para": "PA", "Paraiba": "PB", "Parana": "PR",
    "Pernambuco": "PE", "Piaui": "PI", "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN", "Rio Grande do Sul": "RS", "Rondonia": "RO",
    "Roraima": "RR", "Santa Catarina": "SC", "Sao Paulo": "SP",
    "Sergipe": "SE", "Tocantins": "TO",
    # Variantes com acento
    "Amapá": "AP", "Ceará": "CE", "Espírito Santo": "ES", "Goiás": "GO",
    "Maranhão": "MA", "Pará": "PA", "Paraíba": "PB", "Piauí": "PI",
    "Rondônia": "RO", "São Paulo": "SP", "Paraná": "PR",
}

# Sigla → nome canônico (com acentos, para exibição)
UF_NOMES: dict[str, str] = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul", "RO": "Rondônia",
    "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}

# Sigla → todos os nomes que aparecem nos dados (com e sem acento)
UF_VARIANTES: dict[str, list[str]] = {}
for _nome, _sigla in UF_SIGLAS.items():
    UF_VARIANTES.setdefault(_sigla, []).append(_nome)

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

# ── Tipos de entrada que entram no coeficiente de incidência ──────────────────
# Caderno de Indicadores MS: Caso Novo + Não Sabe + Pós-óbito.
TIPOS_INCIDENCIA = ("Caso Novo", "Não Sabe", "Nao Sabe", "Pós-óbito", "Pos-obito")

# ── Agravos associados ────────────────────────────────────────────────────────
AGRAVOS = {
    "agravo_aids":            "AIDS/HIV",
    "agravo_alcoolismo":      "Alcoolismo",
    "agravo_diabetes":        "Diabetes",
    "agravo_doenca_mental":   "Doença Mental",
    "agravo_drogas_ilicitas": "Drogas Ilícitas",
    "agravo_tabagismo":       "Tabagismo",
}

# ── Populações vulneráveis ────────────────────────────────────────────────────
POPULACOES = {
    "populacao_privada_liberdade": "Privada de Liberdade",
    "populacao_situacao_rua":      "Situação de Rua",
    "populacao_imigrante":         "Imigrante",
    "profissional_saude":          "Profissional de Saúde",
    "beneficiario_governo":        "Beneficiário Prog. Social",
}

# ── Desfechos: normalização para forma canônica (acentuada) ───────────────────
# Os Parquets contêm variantes com e sem acento conforme o ano de origem.
# 'Não informado' vira 'Em acompanhamento' (caso ainda aberto no SINAN).
DESFECHO_CANONICO = {
    "Nao informado":           "Em acompanhamento",
    "Não informado":           "Em acompanhamento",
    "Obito por TB":            "Óbito por TB",
    "Óbito por TB":            "Óbito por TB",
    "Obito por outras causas": "Óbito por outras causas",
    "Óbito por outras causas": "Óbito por outras causas",
    "Mudanca de Esquema":      "Mudança de Esquema",
    "Mudança de Esquema":      "Mudança de Esquema",
    "Abandono Primario":       "Abandono Primário",
    "Abandono Primário":       "Abandono Primário",
    "Transferencia":           "Transferência",
    "Transferência":           "Transferência",
    "Falencia":                "Falência",
    "Falência":                "Falência",
}

# Desfecho canônico → grupo (visão de coorte em 4 categorias)
DESFECHO_GRUPO = {
    "Cura":                    "Cura",
    "Abandono":                "Interrupção",
    "Abandono Primário":       "Interrupção",
    "Óbito por TB":            "Óbito",
    "Óbito por outras causas": "Óbito",
    "Transferência":           "Não avaliado",
    "Mudança de Esquema":      "Não avaliado",
    "TB-DR":                   "Não avaliado",
    "Falência":                "Não avaliado",
    "Em acompanhamento":       "Não avaliado",
}

# ── Colunas expostas no export CSV (Análise Livre) ────────────────────────────
COLUNAS_EXPORT = (
    "estado_notificacao", "municipio_notificacao", "uf_residencia",
    "ano_notificacao", "data_notificacao", "data_diagnostico",
    "data_inicio_tratamento", "data_encerramento",
    "idade_anos", "sexo", "raca_cor", "escolaridade",
    "tipo_entrada", "forma", "situacao_encerramento",
    "status_hiv", "uso_antirretroviral", "raio_x_torax",
    "baciloscopia_primeira_amostra", "cultura_escarro",
    "histopatologia", "teste_molecular", "teste_sensibilidade",
    "tratamento_supervisionado",
    "agravo_aids", "agravo_alcoolismo", "agravo_diabetes",
    "agravo_doenca_mental", "agravo_drogas_ilicitas", "agravo_tabagismo",
    "populacao_privada_liberdade", "populacao_situacao_rua",
    "profissional_saude", "populacao_imigrante", "beneficiario_governo",
    "numero_contatos", "numero_contatos_examinados",
)

# ── Faixas etárias da pirâmide ────────────────────────────────────────────────
FAIXAS_ETARIAS = (
    "0-4", "5-9", "10-14", "15-19", "20-29", "30-39",
    "40-49", "50-59", "60-69", "70-79", "80+",
)
