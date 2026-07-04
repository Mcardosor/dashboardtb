"""Baixa as RAs que faltam usando a OSM API direta."""
import json, time
from pathlib import Path
import requests

SAIDA   = Path("dados_dashboard") / "df_regioes_administrativas.geojson"
HEADERS = {"User-Agent": "dashboard-tb-sinan/1.0 (educational project)"}

FALTAM = [
    (2758138,  "Plano Piloto"),
    (3359465,  "Candangolândia"),
    (3359468,  "Fercal"),
    (3359469,  "Gama"),
    (3359473,  "Lago Norte"),
    (3359474,  "Lago Sul"),
    (3359475,  "Núcleo Bandeirante"),
    (3359479,  "Recanto das Emas"),
    (3359481,  "Riacho Fundo"),
    (3359482,  "Samambaia"),
    (3359483,  "Santa Maria"),
    (3359488,  "Sudoeste e Octogonal"),
    (3359489,  "São Sebastião"),
    (3359490,  "Taguatinga"),
    (12110991, "Arniqueira"),
]


def _extrair_anel(members, node_map):
    way_pts = {}
    for m in members:
        if m.get("type") != "way":
            continue
        nds = m.get("nd", []) or m.get("nodes", [])
        pts = [[node_map[n]["lon"], node_map[n]["lat"]] for n in nds if n in node_map]
        if pts:
            way_pts[m.get("ref", m.get("id"))] = pts

    if not way_pts:
        return None

    ordered, used = [], set()
    first = next(iter(way_pts))
    ordered.extend(way_pts[first]); used.add(first)

    changed = True
    while changed and len(used) < len(way_pts):
        changed = False
        tail = ordered[-1]
        for wid, pts in way_pts.items():
            if wid in used: continue
            if pts[0] == tail:
                ordered.extend(pts[1:]); used.add(wid); changed = True; break
            elif pts[-1] == tail:
                ordered.extend(list(reversed(pts))[1:]); used.add(wid); changed = True; break

    if ordered and ordered[0] != ordered[-1]:
        ordered.append(ordered[0])
    return ordered if len(ordered) >= 4 else None


def buscar_via_overpass(osm_id, nome):
    q = f"[out:json][timeout:60];relation({osm_id});out geom;"
    resp = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": q}, headers=HEADERS, timeout=70
    )
    if resp.status_code != 200:
        return None
    els = resp.json().get("elements", [])
    if not els: return None
    anel = None
    for el in els:
        if el.get("type") == "relation":
            members = el.get("members", [])
            # out geom embeds geometry in members
            way_pts = {}
            for m in members:
                if m.get("type") != "way": continue
                geom = m.get("geometry", [])
                if geom:
                    way_pts[m["ref"]] = [[g["lon"], g["lat"]] for g in geom]
            if way_pts:
                ordered, used = [], set()
                first = next(iter(way_pts))
                ordered.extend(way_pts[first]); used.add(first)
                changed = True
                while changed and len(used) < len(way_pts):
                    changed = False
                    tail = ordered[-1]
                    for wid, pts in way_pts.items():
                        if wid in used: continue
                        if pts[0] == tail:
                            ordered.extend(pts[1:]); used.add(wid); changed = True; break
                        elif pts[-1] == tail:
                            ordered.extend(list(reversed(pts))[1:]); used.add(wid); changed = True; break
                if ordered and ordered[0] != ordered[-1]:
                    ordered.append(ordered[0])
                if len(ordered) >= 4:
                    anel = ordered
                    break
    if not anel: return None
    return {
        "type": "Feature",
        "properties": {"RA_NOME": nome, "osm_id": osm_id},
        "geometry": {"type": "Polygon", "coordinates": [anel]},
    }


def main():
    gj = json.loads(SAIDA.read_text(encoding="utf-8"))
    features = {f["properties"]["osm_id"]: f for f in gj["features"]}
    print(f"Ja temos: {len(features)} RAs\n")

    for i, (osm_id, nome) in enumerate(FALTAM, 1):
        if osm_id in features:
            print(f"[{i:02d}] {nome} - ja existe, pulando")
            continue
        print(f"[{i:02d}/{len(FALTAM)}] {nome} (id={osm_id})...")
        feat = None
        for tentativa in range(3):
            if tentativa > 0:
                print(f"  aguardando 20s...")
                time.sleep(20)
            feat = buscar_via_overpass(osm_id, nome)
            if feat:
                break
            print(f"  tentativa {tentativa+1} falhou")

        if feat:
            features[osm_id] = feat
            print(f"  OK - {len(feat['geometry']['coordinates'][0])} pontos")
        else:
            print(f"  FALHOU definitivamente")
        time.sleep(3)

    gj["features"] = list(features.values())
    SAIDA.write_text(json.dumps(gj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nTotal: {len(features)}/35 RAs salvas")


if __name__ == "__main__":
    main()
