# Arquitetura do Dashboard TB · SINAN v2

> Documentação técnica completa. Este projeto foi desenhado para servir de
> **modelo** para outros dashboards epidemiológicos — a última seção é um
> checklist de adaptação para um novo painel.

---

## 1. Visão geral

```
┌─────────────────────────────────────────────────────────────┐
│  BROWSER                                                    │
│  React 18 + TypeScript + Tailwind v4                        │
│  ECharts (canvas) · TanStack Query (cache de dados)         │
│  bundle: ~275 KB gzip                                       │
└──────────────┬──────────────────────────────────────────────┘
               │ GET /api/*  →  JSON agregado (1–5 KB, gzip)
               │ Cache-Control: max-age=300
┌──────────────▼──────────────────────────────────────────────┐
│  FASTAPI (backend/main.py)                                  │
│  · mesmos filtros em todos os endpoints (query params)      │
│  · lru_cache por combinação de filtros                      │
│  · GZipMiddleware · serve frontend/dist em produção         │
└──────────────┬──────────────────────────────────────────────┘
               │ SQL parametrizado (CTE `sinan`)
┌──────────────▼──────────────────────────────────────────────┐
│  DUCKDB (in-process, conexão por request)                   │
│  · lê SÓ os Parquets dos anos filtrados                     │
│  · projection pushdown: lê só as colunas citadas no SQL     │
│  · paralelismo: SET threads = nº de CPUs                    │
└──────────────┬──────────────────────────────────────────────┘
               │
   dados_dashboard/tuberculose_{ano}_tratado.parquet  (~2 MB/ano)
   dados_dashboard/_geo_cache/*.geojson.gz            (mapas)
   dados_dashboard/historico_*.csv                    (série histórica)
   dados_dashboard/_cache_sim_obitos.csv              (óbitos SIM, TTL 7d)
```

**O princípio central**: dado agregado viaja, microdado não. O browser nunca
recebe milhões de linhas — recebe contagens, percentuais e séries prontas para
plotar. É isso que faz o painel ser rápido: cada interação custa uma query
DuckDB de dezenas de milissegundos e um JSON de poucos KB.

### Números medidos

| Operação | Tempo |
|---|---|
| Agregação DuckDB (1 ano, ~116 mil linhas) | 20–220 ms |
| Agregação DuckDB (3 anos, ~340 mil linhas) | 30–250 ms |
| Endpoint com cache quente (lru_cache) | < 1 ms |
| Resposta na rede (gzip, cache do browser) | 3–6 ms |
| Build do frontend | ~3,5 s |
| Bundle JS gzip (echarts 219 KB + react 57 KB + app 17 KB) | ~275 KB |

---

## 2. Estrutura de pastas

```
dashboard-tb-sinan/
├── backend/                     # API (Python)
│   ├── main.py                  # rotas FastAPI, middlewares, static
│   ├── consultas.py             # TODAS as agregações SQL + caches
│   ├── filtros.py               # query params → WHERE parametrizado
│   ├── constantes.py            # populações, mapeamentos, paths
│   └── requirements.txt
├── frontend/                    # UI (TypeScript)
│   ├── index.html
│   ├── vite.config.ts           # proxy /api → :8000 em dev
│   ├── tsconfig.json
│   ├── package.json
│   └── src/
│       ├── main.tsx             # bootstrap React + QueryClient
│       ├── App.tsx              # casca: topbar, hero, KPIs, abas
│       ├── state.tsx            # filtros globais (Context)
│       ├── api.ts               # tipos da API + hooks TanStack Query
│       ├── theme.ts             # paleta, registro ECharts tree-shaken
│       ├── charts.ts            # construtores de gráficos reutilizáveis
│       ├── index.css            # Tailwind v4 + classes customizadas
│       ├── components/
│       │   ├── Chart.tsx        # wrapper ECharts (init/resize/dispose)
│       │   ├── Hero.tsx         # cabeçalho com badges
│       │   ├── KpiCards.tsx     # grade de 8 KPIs
│       │   ├── Sidebar.tsx      # filtros
│       │   ├── UfModal.tsx      # drill-down de estado
│       │   └── ui.tsx           # ChartCard, Skeleton, CountUp, Metrica
│       └── tabs/
│           ├── MapaTab.tsx
│           ├── PerfilTab.tsx
│           ├── ClinicoTab.tsx
│           ├── ComorbidadesTab.tsx
│           ├── TendenciaTab.tsx
│           └── DadosTab.tsx
├── dados_dashboard/             # dados (não versionado, exceto geo)
├── scripts/                     # ETL PostgreSQL → Parquet (inalterado da v1)
├── app.py + src/                # dashboard Streamlit legado (v1)
├── Dockerfile.api               # build produção v2
└── docs/
    ├── ARQUITETURA.md           # este arquivo
    └── COMO_FOI_FEITO.md        # making-of passo a passo
```

---

## 3. Backend

### 3.1 `constantes.py` — dados de referência

Sem dependências pesadas (importa em <10 ms). Contém:

- `POP_ESTADO` / `POP_BRASIL` — populações IBGE 2022 (denominador de taxas)
- `UF_SIGLAS` / `UF_NOMES` / `UF_VARIANTES` — o SINAN grava o estado por
  extenso, com e sem acento ("Sao Paulo"/"São Paulo"); os mapeamentos cobrem
  todas as variantes
- `DESFECHO_CANONICO` — normaliza `situacao_encerramento` para a forma
  acentuada canônica; `Não informado`/NULL viram "Em acompanhamento"
- `DESFECHO_GRUPO` — desfecho → 4 grupos de coorte (Cura, Interrupção,
  Óbito, Não avaliado)
- `TIPOS_INCIDENCIA` — tipos de entrada que contam no numerador da
  incidência (Caderno de Indicadores do MS)
- `AGRAVOS` / `POPULACOES` — colunas booleanas ("Sim"/"Não") e seus rótulos
- `COLUNAS_EXPORT` — colunas expostas no CSV
- `FAIXAS_ETARIAS` — bins da pirâmide

### 3.2 `filtros.py` — filtros como valor imutável

```python
@dataclass(frozen=True)
class Filtros:
    anos: tuple[int, ...]
    ufs: tuple[str, ...] = ()
    sexo: tuple[str, ...] = ()
    # ... formas, racas, entradas, hiv, vuln, agravos
```

Três decisões importantes aqui:

1. **`frozen=True` + tuplas** → o objeto é hasheável e serve de **chave de
   cache** direto no `lru_cache`. Filtro igual = resposta instantânea.
2. **`where_sql()`** monta a cláusula WHERE com placeholders `?` — valores do
   usuário **nunca** são interpolados no SQL (proteção contra injection).
   Nomes de colunas (vuln/agravos) são validados contra whitelist.
3. **Semântica "vazio = todos"**: filtro sem valores não gera WHERE. O
   frontend só envia o parâmetro quando o usuário restringiu algo.

`parse_filtros()` valida tudo que chega da query string: anos fora do
catálogo são descartados, siglas de UF inexistentes ignoradas, listas
ordenadas (para a mesma seleção gerar a mesma chave de cache).

### 3.3 `consultas.py` — o coração

Toda query passa por `_executar(sql, params, anos)`:

```python
WITH ufs(nome, sigla) AS (VALUES ('Acre','AC'), ...),   -- lookup de UF
sinan AS (SELECT * FROM read_parquet([<arquivos dos anos>],
                                     union_by_name = true))
<sql do chamador>
```

- **Só os arquivos dos anos filtrados** entram no `read_parquet` — filtrar
  um ano lê ~2 MB, não a base toda.
- O `SELECT *` da CTE é seguro: o DuckDB faz *projection pushdown* e só lê
  do disco as colunas que o SQL do chamador realmente cita.
- Conexão nova por chamada (`duckdb.connect()`) → thread-safe sob o pool do
  uvicorn sem locks.

Fragmentos SQL gerados a partir das constantes (uma única fonte de verdade):

- `_CASE_DESFECHO` — CASE que aplica `DESFECHO_CANONICO`
- `_CASE_GRUPO` — CASE que aplica `DESFECHO_GRUPO`
- `_CASE_FAIXA` — CASE das faixas etárias
- `_CTE_UFS` — a tabela VALUES nome→sigla (JOIN para agregar por UF)

Padrões de agregação:

| Padrão | Exemplo | SQL |
|---|---|---|
| Contagem por categoria | sexo, forma, HIV | `GROUP BY coluna` + limpeza de rótulos no Python (`_limpar_rotulos`: NULL/nan → "Não informado", merge de variantes com/sem acento) |
| KPIs em uma passada | resumo | um SELECT com vários `COUNT(*) FILTER (WHERE ...)` |
| Percentual dentro de grupo | desfecho×raça, desfecho×HIV | `GROUP BY categoria, grupo` e normalização para 100% no Python |
| Pirâmide | casos/óbitos por faixa×sexo | `GROUP BY _CASE_FAIXA, sexo` |
| Heatmap | comorbidade×UF | um `COUNT FILTER` por agravo, `GROUP BY uf`, achatado em triplas `[x, y, valor]` (formato do ECharts) |
| Mediana/quantis | tempo até tratamento | `quantile_cont(col, 0.5)` + buckets com `COUNT FILTER` |

**Óbitos oficiais (SIM)** — fonte externa opcional:

1. `_sim_tabela()` tenta o cache em disco (`_cache_sim_obitos.csv`, TTL 7 dias);
2. se vencido/ausente, roda **uma única query** agregada (ano × UF, série
   completa) no PostgreSQL com `connect_timeout=2` e regrava o cache;
3. se o banco não responde, aceita cache vencido; sem nada, retorna `None`
   e o chamador usa o desfecho SINAN, marcando `fonte_obitos: "SINAN"`.

Esse padrão (fonte externa → cache em disco → fallback degradado + campo
`fonte_*` na resposta) vale para qualquer dependência de rede num dashboard.

**Cache em memória**: cada função pública tem `@lru_cache(maxsize=...)`
chaveado pelos `Filtros`. Como os dados só mudam quando os Parquets mudam,
não há invalidação — reiniciar o processo (deploy) zera tudo.

### 3.4 `main.py` — rotas

| Rota | Retorna |
|---|---|
| `GET /api/meta` | anos disponíveis, UFs com região, opções de cada filtro (distincts reais da base), rótulos de vuln/agravos |
| `GET /api/resumo` | KPIs: total, cura, abandono, óbitos (+fonte), HIV+, municípios, incidência, mortalidade, % da base |
| `GET /api/mapa` | por UF: casos, casos novos, óbitos, incidência, mortalidade, %cura, %abandono |
| `GET /api/uf/{sigla}` | drill-down: KPIs de coorte do estado + lista municipal (casos, %cura, %abandono, %óbito, %HIV, `nm_norm`) |
| `GET /api/perfil` | contagens de sexo/forma/entrada/raça/desfecho, desfecho agrupado, desfecho×raça, 2 pirâmides |
| `GET /api/clinico` | HIV, baciloscopia, TMR, desfecho×HIV, coinfecção por UF, tempo até tratamento (stats + histograma) |
| `GET /api/comorbidades` | agravos e populações (n + %), desfecho×vulnerável, heatmap UF×agravo |
| `GET /api/tendencia` | mensal do ano vs média histórica, série anual, óbitos SIM anuais, variação por UF, indicadores clínicos |
| `GET /api/geojson/estados` · `/municipios/{uf}` | GeoJSON pré-gzipado (passthrough) |
| `GET /api/export.csv` | microdados filtrados, streaming, máx. 5 anos |

Exemplo de chamada e resposta (`/api/resumo?anos=2025&ufs=SP,RJ`):

```json
{
  "total": 43489, "total_base": 116267, "pct_filtrado": 37.4,
  "cura": 13591, "abandono": 7671,
  "obitos": 2181, "fonte_obitos": "SIM",
  "hiv_pos": 6079, "municipios": 672,
  "incidencia": 41.2, "mortalidade": 2.4,
  "anos": [2025]
}
```

Detalhes de infraestrutura:

- `GZipMiddleware(minimum_size=1000)` — JSONs viajam comprimidos;
- `Cache-Control: max-age=300` nas rotas de dados e `max-age=86400` no geo —
  o browser reaproveita respostas sem nem chamar a API;
- GeoJSON servido **com o `.gz` do disco** e header `Content-Encoding: gzip`
  (o middleware detecta e não recomprime);
- warmup em thread no startup (`meta()` + tabela SIM) — o primeiro usuário
  não paga o custo frio;
- export CSV com `fetch_df_chunk()` + `StreamingResponse` — memória constante
  mesmo com centenas de milhares de linhas;
- se `frontend/dist` existe, é montado como estático na raiz → **um único
  processo** serve tudo em produção.

---

## 4. Frontend

### 4.1 Fluxo de dados

```
Sidebar ──toggle──▶ FiltrosContext (state.tsx)
                          │ filtros (lista vazia = todos)
                          ▼
                    App.tsx monta `filtrosEfetivos` (aplica ano default)
                          │
                          ▼
        hooks useResumo/usePerfil/... (api.ts)
                          │ queryKey = [endpoint, querystring]
                          ▼
                 TanStack Query (staleTime 5 min)
                          │ só busca o que a aba visível pede
                          ▼
                    tabs/*.tsx montam options ECharts
                          │
                          ▼
                 <Chart option={...}/> (canvas)
```

Pontos-chave:

- **A chave de cache é a querystring** — mudar um filtro dispara refetch só
  do que mudou; voltar a um filtro já visitado é instantâneo (cache).
- **Cada aba busca os próprios dados** e só é montada quando ativa → a carga
  inicial pede apenas `meta` + `resumo` + `mapa` + geojson.
- `staleTime: 5min` casa com o `Cache-Control` do backend; geojson tem
  `staleTime: Infinity` (nunca muda).

### 4.2 `theme.ts` + `charts.ts` — identidade visual única

- ECharts importado **por módulo** (`echarts/core` + só os charts usados):
  é o que segura o bundle em ~660 KB raw / 219 KB gzip em vez de >1 MB.
- `TB_COLORS` — dicionário rótulo→cor semântica (Cura verde, Óbito vermelho,
  Masculino azul...). `tbColors(labels)` resolve qualquer lista de rótulos
  com fallback determinístico. **Todo gráfico usa isso** — é o que dá
  consistência visual entre abas.
- `baseOption` — tooltip escuro, fonte Inter, bordas; todo builder herda.
- `charts.ts` expõe 5 construtores (`donut`, `barH`, `barV`, `stacked100`,
  `piramide`) que recebem os dados **no formato que a API devolve**.
  Um gráfico novo de categoria é uma linha:
  `<Chart option={donut(data.sexo)} height={300}/>`.

### 4.3 `Chart.tsx` — wrapper ECharts

Init uma vez, `setOption(notMerge)` a cada mudança, `ResizeObserver` para
responsividade, `dispose()` no unmount, `onClick` opcional (usado no mapa).
Memoizado — só re-renderiza quando a option muda.

### 4.4 Mapas sem servidor de tiles

- **Brasil**: `echarts.registerMap("BR", geojson)` com `nameProperty: "uf"` —
  a série casa por sigla. `visualMap` contínuo colore pela métrica ativa
  (casos/incidência/mortalidade — trocável pelos KPI cards ou pelo seletor).
- **Municípios**: geojson por UF registrado sob demanda
  (`mun-${uf}`, `nameProperty: "NM_MUN"`). O casamento entre dados e
  geometria é por **nome normalizado** (sem acento, minúsculo) — o backend
  manda `nm_norm` pronto e o frontend normaliza o `NM_MUN` do geojson com o
  mesmo algoritmo.
- Clique num estado (mapa ou ranking) abre o `UfModal` com mapa municipal
  (com `roam` para zoom), KPIs de coorte, top-N e tabela completa.

### 4.5 A camada "bonita"

- Tailwind v4 (`@theme` no CSS, sem config JS) para tokens de design.
- Classes customizadas em `index.css`: `.card` (gradiente sutil + borda),
  `.kpi` (barra de accent via CSS var `--kpi-accent`), `.chip` (filtros),
  `.badge`, `.skeleton` (shimmer), `.rise` (entrada animada), aurora de
  fundo em `position: fixed`.
- `CountUp` anima valores de KPI a cada mudança de filtro (ease-out cúbico
  com `requestAnimationFrame`).
- Skeletons dedicados por aba — nunca há tela branca durante fetch.
- Formatação pt-BR com `Intl.NumberFormat` (`fmt`, `fmt1`) em tudo.

---

## 5. Convenções epidemiológicas implementadas

Documentado porque **é regra de negócio**, não detalhe técnico:

- **Incidência** = casos novos (Caso Novo + Não Sabe + Pós-óbito) ÷ população
  × 100.000. Retratamentos não entram no numerador.
- **Anualização**: com N anos selecionados, divide-se por (população × N) —
  o coeficiente exibido é sempre a média anual.
- **Mortalidade**: preferencialmente SIM (CID A15–A19); fallback = desfecho
  "Óbito por TB" do SINAN, sempre com a fonte explícita na UI.
- **Taxas de coorte** (drill-down): denominador = casos **encerrados**
  (exclui "Em acompanhamento"); cura separada por caso novo × retratamento
  (esquemas de duração diferente; meta MS ≥85% para caso novo).
- **Abandono**: meta OMS <5% — a UI sinaliza vermelho acima disso.
- **% HIV+**: denominador = testagem conhecida (Positivo+Negativo), excluindo
  não realizados/ignorados.
- **Ano parcial** (2026): badge de alerta; ano default = último ano completo.

---

## 6. Executando

```bash
# desenvolvimento (2 terminais)
uvicorn main:app --app-dir backend --port 8000 --reload
cd frontend && npm run dev            # http://localhost:5173 (proxy /api)

# produção local (1 processo)
cd frontend && npm run build && cd ..
uvicorn main:app --app-dir backend --host 0.0.0.0 --port 8000

# Docker
docker build -f Dockerfile.api -t dashboard-tb-api .
docker run -p 8000:8000 -v ./dados_dashboard:/app/dados_dashboard --env-file .env dashboard-tb-api
```

Swagger automático em `/docs`. O `.env` (host/usuário/senha do PostgreSQL)
é opcional — sem ele o painel funciona 100% off-line dos Parquets.

---

## 7. Usando este projeto como modelo para outro dashboard

Checklist de adaptação (ex.: dengue, sífilis, violência, mortalidade...):

**Dados**
1. Gere Parquets tratados por ano (`scripts/` é o exemplo de ETL) — nomes
   `tema_{ano}_tratado.parquet`, colunas categóricas como texto legível.
2. Ajuste `PASTA_DADOS` e o padrão de nome em `backend/constantes.py` +
   `consultas.anos_disponiveis()`.

**Backend**
3. Reescreva as constantes de domínio: dicionários de normalização
   (`*_CANONICO`, `*_GRUPO`), flags booleanas, colunas de export.
4. Em `filtros.py`, troque os campos do `Filtros` pelos filtros do novo tema
   (o padrão lista-vazia-é-todos e o `where_sql()` não mudam).
5. Em `consultas.py`, monte as agregações com os padrões da §3.3 — a maioria
   dos gráficos é `_value_counts(coluna, filtros)`.
6. Exponha um endpoint **por aba** (não por gráfico): menos round-trips.

**Frontend**
7. Atualize os tipos em `api.ts` espelhando as respostas novas.
8. Ajuste `TB_COLORS` para a semântica do novo tema.
9. Monte as abas com os builders de `charts.ts`; crie builders novos só para
   formatos realmente novos.
10. KPIs: edite a lista `CARDS` em `KpiCards.tsx` (título, ícone, cor,
    métrica de mapa).
11. Sidebar: as seções seguem `meta.opcoes` — filtros novos = campos novos
    no `Filtros` + chips na sidebar.

**Mapas**
12. Reaproveite `_geo_cache/` como está (estados por `uf`, municípios por
    `NM_MUN`) — só mude a métrica/tooltip.

**Regra de ouro**: qualquer número que aparece na UI nasce de UMA query SQL
em `consultas.py`. Se dois lugares mostram o mesmo número, ambos leem o
mesmo endpoint. Nunca calcule indicador no frontend.
