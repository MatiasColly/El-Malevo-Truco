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
        self._envido: int = 0  # cacheado por ronda (get_game_state lo pide por turno)

    def recibir_cartas(self, cartas: list[Carta]) -> None:
        self.mano = list(cartas)
        self.cartas_ronda = list(cartas)
        self._envido = self._calcular_envido(self.cartas_ronda)

    def tiene_cartas(self) -> bool:
        return len(self.mano) > 0

    def jugar_carta(self, indice: int) -> Carta:
        """Juega la carta en la posición indicada (0-based)."""
        return self.mano.pop(indice)

    def calcular_envido(self) -> int:
        """Mejor envido de la ronda (calculado al repartir, constante hasta la próxima)."""
        return self._envido

    @staticmethod
    def _calcular_envido(cartas: list[Carta]) -> int:
        """Calcula el mejor envido con las 3 cartas originales de la ronda."""
        if not cartas:
            return 0

        mejor = max(c.valor_envido for c in cartas)

        n = len(cartas)
        for i in range(n):
            for j in range(i + 1, n):
                if cartas[i].palo == cartas[j].palo:
                    valor = 20 + cartas[i].valor_envido + cartas[j].valor_envido
                    if valor > mejor:
                        mejor = valor

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
