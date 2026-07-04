"""
consultas.py — Camada de agregação DuckDB sobre os Parquets tratados.

Princípios de performance:
  - TODA agregação acontece no DuckDB (leitura colunar paralela, projection
    pushdown). Nenhum DataFrame de milhões de linhas transita pelo Python.
  - Só os arquivos dos anos selecionados são lidos (sem glob + WHERE).
  - Resultados (dicts pequenos, prontos para JSON) ficam em lru_cache,
    chaveados pelos Filtros imutáveis.
  - Óbitos oficiais (SIM/PostgreSQL) são opcionais: sem VPN o backend cai
    para o desfecho SINAN em silêncio e marca `fonte_obitos` na resposta.
"""

from __future__ import annotations

import math
import os
import re
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

from constantes import (
    AGRAVOS, ANO_INICIO, DESFECHO_CANONICO, DESFECHO_GRUPO, FAIXAS_ETARIAS,
    HIST_ANUAL, HIST_ESTADUAL, HIST_INDICADORES, HIST_MENSAL,
    PASTA_DADOS, POP_BRASIL, POP_ESTADO, POPULACOES, REGIOES,
    TIPOS_INCIDENCIA, UF_NOMES, UF_SIGLAS,
)
from filtros import Filtros

_THREADS = min(os.cpu_count() or 2, 8)

# ── Fragmentos SQL reutilizados ───────────────────────────────────────────────

def _sql_literal(valor: str) -> str:
    return "'" + valor.replace("'", "''") + "'"


# CASE que normaliza situacao_encerramento para a forma canônica acentuada.
# NULL / 'Não informado' = caso ainda aberto → 'Em acompanhamento'.
_CASE_DESFECHO = "CASE " + " ".join(
    f"WHEN situacao_encerramento = {_sql_literal(k)} THEN {_sql_literal(v)}"
    for k, v in DESFECHO_CANONICO.items()
) + " ELSE coalesce(situacao_encerramento, 'Em acompanhamento') END"

# CASE que agrupa o desfecho canônico em 4 categorias de coorte.
_CASE_GRUPO = "CASE desfecho " + " ".join(
    f"WHEN {_sql_literal(k)} THEN {_sql_literal(v)}"
    for k, v in DESFECHO_GRUPO.items()
) + " ELSE 'Não avaliado' END"

# CTE VALUES: nome do estado (todas as variantes) → sigla.
_CTE_UFS = "ufs(nome, sigla) AS (VALUES " + ", ".join(
    f"({_sql_literal(nome)}, {_sql_literal(sigla)})"
    for nome, sigla in UF_SIGLAS.items()
) + ")"

_IN_INCIDENCIA = "(" + ", ".join(_sql_literal(t) for t in TIPOS_INCIDENCIA) + ")"

_CASE_FAIXA = """CASE
    WHEN idade_anos BETWEEN 0  AND 4  THEN '0-4'
    WHEN idade_anos BETWEEN 5  AND 9  THEN '5-9'
    WHEN idade_anos BETWEEN 10 AND 14 THEN '10-14'
    WHEN idade_anos BETWEEN 15 AND 19 THEN '15-19'
    WHEN idade_anos BETWEEN 20 AND 29 THEN '20-29'
    WHEN idade_anos BETWEEN 30 AND 39 THEN '30-39'
    WHEN idade_anos BETWEEN 40 AND 49 THEN '40-49'
    WHEN idade_anos BETWEEN 50 AND 59 THEN '50-59'
    WHEN idade_anos BETWEEN 60 AND 69 THEN '60-69'
    WHEN idade_anos BETWEEN 70 AND 79 THEN '70-79'
    WHEN idade_anos >= 80             THEN '80+'
    ELSE NULL END"""


# ── Infraestrutura de consulta ────────────────────────────────────────────────

def anos_disponiveis() -> list[int]:
    """Anos com Parquet tratado, do mais antigo ao mais recente."""
    anos = []
    for p in PASTA_DADOS.glob("tuberculose_*_tratado.parquet"):
        m = re.match(r"tuberculose_(\d{4})_tratado", p.stem)
        if m:
            anos.append(int(m.group(1)))
    return sorted(anos)


def _arquivos(anos: tuple[int, ...]) -> list[str]:
    return [
        (PASTA_DADOS / f"tuberculose_{a}_tratado.parquet").as_posix()
        for a in anos
        if (PASTA_DADOS / f"tuberculose_{a}_tratado.parquet").exists()
    ]


def _files_sql(files: list[str]) -> str:
    """Lista de Parquets como array literal do DuckDB (read_parquet([...]))."""
    return "[" + ", ".join(_sql_literal(f) for f in files) + "]"


def _executar(sql: str, params: list, anos: tuple[int, ...]) -> pd.DataFrame:
    """
    Executa SQL com a CTE `sinan` sobre os Parquets dos anos pedidos.
    Conexão própria por chamada — thread-safe sob o pool do uvicorn.
    """
    files = _arquivos(anos)
    if not files:
        return pd.DataFrame()
    files_sql = _files_sql(files)
    wrapped = f"""
        WITH {_CTE_UFS},
        sinan AS (SELECT * FROM read_parquet({files_sql}, union_by_name = true))
        {sql}
    """
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_THREADS}")
        return con.execute(wrapped, params).df()


def _norm(s: str) -> str:
    """Remove acentos, minúsculas, trim — mesmo algoritmo do geo-cache."""
    return (
        unicodedata.normalize("NFD", str(s))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


_ROTULOS_INVALIDOS = {"nan", "none", "undefined", ""}


def _limpar_rotulos(pares: list[tuple[str, int]]) -> list[dict]:
    """Normaliza rótulos ('Nao informado' → 'Não informado'), soma duplicados
    e descarta valores técnicos. NULL vira 'Não informado'."""
    acumulado: dict[str, int] = {}
    for rotulo, casos in pares:
        r = "Não informado" if rotulo is None else str(rotulo).strip()
        if r.lower() in _ROTULOS_INVALIDOS:
            r = "Não informado"
        if _norm(r) == "nao informado":
            r = "Não informado"
        acumulado[r] = acumulado.get(r, 0) + int(casos)
    return sorted(
        [{"label": k, "valor": v} for k, v in acumulado.items()],
        key=lambda d: d["valor"],
        reverse=True,
    )


def _value_counts(coluna: str, f: Filtros) -> list[dict]:
    where, params = f.where_sql()
    df = _executar(
        f"SELECT {coluna} AS rotulo, COUNT(*) AS casos FROM sinan WHERE {where} GROUP BY 1",
        params, f.anos,
    )
    if df.empty:
        return []
    return _limpar_rotulos(list(df.itertuples(index=False, name=None)))


def _pop_filtrada(f: Filtros) -> int:
    if f.ufs:
        return sum(POP_ESTADO.get(u, 0) for u in f.ufs) or POP_BRASIL
    return POP_BRASIL


# ── Óbitos oficiais (SIM via PostgreSQL) — opcional ───────────────────────────
#
# Estratégia: UMA única query agregada (ano × UF) para toda a série, cacheada
# em memória e em disco (dados_dashboard/_cache_sim_obitos.csv). Sem VPN o
# backend usa o cache em disco (mesmo antigo); sem cache, cai para o SINAN.

_SIM_CACHE_ARQ = PASTA_DADOS / "_cache_sim_obitos.csv"
_SIM_CACHE_TTL_S = 7 * 24 * 3600  # 7 dias

_IBGE_UF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}


def _pg_conn():
    import psycopg2  # import tardio: dependência opcional
    from dotenv import load_dotenv
    load_dotenv(PASTA_DADOS.parent / ".env")
    return psycopg2.connect(
        host=os.getenv("DB_HOST", ""),
        dbname=os.getenv("DB_NAME", ""),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        port=int(os.getenv("DB_PORT", 5432)),
        connect_timeout=2,
    )


def _sim_ler_disco() -> dict[tuple[int, str], int] | None:
    if not _SIM_CACHE_ARQ.exists():
        return None
    try:
        df = pd.read_csv(_SIM_CACHE_ARQ)
        return {
            (int(r["ano"]), str(r["uf"])): int(r["obitos"])
            for _, r in df.iterrows()
        }
    except Exception:
        return None


def _sim_consultar_pg() -> dict[tuple[int, str], int] | None:
    """Query única: óbitos TB (CID A15–A19) por ano × UF, série completa."""
    sql = """
        SELECT SUBSTRING(dtobito, 5, 4) AS ano,
               SUBSTRING(codmunres, 1, 2) AS uf_cod,
               COUNT(*) AS obitos
        FROM sim_mortalidade
        WHERE causabas LIKE 'A1%%'
          AND codmunres IS NOT NULL AND LENGTH(TRIM(codmunres)) >= 2
        GROUP BY 1, 2
    """
    try:
        with _pg_conn() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            linhas = cur.fetchall()
        tabela: dict[tuple[int, str], int] = {}
        for ano, cod, n in linhas:
            try:
                a = int(ano)
            except (TypeError, ValueError):
                continue
            uf = _IBGE_UF.get(str(cod))
            if uf:
                tabela[(a, uf)] = tabela.get((a, uf), 0) + int(n)
        return tabela or None
    except Exception:
        return None


@lru_cache(maxsize=1)
def _sim_tabela() -> tuple[tuple[tuple[int, str], int], ...] | None:
    """Tabela (ano, uf) → óbitos SIM, imutável para caber no lru_cache."""
    fresco = (
        _SIM_CACHE_ARQ.exists()
        and time.time() - _SIM_CACHE_ARQ.stat().st_mtime < _SIM_CACHE_TTL_S
    )
    tabela = _sim_ler_disco() if fresco else None
    if tabela is None:
        tabela = _sim_consultar_pg()
        if tabela:
            try:
                pd.DataFrame(
                    [(a, u, n) for (a, u), n in sorted(tabela.items())],
                    columns=["ano", "uf", "obitos"],
                ).to_csv(_SIM_CACHE_ARQ, index=False)
            except Exception:
                pass
        else:
            tabela = _sim_ler_disco()  # aceita cache antigo como fallback
    if tabela is None:
        return None
    return tuple(sorted(tabela.items()))


def _obitos_sim(f: Filtros) -> tuple[int | None, dict[str, int] | None]:
    """Soma de óbitos SIM nos anos/UFs filtrados + dict por UF (ou None×2)."""
    bruto = _sim_tabela()
    if bruto is None:
        return None, None
    anos = set(f.anos)
    por_uf_acum: dict[str, int] = {}
    for (ano, uf), n in bruto:
        if ano in anos:
            por_uf_acum[uf] = por_uf_acum.get(uf, 0) + n
    if not por_uf_acum:
        return None, None  # SIM não cobre os anos pedidos → fallback SINAN
    ufs = f.ufs or tuple(POP_ESTADO.keys())
    total = sum(por_uf_acum.get(u, 0) for u in ufs)
    return total, por_uf_acum


def obitos_sim_anual() -> list[dict] | None:
    """Série anual de óbitos SIM (Brasil) para a aba Tendência."""
    bruto = _sim_tabela()
    if bruto is None:
        return None
    por_ano: dict[int, int] = {}
    for (ano, _uf), n in bruto:
        por_ano[ano] = por_ano.get(ano, 0) + n
    return [{"ano": a, "obitos": por_ano[a]} for a in sorted(por_ano)]


# ── Meta / opções de filtro ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def meta() -> dict:
    """Anos disponíveis + opções de cada filtro (distincts sobre toda a base)."""
    anos = anos_disponiveis()
    todos = tuple(anos)

    def _opcoes(coluna: str) -> list[str]:
        df = _executar(
            f"SELECT DISTINCT {coluna} AS v FROM sinan WHERE {coluna} IS NOT NULL",
            [], todos,
        )
        vistos: dict[str, str] = {}
        for v in df["v"].astype(str):
            v = v.strip()
            if v.lower() in _ROTULOS_INVALIDOS:
                continue
            chave = _norm(v)
            # Prefere a variante acentuada quando há duplicata com/sem acento
            if chave not in vistos or (v != vistos[chave] and any(ord(c) > 127 for c in v)):
                vistos[chave] = v
        return sorted(vistos.values())

    ufs = [
        {"sigla": s, "nome": UF_NOMES[s], "regiao": regiao}
        for regiao, siglas in REGIOES.items()
        for s in siglas
    ]
    return {
        "anos": anos,
        "ano_parcial": max(anos) if anos else None,
        "ufs": sorted(ufs, key=lambda u: u["nome"]),
        "regioes": REGIOES,
        "opcoes": {
            "sexo": _opcoes("sexo"),
            "formas": _opcoes("forma"),
            "racas": _opcoes("raca_cor"),
            "entradas": _opcoes("tipo_entrada"),
            "hiv": _opcoes("status_hiv"),
        },
        "vulneraveis": POPULACOES,
        "agravos": AGRAVOS,
    }


# ── KPIs (resumo) ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=1024)
def resumo(f: Filtros) -> dict:
    where, params = f.where_sql()
    df = _executar(
        f"""
        SELECT
            COUNT(*)                                                    AS total,
            COUNT(*) FILTER (WHERE desfecho = 'Cura')                   AS cura,
            COUNT(*) FILTER (WHERE desfecho IN ('Abandono', 'Abandono Primário')) AS abandono,
            COUNT(*) FILTER (WHERE desfecho = 'Óbito por TB')           AS obito_tb,
            COUNT(*) FILTER (WHERE status_hiv = 'Positivo')             AS hiv_pos,
            COUNT(DISTINCT municipio_notificacao)                       AS municipios,
            COUNT(*) FILTER (WHERE tipo_entrada IN {_IN_INCIDENCIA})    AS casos_novos
        FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        """,
        params, f.anos,
    )
    r = df.iloc[0] if not df.empty else None
    total = int(r["total"]) if r is not None else 0

    pop = _pop_filtrada(f)
    casos_novos = int(r["casos_novos"]) if r is not None else 0
    incidencia = round(casos_novos / (pop * f.n_anos) * 100_000, 1)

    obitos_sim, _ = _obitos_sim(f)
    fonte_obitos = "SIM"
    obitos = obitos_sim
    if not obitos:
        obitos = int(r["obito_tb"]) if r is not None else 0
        fonte_obitos = "SINAN"
    mortalidade = round(obitos / (pop * f.n_anos) * 100_000, 1)

    total_base = _total_base(f.anos)
    return {
        "total": total,
        "total_base": total_base,
        "pct_filtrado": round(total / total_base * 100, 1) if total_base else 0.0,
        "cura": int(r["cura"]) if r is not None else 0,
        "abandono": int(r["abandono"]) if r is not None else 0,
        "obitos": int(obitos),
        "fonte_obitos": fonte_obitos,
        "hiv_pos": int(r["hiv_pos"]) if r is not None else 0,
        "municipios": int(r["municipios"]) if r is not None else 0,
        "incidencia": incidencia,
        "mortalidade": mortalidade,
        "anos": list(f.anos),
    }


@lru_cache(maxsize=64)
def _total_base(anos: tuple[int, ...]) -> int:
    df = _executar("SELECT COUNT(*) AS n FROM sinan", [], anos)
    return int(df["n"].iloc[0]) if not df.empty else 0


# ── Mapa por UF ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=512)
def mapa_uf(f: Filtros) -> dict:
    where, params = f.where_sql()
    df = _executar(
        f"""
        SELECT u.sigla AS uf,
               COUNT(*) AS casos,
               COUNT(*) FILTER (WHERE s.tipo_entrada IN {_IN_INCIDENCIA}) AS casos_novos,
               COUNT(*) FILTER (WHERE s.desfecho = 'Óbito por TB')        AS obitos_sinan,
               COUNT(*) FILTER (WHERE s.desfecho = 'Cura')                AS cura,
               COUNT(*) FILTER (WHERE s.desfecho IN ('Abandono', 'Abandono Primário')) AS abandono
        FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where}) s
        JOIN ufs u ON s.estado_notificacao = u.nome
        GROUP BY 1
        """,
        params, f.anos,
    )
    _, sim_por_uf = _obitos_sim(f)
    fonte = "SIM" if sim_por_uf else "SINAN"

    estados = []
    for _, r in df.iterrows():
        uf = r["uf"]
        pop = POP_ESTADO.get(uf, 0)
        obitos = (sim_por_uf or {}).get(uf) if sim_por_uf else int(r["obitos_sinan"])
        obitos = int(obitos or 0)
        casos = int(r["casos"])
        estados.append({
            "uf": uf,
            "nome": UF_NOMES.get(uf, uf),
            "casos": casos,
            "casos_novos": int(r["casos_novos"]),
            "obitos": obitos,
            "incidencia": round(int(r["casos_novos"]) / (pop * f.n_anos) * 100_000, 1) if pop else 0.0,
            "mortalidade": round(obitos / (pop * f.n_anos) * 100_000, 1) if pop else 0.0,
            "cura_pct": round(int(r["cura"]) / casos * 100, 1) if casos else 0.0,
            "abandono_pct": round(int(r["abandono"]) / casos * 100, 1) if casos else 0.0,
        })
    estados.sort(key=lambda e: e["casos"], reverse=True)
    return {"estados": estados, "fonte_obitos": fonte}


# ── Drill-down: detalhe de um estado ──────────────────────────────────────────

@lru_cache(maxsize=512)
def detalhe_uf(f: Filtros, sigla: str) -> dict:
    f_uf = Filtros(
        anos=f.anos, ufs=(sigla,), sexo=f.sexo, formas=f.formas, racas=f.racas,
        entradas=f.entradas, hiv=f.hiv, vuln=f.vuln, agravos=f.agravos,
    )
    where, params = f_uf.where_sql()

    # Agregação municipal em uma passada
    df = _executar(
        f"""
        SELECT
            trim(municipio_notificacao) AS municipio,
            COUNT(*) AS casos,
            COUNT(*) FILTER (WHERE desfecho = 'Cura')                            AS cura,
            COUNT(*) FILTER (WHERE desfecho IN ('Abandono', 'Abandono Primário')) AS abandono,
            COUNT(*) FILTER (WHERE desfecho = 'Óbito por TB')                     AS obito,
            COUNT(*) FILTER (WHERE status_hiv = 'Positivo')                       AS hiv_pos,
            COUNT(*) FILTER (WHERE status_hiv IN ('Positivo', 'Negativo'))        AS hiv_conhecido
        FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        WHERE municipio_notificacao IS NOT NULL
        GROUP BY 1
        ORDER BY casos DESC
        """,
        params, f.anos,
    )
    municipios = []
    for _, r in df.iterrows():
        casos = int(r["casos"])
        municipios.append({
            "municipio": r["municipio"],
            "nm_norm": _norm(r["municipio"]),
            "casos": casos,
            "cura_pct": round(int(r["cura"]) / casos * 100, 1) if casos else 0.0,
            "abandono_pct": round(int(r["abandono"]) / casos * 100, 1) if casos else 0.0,
            "obito_pct": round(int(r["obito"]) / casos * 100, 1) if casos else 0.0,
            "hiv_pct": round(int(r["hiv_pos"]) / int(r["hiv_conhecido"]) * 100, 1)
                       if int(r["hiv_conhecido"]) else 0.0,
        })

    # KPIs do estado — metodologia de coorte (denominador = encerrados)
    kdf = _executar(
        f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE desfecho != 'Em acompanhamento') AS encerrados,
            COUNT(*) FILTER (WHERE desfecho = 'Cura' AND desfecho != 'Em acompanhamento') AS cura,
            COUNT(*) FILTER (WHERE desfecho IN ('Abandono', 'Abandono Primário')) AS abandono,
            COUNT(*) FILTER (WHERE desfecho = 'Óbito por TB') AS obito,
            COUNT(*) FILTER (WHERE tipo_entrada = 'Caso Novo' AND desfecho != 'Em acompanhamento') AS enc_novo,
            COUNT(*) FILTER (WHERE tipo_entrada = 'Caso Novo' AND desfecho = 'Cura') AS cura_novo,
            COUNT(*) FILTER (WHERE tipo_entrada IN ('Recidiva', 'Reingresso após Abandono', 'Reingresso Após Abandono')
                             AND desfecho != 'Em acompanhamento') AS enc_retrat,
            COUNT(*) FILTER (WHERE tipo_entrada IN ('Recidiva', 'Reingresso após Abandono', 'Reingresso Após Abandono')
                             AND desfecho = 'Cura') AS cura_retrat,
            COUNT(*) FILTER (WHERE status_hiv = 'Positivo') AS hiv_pos,
            COUNT(*) FILTER (WHERE status_hiv IN ('Positivo', 'Negativo')) AS hiv_conhecido
        FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        """,
        params, f.anos,
    )
    k = kdf.iloc[0]
    enc = max(int(k["encerrados"]), 1)
    kpis = {
        "total": int(k["total"]),
        "total_municipios": len(municipios),
        "encerrados": int(k["encerrados"]),
        "cura_pct": round(int(k["cura"]) / enc * 100, 1),
        "abandono_pct": round(int(k["abandono"]) / enc * 100, 1),
        "obito_pct": round(int(k["obito"]) / enc * 100, 1),
        "cura_novo_pct": round(int(k["cura_novo"]) / max(int(k["enc_novo"]), 1) * 100, 1),
        "n_enc_novo": int(k["enc_novo"]),
        "cura_retrat_pct": round(int(k["cura_retrat"]) / max(int(k["enc_retrat"]), 1) * 100, 1),
        "n_enc_retrat": int(k["enc_retrat"]),
        "hiv_pct": round(int(k["hiv_pos"]) / max(int(k["hiv_conhecido"]), 1) * 100, 1),
        "n_hiv_conhecido": int(k["hiv_conhecido"]),
    }
    return {
        "uf": sigla,
        "nome": UF_NOMES.get(sigla, sigla),
        "kpis": kpis,
        "municipios": municipios,
    }


# ── Perfil dos pacientes ──────────────────────────────────────────────────────

def _piramide(f: Filtros, apenas_obitos: bool) -> dict:
    where, params = f.where_sql()
    extra = "AND desfecho = 'Óbito por TB'" if apenas_obitos else ""
    df = _executar(
        f"""
        SELECT {_CASE_FAIXA} AS faixa, sexo, COUNT(*) AS casos
        FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        WHERE idade_anos IS NOT NULL AND sexo IN ('Masculino', 'Feminino') {extra}
        GROUP BY 1, 2
        """,
        params, f.anos,
    )
    tab: dict[tuple[str, str], int] = {
        (r["faixa"], r["sexo"]): int(r["casos"])
        for _, r in df.iterrows() if r["faixa"] is not None
    }
    return {
        "faixas": list(FAIXAS_ETARIAS),
        "masculino": [tab.get((fx, "Masculino"), 0) for fx in FAIXAS_ETARIAS],
        "feminino": [tab.get((fx, "Feminino"), 0) for fx in FAIXAS_ETARIAS],
    }


def _desfecho_grupo_por(f: Filtros, coluna_grupo: str, grupos_sql: str | None = None) -> dict:
    """% de cada grupo de desfecho dentro de cada categoria de `coluna_grupo`."""
    where, params = f.where_sql()
    cond = f"AND {coluna_grupo} IN ({grupos_sql})" if grupos_sql else ""
    df = _executar(
        f"""
        SELECT {coluna_grupo} AS categoria, {_CASE_GRUPO} AS grupo, COUNT(*) AS casos
        FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        WHERE {coluna_grupo} IS NOT NULL {cond}
        GROUP BY 1, 2
        """,
        params, f.anos,
    )
    grupos = ["Cura", "Interrupção", "Óbito", "Não avaliado"]
    tabela: dict[str, dict[str, int]] = {}
    for _, r in df.iterrows():
        cat = str(r["categoria"]).strip()
        if _norm(cat) in _ROTULOS_INVALIDOS or _norm(cat) == "nao informado":
            continue
        tabela.setdefault(cat, {g: 0 for g in grupos})
        tabela[cat][r["grupo"]] = tabela[cat].get(r["grupo"], 0) + int(r["casos"])
    categorias = sorted(tabela.keys(), key=lambda c: -sum(tabela[c].values()))
    return {
        "categorias": categorias,
        "grupos": grupos,
        "n": {c: sum(tabela[c].values()) for c in categorias},
        "pct": {
            c: {
                g: round(tabela[c].get(g, 0) / max(sum(tabela[c].values()), 1) * 100, 1)
                for g in grupos
            }
            for c in categorias
        },
    }


@lru_cache(maxsize=512)
def perfil(f: Filtros) -> dict:
    where, params = f.where_sql()
    desfechos = _executar(
        f"""
        SELECT desfecho AS rotulo, COUNT(*) AS casos
        FROM (SELECT {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        GROUP BY 1
        """,
        params, f.anos,
    )
    grupo = _executar(
        f"""
        SELECT {_CASE_GRUPO} AS rotulo, COUNT(*) AS casos
        FROM (SELECT {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
        GROUP BY 1
        """,
        params, f.anos,
    )
    return {
        "sexo": _value_counts("sexo", f),
        "forma": _value_counts("forma", f),
        "tipo_entrada": _value_counts("tipo_entrada", f),
        "raca_cor": _value_counts("raca_cor", f),
        "escolaridade": _value_counts("escolaridade", f),
        "desfecho": _limpar_rotulos(list(desfechos.itertuples(index=False, name=None))),
        "desfecho_grupo": _limpar_rotulos(list(grupo.itertuples(index=False, name=None))),
        "desfecho_por_raca": _desfecho_grupo_por(f, "raca_cor"),
        "piramide_casos": _piramide(f, apenas_obitos=False),
        "piramide_obitos": _piramide(f, apenas_obitos=True),
    }


# ── Clínico & diagnóstico ─────────────────────────────────────────────────────

@lru_cache(maxsize=512)
def clinico(f: Filtros) -> dict:
    where, params = f.where_sql()

    # Coinfecção TB-HIV por UF: % positivos sobre testagem conhecida
    coinf = _executar(
        f"""
        SELECT u.sigla AS uf,
               COUNT(*) FILTER (WHERE s.status_hiv = 'Positivo') AS pos,
               COUNT(*) FILTER (WHERE s.status_hiv IN ('Positivo', 'Negativo')) AS conhecido
        FROM (SELECT * FROM sinan WHERE {where}) s
        JOIN ufs u ON s.estado_notificacao = u.nome
        GROUP BY 1
        """,
        params, f.anos,
    )
    coinfeccao_uf = sorted(
        [
            {
                "uf": r["uf"],
                "nome": UF_NOMES.get(r["uf"], r["uf"]),
                "pct": round(int(r["pos"]) / int(r["conhecido"]) * 100, 1) if int(r["conhecido"]) else 0.0,
                "n_testado": int(r["conhecido"]),
            }
            for _, r in coinf.iterrows()
        ],
        key=lambda d: d["pct"], reverse=True,
    )

    # Oportunidade do tratamento: diagnóstico → início
    tempo = _executar(
        f"""
        SELECT COUNT(*) AS n,
               quantile_cont(espera, 0.5) AS mediana,
               COUNT(*) FILTER (WHERE espera <= 7)  AS ate_7,
               COUNT(*) FILTER (WHERE espera > 30)  AS acima_30,
               COUNT(*) FILTER (WHERE espera = 0)                    AS b0,
               COUNT(*) FILTER (WHERE espera BETWEEN 1  AND 3)       AS b1,
               COUNT(*) FILTER (WHERE espera BETWEEN 4  AND 7)       AS b2,
               COUNT(*) FILTER (WHERE espera BETWEEN 8  AND 15)      AS b3,
               COUNT(*) FILTER (WHERE espera BETWEEN 16 AND 30)      AS b4,
               COUNT(*) FILTER (WHERE espera BETWEEN 31 AND 60)      AS b5,
               COUNT(*) FILTER (WHERE espera > 60)                   AS b6
        FROM (
            SELECT date_diff('day', data_diagnostico, data_inicio_tratamento) AS espera
            FROM sinan
            WHERE {where}
              AND data_diagnostico IS NOT NULL AND data_inicio_tratamento IS NOT NULL
              AND date_diff('day', data_diagnostico, data_inicio_tratamento) BETWEEN 0 AND 365
        ) esperas
        """,
        params, f.anos,
    )
    t = tempo.iloc[0]
    n_tempo = int(t["n"])
    tempo_tratamento = None
    if n_tempo > 0:
        dur = _executar(
            f"""
            SELECT quantile_cont(date_diff('day', data_notificacao, data_encerramento), 0.5) AS mediana
            FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
            WHERE desfecho != 'Em acompanhamento'
              AND data_notificacao IS NOT NULL AND data_encerramento IS NOT NULL
              AND date_diff('day', data_notificacao, data_encerramento) BETWEEN 1 AND 1000
            """,
            params, f.anos,
        )
        dur_mediana = dur["mediana"].iloc[0]
        tempo_tratamento = {
            "n": n_tempo,
            "mediana_inicio": float(t["mediana"]),
            "pct_ate_7d": round(int(t["ate_7"]) / n_tempo * 100, 1),
            "pct_acima_30d": round(int(t["acima_30"]) / n_tempo * 100, 1),
            "duracao_mediana": float(dur_mediana) if dur_mediana is not None and not (
                isinstance(dur_mediana, float) and math.isnan(dur_mediana)
            ) else None,
            "histograma": [
                {"faixa": "Mesmo dia", "casos": int(t["b0"])},
                {"faixa": "1–3 dias", "casos": int(t["b1"])},
                {"faixa": "4–7 dias", "casos": int(t["b2"])},
                {"faixa": "8–15 dias", "casos": int(t["b3"])},
                {"faixa": "16–30 dias", "casos": int(t["b4"])},
                {"faixa": "31–60 dias", "casos": int(t["b5"])},
                {"faixa": "> 60 dias", "casos": int(t["b6"])},
            ],
        }

    hiv_sql = ", ".join(_sql_literal(v) for v in ("Positivo", "Negativo"))
    return {
        "status_hiv": _value_counts("status_hiv", f),
        "baciloscopia": _value_counts("baciloscopia_primeira_amostra", f),
        "teste_molecular": _value_counts("teste_molecular", f),
        "desfecho_por_hiv": _desfecho_grupo_por(f, "status_hiv", grupos_sql=hiv_sql),
        "coinfeccao_uf": coinfeccao_uf,
        "tempo_tratamento": tempo_tratamento,
    }


# ── Comorbidades & vulnerabilidades ───────────────────────────────────────────

@lru_cache(maxsize=512)
def comorbidades(f: Filtros) -> dict:
    where, params = f.where_sql()

    sim_agravos = ", ".join(
        f"COUNT(*) FILTER (WHERE lower({col}) = 'sim') AS {col}" for col in AGRAVOS
    )
    sim_pops = ", ".join(
        f"COUNT(*) FILTER (WHERE lower({col}) = 'sim') AS {col}" for col in POPULACOES
    )
    df = _executar(
        f"SELECT COUNT(*) AS total, {sim_agravos}, {sim_pops} FROM sinan WHERE {where}",
        params, f.anos,
    )
    r = df.iloc[0]
    total = max(int(r["total"]), 1)

    agravos = sorted(
        [
            {"label": rotulo, "valor": int(r[col]), "pct": round(int(r[col]) / total * 100, 1)}
            for col, rotulo in AGRAVOS.items()
        ],
        key=lambda d: d["valor"], reverse=True,
    )
    populacoes = sorted(
        [
            {"label": rotulo, "coluna": col, "valor": int(r[col]),
             "pct": round(int(r[col]) / total * 100, 1)}
            for col, rotulo in POPULACOES.items()
        ],
        key=lambda d: d["valor"], reverse=True,
    )

    # Desfecho (4 grupos) × população vulnerável
    grupos = ["Cura", "Interrupção", "Óbito", "Não avaliado"]
    desf_vuln = []
    unions = " UNION ALL ".join(
        f"""SELECT {_sql_literal(rotulo)} AS categoria, {_CASE_GRUPO} AS grupo, COUNT(*) AS casos
            FROM (SELECT *, {_CASE_DESFECHO} AS desfecho FROM sinan WHERE {where})
            WHERE lower({col}) = 'sim' GROUP BY 2"""
        for col, rotulo in POPULACOES.items()
    )
    dfv = _executar(unions, params * len(POPULACOES), f.anos)
    tab: dict[str, dict[str, int]] = {}
    for _, row in dfv.iterrows():
        tab.setdefault(row["categoria"], {})[row["grupo"]] = int(row["casos"])
    for rotulo in [POPULACOES[c] for c in POPULACOES]:
        contagens = tab.get(rotulo, {})
        n = sum(contagens.values())
        if n == 0:
            continue
        desf_vuln.append({
            "categoria": rotulo,
            "n": n,
            "pct": {g: round(contagens.get(g, 0) / n * 100, 1) for g in grupos},
        })

    # Heatmap: % de cada agravo por UF
    pct_agravos = ", ".join(
        f"round(COUNT(*) FILTER (WHERE lower(s.{col}) = 'sim') * 100.0 / COUNT(*), 1) AS {col}"
        for col in AGRAVOS
    )
    dfh = _executar(
        f"""
        SELECT u.sigla AS uf, COUNT(*) AS casos, {pct_agravos}
        FROM (SELECT * FROM sinan WHERE {where}) s
        JOIN ufs u ON s.estado_notificacao = u.nome
        GROUP BY 1 ORDER BY 1
        """,
        params, f.anos,
    )
    ufs_heat = dfh["uf"].tolist()
    rotulos_agravos = list(AGRAVOS.values())
    valores = []
    for i, (col, _rotulo) in enumerate(AGRAVOS.items()):
        for j, _uf in enumerate(ufs_heat):
            valores.append([j, i, float(dfh[col].iloc[j])])

    return {
        "agravos": agravos,
        "populacoes": populacoes,
        "total": int(r["total"]),
        "desfecho_por_vulneravel": {"grupos": grupos, "linhas": desf_vuln},
        "heatmap_uf": {"ufs": ufs_heat, "agravos": rotulos_agravos, "valores": valores},
    }


# ── Tendência histórica ───────────────────────────────────────────────────────

@lru_cache(maxsize=4)
def _csv_historico(nome: str) -> pd.DataFrame | None:
    caminho = {
        "mensal": HIST_MENSAL, "estadual": HIST_ESTADUAL,
        "anual": HIST_ANUAL, "indicadores": HIST_INDICADORES,
    }[nome]
    if not caminho.exists():
        return None
    try:
        return pd.read_csv(caminho)
    except Exception:
        return None


_MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
             "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

_INDICADORES_ROTULOS = {
    "pct_cura":     "Taxa de cura (%)",
    "pct_abandon":  "Taxa de abandono (%)",
    "pct_hiv":      "Coinfecção HIV (%)",
    "pct_pulm":     "Forma pulmonar (%)",
    "pct_test_hiv": "Testagem para HIV (%)",
    "pct_obito":    "Óbito por TB (%)",
    "pct_novo":     "Casos novos (%)",
    "pct_aids":     "AIDS (%)",
    "pct_alcool":   "Alcoolismo (%)",
}


@lru_cache(maxsize=512)
def tendencia(f: Filtros) -> dict:
    ano_ref = f.ano_ref
    anos_hist = [a for a in range(ANO_INICIO, ano_ref)]

    # Mensal do ano de referência, com filtros aplicados
    f_ano = Filtros(
        anos=(ano_ref,), ufs=f.ufs, sexo=f.sexo, formas=f.formas, racas=f.racas,
        entradas=f.entradas, hiv=f.hiv, vuln=f.vuln, agravos=f.agravos,
    )
    where, params = f_ano.where_sql()
    dfm = _executar(
        f"""
        SELECT month(data_notificacao) AS mes, COUNT(*) AS casos
        FROM sinan WHERE {where} AND data_notificacao IS NOT NULL
        GROUP BY 1 ORDER BY 1
        """,
        params, (ano_ref,),
    )
    casos_mes = {int(r["mes"]): int(r["casos"]) for _, r in dfm.iterrows()}

    # Média mensal histórica (CSV nacional pré-agregado)
    media_hist_mes: list[float | None] = [None] * 12
    media_anual_hist = 0.0
    hist_mensal = _csv_historico("mensal")
    if hist_mensal is not None and anos_hist:
        h = hist_mensal[hist_mensal["nu_ano"].isin(anos_hist)]
        if not h.empty:
            medias = h.groupby("mes_num")["casos"].mean()
            media_hist_mes = [round(float(medias.get(m, 0)), 0) for m in range(1, 13)]
            media_anual_hist = float(h.groupby("nu_ano")["casos"].sum().mean())

    total_ano = sum(casos_mes.values())
    variacao_pct = (
        round((total_ano - media_anual_hist) / media_anual_hist * 100, 1)
        if media_anual_hist else None
    )

    # Evolução anual (CSV)
    anual = []
    hist_anual = _csv_historico("anual")
    if hist_anual is not None:
        anual = [
            {"ano": int(r["nu_ano"]), "casos": int(r["casos"])}
            for _, r in hist_anual.iterrows()
        ]

    # Variação por estado: ano de referência (filtrado) vs média histórica (CSV)
    estadual = []
    hist_est = _csv_historico("estadual")
    if hist_est is not None and anos_hist:
        atual = {e["uf"]: e["casos"] for e in mapa_uf(f_ano)["estados"]}
        medias_uf = (
            hist_est[hist_est["nu_ano"].isin(anos_hist)]
            .groupby("uf_sigla")["casos"].mean()
        )
        for uf, media in medias_uf.items():
            casos_atuais = atual.get(uf, 0)
            if media > 0:
                estadual.append({
                    "uf": uf,
                    "nome": UF_NOMES.get(uf, uf),
                    "casos": casos_atuais,
                    "media_hist": round(float(media), 0),
                    "variacao_pct": round((casos_atuais - float(media)) / float(media) * 100, 1),
                })
        estadual.sort(key=lambda d: d["variacao_pct"], reverse=True)

    # Indicadores históricos (CSV)
    indicadores = None
    hist_ind = _csv_historico("indicadores")
    if hist_ind is not None:
        series = {
            rotulo: [
                (round(float(v), 1) if pd.notna(v) else None)
                for v in hist_ind[col]
            ]
            for col, rotulo in _INDICADORES_ROTULOS.items()
            if col in hist_ind.columns
        }
        indicadores = {"anos": hist_ind["nu_ano"].astype(int).tolist(), "series": series}

    return {
        "ano": ano_ref,
        "mensal": {
            "meses": _MESES_PT,
            "casos": [casos_mes.get(m, 0) for m in range(1, 13)],
            "media_hist": media_hist_mes,
        },
        "kpis": {
            "total_ano": total_ano,
            "media_anual_hist": round(media_anual_hist, 0),
            "variacao_pct": variacao_pct,
        },
        "anual": anual,
        "obitos_anual": obitos_sim_anual(),
        "estadual": estadual,
        "indicadores": indicadores,
    }


# ── Export CSV ────────────────────────────────────────────────────────────────

def export_csv(f: Filtros):
    """Gerador de chunks CSV (streaming) com os filtros aplicados."""
    from constantes import COLUNAS_EXPORT
    where, params = f.where_sql()
    cols = ", ".join(COLUNAS_EXPORT)
    files = _arquivos(f.anos)
    if not files:
        yield ""
        return
    files_sql = _files_sql(files)
    sql = f"""
        WITH {_CTE_UFS},
        sinan AS (SELECT * FROM read_parquet({files_sql}, union_by_name = true))
        SELECT {cols} FROM sinan WHERE {where}
    """
    with duckdb.connect() as con:
        con.execute(f"SET threads = {_THREADS}")
        resultado = con.execute(sql, params)
        primeira = True
        while True:
            chunk = resultado.fetch_df_chunk()
            if chunk is None or chunk.empty:
                break
            yield chunk.to_csv(index=False, header=primeira)
            primeira = False
