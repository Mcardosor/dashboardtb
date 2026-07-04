"""
baixar_ras_df.py
────────────────
Baixa as Regioes Administrativas do DF via Overpass API (OpenStreetMap)
e salva como GeoJSON em dados_dashboard/df_regioes_administrativas.geojson

Uso:
    python scripts/baixar_ras_df.py
"""

import json
import sys
import time
from pathlib import Path

import requests

SAIDA   = Path("dados_dashboard") / "df_regioes_administrativas.geojson"
HEADERS = {"User-Agent": "dashboard-tb-sinan/1.0 (educational project)"}
URL     = "https://overpass-api.de/api/interpreter"


def overpass(query: str, timeout: int = 60) -> dict:
    resp = requests.post(URL, data={"data": query}, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _extrair_anel(members: list) -> list | None:
    way_pts: dict[int, list] = {}
    for m in members:
        if m.get("type") != "way":
            continue
        geom = m.get("geometry", [])
        if geom:
            way_pts[m["ref"]] = [[g["lon"], g["lat"]] for g in geom]

    if not way_pts:
        return None

    ordered: list = []
    used: set = set()
    first_id = next(iter(way_pts))
    ordered.extend(way_pts[first_id])
    used.add(first_id)

    changed = True
    while changed and len(used) < len(way_pts):
        changed = False
        tail = ordered[-1]
        for wid, pts in way_pts.items():
            if wid in used:
                continue
            if pts[0] == tail:
                ordered.extend(pts[1:]); used.add(wid); changed = True; break
            elif pts[-1] == tail:
                ordered.extend(list(reversed(pts))[1:]); used.add(wid); changed = True; break

    if ordered and ordered[0] != ordered[-1]:
        ordered.append(ordered[0])
    return ordered if len(ordered) >= 4 else None


def buscar_ra(osm_id: int, nome: str, tentativas: int = 3) -> dict | None:
    for t in range(tentativas):
        if t > 0:
            espera = 15 * t
            print(f"    Aguardando {espera}s antes de tentar novamente...")
            time.sleep(espera)
        q = f"[out:json][timeout:60];relation({osm_id});out geom;"
        try:
            d = overpass(q, timeout=70)
            els = d.get("elements", [])
            if not els:
                return None
            anel = _extrair_anel(els[0].get("members", []))
            if anel:
                return {
                    "type": "Feature",
                    "properties": {"RA_NOME": nome, "osm_id": osm_id},
                    "geometry": {"type": "Polygon", "coordinates": [anel]},
                }
        except Exception as e:
            print(f"    Tentativa {t+1}: {str(e)[:60]}")
    return None


def main():
    # Carrega features ja baixadas (para retomar de onde parou)
    existentes: dict[int, dict] = {}
    if SAIDA.exists():
        try:
            gj = json.loads(SAIDA.read_text(encoding="utf-8"))
            for f in gj.get("features", []):
                existentes[f["properties"]["osm_id"]] = f
            print(f"{len(existentes)} RAs ja baixadas anteriormente")
        except Exception:
            pass

    # Passo 1: busca IDs
    print("Buscando IDs das Regioes Administrativas...")
    q_ids = """
[out:json][timeout:60];
area["name"="Distrito Federal"]["boundary"="administrative"]->.df;
relation["boundary"="administrative"]["admin_level"="8"](area.df);
out tags;
"""
    try:
        data = overpass(q_ids)
    except Exception as e:
        print(f"Erro: {e}"); sys.exit(1)

    ras = [(el["id"], el["tags"].get("name", "?"))
           for el in data.get("elements", [])
           if el.get("type") == "relation"]
    print(f"  {len(ras)} RAs no OSM")

    # Passo 2: busca geometria das que faltam
    features = dict(existentes)
    pendentes = [(oid, nome) for oid, nome in ras if oid not in features]
    print(f"  {len(pendentes)} RAs para baixar\n")

    for i, (osm_id, nome) in enumerate(pendentes, 1):
        print(f"[{i:02d}/{len(pendentes)}] {nome}...")
        feat = buscar_ra(osm_id, nome)
        if feat:
            features[osm_id] = feat
            print(f"  OK ({len(feat['geometry']['coordinates'][0])} pontos)")
        else:
            print(f"  FALHOU")
        time.sleep(2)

    if not features:
        print("Nenhuma feature gerada."); sys.exit(1)

    geojson = {"type": "FeatureCollection", "features": list(features.values())}
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(features)}/{len(ras)} RAs salvas em: {SAIDA}")


if __name__ == "__main__":
    main()
