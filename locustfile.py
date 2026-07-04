"""
locustfile.py — Teste de carga do Dashboard TB | SINAN
───────────────────────────────────────────────────────
Simula perfis reais de usuários com ramp-up progressivo.

Executar (interface web — recomendado):
  locust -f locustfile.py --host http://10.20.10.64:8502
  → abrir http://localhost:8089

Executar headless com relatório HTML:
  locust -f locustfile.py --host http://10.20.10.64:8502 \
         --users 50 --spawn-rate 5 --run-time 5m --headless \
         --csv=resultado_carga --html=resultado_carga.html
"""

import time
import threading
import websocket
from locust import HttpUser, task, between, events
from locust import LoadTestShape


BASE_PATH = "/cenarios/tb"


# ══════════════════════════════════════════════════════════════════════════════
#  PERFIS DE USUÁRIO
# ══════════════════════════════════════════════════════════════════════════════

class UsuarioPassivo(HttpUser):
    """
    Usuário que abre o dashboard e lê sem interagir muito.
    Representa ~50% do tráfego real — maior pausa entre ações.
    """
    weight    = 5
    wait_time = between(8, 20)

    def on_start(self):
        self._carregar_pagina()
        self._abrir_websocket()

    def on_stop(self):
        self._fechar_websocket()

    @task(4)
    def visualizar_dashboard(self):
        self._carregar_pagina()

    @task(1)
    def verificar_health(self):
        with self.client.get(
            f"{BASE_PATH}/_stcore/health",
            name="[health] /health",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Health retornou {r.status_code}")

    def _carregar_pagina(self):
        with self.client.get(
            f"{BASE_PATH}/",
            name="[página] carregar dashboard",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 301, 302):
                r.success()
            else:
                r.failure(f"Página retornou {r.status_code}")

    def _abrir_websocket(self):
        host  = self.host.replace("http://", "ws://").replace("https://", "wss://")
        url   = f"{host}{BASE_PATH}/_stcore/stream"
        start = time.time()
        try:
            self._ws = websocket.WebSocketApp(
                url,
                on_open=lambda ws: None,
                on_error=lambda ws, e: None,
                on_close=lambda ws, *a: None,
            )
            threading.Thread(
                target=self._ws.run_forever,
                kwargs={"ping_interval": 20, "ping_timeout": 10},
                daemon=True,
            ).start()
            events.request.fire(
                request_type="WS", name="[ws] handshake",
                response_time=int((time.time() - start) * 1000),
                response_length=0, exception=None, context={},
            )
        except Exception as e:
            events.request.fire(
                request_type="WS", name="[ws] handshake",
                response_time=int((time.time() - start) * 1000),
                response_length=0, exception=e, context={},
            )

    def _fechar_websocket(self):
        if hasattr(self, "_ws") and self._ws:
            try:
                self._ws.close()
            except Exception:
                pass


class UsuarioAtivo(HttpUser):
    """
    Usuário que navega ativamente entre abas e recursos.
    Representa ~35% do tráfego — pausa curta entre ações.
    """
    weight    = 3
    wait_time = between(3, 8)

    def on_start(self):
        self._carregar_pagina()

    @task(5)
    def navegar_abas(self):
        with self.client.get(
            f"{BASE_PATH}/",
            name="[aba] navegar",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 301, 302):
                r.success()
            else:
                r.failure(f"Aba retornou {r.status_code}")

    @task(3)
    def carregar_assets(self):
        assets = [
            "/_stcore/static/js/main.chunk.js",
            "/_stcore/static/css/main.chunk.css",
            f"{BASE_PATH}/_stcore/stream",
        ]
        for path in assets:
            with self.client.get(path, name="[static] asset", catch_response=True) as r:
                if r.status_code in (200, 304, 404):
                    r.success()

    @task(2)
    def recarregar_pagina(self):
        self._carregar_pagina()

    def _carregar_pagina(self):
        with self.client.get(
            f"{BASE_PATH}/",
            name="[página] carregar dashboard",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 301, 302):
                r.success()
            else:
                r.failure(f"Página retornou {r.status_code}")


class UsuarioDownload(HttpUser):
    """
    Usuário que baixa CSV e inspeciona dados.
    Representa ~15% do tráfego — ações pesadas com pausa longa.
    """
    weight    = 2
    wait_time = between(15, 40)

    def on_start(self):
        with self.client.get(
            f"{BASE_PATH}/",
            name="[página] carregar dashboard",
            catch_response=True,
        ) as r:
            if r.status_code in (200, 301, 302):
                r.success()

    @task(3)
    def abrir_stream(self):
        with self.client.get(
            f"{BASE_PATH}/_stcore/stream",
            name="[stream] iniciar sessão",
            catch_response=True,
            stream=True,
        ) as r:
            if r.status_code in (200, 404):
                r.success()
            else:
                r.failure(f"Stream retornou {r.status_code}")

    @task(1)
    def verificar_health(self):
        with self.client.get(
            f"{BASE_PATH}/_stcore/health",
            name="[health] /health",
            catch_response=True,
        ) as r:
            if r.status_code == 200:
                r.success()
            else:
                r.failure(f"Health retornou {r.status_code}")


# ══════════════════════════════════════════════════════════════════════════════
#  SHAPE — Ramp-up progressivo → pico → sustentação → queda
# ══════════════════════════════════════════════════════════════════════════════

class RampUpShape(LoadTestShape):
    """
    Simula um dia de trabalho real:
      0–1min   → sobe de 0 a 10 usuários  (chegada matinal)
      1–2min   → sobe de 10 a 30          (horário de pico)
      2–4min   → sustenta 30 usuários     (uso contínuo)
      4–5min   → sobe para 50 usuários    (pico máximo — estresse)
      5–6min   → sustenta 50              (teste de resistência)
      6–7min   → cai para 20             (fim de expediente)
      7–8min   → cai para 0              (sistema quieto)
    """
    stages = [
        {"duration":  60, "users": 10,  "spawn_rate": 2},
        {"duration": 120, "users": 30,  "spawn_rate": 4},
        {"duration": 240, "users": 30,  "spawn_rate": 1},
        {"duration": 300, "users": 50,  "spawn_rate": 5},
        {"duration": 360, "users": 50,  "spawn_rate": 1},
        {"duration": 420, "users": 20,  "spawn_rate": 5},
        {"duration": 480, "users":  0,  "spawn_rate": 10},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return stage["users"], stage["spawn_rate"]
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  RELATÓRIO NO TERMINAL
# ══════════════════════════════════════════════════════════════════════════════

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("\n" + "=" * 60)
    print("  TESTE DE CARGA — Dashboard TB | SINAN")
    print(f"  Host:      {environment.host}")
    print(f"  Base path: {BASE_PATH}")
    print("  Shape:     Ramp-up 0->10->30->50->20->0 usuarios (8 min)")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    t = environment.stats.total
    p = lambda pct: t.get_response_time_percentile(pct) or 0  # noqa: E731
    falhas_app = t.num_failures - sum(
        e.occurrences for e in environment.stats.errors.values()
        if "404" in str(e.error) and "health" in e.name
    )
    print("\n" + "=" * 60)
    print("  RESULTADO FINAL")
    print(f"  Requisições totais : {t.num_requests:,}")
    print(f"  Falhas (app)       : {falhas_app:,} ({100*falhas_app/max(t.num_requests,1):.1f}%)")
    print(f"  RPS médio          : {t.total_rps:.2f}")
    print(f"  Latência p50       : {p(0.50):.0f} ms")
    print(f"  Latência p75       : {p(0.75):.0f} ms")
    print(f"  Latência p95       : {p(0.95):.0f} ms")
    print(f"  Latência p99       : {p(0.99):.0f} ms")
    print(f"  Latência máx       : {t.max_response_time:.0f} ms")
    print("=" * 60)
    print("  Arquivos gerados:")
    print("    resultado_carga_stats.csv")
    print("    resultado_carga_history.csv")
    print("    resultado_carga_failures.csv")
    print("    resultado_carga.html")
    print("=" * 60 + "\n")
