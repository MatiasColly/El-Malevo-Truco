"""
IA de Barrio para el Truco Argentino.

Simula un jugador humano con heurísticas y un grado de aleatoriedad.
Subclase de AIInterface definida en ai_interface.py.
"""

from __future__ import annotations

import random

from .ai_interface import AIInterface


class BarrioAI(AIInterface):
    """IA de barrio, hecha a mano, tal como guacho viejo y salvaje."""

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
