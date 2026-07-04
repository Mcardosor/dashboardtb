"""
baixar_ibge_municipios.py
─────────────────────────
Baixa shapefiles de municípios do IBGE 2022 para todos os 27 estados,
simplifica com topojson (Visvalingam-Whyatt, preservação de topologia)
e salva como GeoJSON.gz no geo_cache.

Diferença vs preparar_geo_cache.py:
  - Fonte: IBGE direto (não depende de geo_cache externo)
  - Simplificação: topojson (bordas compartilhadas preservadas → sem gaps)
  - Tolerância padrão: 0.005 (melhor que o atual 0.008)

Uso:
    python scripts/baixar_ibge_municipios.py           # todos os estados
    python scripts/baixar_ibge_municipios.py PE SP RJ  # estados específicos

Dependências:
    pip install topojson fiona shapely
"""

import gzip
import io
import json
import ssl
import sys
import time
import unicodedata
import urllib.request
import zipfile
from pathlib import Path

import fiona
import topojson

# ── Configuração ──────────────────────────────────────────────────────────────
IBGE_BASE = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/"
    "malhas_territoriais/malhas_municipais/municipio_2022/UFs"
)
DESTINO = Path(__file__).resolve().parent.parent / "dados_dashboard" / "_geo_cache" / "municipios"
DESTINO.mkdir(parents=True, exist_ok=True)

TOLERANCE = 0.005   # graus — topológico, muito melhor que shapely simples

UFS_ALL = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
    "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
    "RO","RR","RS","SC","SE","SP","TO",
]

# SSL sem verificação (certificado IBGE expirado frequentemente)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


# ── Helpers ───────────────────────────────────────────────────────────────────
def _norm(s: str) -> str:
    return (
        unicodedata.normalize("NFD", str(s))
        .encode("ascii", "ignore")
        .decode()
        .lower()
        .strip()
    )


def _baixar_zip(uf: str) -> bytes:
    url = f"{IBGE_BASE}/{uf}/{uf}_Municipios_2022.zip"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as r:
        return r.read()


def _ler_shapefile(zip_bytes: bytes) -> list[dict]:
    """Lê o .shp dentro do ZIP e retorna lista de features GeoJSON."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        shp_name = next(n for n in zf.namelist() if n.endswith(".shp"))
        # Extrai para memória temporária
        tmpdir = Path(__file__).parent / "_tmp_shp"
        tmpdir.mkdir(exist_ok=True)
        zf.extractall(tmpdir)
        shp_path = tmpdir / shp_name

    features = []
    with fiona.open(str(shp_path)) as src:
        for feat in src:
            props = dict(feat["properties"])
            # Normaliza nomes de colunas (IBGE pode variar)
            cd  = str(props.get("CD_MUN") or props.get("CD_GEOCMU") or props.get("GEOCODIGO") or "")
            nm  = str(props.get("NM_MUN") or props.get("NOME") or "")
            uf  = str(props.get("SIGLA_UF") or props.get("UF") or "")
            features.append({
                "type": "Feature",
                "geometry": dict(feat["geometry"]),
                "properties": {
                    "CD_MUN":     cd,
                    "NM_MUN":     nm,
                    "SIGLA_UF":   uf,
                    "NM_MUN_NORM": _norm(nm),
                },
            })

    # Limpa arquivos temporários
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    return features


def _simplificar_topologico(features: list[dict]) -> list[dict]:
    """
    Simplificação com preservação de topologia via topojson.
    Bordas compartilhadas entre municípios vizinhos são simplificadas
    juntas — elimina os gaps que o shapely.simplify() criava.
    """
    geojson = {"type": "FeatureCollection", "features": features}
    topo = topojson.Topology(geojson, prequantize=False)
    simplified = topo.togeojson(
        simplify=True,
        simplify_factor=TOLERANCE,
    )
    # togeojson pode retornar string ou dict
    if isinstance(simplified, str):
        simplified = json.loads(simplified)
    return simplified.get("features", features)


def processar_uf(uf: str) -> None:
    saida = DESTINO / f"uf={uf}" / "mun_simpl.geojson.gz"
    saida.parent.mkdir(parents=True, exist_ok=True)

    print(f"  [{uf}] Baixando IBGE 2022...", end=" ", flush=True)
    t0 = time.time()
    zip_bytes = _baixar_zip(uf)
    print(f"{len(zip_bytes)//1024} KB", end=" | ", flush=True)

    print("Lendo shapefile...", end=" ", flush=True)
    features = _ler_shapefile(zip_bytes)
    print(f"{len(features)} municípios", end=" | ", flush=True)

    print("Simplificando (topológico)...", end=" ", flush=True)
    features_simpl = _simplificar_topologico(features)
    print(f"{len(features_simpl)} features", end=" | ", flush=True)

    geojson_out = {"type": "FeatureCollection", "features": features_simpl}
    raw = json.dumps(geojson_out, ensure_ascii=False).encode("utf-8")
    with gzip.open(saida, "wb", compresslevel=9) as f:
        f.write(raw)

    elapsed = time.time() - t0
    print(f"Salvo {saida.stat().st_size//1024} KB [{elapsed:.0f}s]")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ufs = sys.argv[1:] if len(sys.argv) > 1 else UFS_ALL
    ufs = [u.upper() for u in ufs]
    invalidos = [u for u in ufs if u not in UFS_ALL]
    if invalidos:
        print(f"UFs inválidas: {invalidos}")
        sys.exit(1)

    print(f"Processando {len(ufs)} estado(s): {', '.join(ufs)}")
    print(f"Destino: {DESTINO}")
    print(f"Tolerância topológica: {TOLERANCE}°")
    print()

    erros = []
    for uf in ufs:
        try:
            processar_uf(uf)
        except Exception as e:
            print(f"ERRO: {e}")
            erros.append(uf)

    print()
    if erros:
        print(f"Falhou: {erros}")
    else:
        print(f"Concluído! {len(ufs)} estado(s) processado(s).")
        print("Reinicie o Streamlit para carregar os novos GeoJSONs.")
