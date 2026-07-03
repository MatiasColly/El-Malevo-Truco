"""
Arena — Simulador de partidas IA vs IA para El Malevo.

Enfrenta dos IAs en múltiples partidas, registra victorias y actualiza ELO.
Configuración en config.py (ARENA_*). Ratings persistidos en elo_ratings.py.

Uso: python arena.py
"""

import importlib
import os
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

from truco.jugador import JugadorAI
from truco.truco_engine import TrucoEngine
from config import ARENA_PARTIDAS, ARENA_IA_1, ARENA_IA_2, ARENA_ELO_K, IA_REGISTRY, crear_ia


MAX_TURNOS_RONDA = 50
MAX_RONDAS_PARTIDA = 200


# ── Simulación silenciosa ────────────────────────────────

def _respuesta_envido_ia(engine, nombre: str) -> str:
    jugador = engine._get_jugador(nombre)
    if isinstance(jugador, JugadorAI):
        game_state = engine.get_game_state(nombre)
        resp = jugador.ai.responder_envido(game_state)
        return resp.get("tipo", "quiero")
    return "quiero"


def _respuesta_truco_ia(engine, nombre: str) -> str:
    jugador = engine._get_jugador(nombre)
    if isinstance(jugador, JugadorAI):
        game_state = engine.get_game_state(nombre)
        resp = jugador.ai.responder_truco(game_state)
        return resp.get("tipo", "quiero")
    return "quiero"


def _simular_envido(engine, cantor: str, tipo_envido: str) -> None:
    if not engine.puede_cantar_envido():
        return

    engine.envido_secuencia = [tipo_envido]
    secuencia = engine.envido_secuencia
    oponente_nombre = engine._oponente_nombre(cantor)

    while True:
        respuestas_validas = engine.cantos_validos_respuesta_envido(secuencia)
        respuesta = _respuesta_envido_ia(engine, oponente_nombre)
        if respuesta not in respuestas_validas:
            respuesta = "quiero"

        if respuesta in ("quiero", "no_quiero"):
            break

        secuencia.append(respuesta)
        cantor, oponente_nombre = oponente_nombre, cantor

    aceptado = respuesta == "quiero"
    puntos_q, puntos_nq = engine.calcular_puntos_envido_secuencia(secuencia)
    resultado = engine.resolver_envido(aceptado, cantor, puntos_q, puntos_nq)
    engine.sumar_puntos(resultado["ganador"], resultado["puntos"])


def _simular_truco(engine, ronda, cantor: str, nivel: str) -> None:
    if not engine.puede_cantar_truco(cantor):
        return

    oponente_nombre = engine._oponente_nombre(cantor)
    puede_subir = engine.nivel_truco + 1 < 3
    puede_envido = engine.puede_cantar_envido()

    respuesta = _respuesta_truco_ia(engine, oponente_nombre)

    # Envido en respuesta al truco
    if respuesta in ("envido", "real_envido", "falta_envido") and puede_envido:
        _simular_envido(engine, oponente_nombre, respuesta)
        if engine.juego_terminado() or ronda.terminada:
            return
        respuesta = _respuesta_truco_ia(engine, oponente_nombre)

    # Validar respuesta
    validas = ["quiero", "no_quiero"]
    if puede_subir:
        validas.append(engine.nombre_siguiente_truco())
    if respuesta not in validas:
        respuesta = "quiero"

    # Escalada de truco
    while respuesta in ("retruco", "vale cuatro"):
        engine.nivel_truco = engine.siguiente_nivel_truco()
        engine.truco_cantado_por = oponente_nombre
        cantor, oponente_nombre = oponente_nombre, cantor
        nivel = respuesta
        puede_subir = engine.nivel_truco + 1 < 3

        respuesta = _respuesta_truco_ia(engine, oponente_nombre)
        validas = ["quiero", "no_quiero"]
        if puede_subir:
            validas.append(engine.nombre_siguiente_truco())
        if respuesta not in validas:
            respuesta = "quiero"

    if respuesta == "quiero":
        engine.resolver_truco(True, cantor)
    else:
        engine.resolver_truco(False, cantor)
        ronda.ganador_ronda = cantor
        ronda.terminada = True


def _simular_mazo(engine, ronda, jugador_nombre: str) -> None:
    if engine.primera_baza and not engine.envido_terminado:
        oponente_nombre = engine._oponente_nombre(jugador_nombre)
        engine.sumar_puntos(oponente_nombre, 1)
        engine.envido_terminado = True
    ronda.ir_al_mazo(jugador_nombre)


def _simular_turno(engine, ronda, jugador) -> None:
    if not isinstance(jugador, JugadorAI):
        return

    game_state = engine.get_game_state(jugador.nombre)
    accion = jugador.decidir(game_state)
    tipo = accion.get("tipo", "jugar_carta")

    if tipo == "jugar_carta":
        indice = accion.get("indice", 0)
        if indice < 0 or indice >= len(jugador.mano):
            indice = 0
        carta = jugador.jugar_carta(indice)
        resultado = ronda.jugar_carta(jugador.nombre, carta)
        if resultado["baza_completa"] and engine.primera_baza:
            engine.marcar_primera_baza_jugada()

    elif tipo in ("envido", "real_envido", "falta_envido") and engine.puede_cantar_envido():
        _simular_envido(engine, jugador.nombre, tipo)

    elif tipo in ("truco", "retruco", "vale cuatro") and engine.puede_cantar_truco(jugador.nombre):
        _simular_truco(engine, ronda, jugador.nombre, tipo)

    elif tipo == "mazo":
        _simular_mazo(engine, ronda, jugador.nombre)

    else:
        # Acción inválida: jugar primera carta disponible
        if jugador.tiene_cartas():
            carta = jugador.jugar_carta(0)
            resultado = ronda.jugar_carta(jugador.nombre, carta)
            if resultado["baza_completa"] and engine.primera_baza:
                engine.marcar_primera_baza_jugada()


def _simular_ronda(engine) -> None:
    ronda = engine.nueva_ronda()
    turnos = 0

    while not ronda.terminada and turnos < MAX_TURNOS_RONDA:
        turno_nombre = ronda.turno
        turno_jugador = ronda.get_jugador(turno_nombre)
        _simular_turno(engine, ronda, turno_jugador)
        turnos += 1
        if ronda.terminada or engine.juego_terminado():
            break

    if ronda.ganador_ronda and not engine.juego_terminado():
        engine.finalizar_ronda(ronda.ganador_ronda)
    engine.alternar_mano()


def simular_partida(ia1_nombre: str, ia2_nombre: str) -> str | None:
    """Simula una partida completa. Retorna el nombre de la IA ganadora."""
    j1 = JugadorAI("Jugador_1", crear_ia(ia1_nombre))
    j2 = JugadorAI("Jugador_2", crear_ia(ia2_nombre))
    engine = TrucoEngine(j1, j2)

    rondas = 0
    while not engine.juego_terminado() and rondas < MAX_RONDAS_PARTIDA:
        _simular_ronda(engine)
        rondas += 1

    ganador = engine.ganador_juego()
    if ganador is None:
        return None
    return ia1_nombre if ganador.nombre == "Jugador_1" else ia2_nombre


# ── ELO ──────────────────────────────────────────────────

ELO_DEFAULT = 1000.0
ELO_PATH = Path(__file__).parent / "elo_ratings.py"


def _calcular_elo(
    rating_a: float, rating_b: float, score_a: float, k: float,
) -> tuple[float, float]:
    """Actualiza ELO. score_a: 1.0=ganó A, 0.0=ganó B, 0.5=empate."""
    expected_a = 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400))
    expected_b = 1.0 - expected_a
    new_a = rating_a + k * (score_a - expected_a)
    new_b = rating_b + k * ((1.0 - score_a) - expected_b)
    return round(new_a, 1), round(new_b, 1)


def _cargar_elo() -> dict[str, float]:
    try:
        import elo_ratings
        importlib.reload(elo_ratings)
        return {k: float(v) for k, v in elo_ratings.RATINGS.items()}
    except (ImportError, AttributeError):
        return {}


def _guardar_elo(ratings: dict[str, float]) -> None:
    lineas = [
        '"""\n',
        "ELO Ratings — Actualizado automáticamente por arena.py.\n",
        '"""\n',
        "\n",
        "RATINGS: dict[str, float] = {\n",
    ]
    for nombre in sorted(ratings):
        lineas.append(f'    "{nombre}": {ratings[nombre]},\n')
    lineas.append("}\n")
    ELO_PATH.write_text("".join(lineas), encoding="utf-8")


# ── Arena principal ──────────────────────────────────────

def arena() -> None:
    ia1 = ARENA_IA_1
    ia2 = ARENA_IA_2
    n = ARENA_PARTIDAS
    k = ARENA_ELO_K

    for ia in (ia1, ia2):
        if ia not in IA_REGISTRY:
            print(f"  ✗ IA desconocida: {ia!r}")
            print(f"    Disponibles: {list(IA_REGISTRY.keys())}")
            return

    ratings = _cargar_elo()
    for ia in (ia1, ia2):
        ratings.setdefault(ia, ELO_DEFAULT)

    elo_inicial = {ia1: ratings[ia1], ia2: ratings[ia2]}

    print(f"\n  ==========================================")
    print(f"  ARENA -- {ia1} vs {ia2}")
    print(f"  ==========================================")
    print(f"  Partidas: {n}")
    print(f"  ELO inicial: {ia1}={elo_inicial[ia1]:.1f}  {ia2}={elo_inicial[ia2]:.1f}")
    print(f"  K-factor: {k}")
    print()

    victorias = {ia1: 0, ia2: 0}
    empates = 0
    inicio = time.time()
    paso = max(1, n // 10)

    devnull = open(os.devnull, "w")
    for i in range(n):
        # Alternar quién es jugador1 cada partida
        if i % 2 == 0:
            j1_ia, j2_ia = ia1, ia2
        else:
            j1_ia, j2_ia = ia2, ia1

        with redirect_stdout(devnull):
            ganador = simular_partida(j1_ia, j2_ia)

        if ganador:
            victorias[ganador] += 1
            score_1 = 1.0 if ganador == ia1 else 0.0
            ratings[ia1], ratings[ia2] = _calcular_elo(
                ratings[ia1], ratings[ia2], score_1, k,
            )
        else:
            empates += 1
            ratings[ia1], ratings[ia2] = _calcular_elo(
                ratings[ia1], ratings[ia2], 0.5, k,
            )

        progreso = i + 1
        if progreso % paso == 0 or progreso == n:
            pct = progreso * 100 // n
            print(
                f"  [{pct:3d}%] {progreso}/{n} — "
                f"{ia1}: {victorias[ia1]}  {ia2}: {victorias[ia2]}  "
                f"ELO: {ratings[ia1]:.0f} / {ratings[ia2]:.0f}"
            )

    devnull.close()
    elapsed = time.time() - inicio
    total = victorias[ia1] + victorias[ia2] + empates

    print(f"\n  -- Resultados --------------------------")
    print(f"  {ia1:>15}: {victorias[ia1]:>4} victorias ({victorias[ia1] * 100 / total:.1f}%)")
    print(f"  {ia2:>15}: {victorias[ia2]:>4} victorias ({victorias[ia2] * 100 / total:.1f}%)")
    if empates:
        print(f"  {'empates':>15}: {empates:>4}")

    print(f"\n  -- ELO --------------------------------")
    for ia in (ia1, ia2):
        delta = ratings[ia] - elo_inicial[ia]
        print(f"  {ia}: {elo_inicial[ia]:.1f} → {ratings[ia]:.1f} ({delta:+.1f})")

    vel = n / elapsed if elapsed > 0 else 0
    print(f"\n  Tiempo: {elapsed:.1f}s ({vel:.1f} partidas/s)")

    _guardar_elo(ratings)
    print(f"  ELO guardado en elo_ratings.py\n")


if __name__ == "__main__":
    arena()
