"""
Modelo de carta española para Truco Argentino.

Jerarquía linealizada (1-13) para facilitar entrenamiento de IA:
  1 = 4 (cualquier palo)
  2 = 5
  3 = 6
  4 = 7 diamante / 7 corazón
  5 = 10 (sota)
  6 = 11 (caballo)
  7 = 12 (rey)
  8 = 1 oro / 1 copa
  9 = 2 (cualquier palo)
 10 = 3 (cualquier palo)
 11 = 7 oro
 12 = 7 espada
 13 = 1 basto
 14 = 1 espada   (máximo)
"""

from __future__ import annotations

PALOS = ("espada", "basto", "oro", "copa")

# (numero, palo) -> poder  (valor linealizado 1-14)
JERARQUIA: dict[tuple[int, str], int] = {
    # Valor 1 — los cuatro
    (4, "espada"): 1, (4, "basto"): 1, (4, "oro"): 1, (4, "copa"): 1,
    # Valor 2 — los cinco
    (5, "espada"): 2, (5, "basto"): 2, (5, "oro"): 2, (5, "copa"): 2,
    # Valor 3 — los seis
    (6, "espada"): 3, (6, "basto"): 3, (6, "oro"): 3, (6, "copa"): 3,
    # Valor 4 — siete falso (basto y copa)
    (7, "basto"): 4, (7, "copa"): 4,
    # Valor 5 — sota (10)
    (10, "espada"): 5, (10, "basto"): 5, (10, "oro"): 5, (10, "copa"): 5,
    # Valor 6 — caballo (11)
    (11, "espada"): 6, (11, "basto"): 6, (11, "oro"): 6, (11, "copa"): 6,
    # Valor 7 — rey (12)
    (12, "espada"): 7, (12, "basto"): 7, (12, "oro"): 7, (12, "copa"): 7,
    # Valor 8 — ancho falso (1 oro, 1 copa)
    (1, "oro"): 8, (1, "copa"): 8,
    # Valor 9 — los dos
    (2, "espada"): 9, (2, "basto"): 9, (2, "oro"): 9, (2, "copa"): 9,
    # Valor 10 — los tres
    (3, "espada"): 10, (3, "basto"): 10, (3, "oro"): 10, (3, "copa"): 10,
    # Valor 11 — siete de oro
    (7, "oro"): 11,
    # Valor 12 — siete de espada
    (7, "espada"): 12,
    # Valor 13 — ancho de basto
    (1, "basto"): 13,
    # Valor 14 — ancho de espada (máximo)
    (1, "espada"): 14,
}

NOMBRE_NUMERO = {
    1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7",
    10: "Sota", 11: "Caballo", 12: "Rey",
}


class Carta:
    """Representa una carta española."""

    __slots__ = ("numero", "palo", "poder", "valor_envido", "_dict")

    def __init__(self, numero: int, palo: str) -> None:
        self.numero = numero
        self.palo = palo
        self.poder: int = JERARQUIA[(numero, palo)]
        # Para envido: figuras (10,11,12) valen 0, el resto su número
        self.valor_envido: int = 0 if numero >= 10 else numero
        # Dict pre-armado para game_state: la carta es inmutable, así que se
        # comparte la misma instancia en cada get_game_state (las IAs lo
        # tratan como solo lectura por contrato de AIInterface).
        self._dict: dict = {
            "numero": numero,
            "palo": palo,
            "poder": self.poder,
            "valor_envido": self.valor_envido,
        }

    def __repr__(self) -> str:
        nombre = NOMBRE_NUMERO.get(self.numero, str(self.numero))
        return f"{nombre} de {self.palo}"

    def __str__(self) -> str:
        return self.__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Carta):
            return NotImplemented
        return self.numero == other.numero and self.palo == other.palo

    def __hash__(self) -> int:
        return hash((self.numero, self.palo))

    def to_dict(self) -> dict:
        """Dict para el estado de IA. Compartido: tratarlo como solo lectura."""
        return self._dict
