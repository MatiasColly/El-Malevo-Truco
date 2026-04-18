"""Mazo de cartas españolas (40 cartas, sin 8 ni 9)."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .carta import Carta, PALOS

if TYPE_CHECKING:
    pass

NUMEROS = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)


class Mazo:
    """Mazo español de 40 cartas."""

    def __init__(self) -> None:
        self.cartas: list[Carta] = []
        self.reset()

    def reset(self) -> None:
        """Reconstruye y mezcla el mazo."""
        self.cartas = [Carta(n, p) for n in NUMEROS for p in PALOS]
        self.mezclar()

    def mezclar(self) -> None:
        random.shuffle(self.cartas)

    def repartir(self, cantidad: int = 3) -> list[Carta]:
        """Reparte `cantidad` cartas del tope del mazo."""
        if len(self.cartas) < cantidad:
            self.reset()
        mano = self.cartas[:cantidad]
        self.cartas = self.cartas[cantidad:]
        return mano

    def __len__(self) -> int:
        return len(self.cartas)
