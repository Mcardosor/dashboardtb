"""
conectar_banco.py
-----------------
Exporta dados do PostgreSQL (schema silver) para Parquet local, por ano.

Uso:
    python scripts/conectar_banco.py           # exporta 2025 (padrao)
    python scripts/conectar_banco.py 2024      # exporta um ano especifico
    python scripts/conectar_banco.py 2020 2025 # exporta um intervalo de anos

Arquivos gerados em dados_dashboard/:
    sinan_tube_2025.parquet
    sinan_tube_2024.parquet
    ...
"""

import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine

load_dotenv()

SCHEMA      = "silver"
TABELA      = "tuberculose"
PASTA_DADOS = Path("dados_dashboard")
PASTA_DADOS.mkdir(exist_ok=True)

# -- Determina anos a exportar via argumento CLI ------------------------------
args = sys.argv[1:]
if len(args) == 0:
    anos = [2025]
elif len(args) == 1:
    anos = [int(args[0])]
elif len(args) == 2:
    anos = list(range(int(args[0]), int(args[1]) + 1))
else:
    print("Uso: python conectar_banco.py [ano_inicio] [ano_fim]")
    sys.exit(1)

# -- Conexao ------------------------------------------------------------------
url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)
engine = create_engine(url, pool_pre_ping=True, connect_args={"sslmode": "disable"})

# -- Exportacao por ano -------------------------------------------------------
for ano in anos:
    saida = PASTA_DADOS / f"tuberculose_{ano}.parquet"

    print(f"\n[{ano}] Baixando dados de {SCHEMA}.{TABELA}...")
    inicio = time.time()

    df = pd.read_sql(
        f"SELECT * FROM {SCHEMA}.{TABELA} WHERE ano_notificacao = '{ano}'",
        engine,
    )

    elapsed = time.time() - inicio
    print(f"  OK  {len(df):,} registros em {elapsed:.1f}s")

    df.to_parquet(saida, index=False, compression="snappy")
    tamanho_mb = saida.stat().st_size / 1024 / 1024
    print(f"  Salvo em: {saida}  ({tamanho_mb:.1f} MB)")

n = len(anos)
print(f"\nExportacao concluida: {n} ano(s)")
print("Próximo passo: python scripts/preparar_dados.py ANO_INICIO ANO_FIM")
