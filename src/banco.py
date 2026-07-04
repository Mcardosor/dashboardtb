"""
banco.py
────────
Engine DuckDB sobre os Parquets tratados.

Estratégia: cada chamada abre uma conexão DuckDB própria (thread-safe).
O cache fica no nível do resultado (DataFrame), via @st.cache_data em dados.py.

Otimizações:
  - SELECT com colunas específicas (não SELECT *) — 44% menos dados lidos
  - SET threads para paralelismo máximo na leitura colunar
  - read_parquet() inline como CTE — sem CREATE VIEW separado
  - Colunas string reconvertidas para category após carga (~60% menos RAM)
"""

from pathlib import Path
import os
import duckdb
import pandas as pd
import psycopg2

from src.constantes import PASTA_DADOS, COLUNAS_DASHBOARD

# Mapeamento código IBGE UF (2 dígitos) → sigla
_IBGE_UF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}

def _pg_conn():
    """Conexão PostgreSQL com as credenciais do banco central."""
    import os as _os
    from dotenv import load_dotenv
    load_dotenv()
    return psycopg2.connect(
        host=_os.getenv("DB_HOST", "10.20.10.107"),
        dbname=_os.getenv("DB_NAME", "cenarios_ai"),
        user=_os.getenv("DB_USER", "matheus"),
        password=_os.getenv("DB_PASSWORD", "@Matheus_Cardoso"),
        port=int(_os.getenv("DB_PORT", 5432)),
        connect_timeout=10,
    )


def obitos_sim_por_uf(ano: int) -> pd.DataFrame:
    """
    Retorna óbitos por TB (CID A15-A19) do SIM para um dado ano, agregados por UF.
    Fonte oficial para mortalidade — não usa SINAN (Caderno de Indicadores MS).
    Retorna DataFrame com colunas: uf_sigla, obitos_sim.
    """
    sql = """
        SELECT SUBSTRING(codmunres, 1, 2) AS uf_cod, COUNT(*) AS obitos
        FROM sim_mortalidade
        WHERE causabas LIKE 'A1%%'
          AND SUBSTRING(dtobito, 5, 4) = %s
          AND codmunres IS NOT NULL
          AND LENGTH(TRIM(codmunres)) >= 2
        GROUP BY uf_cod
    """
    try:
        with _pg_conn() as conn:
            df = pd.read_sql(sql, conn, params=(str(ano),))
        df["uf_sigla"] = df["uf_cod"].map(_IBGE_UF)
        return df[["uf_sigla", "obitos"]].dropna(subset=["uf_sigla"]).rename(columns={"obitos": "obitos_sim"})
    except Exception:
        return pd.DataFrame(columns=["uf_sigla", "obitos_sim"])


def obitos_sim_brasil(ano: int) -> int:
    """Total de óbitos TB no Brasil para um ano (fonte SIM)."""
    sql = """
        SELECT COUNT(*) FROM sim_mortalidade
        WHERE causabas LIKE 'A1%%'
          AND SUBSTRING(dtobito, 5, 4) = %s
    """
    try:
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (str(ano),))
            return int(cur.fetchone()[0])
    except Exception:
        return 0


def historico_obitos_sim() -> pd.DataFrame:
    """
    Série histórica anual de óbitos TB do SIM (2001-2024).
    Retorna DataFrame com colunas: nu_ano, obitos_sim.
    """
    sql = """
        SELECT SUBSTRING(dtobito, 5, 4) AS nu_ano, COUNT(*) AS obitos_sim
        FROM sim_mortalidade
        WHERE causabas LIKE 'A1%%'
          AND SUBSTRING(dtobito, 5, 4) BETWEEN '2001' AND '2024'
        GROUP BY nu_ano ORDER BY nu_ano
    """
    try:
        with _pg_conn() as conn:
            df = pd.read_sql(sql, conn)
        df["nu_ano"] = pd.to_numeric(df["nu_ano"], errors="coerce")
        return df.dropna(subset=["nu_ano"]).astype({"nu_ano": int})
    except Exception:
        return pd.DataFrame(columns=["nu_ano", "obitos_sim"])


def historico_pulmonar_conf_lab() -> pd.DataFrame:
    """
    Série histórica de proporção de casos novos de TB pulmonar confirmados
    por critério laboratorial (baciloscopia+/cultura+/TRM+).
    Fonte: sinan_tube.
    Retorna DataFrame: nu_ano, pulm_conf_lab, pulm_total, pct_pulm_conf_lab.
    """
    sql = """
        SELECT
            nu_ano,
            COUNT(*) FILTER (
                WHERE forma IN ('1','3')
                AND tratamento IN ('1','4','6')
                AND situa_ence NOT IN ('7',' 7')
            ) AS pulm_total,
            COUNT(*) FILTER (
                WHERE forma IN ('1','3')
                AND tratamento IN ('1','4','6')
                AND situa_ence NOT IN ('7',' 7')
                AND (
                    bacilosc_e = '1'
                    OR bacilos_e2 = '1'
                    OR bacilosc_o = '1'
                    OR cultura_es = '1'
                    OR test_molec IN ('1','2')
                )
            ) AS pulm_conf_lab
        FROM sinan_tube
        WHERE nu_ano BETWEEN '2001' AND '2025'
        GROUP BY nu_ano ORDER BY nu_ano
    """
    try:
        with _pg_conn() as conn:
            df = pd.read_sql(sql, conn)
        df["nu_ano"] = pd.to_numeric(df["nu_ano"], errors="coerce")
        df = df.dropna(subset=["nu_ano"]).astype({"nu_ano": int})
        df["pct_pulm_conf_lab"] = (
            df["pulm_conf_lab"] / df["pulm_total"].replace(0, 1) * 100
        ).round(1)
        return df
    except Exception:
        return pd.DataFrame(columns=["nu_ano", "pulm_total", "pulm_conf_lab", "pct_pulm_conf_lab"])


def historico_contatos() -> pd.DataFrame:
    """
    Série histórica da proporção de contatos de TB pulmonar conf. lab. examinados.
    Retorna DataFrame: nu_ano, contatos_id, contatos_exam, pct_contatos_exam.
    """
    sql = """
        SELECT
            nu_ano,
            SUM(CAST(nu_contato AS FLOAT)) AS contatos_id,
            SUM(CAST(nu_comu_ex AS FLOAT)) AS contatos_exam
        FROM sinan_tube
        WHERE nu_ano BETWEEN '2001' AND '2025'
          AND forma IN ('1','3')
          AND tratamento IN ('1','4','6')
          AND situa_ence NOT IN ('7',' 7')
          AND (
              bacilosc_e = '1' OR bacilos_e2 = '1' OR bacilosc_o = '1'
              OR cultura_es = '1' OR test_molec IN ('1','2')
          )
          AND nu_contato ~ '^[0-9]+$'
          AND nu_comu_ex ~ '^[0-9]+$'
        GROUP BY nu_ano ORDER BY nu_ano
    """
    try:
        with _pg_conn() as conn:
            df = pd.read_sql(sql, conn)
        df["nu_ano"] = pd.to_numeric(df["nu_ano"], errors="coerce")
        df = df.dropna(subset=["nu_ano"]).astype({"nu_ano": int})
        df["pct_contatos_exam"] = (
            df["contatos_exam"] / df["contatos_id"].replace(0, 1) * 100
        ).round(1)
        return df
    except Exception:
        return pd.DataFrame(columns=["nu_ano", "contatos_id", "contatos_exam", "pct_contatos_exam"])

# Colunas de baixa cardinalidade que voltam como object do DuckDB — reconverter
# para category economiza ~60% de memória nessas colunas.
_COLUNAS_CATEGORIA = (
    "estado_notificacao", "uf_residencia", "municipio_notificacao", "municipio_residencia",
    "sexo", "raca_cor", "escolaridade",
    "tipo_entrada", "forma", "extrapulmonar",
    "situacao_encerramento",
    "status_hiv", "uso_antirretroviral", "raio_x_torax", "teste_tuberculinico",
    "baciloscopia_primeira_amostra", "cultura_escarro", "histopatologia",
    "teste_molecular", "teste_sensibilidade", "tratamento_supervisionado",
    "baciloscopia_mes_1", "baciloscopia_mes_2", "baciloscopia_mes_3",
    "baciloscopia_mes_4", "baciloscopia_mes_5", "baciloscopia_mes_6",
    "baciloscopia_apos_6_meses",
    "agravo_aids", "agravo_alcoolismo", "agravo_diabetes",
    "agravo_doenca_mental", "agravo_drogas_ilicitas", "agravo_tabagismo", "agravo_outros",
    "populacao_privada_liberdade", "populacao_situacao_rua",
    "profissional_saude", "populacao_imigrante", "beneficiario_governo",
    "tipo_notificacao",
)


def _aplicar_categorias(df: pd.DataFrame) -> pd.DataFrame:
    """Reconverte colunas string para category após carga do DuckDB."""
    for col in _COLUNAS_CATEGORIA:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].astype("category")
    return df


def _glob() -> str:
    """Glob dos Parquets tratados (forward slashes para DuckDB em qualquer OS)."""
    return (PASTA_DADOS / "tuberculose_*_tratado.parquet").as_posix()


def _threads() -> int:
    """Número de threads para DuckDB — usa todos os CPUs disponíveis (max 8)."""
    return min(os.cpu_count() or 2, 8)


def _arquivos_anos(anos: tuple[int, ...]) -> list[str]:
    """Retorna os caminhos dos Parquets tratados para os anos solicitados."""
    return [
        (PASTA_DADOS / f"tuberculose_{ano}_tratado.parquet").as_posix()
        for ano in anos
        if (PASTA_DADOS / f"tuberculose_{ano}_tratado.parquet").exists()
    ]


def query(sql: str, params: list | None = None,
          anos: tuple[int, ...] | None = None) -> pd.DataFrame:
    """
    Executa SQL sobre os Parquets tratados e retorna um DataFrame.
    Thread-safe: cada chamada usa sua própria conexão DuckDB em memória.

    Se `anos` for fornecido, lê apenas os arquivos desses anos (muito mais
    rápido que glob sobre todos os 50+ arquivos + WHERE). Se omitido, usa
    glob sobre todos os arquivos (compatibilidade com chamadas legadas).

    O SQL do chamador deve referenciar a tabela como 'sinan'.
    """
    cols = ", ".join(COLUNAS_DASHBOARD)
    if anos:
        files = _arquivos_anos(anos)
        if not files:
            return pd.DataFrame()
        files_sql = str(files).replace("'", '"')
        source = f"read_parquet({files_sql}, union_by_name = true)"
    else:
        source = f"read_parquet('{_glob()}', union_by_name = true)"

    wrapped = f"""
        WITH sinan AS (SELECT {cols} FROM {source})
        {sql}
    """
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_threads()}")
        return con.execute(wrapped, params or []).df()


def query_all_cols(sql: str, params: list | None = None,
                   anos: tuple[int, ...] | None = None) -> pd.DataFrame:
    """
    Igual a query() mas com SELECT * — usado pela aba Análise Livre (PyGWalker).
    """
    if anos:
        files = _arquivos_anos(anos)
        if not files:
            return pd.DataFrame()
        files_sql = str(files).replace("'", '"')
        source = f"read_parquet({files_sql}, union_by_name = true)"
    else:
        source = f"read_parquet('{_glob()}', union_by_name = true)"

    wrapped = f"WITH sinan AS (SELECT * FROM {source}) {sql}"
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_threads()}")
        return con.execute(wrapped, params or []).df()


def anos_no_banco() -> list[int]:
    """Retorna anos com Parquet tratado disponível, do mais recente ao mais antigo."""
    return sorted(
        [
            int(p.stem.split("_")[1])
            for p in PASTA_DADOS.glob("tuberculose_*_tratado.parquet")
        ],
        reverse=True,
    )
