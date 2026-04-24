"""Clases de jugador: humano y IA."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .carta import Carta

if TYPE_CHECKING:
    from .ai_interface import AIInterface


class Jugador:
    """Jugador base."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        self.mano: list[Carta] = []
        self.cartas_ronda: list[Carta] = []  # las 3 cartas originales de la ronda
        self.puntos: int = 0

    def recibir_cartas(self, cartas: list[Carta]) -> None:
        self.mano = list(cartas)
        self.cartas_ronda = list(cartas)

    def tiene_cartas(self) -> bool:
        return len(self.mano) > 0

    def jugar_carta(self, indice: int) -> Carta:
        """Juega la carta en la posición indicada (0-based)."""
        return self.mano.pop(indice)

    def calcular_envido(self) -> int:
        """Calcula el mejor envido usando las 3 cartas originales de la ronda."""
        from itertools import combinations

        cartas = self.cartas_ronda
        if not cartas:
            return 0

        mejor = max(c.valor_envido for c in cartas)

        for c1, c2 in combinations(cartas, 2):
            if c1.palo == c2.palo:
                valor = 20 + c1.valor_envido + c2.valor_envido
                mejor = max(mejor, valor)

        return mejor

    def __repr__(self) -> str:
        return f"Jugador({self.nombre})"


class JugadorHumano(Jugador):
    """Jugador controlado por terminal."""

    def __init__(self, nombre: str = "Jugador") -> None:
        super().__init__(nombre)
        self.es_humano = True


class JugadorAI(Jugador):
    """Jugador controlado por IA (placeholder para futuro entrenamiento)."""

    def __init__(self, nombre: str = "CPU", ai: AIInterface | None = None) -> None:
        super().__init__(nombre)
        self.es_humano = False
        self._ai: AIInterface | None = ai

    @property
    def ai(self) -> AIInterface:
        if self._ai is None:
            from .AI.ai_random import RandomAI
            self._ai = RandomAI()
        return self._ai

    @ai.setter
    def ai(self, value: AIInterface) -> None:
        self._ai = value

    def decidir(self, game_state: dict) -> dict:
        """Delega la decisión a la interfaz de IA."""
        return self.ai.elegir_accion(game_state)
