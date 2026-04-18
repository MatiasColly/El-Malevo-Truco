"""
Interfaz de terminal para el Truco Argentino.

Separada del motor para facilitar reemplazo por GUI en el futuro.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .jugador import Jugador
    from .carta import Carta
    from .truco_engine import TrucoEngine


def limpiar_pantalla() -> None:
    import os
    os.system("cls" if os.name == "nt" else "clear")


def mostrar_titulo() -> None:
    print("=" * 50)
    print("       TRUCO ARGENTINO")
    print("=" * 50)


def mostrar_puntuacion(j1: Jugador, j2: Jugador) -> None:
    print(f"\n  {j1.nombre}: {j1.puntos} pts  |  {j2.nombre}: {j2.puntos} pts")
    print("-" * 50)


def mostrar_mano(jugador: Jugador) -> None:
    print(f"\nTu mano ({jugador.nombre}):")
    for i, carta in enumerate(jugador.mano):
        print(f"  [{i + 1}] {carta}")


def mostrar_carta_jugada(nombre: str, carta: Carta) -> None:
    print(f"  {nombre} juega: {carta}")


def mostrar_resultado_baza(ganador: str | None, parda: bool) -> None:
    if parda:
        print("  ¡Parda! (empate)")
    elif ganador:
        print(f"  Gana la baza: {ganador}")


def mostrar_ganador_ronda(ganador: str, puntos: int) -> None:
    print(f"\n{'*' * 40}")
    print(f"  {ganador} gana la ronda (+{puntos} pts)")
    print(f"{'*' * 40}")


def mostrar_ganador_juego(ganador: Jugador) -> None:
    print(f"\n{'=' * 50}")
    print(f"  ¡¡¡ {ganador.nombre} GANA EL JUEGO !!!")
    print(f"  Puntaje final: {ganador.puntos}")
    print(f"{'=' * 50}")


def mostrar_envido_resultado(resultado: dict) -> None:
    if resultado["aceptado"]:
        print(f"  Envido de {resultado.get('nombre_j1', 'J1')}: {resultado['envido_j1']}")
        print(f"  Envido de {resultado.get('nombre_j2', 'J2')}: {resultado['envido_j2']}")
        print(f"  Gana el envido: {resultado['ganador']} (+{resultado['puntos']} pts)")
    else:
        print(f"  No quiso. {resultado['ganador']} gana +{resultado['puntos']} pts de envido.")


def mostrar_truco_canto(nombre: str, nivel: str) -> None:
    print(f"\n  ¡{nombre} canta {nivel.upper()}!")


def mostrar_truco_respuesta(nombre: str, acepta: bool) -> None:
    if acepta:
        print(f"  {nombre}: ¡Quiero!")
    else:
        print(f"  {nombre}: No quiero.")


def mostrar_mensaje(msg: str) -> None:
    print(f"  {msg}")


def pedir_accion(jugador: Jugador, acciones_extra: list[str]) -> str:
    """
    Pide al jugador humano que elija una acción.
    
    Returns:
        La acción elegida como string.
    """
    print(f"\n¿Qué hacés, {jugador.nombre}?")
    opciones = []

    # Siempre puede jugar carta si tiene
    if jugador.tiene_cartas():
        print("  [1-{}] Jugar carta".format(len(jugador.mano)))
        opciones.append("carta")

    idx = len(jugador.mano) + 1 if jugador.tiene_cartas() else 1
    mapa_opciones: dict[int, str] = {}

    for accion in acciones_extra:
        etiqueta = _etiqueta_accion(accion)
        print(f"  [{idx}] {etiqueta}")
        mapa_opciones[idx] = accion
        idx += 1

    while True:
        try:
            entrada = input("\n> ").strip()
            if not entrada:
                continue
            num = int(entrada)

            # Jugar carta
            if jugador.tiene_cartas() and 1 <= num <= len(jugador.mano):
                return f"carta:{num - 1}"

            # Acción extra
            if num in mapa_opciones:
                return mapa_opciones[num]

            print("  Opción inválida, intentá de nuevo.")
        except ValueError:
            # Aceptar texto directo
            texto = entrada.lower()
            if texto in ("envido", "real_envido", "falta_envido",
                         "truco", "retruco", "vale cuatro", "mazo"):
                return texto
            print("  Entrada inválida.")
        except (EOFError, KeyboardInterrupt):
            print("\n  Saliendo...")
            raise SystemExit(0)


def pedir_respuesta_envido(jugador: Jugador, canto: str,
                           respuestas_validas: list[str]) -> str:
    """Pide respuesta a un canto de envido mostrando solo las opciones válidas."""
    print(f"\n  Te cantaron {canto.upper()}. ¿Qué hacés, {jugador.nombre}?")

    etiquetas = {
        "quiero":       "Quiero",
        "no_quiero":    "No quiero",
        "envido":       "Envido",
        "real_envido":  "Real Envido",
        "falta_envido": "Falta Envido",
    }

    mapa: dict[int, str] = {}
    for i, resp in enumerate(respuestas_validas, start=1):
        print(f"  [{i}] {etiquetas.get(resp, resp)}")
        mapa[i] = resp

    while True:
        try:
            entrada = input("\n> ").strip()
            num = int(entrada)
            if num in mapa:
                return mapa[num]
            print("  Opción inválida.")
        except ValueError:
            print("  Opción inválida.")
        except (EOFError, KeyboardInterrupt):
            raise SystemExit(0)


def pedir_respuesta_truco(jugador: Jugador, nivel: str,
                          puede_subir: bool) -> str:
    """Pide respuesta a un canto de truco."""
    print(f"\n  Te cantaron {nivel.upper()}. ¿Qué hacés, {jugador.nombre}?")
    print("  [1] Quiero")
    print("  [2] No quiero")
    if puede_subir:
        siguiente = _nombre_siguiente_truco(nivel)
        print(f"  [3] {siguiente}")

    while True:
        try:
            entrada = input("\n> ").strip()
            if entrada == "1":
                return "quiero"
            elif entrada == "2":
                return "no_quiero"
            elif entrada == "3" and puede_subir:
                return _nombre_siguiente_truco(nivel)
            else:
                print("  Opción inválida.")
        except (EOFError, KeyboardInterrupt):
            raise SystemExit(0)


def pausar() -> None:
    try:
        input("\n  Presioná Enter para continuar...")
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(0)


def _etiqueta_accion(accion: str) -> str:
    etiquetas = {
        "envido": "Envido",
        "real_envido": "Real Envido",
        "falta_envido": "Falta Envido",
        "truco": "Truco",
        "retruco": "Retruco",
        "vale cuatro": "Vale Cuatro",
        "mazo": "Me voy al mazo",
    }
    return etiquetas.get(accion, accion)


def _nombre_siguiente_truco(nivel_actual: str) -> str:
    niveles = {"truco": "retruco", "retruco": "vale cuatro"}
    return niveles.get(nivel_actual, "vale cuatro")
