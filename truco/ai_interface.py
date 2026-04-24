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
    
    Implementar elegir_accion() para crear una IA personalizada.
    
    El game_state contiene:
        - mano: list[dict]           — cartas en mano (numero, palo, poder, valor_envido)
        - cartas_jugadas_propias      — cartas que ya jugaste
        - cartas_jugadas_oponente     — cartas que jugó el oponente
        - carta_oponente_mesa         — carta del oponente en la baza actual (o None)
        - puntos_propios: int
        - puntos_oponente: int
        - nivel_truco: int            — 0=nada, 1=truco, 2=retruco, 3=vale4
        - envido_disponible: bool
        - puede_cantar_truco: bool
        - es_mano: bool
        - es_mi_turno: bool
        - acciones_disponibles: list[str]
        - puntos_objetivo: int        — 30
    
    Las acciones posibles son dicts:
        {"tipo": "jugar_carta", "indice": 0}     — jugar carta por índice
        {"tipo": "envido"}
        {"tipo": "real_envido"}
        {"tipo": "falta_envido"}
        {"tipo": "truco"}
        {"tipo": "retruco"}
        {"tipo": "vale cuatro"}
        {"tipo": "mazo"}                          — irse al mazo
        {"tipo": "quiero"}                        — aceptar envido/truco
        {"tipo": "no_quiero"}                     — rechazar envido/truco
    """

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

