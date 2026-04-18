"""
Truco Argentino — Punto de entrada principal.

Juego por terminal: Humano vs IA (placeholder aleatorio).
"""

from truco.jugador import JugadorHumano, JugadorAI
from truco.truco_engine import TrucoEngine, NOMBRES_TRUCO
from truco.ai_interface import AIInterface, RandomAI
from truco.ai_barrio import BarrioAI
from truco import terminal_ui as ui
from config import INTERFAZ, IA_MODEL


def jugar_ronda(engine: TrucoEngine) -> None:
    """Juega una ronda completa."""
    ronda = engine.nueva_ronda()
    humano = engine.jugador1
    cpu = engine.jugador2

    ui.mostrar_puntuacion(humano, cpu)
    ui.mostrar_mensaje(f"Mano: {engine.mano_nombre}")

    while not ronda.terminada:
        turno_nombre = ronda.turno
        turno_jugador = ronda.get_jugador(turno_nombre)
        es_humano = isinstance(turno_jugador, JugadorHumano)

        if es_humano:
            _turno_humano(engine, ronda, turno_jugador)
        else:
            _turno_cpu(engine, ronda, turno_jugador)

        if ronda.terminada or engine.juego_terminado():
            break

    # Fin de la ronda: no sumar puntos de truco si ya ganó alguien (ej: envido)
    if ronda.ganador_ronda and not engine.juego_terminado():
        puntos = engine.finalizar_ronda(ronda.ganador_ronda)
        ui.mostrar_ganador_ronda(ronda.ganador_ronda, puntos)

    engine.alternar_mano()


def _turno_humano(engine: TrucoEngine, ronda, jugador) -> None:
    """Procesa el turno del jugador humano."""
    ui.mostrar_mano(jugador)

    # Mostrar carta del oponente si ya jugó en esta baza
    carta_op = ronda.carta_oponente_en_baza_actual(jugador.nombre)
    if carta_op:
        oponente = ronda.get_oponente(jugador.nombre)
        ui.mostrar_mensaje(f"{oponente} jugó: {carta_op}")

    # Armar acciones disponibles
    acciones_extra = []
    if engine.puede_cantar_envido():
        acciones_extra.extend(["envido", "real_envido", "falta_envido"])
    if engine.puede_cantar_truco(jugador.nombre):
        nombre_truco = engine.nombre_siguiente_truco()
        acciones_extra.append(nombre_truco)
    acciones_extra.append("mazo")

    accion = ui.pedir_accion(jugador, acciones_extra)

    if accion.startswith("carta:"):
        indice = int(accion.split(":")[1])
        carta = jugador.jugar_carta(indice)
        ui.mostrar_carta_jugada(jugador.nombre, carta)
        resultado = ronda.jugar_carta(jugador.nombre, carta)
        _procesar_resultado_baza(engine, resultado)

    elif accion in ("envido", "real_envido", "falta_envido"):
        _manejar_envido(engine, jugador.nombre, accion)

    elif accion in ("truco", "retruco", "vale cuatro"):
        _manejar_truco(engine, ronda, jugador.nombre, accion)

    elif accion == "mazo":
        _manejar_mazo(engine, ronda, jugador.nombre)


def _turno_cpu(engine: TrucoEngine, ronda, jugador) -> None:
    """Procesa el turno de la CPU."""
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
        ui.mostrar_carta_jugada(jugador.nombre, carta)
        resultado = ronda.jugar_carta(jugador.nombre, carta)
        _procesar_resultado_baza(engine, resultado)

    elif tipo in ("envido", "real_envido", "falta_envido"):
        _manejar_envido(engine, jugador.nombre, tipo)

    elif tipo in ("truco", "retruco", "vale cuatro"):
        _manejar_truco(engine, ronda, jugador.nombre, tipo)

    elif tipo == "mazo":
        _manejar_mazo(engine, ronda, jugador.nombre)

    else:
        # Fallback: jugar primera carta
        if jugador.tiene_cartas():
            carta = jugador.jugar_carta(0)
            ui.mostrar_carta_jugada(jugador.nombre, carta)
            resultado = ronda.jugar_carta(jugador.nombre, carta)
            _procesar_resultado_baza(engine, resultado)


def _procesar_resultado_baza(engine: TrucoEngine, resultado: dict) -> None:
    """Muestra el resultado de una baza si está completa."""
    if resultado["baza_completa"]:
        ui.mostrar_resultado_baza(resultado["ganador_baza"], resultado["parda"])
        if engine.primera_baza:
            engine.marcar_primera_baza_jugada()
        print()


def _manejar_envido(engine: TrucoEngine, cantor: str, tipo_envido: str) -> None:
    """Maneja el flujo completo de envido con re-cantos y puntos correctos."""
    if not engine.puede_cantar_envido():
        ui.mostrar_mensaje("No se puede cantar envido ahora.")
        return

    ui.mostrar_truco_canto(cantor, tipo_envido.replace("_", " "))

    engine.envido_secuencia = [tipo_envido]
    secuencia = engine.envido_secuencia
    oponente_nombre = engine._oponente_nombre(cantor)
    oponente = engine._get_jugador(oponente_nombre)

    while True:
        respuestas_validas = engine.cantos_validos_respuesta_envido(secuencia)

        if isinstance(oponente, JugadorHumano):
            # Mostrar cartas antes de pedir respuesta
            ui.mostrar_mano(oponente)
            respuesta = ui.pedir_respuesta_envido(
                oponente,
                secuencia[-1].replace("_", " "),
                respuestas_validas,
            )
        else:
            game_state = engine.get_game_state(oponente_nombre)
            resp = oponente.decidir(game_state) if isinstance(oponente, JugadorAI) else {"tipo": "quiero"}
            respuesta = resp.get("tipo", "quiero")
            if respuesta not in respuestas_validas:
                respuesta = "quiero"

        if respuesta in ("quiero", "no_quiero"):
            break

        # Re-canto: el oponente sube la apuesta
        ui.mostrar_truco_canto(oponente_nombre, respuesta.replace("_", " "))
        secuencia.append(respuesta)
        cantor, oponente_nombre = oponente_nombre, cantor
        oponente = engine._get_jugador(oponente_nombre)

    aceptado = respuesta == "quiero"
    puntos_quiero, puntos_no_quiero = engine.calcular_puntos_envido_secuencia(secuencia)
    resultado = engine.resolver_envido(aceptado, cantor, puntos_quiero, puntos_no_quiero)
    resultado["nombre_j1"] = engine.jugador1.nombre
    resultado["nombre_j2"] = engine.jugador2.nombre

    ui.mostrar_envido_resultado(resultado)
    engine.sumar_puntos(resultado["ganador"], resultado["puntos"])
    ui.mostrar_puntuacion(engine.jugador1, engine.jugador2)


def _manejar_mazo(engine: TrucoEngine, ronda, jugador_nombre: str) -> None:
    """Irse al mazo: si es en primera sin envido cantado, el oponente gana 1 pt de envido."""
    ui.mostrar_mensaje(f"{jugador_nombre} se va al mazo.")
    if engine.primera_baza and not engine.envido_terminado:
        oponente_nombre = engine._oponente_nombre(jugador_nombre)
        engine.sumar_puntos(oponente_nombre, 1)
        engine.envido_terminado = True
        ui.mostrar_mensaje(f"Envido no cantado: {oponente_nombre} gana 1 pt.")
        ui.mostrar_puntuacion(engine.jugador1, engine.jugador2)
    ronda.ir_al_mazo(jugador_nombre)


def _manejar_truco(engine: TrucoEngine, ronda, cantor: str, nivel: str) -> None:
    """Maneja el flujo completo de truco/retruco/vale cuatro."""
    if not engine.puede_cantar_truco(cantor):
        ui.mostrar_mensaje("No podés cantar truco ahora.")
        return

    ui.mostrar_truco_canto(cantor, nivel)

    oponente_nombre = engine._oponente_nombre(cantor)
    oponente = engine._get_jugador(oponente_nombre)

    puede_subir = engine.nivel_truco + 1 < 3  # puede subir si no está en vale cuatro

    if isinstance(oponente, JugadorHumano):
        respuesta = ui.pedir_respuesta_truco(oponente, nivel, puede_subir)
    else:
        game_state = engine.get_game_state(oponente_nombre)
        if isinstance(oponente, JugadorAI):
            resp = oponente.ai.responder_truco(game_state)
        else:
            resp = {"tipo": "quiero"}
        respuesta = resp.get("tipo", "quiero")

    # El oponente puede subir la apuesta
    while respuesta in ("retruco", "vale cuatro"):
        ui.mostrar_truco_canto(oponente_nombre, respuesta)
        # Aceptar el nivel intermedio primero
        engine.nivel_truco = engine.siguiente_nivel_truco()
        engine.truco_cantado_por = oponente_nombre

        # Ahora el cantor original debe responder
        cantor, oponente_nombre = oponente_nombre, cantor
        oponente = engine._get_jugador(oponente_nombre)
        nivel = respuesta
        puede_subir = engine.nivel_truco + 1 < 3

        if isinstance(oponente, JugadorHumano):
            respuesta = ui.pedir_respuesta_truco(oponente, nivel, puede_subir)
        else:
            game_state = engine.get_game_state(oponente_nombre)
            if isinstance(oponente, JugadorAI):
                resp = oponente.ai.responder_truco(game_state)
            else:
                resp = {"tipo": "quiero"}
            respuesta = resp.get("tipo", "quiero")

    if respuesta == "quiero":
        resultado = engine.resolver_truco(True, cantor)
        ui.mostrar_truco_respuesta(oponente_nombre, True)
    else:
        resultado = engine.resolver_truco(False, cantor)
        ui.mostrar_truco_respuesta(oponente_nombre, False)
        # No quiero: el cantor gana la ronda con los puntos actuales
        ronda.ganador_ronda = cantor
        ronda.terminada = True

def _seleccionar_ia(model: str) -> AIInterface:
    if model == "barrio":
        return BarrioAI()
    return RandomAI()

def main() -> None:
    """Punto de entrada del juego."""
    if INTERFAZ == "gui":
        main_gui()
    else:
        main_cli()


def main_gui() -> None:
    """Inicia el juego con interfaz gráfica (Pygame)."""
    from truco.gui import TrucoGUI

    nombre = "Jugador"
    humano = JugadorHumano(nombre)
    cpu = JugadorAI("CPU", _seleccionar_ia(IA_MODEL))
    engine = TrucoEngine(humano, cpu)

    gui = TrucoGUI(engine)
    gui.run()


def main_cli() -> None:
    """Inicia el juego con interfaz de terminal."""
    ui.limpiar_pantalla()
    ui.mostrar_titulo()

    nombre = input("\n  Tu nombre: ").strip() or "Jugador"
    humano = JugadorHumano(nombre)
    cpu = JugadorAI("CPU", _seleccionar_ia(IA_MODEL))

    engine = TrucoEngine(humano, cpu)

    print(f"\n  ¡Arrancamos! {nombre} vs CPU — Primero a 30 puntos.\n")

    while not engine.juego_terminado():
        jugar_ronda(engine)
        if not engine.juego_terminado():
            ui.pausar()
            ui.limpiar_pantalla()
            ui.mostrar_titulo()

    ganador = engine.ganador_juego()
    if ganador:
        ui.mostrar_ganador_juego(ganador)

if __name__ == "__main__":
    main()
