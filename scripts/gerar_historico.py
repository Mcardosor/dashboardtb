"""
gerar_historico.py
------------------
Gera 4 CSVs pre-agregados para a aba de Tendencias usando DuckDB.
Muito mais rapido que carregar todos os Parquets no pandas:
  - Leitura colunar paralela
  - Agregacoes feitas em C++ (DuckDB), nao em pandas
  - union_by_name lida com colunas ausentes em anos antigos

Arquivos gerados em dados_dashboard/:
  historico_mensal.csv      -- casos por nu_ano x mes_num
  historico_estadual.csv    -- casos por nu_ano x uf_sigla
  historico_anual.csv       -- total de casos por nu_ano
  historico_indicadores.csv -- taxas percentuais por nu_ano

Uso:
    python scripts/gerar_historico.py
    python scripts/gerar_historico.py 2022 2025
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import duckdb
from src.constantes import PASTA_DADOS, UF_SIGLAS

# ── CLI ───────────────────────────────────────────────────────────────────────
args = sys.argv[1:]
if len(args) == 0:
    ano_ini, ano_fim = 2001, 2025
elif len(args) == 1:
    ano_ini = ano_fim = int(args[0])
elif len(args) == 2:
    ano_ini, ano_fim = int(args[0]), int(args[1])
else:
    print("Uso: python gerar_historico.py [ano_inicio] [ano_fim]")
    sys.exit(1)

# ── Conecta DuckDB e registra view sobre os Parquets ─────────────────────────
glob = (PASTA_DADOS / "tuberculose_*_tratado.parquet").as_posix()

arquivos = list(PASTA_DADOS.glob("tuberculose_*_tratado.parquet"))
if not arquivos:
    print(f"Nenhum parquet tratado encontrado em {PASTA_DADOS}.")
    sys.exit(1)

inicio = time.time()
con = duckdb.connect()
con.execute(f"""
    CREATE VIEW sinan AS
    SELECT * FROM read_parquet('{glob}', union_by_name = true)
    WHERE CAST(ano_notificacao AS INTEGER) BETWEEN {ano_ini} AND {ano_fim}
""")

total = con.execute("SELECT COUNT(*) FROM sinan").fetchone()[0]
print(f"DuckDB conectado: {total:,} registros ({ano_ini}-{ano_fim}) em {time.time()-inicio:.1f}s\n")

# ── 1. Mensal ─────────────────────────────────────────────────────────────────
print("[1/4] historico_mensal.csv...")
mensal = con.execute("""
    SELECT
        CAST(ano_notificacao AS INTEGER)          AS nu_ano,
        MONTH(TRY_CAST(data_notificacao AS DATE)) AS mes_num,
        COUNT(*)                                  AS casos
    FROM sinan
    WHERE data_notificacao IS NOT NULL
      AND TRY_CAST(data_notificacao AS DATE) IS NOT NULL
    GROUP BY 1, 2
    ORDER BY 1, 2
""").df()
mensal.to_csv(PASTA_DADOS / "historico_mensal.csv", index=False)
print(f"      {len(mensal)} linhas")

# ── 2. Estadual ───────────────────────────────────────────────────────────────
print("[2/4] historico_estadual.csv...")
estadual = con.execute("""
    SELECT
        CAST(ano_notificacao AS INTEGER) AS nu_ano,
        estado_notificacao               AS estado,
        COUNT(*)                         AS casos
    FROM sinan
    WHERE estado_notificacao IS NOT NULL
      AND estado_notificacao != ''
    GROUP BY 1, 2
    ORDER BY 1, 2
""").df()
# Converte nome completo → sigla (mesmo mapeamento usado no dashboard)
estadual["uf_sigla"] = estadual["estado"].map(UF_SIGLAS).fillna("?")
estadual = (estadual[estadual["uf_sigla"] != "?"]
            [["nu_ano", "uf_sigla", "casos"]]
            .sort_values(["nu_ano", "uf_sigla"]))
estadual.to_csv(PASTA_DADOS / "historico_estadual.csv", index=False)
print(f"      {len(estadual)} linhas")

# ── 3. Anual ──────────────────────────────────────────────────────────────────
print("[3/4] historico_anual.csv...")
anual = con.execute("""
    SELECT
        CAST(ano_notificacao AS INTEGER) AS nu_ano,
        COUNT(*)                         AS casos
    FROM sinan
    GROUP BY 1
    ORDER BY 1
""").df()
anual.to_csv(PASTA_DADOS / "historico_anual.csv", index=False)
print(f"      {len(anual)} linhas")

# ── 4. Indicadores ────────────────────────────────────────────────────────────
print("[4/4] historico_indicadores.csv...")
ind = con.execute("""
    SELECT
        CAST(ano_notificacao AS INTEGER)                        AS nu_ano,
        COUNT(*)                                                AS total,

        SUM(CASE WHEN LOWER(TRIM(status_hiv)) = 'positivo'
                 THEN 1 ELSE 0 END)                            AS hiv_pos,
        -- HIV com resultado conhecido (denominador da coinfecção e da testagem)
        SUM(CASE WHEN LOWER(TRIM(status_hiv)) IN ('positivo','negativo')
                 THEN 1 ELSE 0 END)                            AS hiv_testado,

        SUM(CASE WHEN TRIM(situacao_encerramento) = 'Cura'
                 THEN 1 ELSE 0 END)                            AS cura,
        -- valores crus do parquet são ACENTUADOS (antes da normalização do app)
        SUM(CASE WHEN TRIM(situacao_encerramento)
                      IN ('Abandono','Abandono Primário')
                 THEN 1 ELSE 0 END)                            AS abandono,
        SUM(CASE WHEN TRIM(situacao_encerramento) = 'Óbito por TB'
                 THEN 1 ELSE 0 END)                            AS obito_tb,
        -- Encerrados = casos com desfecho definido (exclui "Não informado" = em acompanhamento)
        SUM(CASE WHEN TRIM(situacao_encerramento) NOT IN ('Não informado','Nao informado','')
                  AND situacao_encerramento IS NOT NULL
                 THEN 1 ELSE 0 END)                            AS encerrados,

        SUM(CASE WHEN TRIM(tipo_entrada) = 'Caso Novo'
                 THEN 1 ELSE 0 END)                            AS caso_novo,
        SUM(CASE WHEN TRIM(forma) = 'Pulmonar'
                 THEN 1 ELSE 0 END)                            AS pulmonar,

        SUM(CASE WHEN LOWER(TRIM(agravo_aids))       = 'sim'
                 THEN 1 ELSE 0 END)                            AS aids,
        SUM(CASE WHEN LOWER(TRIM(agravo_alcoolismo)) = 'sim'
                 THEN 1 ELSE 0 END)                            AS alcool,

        SUM(CASE WHEN LOWER(TRIM(populacao_situacao_rua))      = 'sim'
                 THEN 1 ELSE 0 END)                            AS pop_rua,
        SUM(CASE WHEN LOWER(TRIM(populacao_privada_liberdade)) = 'sim'
                 THEN 1 ELSE 0 END)                            AS pop_liber

    FROM sinan
    GROUP BY 1
    ORDER BY 1
""").df()

t   = ind["total"].replace(0, 1)
enc = ind["encerrados"].replace(0, 1)   # denominador de desfecho (coorte)
tst = ind["hiv_testado"].replace(0, 1)  # denominador de coinfecção HIV
# Coinfecção HIV = positivo / testados (consistente com modal e gráfico por UF)
ind["pct_hiv"]      = (ind["hiv_pos"]   / tst * 100).round(1)
# Cobertura de testagem HIV = testados / total
ind["pct_test_hiv"] = (ind["hiv_testado"] / t * 100).round(1)
# Desfechos sobre ENCERRADOS (não sobre o total) — metodologia de coorte
ind["pct_cura"]   = (ind["cura"]      / enc * 100).round(1)
ind["pct_abandon"]= (ind["abandono"]  / enc * 100).round(1)
ind["pct_obito"]  = (ind["obito_tb"]  / enc * 100).round(1)
ind["pct_novo"]   = (ind["caso_novo"] / t * 100).round(1)
ind["pct_pulm"]   = (ind["pulmonar"]  / t * 100).round(1)
ind["pct_aids"]   = (ind["aids"]      / t * 100).round(1)
ind["pct_alcool"] = (ind["alcool"]    / t * 100).round(1)

ind.to_csv(PASTA_DADOS / "historico_indicadores.csv", index=False)
print(f"      {len(ind)} anos")

# ── Resumo ────────────────────────────────────────────────────────────────────
elapsed = time.time() - inicio
print(f"\nConcluido em {elapsed:.1f}s")
for nome in ["historico_mensal.csv", "historico_estadual.csv",
             "historico_anual.csv",  "historico_indicadores.csv"]:
    p = PASTA_DADOS / nome
    if p.exists():
        print(f"  {nome:<35} {p.stat().st_size/1024:.1f} KB")
