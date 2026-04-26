"""
Round Robin — Torneo de IAs para El Malevo.

Enfrenta todas las IAs de ROUND_ROBIN_IAS entre sí (cada par juega
ROUND_ROBIN_PARTIDAS partidas), registra resultados y actualiza ELO.
Configuración en config.py (ROUND_ROBIN_*).

Uso: python round_robin.py
"""

import itertools
import os
import time
from contextlib import redirect_stdout

from config import ROUND_ROBIN_IAS, ROUND_ROBIN_PARTIDAS, ROUND_ROBIN_ELO_K, IA_REGISTRY
from arena import simular_partida, _calcular_elo, _cargar_elo, _guardar_elo, ELO_DEFAULT


def _imprimir_tabla(ias: list[str], stats: dict, ratings: dict, elo_inicial: dict) -> None:
    print(f"\n  {'Pos':>3}  {'IA':<20} {'V':>5} {'D':>5} {'E':>5}  {'%Win':>6}  {'ELO':>7}  {'Δ ELO':>7}")
    print(f"  {'─' * 65}")

    orden = sorted(ias, key=lambda ia: (-ratings[ia], -stats[ia]["victorias"]))
    for pos, ia in enumerate(orden, 1):
        v = stats[ia]["victorias"]
        d = stats[ia]["derrotas"]
        e = stats[ia]["empates"]
        total = v + d + e
        pct = (v / total * 100) if total > 0 else 0.0
        delta = ratings[ia] - elo_inicial[ia]
        print(
            f"  {pos:>3}. {ia:<20} {v:>5} {d:>5} {e:>5}  {pct:>5.1f}%  "
            f"{ratings[ia]:>7.1f}  {delta:>+7.1f}"
        )


def _imprimir_matriz(ias: list[str], versus: dict) -> None:
    n = len(ias)
    idx = {ia: i + 1 for i, ia in enumerate(ias)}
    ancho = max(len(str(v)) for v in versus.values()) * 2 + 1  # "WW-WW"
    ancho = max(ancho, 5)
    col = ancho + 2  # padding

    print(f"\n  Matriz de resultados (victorias fila vs columna)\n")

    # Encabezado de columnas
    header = "       " + "".join(f"{i:>{col}}" for i in range(1, n + 1))
    print(f"  {header}")
    print(f"  {'─' * len(header)}")

    for ia_f in ias:
        fila = f"  {idx[ia_f]:>2}.  "
        for ia_c in ias:
            if ia_f == ia_c:
                celda = "─"
            else:
                w = versus.get((ia_f, ia_c), 0)
                l = versus.get((ia_c, ia_f), 0)
                celda = f"{w}-{l}"
            fila += f"{celda:>{col}}"
        print(fila)

    print()
    for ia in ias:
        print(f"    {idx[ia]}. {ia}")


def round_robin() -> None:
    ias = ROUND_ROBIN_IAS
    n_partidas = ROUND_ROBIN_PARTIDAS
    k = ROUND_ROBIN_ELO_K

    # Validar IAs
    desconocidas = [ia for ia in ias if ia not in IA_REGISTRY]
    if desconocidas:
        for ia in desconocidas:
            print(f"  ✗ IA desconocida: {ia!r}")
        print(f"    Disponibles: {list(IA_REGISTRY.keys())}")
        return

    if len(ias) < 2:
        print("  ✗ Se necesitan al menos 2 IAs en ROUND_ROBIN_IAS.")
        return

    pares = list(itertools.combinations(ias, 2))
    total_enfrentamientos = len(pares)
    total_partidas = total_enfrentamientos * n_partidas

    ratings = _cargar_elo()
    for ia in ias:
        ratings.setdefault(ia, ELO_DEFAULT)

    elo_inicial = {ia: ratings[ia] for ia in ias}

    stats: dict[str, dict] = {
        ia: {"victorias": 0, "derrotas": 0, "empates": 0} for ia in ias
    }
    versus: dict[tuple[str, str], int] = {
        (ia1, ia2): 0 for ia1 in ias for ia2 in ias if ia1 != ia2
    }

    print(f"\n  ==========================================")
    print(f"  ROUND ROBIN — {len(ias)} IAs")
    print(f"  ==========================================")
    print(f"  IAs: {', '.join(ias)}")
    print(f"  Partidas por enfrentamiento: {n_partidas}")
    print(f"  Enfrentamientos: {total_enfrentamientos}  |  Total partidas: {total_partidas}")
    print(f"  K-factor: {k}")
    for ia in ias:
        print(f"  ELO inicial {ia}: {elo_inicial[ia]:.1f}")
    print()

    inicio_total = time.time()
    paso = max(1, n_partidas // 10)

    # Bucle externo: rondas. En cada ronda, todos los pares juegan 1 partida.
    # Así el ELO se actualiza de forma cruzada entre todos los enfrentamientos.
    for ronda in range(n_partidas):
        for ia1, ia2 in pares:
            # Alternar quién es mano según la ronda
            j1_ia, j2_ia = (ia1, ia2) if ronda % 2 == 0 else (ia2, ia1)

            with open(os.devnull, "w") as devnull, redirect_stdout(devnull):
                ganador = simular_partida(j1_ia, j2_ia)

            if ganador:
                stats[ganador]["victorias"] += 1
                perdedor = ia2 if ganador == ia1 else ia1
                stats[perdedor]["derrotas"] += 1
                versus[(ganador, perdedor)] += 1
                score_1 = 1.0 if ganador == ia1 else 0.0
                ratings[ia1], ratings[ia2] = _calcular_elo(ratings[ia1], ratings[ia2], score_1, k)
            else:
                stats[ia1]["empates"] += 1
                stats[ia2]["empates"] += 1
                ratings[ia1], ratings[ia2] = _calcular_elo(ratings[ia1], ratings[ia2], 0.5, k)

        progreso = ronda + 1
        if progreso % paso == 0 or progreso == n_partidas:
            pct = progreso * 100 // n_partidas
            elo_str = "  ".join(f"{ia}:{ratings[ia]:.0f}" for ia in ias)
            print(f"  [{pct:3d}%] Ronda {progreso}/{n_partidas} — {elo_str}")

    elapsed_total = time.time() - inicio_total

    print(f"  ── Tabla de posiciones ─────────────────────────────────────────")
    _imprimir_tabla(ias, stats, ratings, elo_inicial)
    _imprimir_matriz(ias, versus)

    vel = total_partidas / elapsed_total if elapsed_total > 0 else 0
    print(f"\n  Tiempo total: {elapsed_total:.1f}s ({vel:.1f} partidas/s)")

    _guardar_elo(ratings)
    print(f"  ELO guardado en elo_ratings.py\n")


if __name__ == "__main__":
    round_robin()
