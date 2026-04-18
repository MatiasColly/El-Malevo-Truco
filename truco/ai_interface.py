"""
Interfaz de IA para el Truco Argentino.

Define la interfaz abstracta y una implementación aleatoria como placeholder.
Para entrenar una IA, crear una subclase de AIInterface e implementar elegir_accion().
"""

from __future__ import annotations

import random
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


class RandomAI(AIInterface):
    """IA aleatoria como placeholder — útil para testing."""

    def elegir_accion(self, game_state: dict) -> dict:
        mano = game_state.get("mano", [])
        acciones = game_state.get("acciones_disponibles", [])

        # 80% de las veces juega carta, 20% intenta cantar algo
        if mano and random.random() < 0.8:
            indice = random.randint(0, len(mano) - 1)
            return {"tipo": "jugar_carta", "indice": indice}

        # Intentar cantar algo
        cantos = [a for a in acciones if a != "jugar_carta" and a != "mazo"]
        if cantos:
            canto = random.choice(cantos)
            return {"tipo": canto}

        # Fallback: jugar carta
        if mano:
            indice = random.randint(0, len(mano) - 1)
            return {"tipo": "jugar_carta", "indice": indice}

        return {"tipo": "mazo"}

    def responder_envido(self, game_state: dict) -> dict:
        # 60% quiero, 20% no quiero, 20% subir
        r = random.random()
        if r < 0.6:
            return {"tipo": "quiero"}
        elif r < 0.8:
            return {"tipo": "no_quiero"}
        else:
            if game_state.get("envido_disponible", False):
                return {"tipo": random.choice(["real_envido", "falta_envido"])}
            return {"tipo": "quiero"}

    def responder_truco(self, game_state: dict) -> dict:
        # 60% quiero, 25% no quiero, 15% subir
        r = random.random()
        if r < 0.6:
            return {"tipo": "quiero"}
        elif r < 0.85:
            return {"tipo": "no_quiero"}
        else:
            if game_state.get("puede_cantar_truco", False):
                nivel = game_state.get("nivel_truco", 0)
                if nivel == 0:
                    return {"tipo": "retruco"}
                elif nivel == 1:
                    return {"tipo": "vale cuatro"}
            return {"tipo": "quiero"}
