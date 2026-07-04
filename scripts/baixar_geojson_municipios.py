"""
baixar_geojson_municipios.py
────────────────────────────
Baixa e salva os GeoJSONs de municípios (por estado) e os nomes/códigos
municipais via API pública do IBGE. Execute uma única vez antes de rodar
o dashboard.

Uso:
    python scripts/baixar_geojson_municipios.py          # todos os estados
    python scripts/baixar_geojson_municipios.py SP RJ MG # estados específicos
"""

import json
import sys
import time
from pathlib import Path

import requests

# ── Mapeamento UF → código numérico IBGE ──────────────────────────────────────
IBGE_UF_CODES: dict[str, int] = {
    "AC": 12, "AL": 27, "AP": 16, "AM": 13, "BA": 29, "CE": 23,
    "DF": 53, "ES": 32, "GO": 52, "MA": 21, "MT": 51, "MS": 50,
    "MG": 31, "PA": 15, "PB": 25, "PR": 41, "PE": 26, "PI": 22,
    "RJ": 33, "RN": 24, "RS": 43, "RO": 11, "RR": 14, "SC": 42,
    "SP": 35, "SE": 28, "TO": 17,
}

PASTA_MUNICIPIOS = Path("dados_dashboard") / "municipios"
TIMEOUT = 30  # segundos por request


def baixar_geojson(uf: str, cod: int) -> None:
    """Baixa o GeoJSON de municípios de um estado e salva em disco."""
    path_geo = PASTA_MUNICIPIOS / f"{uf}_geojson.json"
    path_nomes = PASTA_MUNICIPIOS / f"{uf}_nomes.json"

    # ── GeoJSON (polígonos dos municípios) ─────────────────────────────────────
    if not path_geo.exists():
        url = (
            f"https://servicodados.ibge.gov.br/api/v3/malhas/estados/{cod}"
            f"?formato=application/vnd.geo+json&resolucao=5"
        )
        print(f"  [{uf}] Baixando GeoJSON...", end=" ", flush=True)
        r = requests.get(url, timeout=TIMEOUT)
        r.raise_for_status()
        path_geo.write_text(r.text, encoding="utf-8")
        print("OK")
        time.sleep(0.3)  # respeitar rate limit da API
    else:
        print(f"  [{uf}] GeoJSON já existe, pulando.")

    # ── Nomes dos municípios (código IBGE → nome) ──────────────────────────────
    if not path_nomes.exists():
        url_nomes = (
            f"https://servicodados.ibge.gov.br/api/v1/localidades"
            f"/estados/{uf}/municipios"
        )
        print(f"  [{uf}] Baixando nomes...", end=" ", flush=True)
        r = requests.get(url_nomes, timeout=TIMEOUT)
        r.raise_for_status()
        # Salva só o que o dashboard precisa: {codarea: nome}
        municipios = {str(m["id"]): m["nome"] for m in r.json()}
        path_nomes.write_text(
            json.dumps(municipios, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("OK")
        time.sleep(0.3)
    else:
        print(f"  [{uf}] Nomes já existem, pulando.")


def main() -> None:
    PASTA_MUNICIPIOS.mkdir(parents=True, exist_ok=True)

    ufs = [u.upper() for u in sys.argv[1:]] if len(sys.argv) > 1 else list(IBGE_UF_CODES)
    invalidos = [u for u in ufs if u not in IBGE_UF_CODES]
    if invalidos:
        print(f"AVISO: UFs desconhecidas ignoradas: {invalidos}")
        ufs = [u for u in ufs if u in IBGE_UF_CODES]

    print(f"Baixando dados de {len(ufs)} estado(s)...\n")
    for uf in ufs:
        try:
            baixar_geojson(uf, IBGE_UF_CODES[uf])
        except Exception as e:
            print(f"  [{uf}] ERRO: {e}")

    print(f"\nConcluído. Arquivos salvos em: {PASTA_MUNICIPIOS.resolve()}")


if __name__ == "__main__":
    main()
