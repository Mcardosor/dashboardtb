"""
consultar_banco.py
------------------
Script de diagnostico: mostra anos disponíveis, nomes das colunas
e valores reais dos campos categóricos principais.

Uso:
    python scripts/consultar_banco.py
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

url = URL.create(
    drivername="postgresql+psycopg2",
    username=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME"),
)
engine = create_engine(url, pool_pre_ping=True)

with engine.connect() as conn:
    print("=== CONEXAO OK ===\n")

    # Anos disponíveis
    print("=== ANOS DISPONIVEIS ===")
    r = conn.execute(text(
        "SELECT ano_notificacao, COUNT(*) as total "
        "FROM silver.sinan_tube "
        "GROUP BY ano_notificacao "
        "ORDER BY ano_notificacao"
    ))
    total_geral = 0
    for row in r:
        print(f"  {row[0]}: {row[1]:,} registros")
        total_geral += row[1]
    print(f"  TOTAL GERAL: {total_geral:,} registros\n")

    # Colunas da tabela
    print("=== COLUNAS DA TABELA ===")
    r = conn.execute(text(
        "SELECT column_name, data_type "
        "FROM information_schema.columns "
        "WHERE table_schema = 'silver' AND table_name = 'sinan_tube' "
        "ORDER BY ordinal_position"
    ))
    for row in r:
        print(f"  {row[0]}  ({row[1]})")
    print()

    # Valores reais dos campos categóricos
    campos = [
        "forma",
        "situacao_encerramento",
        "tipo_entrada",
        "agravo_aids",
        "populacao_privada_liberdade",
        "sexo",
        "raca_cor",
        "status_hiv",
    ]
    print("=== VALORES DISTINTOS POR CAMPO ===")
    for campo in campos:
        try:
            r = conn.execute(text(
                f"SELECT DISTINCT {campo} "
                f"FROM silver.sinan_tube "
                f"WHERE {campo} IS NOT NULL "
                f"ORDER BY {campo} "
                f"LIMIT 15"
            ))
            valores = [str(row[0]) for row in r]
            print(f"  {campo}: {valores}")
        except Exception as e:
            print(f"  {campo}: ERRO - {e}")
    print()

print("Diagnostico concluido.")
