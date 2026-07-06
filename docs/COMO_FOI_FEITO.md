# Como este dashboard foi construído — making-of

> Registro didático de como a v2 saiu do zero ao ar em uma sessão de
> trabalho. Não é a documentação da arquitetura (essa está em
> [ARQUITETURA.md](ARQUITETURA.md)) — é o **processo**: a ordem das
> decisões, o porquê de cada uma, os problemas que apareceram e como
> foram diagnosticados. A última seção é a receita condensada para você
> repetir em outro painel.

---

## Etapa 0 — Ler antes de escrever (≈30 min)

Nenhuma linha de código antes de entender o que existia. A leitura seguiu
uma ordem deliberada, do mais barato ao mais caro:

1. **`README.md` e `docs/DESENVOLVIMENTO.md`** — o que o painel faz, como
   roda, qual o pipeline de dados.
2. **Listagem completa de arquivos com tamanhos** — isso revelou muito:
   Parquets de ~2 MB/ano (dados leves!), um `_geo_cache/` com GeoJSON
   pré-gzipado (mapas resolvidos!), CSVs históricos pré-agregados, uma
   pasta `load_tests/` (performance já era uma dor conhecida).
3. **`src/banco.py` e `src/dados.py`** — a v1 já usava DuckDB, e os
   comentários documentavam otimizações (leitura colunar, category dtype).
   Conclusão: o gargalo não eram os dados, era o **modelo do Streamlit**
   (recarregar e refiltrar DataFrames inteiros a cada clique).
4. **`app.py` inteiro + `constantes.py` + `ui_sidebar.py`** — inventário de
   TUDO que precisava ser portado: 8 KPIs, 6 abas, cada gráfico, cada
   filtro, cada regra de negócio (incidência = casos novos, coorte exclui
   "Em acompanhamento", meta OMS de abandono...).
5. **Schema real dos Parquets** — um script de 30 linhas com DuckDB
   imprimindo colunas, tipos e os valores reais de cada categórica.
   Isso evitou dezenas de surpresas ("Reingresso após Abandono" tem
   variantes de capitalização; desfechos vêm com e sem acento; sexo tem
   "Ignorado").

> **Lição**: uma hora lendo economiza um dia debugando. O inventário de
> funcionalidades (passo 4) virou literalmente a lista de tarefas.

## Etapa 1 — Decidir a arquitetura (≈10 min)

A pergunta certa não é "qual framework?", é **"onde mora cada custo?"**:

| Custo | v1 (Streamlit) | v2 (decisão) |
|---|---|---|
| Filtrar 116 mil linhas | pandas no servidor, a cada rerun | SQL no DuckDB, só quando o filtro muda |
| Transportar dados | objetos Plotly serializados | JSON agregado de 1–5 KB |
| Renderizar gráfico | re-render do servidor | canvas no browser (ECharts) |
| Estado da UI | session_state + rerun global | React (só o componente afetado) |

Escolhas concretas e os porquês:

- **FastAPI** — o requisito era manter Python; FastAPI dá validação de
  query params, docs automáticas e async de graça.
- **DuckDB direto nos Parquets** — já estava no projeto e é imbatível para
  agregação colunar local. Zero ETL novo.
- **React + Vite + TypeScript** — TS paga o próprio custo num projeto com
  dezenas de shapes de JSON; Vite dá build de 3 s.
- **ECharts em vez de Plotly/Folium** — um único motor para TODOS os
  gráficos **incluindo os mapas** (choropleth via `registerMap` com o
  GeoJSON local) → sem tiles externos, sem Leaflet, bundle menor, tema
  100% consistente.
- **TanStack Query** — cache por chave de filtro no browser; trocar de aba
  ou repetir um filtro vira 0 requisições.
- **Não quebrar a v1** — tudo novo em `backend/` e `frontend/`; o Streamlit
  continua funcionando. Rollback é trivial.

## Etapa 2 — Backend primeiro, e testado antes da UI (≈1 h)

Ordem dos arquivos: `constantes.py` → `filtros.py` → `consultas.py` →
`main.py`. Dados de referência primeiro, porque todo o resto depende deles.

Os três padrões que sustentam o backend:

1. **Filtros = dataclass congelada** → hasheável → chave de `lru_cache`.
   Um conceito só resolve validação, SQL injection (placeholders `?`) e
   cache.
2. **Uma CTE `sinan` universal** — toda query enxerga a mesma "tabela",
   montada só com os arquivos dos anos filtrados. As regras de negócio
   (normalização de desfecho, faixas etárias, UF→sigla) viram fragmentos
   SQL **gerados a partir dos dicionários** de constantes — fonte única de
   verdade.
3. **Um endpoint por aba** — a aba Perfil faz 1 request, não 9.

**O teste que valeu ouro**: antes de existir qualquer frontend, um script
(`smoke_backend.py`) chamou cada função de agregação e imprimiu tempo +
amostra do JSON. Primeira rodada encontrou dois problemas:

- `WITH` aninhado (a query de tempo de tratamento tinha CTE própria dentro
  da CTE do wrapper) → erro de sintaxe → reescrita como subquery.
- Óbitos SIM levavam **6–12 s**: era uma conexão PostgreSQL + query por
  ano. Redesenho: **uma única query agregada (ano × UF) da série inteira**,
  cache em CSV com TTL de 7 dias, fallback para o desfecho SINAN sem VPN.
  Resultado: 6 s uma vez por semana, 0 ms no resto.

Depois disso, todas as agregações rodavam em 20–220 ms. Só então a UI
começou.

> **Lição**: teste a camada de dados isolada, com números de verdade, antes
> de qualquer pixel. Bug de SQL com UI na frente vira caça ao fantasma.

## Etapa 3 — Frontend: fundação → casca → abas (≈2 h)

Ordem deliberada, cada camada usando a anterior:

1. **Fundação**: `theme.ts` (paleta semântica portada da v1 + ECharts
   tree-shaken), `index.css` (tokens + classes), `api.ts` (tipos espelhando
   cada resposta da API + hooks), `state.tsx` (filtros).
2. **Infra de gráfico**: `Chart.tsx` (wrapper: init/resize/dispose/click) e
   `charts.ts` (5 construtores: donut, barras H/V, 100% empilhado,
   pirâmide). **Investir aqui primeiro fez cada aba custar minutos**: um
   gráfico novo é `<Chart option={donut(data.sexo)}/>`.
3. **Casca**: `App.tsx` (topbar, hero, KPIs, navegação), `Sidebar.tsx`,
   `KpiCards.tsx`.
4. **Abas**, da mais complexa para a mais simples: Mapa (com o modal de
   drill-down), Perfil, Clínico, Comorbidades, Tendência, Dados.

Decisões de UX que fazem o painel "parecer rápido" além de ser:

- **Skeletons** em toda aba (nunca tela branca);
- **CountUp** nos KPIs (o número anima ao mudar filtro — feedback imediato);
- filtros como **chips** com semântica "vazio = todos" (o backend só recebe
  parâmetro quando há restrição real);
- aba só monta quando visitada; ao voltar, o cache responde na hora.

O detalhe mais delicado do frontend foi o **casamento dado↔geometria** nos
mapas municipais: o SINAN grava nomes de município como texto. Solução:
normalizar dos dois lados com o MESMO algoritmo (remover acento, minúsculas,
trim) — o backend já manda `nm_norm` pronto e o frontend normaliza o
`NM_MUN` do GeoJSON. Verificado: 60/60 municípios do AM casados.

## Etapa 4 — Depuração real (a parte que ninguém documenta)

Três problemas de ambiente apareceram ao subir tudo. O método foi sempre o
mesmo: **isolar a camada** (o servidor responde? o processo está vivo? o
browser recebe?) e comparar um caso que funciona com um que não.

1. **"Servidor no ar" mas conexão recusada.** `curl 127.0.0.1:5173`
   falhava, mas o Vite dizia "ready". Causa: Node moderno resolve
   `localhost` para IPv6 (`::1`) e o teste batia em IPv4. Fix de uma linha:
   `server.host: "127.0.0.1"` no `vite.config.ts`.
2. **Página em branco, zero erros no console.** `fetch()` dos módulos
   retornava 200, mas `import()` falhava. Comparando as duas coisas
   percebeu-se que o painel de preview bloqueava `/@vite/client` (o cliente
   de HMR) — e no Vite 6 todo módulo transformado importa esse cliente, o
   que derrubava o grafo inteiro. Solução: verificar com o **build de
   produção servido pelo FastAPI** (que é a arquitetura real de deploy;
   dev com HMR continua funcionando em navegador normal).
3. **Cache do Vite corrompido** por inicializações interrompidas (chunks
   com hashes `?v=` inconsistentes). `rm -rf node_modules/.vite` e subir de
   novo.

> **Lição**: quando "não tem erro nenhum", o bug está entre as camadas, não
> dentro de uma. Teste cada fronteira com a ferramenta mais burra possível
> (curl, fetch, um import isolado).

## Etapa 5 — Verificar como usuário, não como autor (≈30 min)

Checklist executado no browser real, com evidência para cada item:

- 8 KPIs com os **mesmos números** do smoke test do backend (40,8 de
  incidência; 116.267 casos) — bateu ponta a ponta;
- as 6 abas renderizando (contagem de canvas + títulos dos cards);
- clique no mapa → modal do Amazonas com coorte correta;
- filtro Nordeste → 28.548 registros, KPIs recalculados;
- "Últimos 3 anos" → 339.132 registros, incidência anualizada 40,4 e fonte
  de óbitos trocando para SIM automaticamente;
- export CSV → 660 linhas para AC/2025 com cabeçalho correto;
- console: zero erros; API: 3–6 ms com cache.

Só depois disso: README, Dockerfile e esta documentação.

---

## A receita condensada (para o seu próximo dashboard)

1. **Inventarie antes de codar.** Liste cada KPI, gráfico, filtro e regra
   de negócio do que existe (ou do que se quer). Inspecione o schema REAL
   dos dados, incluindo valores das categóricas.
2. **Prepare dados colunares por partição natural** (ano): Parquet tratado,
   ~MBs por arquivo, categóricas como texto legível.
3. **Backend = agregados, nunca microdados.** FastAPI + DuckDB; filtros
   como dataclass congelada (validação + SQL seguro + chave de cache);
   uma CTE universal; regras de negócio como fragmentos SQL gerados de
   dicionários; um endpoint por aba; `lru_cache` em tudo; fonte externa
   com cache em disco + fallback + campo `fonte_*`.
4. **Smoke test da camada de dados** com tempos e amostras de JSON, antes
   de qualquer UI.
5. **Frontend na ordem fundação → casca → abas**: tema/tipos/hooks primeiro,
   wrapper de gráfico + construtores reutilizáveis depois, abas por último
   (viram colagem de peças prontas).
6. **Percepção de velocidade é feature**: skeletons, números animados,
   cache no browser (TanStack Query com `staleTime` = `Cache-Control`),
   gzip, aba preguiçosa.
7. **Mapas**: GeoJSON local + `registerMap` do ECharts; casamento por chave
   normalizada dos dois lados com o mesmo algoritmo.
8. **Verifique como usuário** com evidências (números batendo ponta a
   ponta, interações reais, console limpo) — e só então escreva docs e
   Dockerfile.
9. **Não destrua a versão anterior** — construa ao lado, compare, migre.

### Ferramentas para instalar uma vez

```bash
# backend
pip install fastapi "uvicorn[standard]" duckdb pandas python-dotenv

# frontend (Node 20+)
npm create vite@latest meu-painel -- --template react-ts
npm i echarts @tanstack/react-query @fontsource-variable/inter
npm i -D tailwindcss @tailwindcss/vite
```

O tempo total desta reconstrução — leitura, backend, frontend, depuração,
verificação e documentação — coube em uma tarde. O que tornou isso possível
não foi digitar rápido: foi a ordem (entender → dados → teste → UI →
verificação) e o reuso agressivo do que o projeto já tinha (Parquets,
GeoJSON em cache, CSVs históricos, regras de negócio documentadas no código
da v1).
