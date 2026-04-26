"""
CMA-ES Training — Optimización de parámetros para ai_barrio_v3.

Implementa CMA-ES (Covariance Matrix Adaptation Evolution Strategy) para
optimizar los 29 parámetros de probabilidad del modelo barrio_v3.
Cada candidato se evalúa en un mini round-robin contra oponentes fijos
para evitar overfitting.

Uso: python train_cma_es.py
"""

import importlib
import os
import sys
import time
import numpy as np
from contextlib import redirect_stdout
from pathlib import Path

from arena import simular_partida
from config import IA_REGISTRY


# ── Configuración del entrenamiento ─────────────────────

GENERACIONES = 30
PARTIDAS_POR_OPONENTE = 100
SIGMA_INICIAL = 0.15
OPONENTES_FIJOS = ["aleatoria", "barrio_v1", "barrio_agresiva", "barrio_v2"]

PARAM_NAMES = [
    "CE_M_0_7",
    "CE_M_20", "CE_M_25", "CE_M_29", "CE_M_33",
    "CE_NM_0_7",
    "CE_NM_20", "CE_NM_25", "CE_NM_29", "CE_NM_33",
    "RE_2_20", "RE_2_25", "RE_2_29",
    "SE_2_20", "SE_2_25", "SE_2_29", "SE_2_33",
    "RE_4_20", "RE_4_25", "RE_4_29", "RE_4_33",
    "SE_4_20", "SE_4_25", "SE_4_29", "SE_4_33",
    "RE_7_20", "RE_7_25", "RE_7_29", "RE_7_33",
]

N_PARAMS = len(PARAM_NAMES)
PARAMS_PATH = Path(__file__).parent / "truco" / "AI" / "ai_barrio_v3_params.py"


# ── Manejo de parámetros ────────────────────────────────

def _leer_params_actuales() -> dict[str, float]:
    from truco.AI import ai_barrio_v3_params as p
    importlib.reload(p)
    return {name: getattr(p, name) for name in PARAM_NAMES}


def _vector_a_params(vector: np.ndarray) -> dict[str, float]:
    """Convierte vector a dict, clampeando todos los valores a [0,1]."""
    return {name: float(np.clip(val, 0.0, 1.0))
            for name, val in zip(PARAM_NAMES, vector)}


def _params_a_vector(params: dict[str, float]) -> np.ndarray:
    return np.array([params[name] for name in PARAM_NAMES])


def _inyectar_params(params: dict[str, float]) -> None:
    """Modifica los globals del módulo ai_barrio_v3 para que las nuevas instancias los usen."""
    mod_name = "truco.AI.ai_barrio_v3"
    if mod_name not in sys.modules:
        importlib.import_module(mod_name)
    mod = sys.modules[mod_name]
    for name, val in params.items():
        setattr(mod, name, val)


def _guardar_params(params: dict[str, float]) -> None:
    """Reescribe ai_barrio_v3_params.py preservando comentarios y formato."""
    lineas = PARAMS_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    nuevas = []
    for linea in lineas:
        stripped = linea.strip()
        if stripped and not stripped.startswith("#"):
            parts = stripped.split("=", 1)
            if len(parts) == 2:
                name = parts[0].strip()
                if name in params:
                    nuevas.append(f"{name} = {round(params[name], 4)}\n")
                    continue
        nuevas.append(linea)
    PARAMS_PATH.write_text("".join(nuevas), encoding="utf-8")


# ── Evaluación fitness ──────────────────────────────────

def _evaluar_winrate(params: dict[str, float]) -> float:
    """Evalúa un candidato contra los oponentes fijos. Retorna win rate."""
    _inyectar_params(params)
    victorias = 0
    total = 0
    with open(os.devnull, "w") as devnull:
        for oponente in OPONENTES_FIJOS:
            for i in range(PARTIDAS_POR_OPONENTE):
                j1, j2 = ("barrio_v3", oponente) if i % 2 == 0 else (oponente, "barrio_v3")
                with redirect_stdout(devnull):
                    ganador = simular_partida(j1, j2)
                total += 1
                if ganador == "barrio_v3":
                    victorias += 1
    return victorias / total if total > 0 else 0.0


# ── CMA-ES ──────────────────────────────────────────────

class CMAES:
    """Implementación de (μ/μ_w, λ)-CMA-ES."""

    def __init__(self, x0: np.ndarray, sigma: float):
        self.n = len(x0)
        self.mean = x0.astype(float).copy()
        self.sigma = sigma

        self.lam = 4 + int(3 * np.log(self.n))
        self.mu = self.lam // 2

        w = np.log(self.mu + 0.5) - np.log(np.arange(1, self.mu + 1))
        self.weights = w / w.sum()
        self.mu_eff = 1.0 / (self.weights ** 2).sum()

        self.c_sigma = (self.mu_eff + 2) / (self.n + self.mu_eff + 5)
        self.d_sigma = (1 + 2 * max(0, np.sqrt((self.mu_eff - 1) / (self.n + 1)) - 1)
                        + self.c_sigma)
        self.c_c = ((4 + self.mu_eff / self.n) /
                    (self.n + 4 + 2 * self.mu_eff / self.n))
        self.c_1 = 2 / ((self.n + 1.3) ** 2 + self.mu_eff)
        self.c_mu = min(1 - self.c_1,
                        2 * (self.mu_eff - 2 + 1 / self.mu_eff) /
                        ((self.n + 2) ** 2 + self.mu_eff))

        self.chi_n = np.sqrt(self.n) * (1 - 1 / (4 * self.n) + 1 / (21 * self.n ** 2))

        self.p_sigma = np.zeros(self.n)
        self.p_c = np.zeros(self.n)
        self.C = np.eye(self.n)
        self.B = np.eye(self.n)
        self.D = np.ones(self.n)
        self.gen = 0

    def sample(self) -> list[np.ndarray]:
        """Genera λ candidatos a partir de la distribución actual."""
        candidatos = []
        for _ in range(self.lam):
            z = np.random.randn(self.n)
            x = self.mean + self.sigma * (self.B @ (self.D * z))
            candidatos.append(x)
        return candidatos

    def update(self, candidatos: list[np.ndarray], fitness: list[float]) -> None:
        """Actualiza estado CMA-ES. Fitness mayor = mejor."""
        idx = np.argsort(fitness)[::-1]
        selected = np.array([candidatos[i] for i in idx[:self.mu]])

        old_mean = self.mean.copy()
        self.mean = self.weights @ selected
        diff = (self.mean - old_mean) / self.sigma

        # Path para step-size control
        invsqrt_C = self.B @ np.diag(1.0 / self.D) @ self.B.T
        self.p_sigma = ((1 - self.c_sigma) * self.p_sigma +
                        np.sqrt(self.c_sigma * (2 - self.c_sigma) * self.mu_eff) *
                        invsqrt_C @ diff)

        norm_ps = np.linalg.norm(self.p_sigma)
        denom = np.sqrt(1 - (1 - self.c_sigma) ** (2 * (self.gen + 1)))
        h_sigma = 1.0 if norm_ps / max(denom, 1e-20) < (1.4 + 2 / (self.n + 1)) * self.chi_n else 0.0

        # Path para covarianza
        self.p_c = ((1 - self.c_c) * self.p_c +
                    h_sigma * np.sqrt(self.c_c * (2 - self.c_c) * self.mu_eff) * diff)

        # Actualizar matriz de covarianza
        delta_h = (1 - h_sigma) * self.c_c * (2 - self.c_c)
        rank_one = np.outer(self.p_c, self.p_c)

        y_sel = np.array([(candidatos[i] - old_mean) / self.sigma for i in idx[:self.mu]])
        rank_mu = sum(w * np.outer(y, y) for w, y in zip(self.weights, y_sel))

        self.C = ((1 - self.c_1 - self.c_mu + delta_h * self.c_1) * self.C +
                  self.c_1 * rank_one + self.c_mu * rank_mu)

        # Actualizar step-size
        self.sigma *= np.exp((self.c_sigma / self.d_sigma) * (norm_ps / self.chi_n - 1))

        # Eigendecomposición para el siguiente paso
        self.C = (self.C + self.C.T) / 2
        eigvals, self.B = np.linalg.eigh(self.C)
        self.D = np.sqrt(np.maximum(eigvals, 1e-20))

        self.gen += 1


# ── Entrenamiento principal ─────────────────────────────

def entrenar() -> None:
    partidas_por_eval = PARTIDAS_POR_OPONENTE * len(OPONENTES_FIJOS)

    for ia in OPONENTES_FIJOS + ["barrio_v3"]:
        if ia not in IA_REGISTRY:
            print(f"  ✗ IA desconocida: {ia!r}")
            print(f"    Disponibles: {list(IA_REGISTRY.keys())}")
            return

    params_iniciales = _leer_params_actuales()
    x0 = _params_a_vector(params_iniciales)
    cma = CMAES(x0, SIGMA_INICIAL)

    total_juegos_est = (1 + cma.lam * GENERACIONES) * partidas_por_eval
    tiempo_est = total_juegos_est / 100  # ~100 partidas/s estimado

    print(f"\n  ==========================================")
    print(f"  CMA-ES TRAINING — barrio_v3")
    print(f"  ==========================================")
    print(f"  Parámetros: {N_PARAMS}")
    print(f"  Población (λ): {cma.lam}  |  Padres (μ): {cma.mu}")
    print(f"  Generaciones: {GENERACIONES}")
    print(f"  Partidas por eval: {partidas_por_eval} ({PARTIDAS_POR_OPONENTE} × {len(OPONENTES_FIJOS)})")
    print(f"  Oponentes: {', '.join(OPONENTES_FIJOS)}")
    print(f"  σ inicial: {SIGMA_INICIAL}")
    print(f"  Estimado: ~{total_juegos_est:,} partidas (~{tiempo_est / 60:.0f} min)")
    print()

    # ── Baseline ──
    print(f"  Evaluando baseline...", flush=True)
    baseline_wr = _evaluar_winrate(params_iniciales)
    print(f"  Baseline: {baseline_wr:.1%} win rate\n")

    mejor_wr = baseline_wr
    mejor_params = params_iniciales.copy()
    inicio = time.time()

    # ── Loop de generaciones ──
    for gen in range(GENERACIONES):
        t_gen = time.time()
        print(f"  ── Gen {gen + 1:>2}/{GENERACIONES} ──────────────────────────────")

        candidatos = cma.sample()
        params_list = [_vector_a_params(v) for v in candidatos]

        winrates = []
        for i, params in enumerate(params_list):
            wr = _evaluar_winrate(params)
            winrates.append(wr)
            marca = " ★" if wr > mejor_wr else ""
            print(f"    [{i + 1:>2}/{cma.lam}] {wr:.1%}{marca}", flush=True)

        cma.update(candidatos, winrates)

        mejor_gen = max(winrates)
        media_gen = float(np.mean(winrates))

        if mejor_gen > mejor_wr:
            idx_mejor = int(np.argmax(winrates))
            mejor_wr = mejor_gen
            mejor_params = params_list[idx_mejor].copy()

        dt = time.time() - t_gen
        print(f"    Mejor gen: {mejor_gen:.1%}  Media: {media_gen:.1%}  σ: {cma.sigma:.4f}  ({dt:.1f}s)")
        print(f"    ★ Mejor global: {mejor_wr:.1%}")
        print()

    # ── Restaurar e inyectar mejores params ──
    _inyectar_params(mejor_params)
    total_t = time.time() - inicio

    # ── Resultado final ──
    print(f"  ── Resultado final ───────────────────────")
    print(f"  Baseline: {baseline_wr:.1%} → Mejor: {mejor_wr:.1%} ({mejor_wr - baseline_wr:+.1%})")

    print(f"\n  Top 10 cambios:")
    cambios = [(n, params_iniciales[n], mejor_params[n]) for n in PARAM_NAMES]
    cambios.sort(key=lambda x: -abs(x[2] - x[1]))
    for n, old, new in cambios[:10]:
        print(f"    {n:<22} {old:.4f} → {new:.4f} ({new - old:+.4f})")

    print(f"\n  Tiempo total: {total_t:.1f}s")

    _guardar_params(mejor_params)
    print(f"  Parámetros guardados en {PARAMS_PATH}\n")


if __name__ == "__main__":
    entrenar()
