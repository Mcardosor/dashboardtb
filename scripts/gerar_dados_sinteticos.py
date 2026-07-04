"""
gerar_dados_sinteticos.py
--------------------------
Gera um Parquet sintético que imita a estrutura e as distribuições
do SINAN TB (silver.sinan_tube) para testes offline do dashboard.

O arquivo gerado já está no formato _tratado (tipos otimizados),
dispensando o conectar_banco.py e o preparar_dados.py.

Uso:
    python scripts/gerar_dados_sinteticos.py           # 2025, 100 000 registros
    python scripts/gerar_dados_sinteticos.py 2024      # ano específico
    python scripts/gerar_dados_sinteticos.py 2023 2025 # intervalo de anos
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PASTA = Path("dados_dashboard")
PASTA.mkdir(exist_ok=True)

RNG = np.random.default_rng(42)

# ── CLI ───────────────────────────────────────────────────────────────────────
args = sys.argv[1:]
if len(args) == 0:
    anos = [2025]
elif len(args) == 1:
    anos = [int(args[0])]
elif len(args) == 2:
    anos = list(range(int(args[0]), int(args[1]) + 1))
else:
    print("Uso: python gerar_dados_sinteticos.py [ano_inicio] [ano_fim]")
    sys.exit(1)

N_REGISTROS = 100_000

# ── Distribuições realistas ───────────────────────────────────────────────────
ESTADOS = [
    ("Sao Paulo",            "SP", 0.19),
    ("Rio de Janeiro",       "RJ", 0.14),
    ("Amazonas",             "AM", 0.07),
    ("Para",                 "PA", 0.07),
    ("Bahia",                "BA", 0.06),
    ("Ceara",                "CE", 0.05),
    ("Minas Gerais",         "MG", 0.05),
    ("Pernambuco",           "PE", 0.05),
    ("Rio Grande do Sul",    "RS", 0.04),
    ("Mato Grosso",          "MT", 0.03),
    ("Maranhao",             "MA", 0.03),
    ("Parana",               "PR", 0.03),
    ("Espirito Santo",       "ES", 0.02),
    ("Rondonia",             "RO", 0.02),
    ("Goias",                "GO", 0.02),
    ("Alagoas",              "AL", 0.02),
    ("Santa Catarina",       "SC", 0.02),
    ("Rio Grande do Norte",  "RN", 0.02),
    ("Paraiba",              "PB", 0.01),
    ("Piaui",                "PI", 0.01),
    ("Mato Grosso do Sul",   "MS", 0.01),
    ("Tocantins",            "TO", 0.01),
    ("Acre",                 "AC", 0.01),
    ("Roraima",              "RR", 0.01),
    ("Amapa",                "AP", 0.01),
    ("Sergipe",              "SE", 0.01),
    ("Distrito Federal",     "DF", 0.01),
]

# ~3 municípios por estado no sintético (suficiente para testar o mapa)
MUNICIPIOS_POR_UF = {
    "SP": ["Sao Paulo", "Campinas", "Santos"],
    "RJ": ["Rio de Janeiro", "Niteroi", "Duque de Caxias"],
    "AM": ["Manaus", "Parintins", "Itacoatiara"],
    "PA": ["Belem", "Santarem", "Ananindeua"],
    "BA": ["Salvador", "Feira de Santana", "Vitoria da Conquista"],
    "CE": ["Fortaleza", "Caucaia", "Juazeiro do Norte"],
    "MG": ["Belo Horizonte", "Contagem", "Uberlandia"],
    "PE": ["Recife", "Caruaru", "Olinda"],
    "RS": ["Porto Alegre", "Canoas", "Pelotas"],
    "MT": ["Cuiaba", "Varzea Grande", "Rondonopolis"],
    "MA": ["Sao Luis", "Imperatriz", "Timon"],
    "PR": ["Curitiba", "Londrina", "Maringa"],
    "ES": ["Vitoria", "Vila Velha", "Cariacica"],
    "RO": ["Porto Velho", "Ji-Parana", "Ariquemes"],
    "GO": ["Goiania", "Aparecida de Goiania", "Anapolis"],
    "AL": ["Maceio", "Arapiraca", "Palmeira dos Indios"],
    "SC": ["Florianopolis", "Joinville", "Blumenau"],
    "RN": ["Natal", "Mossoro", "Parnamirim"],
    "PB": ["Joao Pessoa", "Campina Grande", "Santa Rita"],
    "PI": ["Teresina", "Parnaiba", "Picos"],
    "MS": ["Campo Grande", "Dourados", "Tres Lagoas"],
    "TO": ["Palmas", "Araguaina", "Gurupi"],
    "AC": ["Rio Branco", "Cruzeiro do Sul", "Sena Madureira"],
    "RR": ["Boa Vista", "Caracarai", "Rorainopolis"],
    "AP": ["Macapa", "Santana", "Laranjal do Jari"],
    "SE": ["Aracaju", "Nossa Senhora do Socorro", "Lagarto"],
    "DF": ["Brasilia", "Ceilandia", "Taguatinga"],
}

NOMES_ESTADO = [e[0] for e in ESTADOS]
PESOS_ESTADO = np.array([e[2] for e in ESTADOS])
PESOS_ESTADO /= PESOS_ESTADO.sum()
UF_POR_NOME = {e[0]: e[1] for e in ESTADOS}

SIM_NAO = ["Sim", "Não", "Ignorado", "Não informado"]
SIM_NAO_PESOS = [0.10, 0.75, 0.08, 0.07]

BACI_VALS = ["Positivo", "Negativo", "Não realizado", "Não informado", "Ignorado"]
BACI_PESOS = [0.35, 0.25, 0.25, 0.10, 0.05]

MES_VALS = ["Positivo", "Negativo", "Não realizado", "Não informado"]
MES_PESOS = [0.20, 0.40, 0.30, 0.10]

RESIST_VALS = ["Sensível", "Resistente", "Não realizado", "Não informado"]
RESIST_PESOS = [0.50, 0.05, 0.35, 0.10]


def escolher(valores, pesos, n):
    return RNG.choice(valores, size=n, p=np.array(pesos) / sum(pesos))


def gerar_ano(ano: int, n: int) -> pd.DataFrame:
    estados = RNG.choice(NOMES_ESTADO, size=n, p=PESOS_ESTADO)

    # Municipio conforme estado
    municipios = np.array([
        RNG.choice(MUNICIPIOS_POR_UF.get(UF_POR_NOME.get(e, "SP"), ["Municipio"])) for e in estados
    ])

    # Datas distribuídas ao longo do ano
    inicio_ano = pd.Timestamp(f"{ano}-01-01")
    dias = RNG.integers(0, 365, size=n)
    datas_notif = pd.to_datetime(inicio_ano) + pd.to_timedelta(dias, unit="D")
    datas_diag  = datas_notif - pd.to_timedelta(RNG.integers(0, 30, size=n), unit="D")
    datas_trat  = datas_notif + pd.to_timedelta(RNG.integers(0, 14, size=n), unit="D")
    datas_enc   = datas_trat  + pd.to_timedelta(RNG.integers(180, 365, size=n), unit="D")

    # Idade: distribuição realista (pico 20-50)
    idades_np = np.clip(
        (RNG.exponential(scale=20, size=n) + RNG.integers(10, 30, size=n)).astype(int),
        0, 90
    )
    idades = pd.array(idades_np, dtype="Int16")

    df = pd.DataFrame({
        "estado_notificacao":  pd.Categorical(estados),
        "municipio_notificacao": pd.Categorical(municipios),
        "uf_residencia":       pd.Categorical(np.vectorize(UF_POR_NOME.get)(estados)),
        "municipio_residencia": pd.Categorical(municipios),
        "regional_notificacao": pd.Categorical(
            escolher(["Regional Norte", "Regional Sul", "Regional Leste", "Regional Oeste"], [0.25]*4, n)
        ),
        "regional_residencia": pd.Categorical(
            escolher(["Regional Norte", "Regional Sul", "Regional Leste", "Regional Oeste"], [0.25]*4, n)
        ),
        "pais_residencia":     pd.Categorical(escolher(["Brasil", "Outros"], [0.97, 0.03], n)),
        "ano_notificacao":     pd.array([ano] * n, dtype="Int16"),
        "data_notificacao":    datas_notif,
        "data_diagnostico":    datas_diag,
        "data_digitacao":      datas_notif + pd.to_timedelta(RNG.integers(0, 7, size=n), unit="D"),
        "data_inicio_tratamento": datas_trat,
        "data_encerramento":   datas_enc,
        "data_mudanca_situacao": pd.NaT,
        "data_transferencia_us": pd.NaT,
        "data_transferencia_dm": pd.NaT,
        "data_transferencia_sm": pd.NaT,
        "data_transferencia_rs": pd.NaT,
        "data_transferencia_se": pd.NaT,
        "idade_anos":          idades,
        "ano_nascimento":      pd.array(ano - idades_np, dtype="Int16"),
        "sexo":                pd.Categorical(
            escolher(["Masculino", "Feminino", "Ignorado"], [0.65, 0.34, 0.01], n)
        ),
        "raca_cor":            pd.Categorical(
            escolher(["Parda", "Branca", "Preta", "Amarela", "Indigena", "Nao informado"],
                     [0.42, 0.28, 0.17, 0.02, 0.02, 0.09], n)
        ),
        "escolaridade":        pd.Categorical(
            escolher(["Ensino Medio", "Ensino Fundamental", "Analfabeto",
                      "Ensino Superior", "Nao informado"],
                     [0.30, 0.35, 0.10, 0.10, 0.15], n)
        ),
        "gestante":            pd.Categorical(
            escolher(SIM_NAO, [0.05, 0.70, 0.10, 0.15], n)
        ),
        "tipo_notificacao":    pd.Categorical(["Individual"] * n),
        "tipo_entrada":        pd.Categorical(
            escolher(["Caso Novo", "Recidiva", "Reingresso após Abandono",
                      "Transferência", "Pós-óbito", "Não informado"],
                     [0.72, 0.10, 0.08, 0.06, 0.01, 0.03], n)
        ),
        "tipo_unidade_notificante": pd.Categorical(
            escolher(["Unidade Básica de Saúde", "Hospital", "Ambulatório Especializado",
                      "Outros"], [0.45, 0.35, 0.15, 0.05], n)
        ),
        "tipo_instituicao":    pd.Categorical(
            escolher(["Pública", "Privada", "Filantrópica", "Não informado"],
                     [0.70, 0.15, 0.10, 0.05], n)
        ),
        "agravo":              pd.Categorical(["Tuberculose"] * n),
        "arquivo_origem":      pd.Categorical(["SINAN"] * n),
        "forma":               pd.Categorical(
            escolher(["Pulmonar", "Extrapulmonar", "Pulmonar + Extrapulmonar", "Não informado"],
                     [0.78, 0.14, 0.05, 0.03], n)
        ),
        "extrapulmonar":       pd.Categorical(
            escolher(["Pleural", "Ganglionar", "Meningoencefálica", "Renal",
                      "Óssea", "Outros", "Não informado", "Não se aplica"],
                     [0.30, 0.25, 0.10, 0.08, 0.07, 0.10, 0.05, 0.05], n)
        ),
        "extrapulmonar2":      pd.Categorical(
            escolher(["Não se aplica", "Pleural", "Ganglionar", "Outros"],
                     [0.70, 0.10, 0.10, 0.10], n)
        ),
        "situacao_encerramento": pd.Categorical(
            escolher(["Cura", "Abandono", "Transferência", "Óbito por TB",
                      "Óbito por outras causas", "Não informado", "Mudança de Esquema",
                      "TB-DR", "Abandono Primário", "Falência"],
                     [0.69, 0.09, 0.07, 0.04, 0.03, 0.03, 0.02, 0.01, 0.01, 0.01], n)
        ),
        "transferencia":       pd.Categorical(
            escolher(SIM_NAO, [0.07, 0.85, 0.04, 0.04], n)
        ),
        "status_hiv":          pd.Categorical(
            escolher(["Negativo", "Positivo", "Em andamento", "Não realizado", "Não informado"],
                     [0.48, 0.11, 0.14, 0.17, 0.10], n)
        ),
        "uso_antirretroviral": pd.Categorical(
            escolher(SIM_NAO, [0.08, 0.78, 0.05, 0.09], n)
        ),
        "raio_x_torax":        pd.Categorical(
            escolher(["Normal", "Suspeito", "Outras alterações", "Não realizado", "Não informado"],
                     [0.10, 0.55, 0.15, 0.10, 0.10], n)
        ),
        "teste_tuberculinico": pd.Categorical(
            escolher(["Não reator", "Reator fraco", "Reator forte", "Não realizado", "Não informado"],
                     [0.20, 0.15, 0.25, 0.30, 0.10], n)
        ),
        "baciloscopia_primeira_amostra": pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "baciloscopia_segunda_amostra":  pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "baciloscopia_outro_material":   pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "cultura_escarro":               pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "cultura_outro_material":        pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "histopatologia":                pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "teste_molecular":               pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "teste_sensibilidade":           pd.Categorical(escolher(BACI_VALS, BACI_PESOS, n)),
        "tratamento_supervisionado":     pd.Categorical(
            escolher(SIM_NAO, [0.45, 0.40, 0.08, 0.07], n)
        ),
        "tratamento_supervisionado_atual": pd.Categorical(
            escolher(SIM_NAO, [0.45, 0.40, 0.08, 0.07], n)
        ),
        "baciloscopia_mes_1": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "baciloscopia_mes_2": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "baciloscopia_mes_3": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "baciloscopia_mes_4": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "baciloscopia_mes_5": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "baciloscopia_mes_6": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "baciloscopia_apos_6_meses": pd.Categorical(escolher(MES_VALS, MES_PESOS, n)),
        "resistencia_rifampicina":    pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "resistencia_isoniazida":     pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "resistencia_etambutol":      pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "resistencia_pirazinamida":   pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "resistencia_etionamida":     pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "resistencia_estreptomicina": pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "resistencia_outras_drogas":  pd.Categorical(escolher(RESIST_VALS, RESIST_PESOS, n)),
        "agravo_aids":            pd.Categorical(escolher(SIM_NAO, [0.10, 0.75, 0.08, 0.07], n)),
        "agravo_alcoolismo":      pd.Categorical(escolher(SIM_NAO, [0.15, 0.70, 0.08, 0.07], n)),
        "agravo_diabetes":        pd.Categorical(escolher(SIM_NAO, [0.12, 0.73, 0.08, 0.07], n)),
        "agravo_doenca_mental":   pd.Categorical(escolher(SIM_NAO, [0.08, 0.77, 0.08, 0.07], n)),
        "agravo_outros":          pd.Categorical(escolher(SIM_NAO, [0.05, 0.80, 0.08, 0.07], n)),
        "agravo_drogas_ilicitas": pd.Categorical(escolher(SIM_NAO, [0.10, 0.75, 0.08, 0.07], n)),
        "agravo_tabagismo":       pd.Categorical(escolher(SIM_NAO, [0.18, 0.67, 0.08, 0.07], n)),
        "populacao_privada_liberdade": pd.Categorical(escolher(SIM_NAO, [0.08, 0.80, 0.06, 0.06], n)),
        "populacao_situacao_rua":      pd.Categorical(escolher(SIM_NAO, [0.06, 0.82, 0.06, 0.06], n)),
        "profissional_saude":          pd.Categorical(escolher(SIM_NAO, [0.04, 0.84, 0.06, 0.06], n)),
        "populacao_imigrante":         pd.Categorical(escolher(SIM_NAO, [0.03, 0.85, 0.06, 0.06], n)),
        "beneficiario_governo":        pd.Categorical(escolher(SIM_NAO, [0.25, 0.60, 0.08, 0.07], n)),
        "doenca_relacionada_trabalho": pd.Categorical(escolher(SIM_NAO, [0.04, 0.82, 0.07, 0.07], n)),
        "numero_contatos":             pd.array(RNG.integers(0, 10, size=n), dtype="Int16"),
        "numero_contatos_examinados":  pd.array(RNG.integers(0, 8, size=n),  dtype="Int16"),
        "situacao_9_meses":  pd.Categorical(
            escolher(["Em tratamento", "Curado", "Abandono", "Óbito", "Não informado"],
                     [0.15, 0.60, 0.10, 0.05, 0.10], n)
        ),
        "situacao_12_meses": pd.Categorical(
            escolher(["Em tratamento", "Curado", "Abandono", "Óbito", "Não informado"],
                     [0.05, 0.75, 0.08, 0.05, 0.07], n)
        ),
        "status_duplicidade": pd.Categorical(
            escolher(["Original", "Duplicado", "Não informado"], [0.95, 0.02, 0.03], n)
        ),
        "status_vinculacao":  pd.Categorical(
            escolher(["Vinculado", "Não vinculado", "Não informado"], [0.80, 0.15, 0.05], n)
        ),
        "estado_atendimento_atual":    pd.Categorical(estados),
        "municipio_atendimento_atual": pd.Categorical(municipios),
        "estado_segunda_notificacao":  pd.Categorical(["Não se aplica"] * n),
        "municipio_segunda_notificacao": pd.Categorical(["Não se aplica"] * n),
        "estado_transferencia":        pd.Categorical(["Não se aplica"] * n),
        "municipio_transferencia":     pd.Categorical(["Não se aplica"] * n),
        "cbo_ocupacao":                pd.Categorical(
            escolher(["711110", "512140", "516210", "Outros", "Não informado"],
                     [0.10, 0.10, 0.10, 0.40, 0.30], n)
        ),
    })
    return df


# ── Geração ───────────────────────────────────────────────────────────────────
for ano in anos:
    saida = PASTA / f"sinan_tube_{ano}_tratado.parquet"
    print(f"\n[{ano}] Gerando {N_REGISTROS:,} registros sintéticos...")
    inicio = time.time()

    df = gerar_ano(ano, N_REGISTROS)
    mem = df.memory_usage(deep=True).sum() / 1024**2

    df.to_parquet(saida, index=False, compression="snappy")
    tamanho = saida.stat().st_size / 1024**2
    elapsed = time.time() - inicio

    print(f"  Memoria em RAM : {mem:.1f} MB")
    print(f"  Arquivo salvo  : {saida.name}  ({tamanho:.1f} MB)  [{elapsed:.1f}s]")

print(f"\nDados sinteticos prontos para {len(anos)} ano(s). Rode: streamlit run app.py")
