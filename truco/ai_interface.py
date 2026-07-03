"""
Interfaz de IA para el Truco Argentino.

Define la interfaz abstracta. Las implementaciones concretas viven en truco/AI/.
Para crear una nueva IA, subclasear AIInterface e implementar los tres métodos.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIInterface(ABC):
    """
    Interfaz abstracta para la IA del truco.

    Implementar los tres métodos abstractos para crear una IA personalizada.

    ── game_state ────────────────────────────────────────────────────────────
    Cartas (cada carta es un dict con: numero, palo, poder, valor_envido):
        mano: list[dict]                — cartas que aún tenés en la mano
        cartas_jugadas_propias: list[dict]
        cartas_jugadas_oponente: list[dict]
        carta_oponente_mesa: dict | None — carta que el oponente ya puso en
                                          la baza actual, o None si aún no jugó

    Bazas completadas (listas paralelas, una entrada por baza terminada):
        bazas: list[str]        — "yo" | "oponente" | "parda"
        manos_baza: list[str]   — quién jugó primero: "yo" | "oponente"

    Puntos:
        puntos_propios: int
        puntos_oponente: int
        puntos_objetivo: int    — 30
        envido_propio: int      — puntaje de envido de tu mano

    Truco:
        nivel_truco: int        — 0=sin cantar, 1=truco, 2=retruco, 3=vale4
        puede_cantar_truco: bool

    Envido:
        envido_disponible: bool
        envido_secuencia: list[str]     — cantos ya realizados en esta ronda,
                                          e.g. ["envido", "real_envido"]
        envido_en_juego: int | None     — puntos apostados si se resuelve querido

    Turno / rol:
        es_mano: bool           — True si sos el primero en jugar la baza actual
        es_mano_ronda: bool     — True si sos el mano de la ronda (reparte el contrario)
        es_mi_turno: bool
        acciones_disponibles: list[str]   — subconjunto de las acciones válidas ahora

    ── Acciones ──────────────────────────────────────────────────────────────
    elegir_accion() y responder_*() deben retornar uno de estos dicts:
        {"tipo": "jugar_carta", "indice": int}  — índice en `mano`
        {"tipo": "envido"}
        {"tipo": "real_envido"}
        {"tipo": "falta_envido"}
        {"tipo": "truco"}
        {"tipo": "retruco"}
        {"tipo": "vale cuatro"}
        {"tipo": "quiero"}
        {"tipo": "no_quiero"}
        {"tipo": "mazo"}                        — rendirse / irse al mazo
    """

    # Log de razonamiento de la IA. Con debug=False (default) _log no formatea
    # ni imprime nada: crítico para la velocidad de arena/entrenamiento, donde
    # los print() consumían ~30% del tiempo aunque fueran redirigidos a devnull.
    # Poner AIInterface.debug = True para ver el razonamiento jugando por CLI.
    debug: bool = False

    def _log(self, *args) -> None:
        if self.debug:
            print(*args)

    @abstractmethod
    def elegir_accion(self, game_state: dict) -> dict:
        """
        Dado el estado del juego, retorna la acción a tomar.
        
        Args:
            game_state: Estado actual del juego.
            
        Returns:
            Diccionario con la acción elegida.
        """
        ...

    @abstractmethod
    def responder_envido(self, game_state: dict) -> dict:
        """
        Responde a un canto de envido.
        
        Returns:
            {"tipo": "quiero"} o {"tipo": "no_quiero"}
            o un re-canto: {"tipo": "real_envido"}, {"tipo": "falta_envido"}
        """
        ...

    @abstractmethod
    def responder_truco(self, game_state: dict) -> dict:
        """
        Responde a un canto de truco.
        
        Returns:
            {"tipo": "quiero"} o {"tipo": "no_quiero"}
            o subir: {"tipo": "retruco"}, {"tipo": "vale cuatro"}
        """
        ...

