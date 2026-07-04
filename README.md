# Dashboard TB · SINAN NET

Painel de vigilância epidemiológica da tuberculose no Brasil, a partir das notificações do SINAN NET (2001–2026).

Acesso: https://telessaude.unb.br/cenarios/tb

## Duas versões no repositório

| Versão | Stack | Onde |
|---|---|---|
| **v2 (atual)** | React + Vite + ECharts no browser · FastAPI + DuckDB no servidor | `frontend/` + `backend/` |
| v1 (legada) | Streamlit + Plotly + Folium | `app.py` + `src/` |

A v2 nasceu para resolver os gargalos de performance da v1: em vez de recarregar
DataFrames de milhões de linhas a cada interação (modelo Streamlit), o backend
responde **apenas agregados em JSON** (5–200 KB) calculados pelo DuckDB direto
nos Parquets, e o browser renderiza tudo em canvas (ECharts). Resultado:

- Troca de filtro: **~20–200 ms** de API (com cache LRU, ~0 ms)
- Troca de aba: instantânea (cache TanStack Query no browser)
- Sem limite de 3 anos: dá para filtrar a **série completa 2001–2026**
- Bundle: ~275 KB gzip · sem tiles externos (GeoJSON local)

## Documentação

- **[docs/ARQUITETURA.md](docs/ARQUITETURA.md)** — documentação técnica completa: arquitetura, contratos da API, módulos, convenções epidemiológicas e o **checklist para usar este projeto como modelo de outros dashboards**.
- **[docs/COMO_FOI_FEITO.md](docs/COMO_FOI_FEITO.md)** — making-of didático: o passo a passo da construção, as decisões e seus porquês, os problemas encontrados e a receita replicável.
- `http://localhost:8000/docs` — Swagger interativo da API (gerado automaticamente).

## Conteúdo

- KPIs: incidência, mortalidade (SIM quando disponível), óbitos, cura, abandono e coinfecção HIV
- Distribuição geográfica: mapa coroplético por estado com drill-down para municípios (mapa municipal + coorte + top-N + tabela)
- Perfil dos pacientes: sexo, raça/cor, forma clínica, tipo de entrada, desfechos, pirâmides etárias (casos e óbitos)
- Clínico & diagnóstico: HIV, baciloscopia, TMR-TB, desfecho por status HIV, coinfecção por UF, oportunidade do tratamento
- Comorbidades & vulnerabilidades: agravos, populações vulneráveis, desfecho por grupo, heatmap comorbidade × UF
- Tendência histórica: série 2001–2026, mensal vs média histórica, óbitos SIM, variação por estado, indicadores clínicos
- Dados: download do CSV filtrado (streaming DuckDB, até 5 anos por vez)

## Como rodar (v2)

```bash
# Backend — FastAPI + DuckDB (porta 8000)
pip install -r backend/requirements.txt
uvicorn main:app --app-dir backend --port 8000

# Frontend — dev com HMR (porta 5173, proxy /api → 8000)
cd frontend
npm install
npm run dev
```

Produção: `npm run build` gera `frontend/dist`, que o próprio FastAPI serve —
um único processo atende API + estáticos:

```bash
cd frontend && npm run build && cd ..
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Docker (multi-stage, Node + Python):

```bash
docker build -f Dockerfile.api -t dashboard-tb-api .
docker run -p 8000:8000 -v ./dados_dashboard:/app/dados_dashboard --env-file .env dashboard-tb-api
```

A versão Streamlit continua funcionando: `streamlit run app.py`.

## Arquitetura (v2)

```
browser (React + ECharts)
   │  JSON agregado (gzip, cache 5 min)
   ▼
FastAPI (backend/main.py)
   │  SQL parametrizado, lru_cache por combinação de filtros
   ▼
DuckDB ─ lê apenas os Parquets dos anos filtrados (projection pushdown)
   │
dados_dashboard/tuberculose_{ano}_tratado.parquet  (~2 MB/ano)
```

- **Filtros**: todos os endpoints aceitam os mesmos query params
  (`anos`, `ufs`, `sexo`, `formas`, `racas`, `entradas`, `hiv`, `vuln`, `agravos`).
- **Óbitos oficiais (SIM)**: uma única query agregada ano×UF no PostgreSQL,
  cacheada em `dados_dashboard/_cache_sim_obitos.csv` (TTL 7 dias). Sem VPN,
  a API usa o cache em disco; sem cache, cai para o desfecho SINAN e marca
  `fonte_obitos: "SINAN"` na resposta.
- **GeoJSON**: servido dos `.gz` já existentes em `_geo_cache/` com
  `Content-Encoding: gzip` (zero recompressão). Estados casam por
  `properties.uf`; municípios por nome normalizado (`NM_MUN` sem acento).
- **Incidência**: casos novos (Caso Novo + Não Sabe + Pós-óbito, Caderno de
  Indicadores MS) / população IBGE 2022, anualizada quando há múltiplos anos.

### Endpoints

```
GET /api/meta                     anos disponíveis + opções de filtro
GET /api/resumo                   KPIs do topo
GET /api/mapa                     agregado por UF
GET /api/uf/{sigla}               drill-down municipal + coorte do estado
GET /api/perfil                   perfil dos pacientes
GET /api/clinico                  clínico & diagnóstico
GET /api/comorbidades             comorbidades & vulnerabilidades
GET /api/tendencia                série histórica
GET /api/geojson/estados          GeoJSON Brasil (gzip)
GET /api/geojson/municipios/{uf}  GeoJSON municipal (gzip)
GET /api/export.csv               microdados filtrados (streaming)
```

Documentação interativa: `http://localhost:8000/docs`.

## Pipeline de dados (inalterado)

```bash
pip install -r requirements-pipeline.txt
cp .env.example .env   # credenciais do PostgreSQL (VPN)

python scripts/conectar_banco.py 2001 2026   # PostgreSQL → Parquet bruto
python scripts/preparar_dados.py 2001 2026   # → Parquet otimizado (_tratado)
python scripts/gerar_historico.py            # → CSVs da aba Tendência
```

## Estrutura

```
dashboard-tb-sinan/
├── backend/                  # API FastAPI + DuckDB (v2)
│   ├── main.py               #   rotas, gzip, static, warmup
│   ├── consultas.py          #   agregações SQL + caches
│   ├── filtros.py            #   query params → WHERE parametrizado
│   └── constantes.py         #   populações, paletas, mapeamentos
├── frontend/                 # React + Vite + TS + Tailwind + ECharts (v2)
│   └── src/
│       ├── App.tsx            #   casca: topbar, hero, KPIs, abas
│       ├── api.ts             #   tipos + hooks TanStack Query
│       ├── state.tsx          #   filtros globais (Context)
│       ├── theme.ts           #   paleta TB + registro ECharts
│       ├── charts.ts          #   construtores de gráficos compartilhados
│       ├── components/        #   Hero, KpiCards, Sidebar, UfModal, Chart…
│       └── tabs/              #   Mapa, Perfil, Clínico, Comorb., Tendência, Dados
├── app.py + src/             # dashboard Streamlit (v1, legado)
├── scripts/                  # pipeline ETL PostgreSQL → Parquet
├── dados_dashboard/          # Parquets, GeoJSON, históricos (não versionado)
├── Dockerfile.api            # build produção v2 (Node + Python)
└── Dockerfile                # build produção v1 (Streamlit)
```

Fonte: SINAN NET (Ministério da Saúde). Cobertura: Brasil, 2001–2026. Última atualização: julho/2026.
