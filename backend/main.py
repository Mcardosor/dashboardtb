"""
main.py — API do Dashboard TB · SINAN (FastAPI + DuckDB).

Rotas:
    GET /api/meta                     anos disponíveis + opções de filtro
    GET /api/resumo                   KPIs do topo
    GET /api/mapa                     agregado por UF (choropleth + ranking)
    GET /api/uf/{sigla}               drill-down municipal de um estado
    GET /api/perfil                   perfil dos pacientes
    GET /api/clinico                  clínico & diagnóstico
    GET /api/comorbidades             comorbidades & vulnerabilidades
    GET /api/tendencia                série histórica
    GET /api/geojson/estados          GeoJSON do Brasil (pré-gzipado)
    GET /api/geojson/municipios/{uf}  GeoJSON municipal de uma UF (pré-gzipado)
    GET /api/export.csv               dados filtrados em CSV (streaming)

Todos os endpoints de dados aceitam os mesmos filtros (ver filtros.py).

Em produção o build do frontend (frontend/dist) é servido pela própria API.

Rodar em desenvolvimento:
    cd backend && uvicorn main:app --reload --port 8000
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

import consultas
from constantes import GEO_CACHE, UF_NOMES
from filtros import Filtros, parse_filtros

app = FastAPI(
    title="Dashboard TB · SINAN — API",
    description="Agregações epidemiológicas de tuberculose (SINAN NET, 2001–2026).",
    version="2.0.0",
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

_CACHE_API = {"Cache-Control": "public, max-age=300"}
_CACHE_GEO = {"Cache-Control": "public, max-age=86400"}


@app.on_event("startup")
def _warmup():
    """Pré-aquece meta + tabela SIM em background — sem bloquear o 1º request."""
    import threading

    def _bg():
        try:
            consultas.meta()
            consultas._sim_tabela()
        except Exception:
            pass

    threading.Thread(target=_bg, daemon=True).start()


def _filtros(
    anos: str | None = Query(None, description="Anos, ex: 2024,2025"),
    ufs: str | None = Query(None, description="Siglas de UF, ex: SP,RJ"),
    sexo: str | None = Query(None),
    formas: str | None = Query(None),
    racas: str | None = Query(None),
    entradas: str | None = Query(None),
    hiv: str | None = Query(None),
    vuln: str | None = Query(None),
    agravos: str | None = Query(None),
) -> Filtros:
    disponiveis = consultas.anos_disponiveis()
    if not disponiveis:
        raise HTTPException(503, "Nenhum Parquet tratado em dados_dashboard/.")
    return parse_filtros(anos, disponiveis, ufs, sexo, formas, racas,
                         entradas, hiv, vuln, agravos)


from fastapi import Depends  # noqa: E402

FiltrosDep = Depends(_filtros)


@app.get("/api/meta")
def rota_meta():
    return consultas.meta()


@app.get("/api/resumo")
def rota_resumo(f: Filtros = FiltrosDep):
    return Response(
        content=_json(consultas.resumo(f)),
        media_type="application/json", headers=_CACHE_API,
    )


@app.get("/api/mapa")
def rota_mapa(f: Filtros = FiltrosDep):
    return Response(
        content=_json(consultas.mapa_uf(f)),
        media_type="application/json", headers=_CACHE_API,
    )


@app.get("/api/uf/{sigla}")
def rota_uf(sigla: str, f: Filtros = FiltrosDep):
    sigla = sigla.upper()
    if sigla not in UF_NOMES:
        raise HTTPException(404, f"UF desconhecida: {sigla}")
    return Response(
        content=_json(consultas.detalhe_uf(f, sigla)),
        media_type="application/json", headers=_CACHE_API,
    )


@app.get("/api/perfil")
def rota_perfil(f: Filtros = FiltrosDep):
    return Response(
        content=_json(consultas.perfil(f)),
        media_type="application/json", headers=_CACHE_API,
    )


@app.get("/api/clinico")
def rota_clinico(f: Filtros = FiltrosDep):
    return Response(
        content=_json(consultas.clinico(f)),
        media_type="application/json", headers=_CACHE_API,
    )


@app.get("/api/comorbidades")
def rota_comorbidades(f: Filtros = FiltrosDep):
    return Response(
        content=_json(consultas.comorbidades(f)),
        media_type="application/json", headers=_CACHE_API,
    )


@app.get("/api/tendencia")
def rota_tendencia(f: Filtros = FiltrosDep):
    return Response(
        content=_json(consultas.tendencia(f)),
        media_type="application/json", headers=_CACHE_API,
    )


# ── GeoJSON: arquivos já gzipados em disco, servidos com Content-Encoding ─────

def _servir_gz(caminho: Path) -> Response:
    if not caminho.exists():
        raise HTTPException(404, "GeoJSON não encontrado.")
    return Response(
        content=caminho.read_bytes(),
        media_type="application/json",
        headers={**_CACHE_GEO, "Content-Encoding": "gzip"},
    )


@app.get("/api/geojson/estados")
def rota_geo_estados():
    return _servir_gz(GEO_CACHE / "br_ufs.geojson.gz")


@app.get("/api/geojson/municipios/{uf}")
def rota_geo_municipios(uf: str):
    uf = uf.upper()
    if uf not in UF_NOMES:
        raise HTTPException(404, f"UF desconhecida: {uf}")
    return _servir_gz(GEO_CACHE / "municipios" / f"uf={uf}" / "mun_simpl.geojson.gz")


# ── Export CSV (streaming) ────────────────────────────────────────────────────

@app.get("/api/export.csv")
def rota_export(f: Filtros = FiltrosDep):
    if len(f.anos) > 5:
        raise HTTPException(400, "Export limitado a 5 anos por vez.")
    nome = f"sinan_tb_{'-'.join(str(a) for a in f.anos)}.csv"
    return StreamingResponse(
        consultas.export_csv(f),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


# ── JSON rápido ───────────────────────────────────────────────────────────────

import json  # noqa: E402


def _json(dados: dict) -> bytes:
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# ── Frontend estático (produção) ──────────────────────────────────────────────

_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if _DIST.exists():
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="frontend")
