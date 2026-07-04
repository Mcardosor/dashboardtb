"""
preparar_geo_cache.py
─────────────────────
Lê os GeoJSONs comprimidos do geo_cache dos colaboradores,
simplifica as geometrias para uso no dashboard Plotly e salva
em dados_dashboard/_geo_cache/.

Por que simplificar:
  - Os arquivos originais têm resolução máxima do IBGE (~60 MB p/ SP)
  - Plotly envia o GeoJSON ao browser de cada usuário → precisa ser leve
  - tolerance=0.01° ≈ 1 km: imperceptível na escala de dashboard, reduz ~80% dos vértices

Uso:
    python scripts/preparar_geo_cache.py                 # usa caminho padrão
    python scripts/preparar_geo_cache.py /caminho/geo_cache

Dependências (só para este script, não para o app):
    pip install shapely --break-system-packages
"""

import gzip
import json
import sys
import time
import unicodedata
from pathlib import Path

try:
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union
except ImportError:
    print("Instalando shapely...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "shapely",
                           "--break-system-packages", "-q"])
    from shapely.geometry import mapping, shape
    from shapely.ops import unary_union

# ── Caminhos ───────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

# Fonte: geo_cache dos colaboradores (ajuste se necessário)
GEO_CACHE_ORIGEM = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    Path(r"C:\Users\Matheus\Downloads\BR_2026_04_24\update\update")
    / "data" / "parquet" / "dashboard" / "_geo_cache"
)

# Destino: nosso projeto
GEO_CACHE_DESTINO = ROOT / "dados_dashboard" / "_geo_cache"

TOLERANCE = 0.008   # graus decimais ≈ 800 m — suficiente para visualização

UFS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
    "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
    "RO","RR","RS","SC","SE","SP","TO",
]


def _norm(s: str) -> str:
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower().strip()


def _simplify_feature(feat: dict, tolerance: float) -> dict:
    """Simplifica a geometria de uma feature GeoJSON usando Shapely."""
    try:
        geom = shape(feat["geometry"])
        geom = geom.simplify(tolerance, preserve_topology=True)
        feat = dict(feat)
        feat["geometry"] = mapping(geom)
    except Exception:
        pass
    return feat


def _strip_props(feat: dict, keep: list[str]) -> dict:
    """Mantém apenas as propriedades essenciais para reduzir tamanho."""
    feat = dict(feat)
    feat["properties"] = {k: feat["properties"][k]
                          for k in keep if k in feat["properties"]}
    return feat


def processar_estados() -> None:
    src = GEO_CACHE_ORIGEM / "br_ufs.geojson.gz"
    dst = GEO_CACHE_DESTINO / "br_ufs.geojson.gz"
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(f"  AVISO: {src} não encontrado, pulando.")
        return

    with gzip.open(src, "rt", encoding="utf-8") as f:
        geo = json.load(f)

    # Simplifica e mantém só uf + nome_uf
    features = []
    for feat in geo.get("features", []):
        feat = _strip_props(feat, ["uf", "nome_uf"])
        feat = _simplify_feature(feat, TOLERANCE * 1.5)   # estados têm borda mais suave
        features.append(feat)

    geo["features"] = features
    raw = json.dumps(geo, ensure_ascii=False, separators=(",", ":"))
    with gzip.open(dst, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(raw)

    size_kb = dst.stat().st_size / 1024
    print(f"  br_ufs.geojson.gz  →  {size_kb:.0f} KB  ({len(features)} estados)")


def processar_municipios() -> None:
    mun_dst_base = GEO_CACHE_DESTINO / "municipios"

    for uf in UFS:
        src = GEO_CACHE_ORIGEM / "municipios" / f"uf={uf}" / "mun.geojson.gz"
        if not src.exists():
            print(f"  AVISO: {src} não encontrado, pulando {uf}.")
            continue

        dst_dir = mun_dst_base / f"uf={uf}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "mun_simpl.geojson.gz"

        t0 = time.time()
        with gzip.open(src, "rt", encoding="utf-8") as f:
            geo = json.load(f)

        n_orig = len(geo.get("features", []))
        features = []
        for feat in geo.get("features", []):
            # Mantém apenas propriedades essenciais
            feat = _strip_props(feat, ["CD_MUN", "NM_MUN", "SIGLA_UF"])
            # Adiciona nome normalizado para join com dados SINAN
            nm = feat["properties"].get("NM_MUN", "")
            feat["properties"]["NM_MUN_NORM"] = _norm(nm)
            # Simplifica geometria
            feat = _simplify_feature(feat, TOLERANCE)
            features.append(feat)

        geo["features"] = features
        raw = json.dumps(geo, ensure_ascii=False, separators=(",", ":"))
        with gzip.open(dst, "wt", encoding="utf-8", compresslevel=9) as f:
            f.write(raw)

        size_kb = dst.stat().st_size / 1024
        elapsed = time.time() - t0
        print(f"  {uf}  {n_orig:>4} mun  →  {size_kb:>6.0f} KB  ({elapsed:.1f}s)")


# ── Main ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Origem : {GEO_CACHE_ORIGEM}")
    print(f"Destino: {GEO_CACHE_DESTINO}\n")

    if not GEO_CACHE_ORIGEM.exists():
        print(f"ERRO: geo_cache de origem não encontrado em {GEO_CACHE_ORIGEM}")
        print("Passe o caminho como argumento: python scripts/preparar_geo_cache.py /caminho")
        sys.exit(1)

    t_total = time.time()

    print("[1/2] Processando estados...")
    processar_estados()

    print("\n[2/2] Processando municípios...")
    processar_municipios()

    elapsed = time.time() - t_total
    total_kb = sum(f.stat().st_size for f in GEO_CACHE_DESTINO.rglob("*.gz")) / 1024
    print(f"\nConcluído em {elapsed:.0f}s — total no destino: {total_kb:.0f} KB")
