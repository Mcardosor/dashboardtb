"""
preparar_dados.py
-----------------
Transforma o Parquet bruto (exportado pelo conectar_banco.py) em um Parquet
otimizado, com tipos corretos e pronto para o dashboard.

Uso:
    python scripts/preparar_dados.py           # processa 2025 (padrão)
    python scripts/preparar_dados.py 2024      # processa um ano específico
    python scripts/preparar_dados.py 2020 2025 # processa um intervalo de anos
"""

import sys
import time
from pathlib import Path

import pandas as pd

PASTA = Path("dados_dashboard")

# ── Determina anos via CLI ────────────────────────────────────────────────────
args = sys.argv[1:]
if len(args) == 0:
    anos = [2025]
elif len(args) == 1:
    anos = [int(args[0])]
elif len(args) == 2:
    anos = list(range(int(args[0]), int(args[1]) + 1))
else:
    print("Uso: python preparar_dados.py [ano_inicio] [ano_fim]")
    sys.exit(1)

# ── Configurações de colunas ──────────────────────────────────────────────────
COLUNAS_REMOVER = [
    "data_transferencia_rm", "codigo_fluxo_retorno", "codigo_fluxo_recebido",
    "indicador_migracao", "detalhe_agravo_outros", "detalhe_outras_drogas",
    "data_notificacao_atual", "sk_sinan_tube",
]

COLUNAS_DATA = [
    "data_notificacao", "data_diagnostico", "data_digitacao",
    "data_inicio_tratamento", "data_encerramento", "data_mudanca_situacao",
    "data_transferencia_us", "data_transferencia_dm", "data_transferencia_sm",
    "data_transferencia_rs", "data_transferencia_se",
]

COLUNAS_INT = [
    "numero_contatos", "numero_contatos_examinados",
    "ano_notificacao", "ano_nascimento",
]

COLUNAS_CATEGORIA = [
    # Identificação geográfica
    "estado_notificacao", "municipio_notificacao",
    "uf_residencia", "municipio_residencia",
    "regional_notificacao", "regional_residencia",
    "estado_atendimento_atual", "municipio_atendimento_atual",
    "estado_segunda_notificacao", "municipio_segunda_notificacao",
    "estado_transferencia", "municipio_transferencia",
    "pais_residencia",
    # Notificação
    "tipo_notificacao", "tipo_entrada", "tipo_unidade_notificante",
    "tipo_instituicao", "agravo", "arquivo_origem",
    "status_duplicidade", "status_vinculacao",
    # Dados pessoais
    "sexo", "raca_cor", "escolaridade", "gestante", "cbo_ocupacao",
    # Clínica
    "forma", "extrapulmonar", "extrapulmonar2",
    "situacao_encerramento", "transferencia",
    "status_hiv", "uso_antirretroviral", "raio_x_torax",
    "teste_tuberculinico",
    # Bacteriologia
    "baciloscopia_primeira_amostra", "baciloscopia_segunda_amostra",
    "baciloscopia_outro_material", "cultura_escarro", "cultura_outro_material",
    "histopatologia", "teste_molecular", "teste_sensibilidade",
    "tratamento_supervisionado", "tratamento_supervisionado_atual",
    "baciloscopia_mes_1", "baciloscopia_mes_2", "baciloscopia_mes_3",
    "baciloscopia_mes_4", "baciloscopia_mes_5", "baciloscopia_mes_6",
    "baciloscopia_apos_6_meses",
    # Resistência
    "resistencia_rifampicina", "resistencia_isoniazida", "resistencia_etambutol",
    "resistencia_pirazinamida", "resistencia_etionamida", "resistencia_estreptomicina",
    "resistencia_outras_drogas",
    # Agravos e populações
    "agravo_aids", "agravo_alcoolismo", "agravo_diabetes",
    "agravo_doenca_mental", "agravo_outros", "agravo_drogas_ilicitas",
    "agravo_tabagismo",
    "populacao_privada_liberdade", "populacao_situacao_rua",
    "profissional_saude", "populacao_imigrante", "beneficiario_governo",
    # Outros
    "doenca_relacionada_trabalho",
    "situacao_9_meses", "situacao_12_meses",
]


def parse_idade_anos(serie: pd.Series) -> pd.Series:
    """Converte 'X anos/meses/dias' para idade em anos (Int16). Vetorizado."""
    ext = serie.astype(str).str.extract(r"(\d+)\s+(ano|m[eê]s|dia|hora)", expand=True)
    n = pd.to_numeric(ext[0], errors="coerce")
    u = ext[1]
    # anos: valor direto; meses: divisao inteira; dias/horas: 0
    resultado = n.where(u == "ano", (n // 12).where(u.str.match(r"m[eê]s", na=False), 0))
    return resultado.astype("Int16")


def preparar(df: pd.DataFrame) -> pd.DataFrame:
    print(f"  Registros     : {len(df):,}")
    print(f"  Memória bruta : {df.memory_usage(deep=True).sum()/1024**2:.1f} MB")

    existentes = [c for c in COLUNAS_REMOVER if c in df.columns]
    df = df.drop(columns=existentes)

    for col in [c for c in COLUNAS_DATA if c in df.columns]:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    if "idade_notificada" in df.columns:
        df["idade_anos"] = parse_idade_anos(df["idade_notificada"])
        df = df.drop(columns=["idade_notificada"])

    for col in [c for c in COLUNAS_INT if c in df.columns]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int16")

    for col in [c for c in COLUNAS_CATEGORIA if c in df.columns]:
        df[col] = df[col].astype("category")

    print(f"  Memória final : {df.memory_usage(deep=True).sum()/1024**2:.1f} MB")
    return df


# ── Execução ──────────────────────────────────────────────────────────────────
for ano in anos:
    entrada = PASTA / f"tuberculose_{ano}.parquet"
    saida   = PASTA / f"tuberculose_{ano}_tratado.parquet"

    if not entrada.exists():
        print(f"\n[{ano}] ⚠️  Arquivo não encontrado: {entrada} — rode conectar_banco.py {ano}")
        continue

    print(f"\n[{ano}] Processando...")
    inicio = time.time()

    df = pd.read_parquet(entrada)
    df = preparar(df)
    df.to_parquet(saida, index=False, compression="snappy")

    elapsed = time.time() - inicio
    tamanho = saida.stat().st_size / 1024**2
    print(f"  ✅ Salvo: {saida.name}  ({tamanho:.1f} MB)  [{elapsed:.1f}s]")

print(f"\n✅ Concluído: {len(anos)} ano(s) processado(s)")
