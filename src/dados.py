"""
dados.py
--------
Funcoes de carregamento e cache dos dados do dashboard.
"""

import copy
import json
import requests
import streamlit as st
import pandas as pd
from io import StringIO
from pathlib import Path

from src.constantes import (
    GEOJSON_PATH, HIST_MENSAL, HIST_ESTADUAL, HIST_ANUAL,
    MUN_PARQUET, MUN_URL, UF_SIGLAS,
    NORMALIZAR_DESFECHO,
)


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


@st.cache_data(show_spinner="Carregando dados...", max_entries=6)
def carregar_dados(anos: tuple) -> pd.DataFrame:
    """
    Carrega os dados de um ou mais anos via DuckDB (max. 3 anos).
    anos: tupla ordenada de inteiros, ex: (2022,) ou (2022, 2023, 2024)
    Leitura colunar: so as colunas usadas pelo dashboard (COLUNAS_DASHBOARD)
    cache_data: resultado cacheado pela combinacao de anos (max 6 entradas)
    Colunas string convertidas para category no cache (~60% menos RAM).
    O app.py usa .astype(str) ao operar, então não vê dtype category.
    """
    from src.banco import query
    df = query("SELECT * FROM sinan", anos=anos)
    for col in _COLUNAS_CATEGORIA:
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df


@st.cache_resource(show_spinner=False)
def carregar_geojson() -> dict:
    """Carrega o GeoJSON dos estados brasileiros (leitura unica)."""
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(f"GeoJSON nao encontrado em {GEOJSON_PATH}")
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def geojson_enriquecido(casos_uf: pd.DataFrame) -> dict:
    """
    Retorna uma copia do GeoJSON com casos/incidencia/mortalidade injetados.
    Cacheado por casos_uf: so refaz o deepcopy quando os dados mudam.
    Evita deepcopy a cada rerun do Streamlit (operacao O(n) no GeoJSON inteiro).
    """
    geojson = carregar_geojson()
    gj = copy.deepcopy(geojson)
    for feat in gj["features"]:
        sigla = feat["properties"].get("sigla", "")
        row = casos_uf[casos_uf["uf_sigla"] == sigla]
        if not row.empty:
            r = row.iloc[0]
            feat["properties"]["casos"]       = int(r["casos"])
            feat["properties"]["incidencia"]  = float(r["incidencia"])
            feat["properties"]["mortalidade"] = float(r["mortalidade"])
        else:
            feat["properties"]["casos"]       = 0
            feat["properties"]["incidencia"]  = 0.0
            feat["properties"]["mortalidade"] = 0.0
    return gj


def selecionar_colunas(df: pd.DataFrame, colunas: tuple) -> pd.DataFrame:
    """Filtra apenas as colunas existentes no DataFrame."""
    return df[[c for c in colunas if c in df.columns]]


def render_pygwalker(df: pd.DataFrame, spec_path: str | None = None) -> None:
    """
    Renderiza o PyGWalker com kernel_computation=True — dados ficam no servidor,
    apenas agregações são enviadas ao browser. Sem limite de tamanho de mensagem.
    """
    try:
        import pygwalker as pyg
        import streamlit.components.v1 as components
        kwargs: dict = {"appearance": "light"}
        if spec_path and Path(spec_path).exists():
            kwargs["spec"] = spec_path
        pyg.walk(df, **kwargs)
    except Exception as e:
        st.error(f"PyGWalker indisponível: {e}")


def enriquecer_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas derivadas ao DataFrame para uso nos dashboards.
    Nao usa cache pois recebe df ja filtrado.
    Usa assign() para evitar copia completa do DataFrame.
    """
    extras: dict = {}

    if "estado_notificacao" in df.columns:
        extras["uf_sigla"] = (
            df["estado_notificacao"].astype(str)
            .map(UF_SIGLAS)
            .fillna("?")
        )

    if "situacao_encerramento" in df.columns:
        extras["situacao_enc_norm"] = (
            df["situacao_encerramento"].astype(str)
            .map(lambda x: NORMALIZAR_DESFECHO.get(x, x))
        )

    if "data_notificacao" in df.columns:
        try:
            dts = pd.to_datetime(df["data_notificacao"], errors="coerce")
            extras["mes_num"] = dts.dt.month
        except Exception:
            extras["mes_num"] = None

    return df.assign(**extras) if extras else df


@st.cache_data(show_spinner="Carregando historico...")
def load_historico() -> dict | None:
    """Carrega os CSVs pre-agregados de historico. Retorna dict ou None."""
    paths = {
        "mensal":   HIST_MENSAL,
        "estadual": HIST_ESTADUAL,
        "anual":    HIST_ANUAL,
    }
    if not all(p.exists() for p in paths.values()):
        return None
    try:
        return {k: pd.read_csv(str(v)) for k, v in paths.items()}
    except Exception:
        return None


@st.cache_resource(show_spinner="Carregando coordenadas dos municipios...")
def load_municipios() -> pd.DataFrame:
    """Carrega coordenadas dos municipios (local ou download)."""
    if MUN_PARQUET.exists():
        return pd.read_parquet(str(MUN_PARQUET))
    try:
        r = requests.get(MUN_URL, timeout=15)
        r.raise_for_status()
        mun = pd.read_csv(StringIO(r.text))
        mun["codigo_6"] = mun["codigo_ibge"].astype(str).str[:6]
        return mun[["codigo_6", "nome", "latitude", "longitude"]]
    except Exception:
        return pd.DataFrame(columns=["codigo_6", "nome", "latitude", "longitude"])


def agregar_por_uf(df: pd.DataFrame, enc_norm: pd.Series | None = None,
                   ano_sel: int | None = None, anos: list | None = None) -> pd.DataFrame:
    """
    Agrega casos, óbitos (fonte SIM), incidência e mortalidade por UF.
    Retorna DataFrame com colunas: uf_sigla, casos, casos_novos, obitos, populacao, incidencia, mortalidade.

    Incidência = CASOS NOVOS / pop (Caderno de Indicadores MS: Caso Novo + Não Sabe + Pós-óbito),
    não o total de casos — retratamentos/recidivas não entram no coeficiente de incidência.

    Coeficientes (por 100 mil) são ANUAIS: com múltiplos anos selecionados, anualizamos
    (média anual) dividindo por (população × nº de anos). Óbitos SIM são somados sobre
    todos os anos selecionados. `anos` = lista de anos; se omitida, usa [ano_sel].
    """
    from src.constantes import POP_ESTADO
    from src.banco import obitos_sim_por_uf

    _TIPOS_INC = {"Caso Novo", "Não Sabe", "Pós-óbito"}
    _anos = anos if anos else ([ano_sel] if ano_sel is not None else [])
    _n_anos = max(len(_anos), 1)

    casos_uf = df.groupby("uf_sigla", observed=True).size().reset_index(name="casos")

    # Casos novos por UF — denominador correto da incidência
    if "tipo_entrada" in df.columns:
        _novos = df[df["tipo_entrada"].astype(str).isin(_TIPOS_INC)]
        casos_novos_uf = _novos.groupby("uf_sigla", observed=True).size().reset_index(name="casos_novos")
        casos_uf = casos_uf.merge(casos_novos_uf, on="uf_sigla", how="left")
        casos_uf["casos_novos"] = casos_uf["casos_novos"].fillna(0).astype(int)
    else:
        casos_uf["casos_novos"] = casos_uf["casos"]

    # Mortalidade oficial: fonte SIM — soma sobre todos os anos selecionados
    if _anos:
        try:
            sim_uf = None
            for _a in _anos:
                _s = obitos_sim_por_uf(_a)
                sim_uf = _s if sim_uf is None else (
                    pd.concat([sim_uf, _s]).groupby("uf_sigla", as_index=False)["obitos_sim"].sum()
                )
            casos_uf = casos_uf.merge(sim_uf, on="uf_sigla", how="left")
            casos_uf = casos_uf.rename(columns={"obitos_sim": "obitos"})
        except Exception:
            casos_uf["obitos"] = 0
    elif enc_norm is not None:
        enc_s = enc_norm.copy()
        enc_s.index = df.index
        obitos_uf = (
            df.assign(_enc=enc_s)[df.assign(_enc=enc_s)["_enc"] == "Obito por TB"]
            .groupby("uf_sigla", observed=True).size().reset_index(name="obitos")
        )
        casos_uf = casos_uf.merge(obitos_uf, on="uf_sigla", how="left")
    else:
        casos_uf["obitos"] = 0

    casos_uf["obitos"]      = casos_uf["obitos"].fillna(0).astype(int)
    casos_uf["populacao"]   = casos_uf["uf_sigla"].map(POP_ESTADO)
    # Anualiza: divide por nº de anos para obter coeficiente anual médio
    casos_uf["incidencia"]  = (casos_uf["casos_novos"] / (casos_uf["populacao"] * _n_anos) * 100_000).round(1)
    casos_uf["mortalidade"] = (casos_uf["obitos"]      / (casos_uf["populacao"] * _n_anos) * 100_000).round(1)
    return casos_uf
