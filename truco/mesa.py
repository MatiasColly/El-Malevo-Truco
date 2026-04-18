"""
Mesa / Ronda: gestiona las 3 bazas de una ronda de truco.

Cada ronda tiene hasta 3 bazas. El ganador de 2 bazas gana la ronda.
En caso de empate (parda), gana quien es mano o quien ganó la primera baza.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .jugador import Jugador
    from .carta import Carta


class Baza:
    """Una baza (enfrentamiento de 2 cartas)."""

    def __init__(self) -> None:
        self.cartas: dict[str, Carta] = {}  # nombre_jugador -> carta
        self.ganador: str | None = None
        self.parda: bool = False

    def jugar(self, jugador: Jugador, carta: Carta) -> None:
        self.cartas[jugador.nombre] = carta

    def esta_completa(self) -> bool:
        return len(self.cartas) == 2

    def resolver(self, nombre_j1: str, nombre_j2: str) -> str | None:
        """Resuelve la baza. Retorna nombre del ganador o None si parda."""
        if not self.esta_completa():
            return None

        c1 = self.cartas[nombre_j1]
        c2 = self.cartas[nombre_j2]

        if c1.poder > c2.poder:
            self.ganador = nombre_j1
        elif c2.poder > c1.poder:
            self.ganador = nombre_j2
        else:
            self.parda = True
            self.ganador = None

        return self.ganador


class Ronda:
    """Gestiona una ronda completa (hasta 3 bazas)."""

    def __init__(self, jugador1: Jugador, jugador2: Jugador, mano: str) -> None:
        """
        Args:
            jugador1, jugador2: los dos jugadores
            mano: nombre del jugador que es mano (juega primero)
        """
        self.jugador1 = jugador1
        self.jugador2 = jugador2
        self.mano = mano  # quien es mano
        self.bazas: list[Baza] = []
        self.baza_actual: Baza = Baza()
        self.turno: str = mano  # quien juega ahora
        self.ganador_ronda: str | None = None
        self.terminada: bool = False
        self.fold: str | None = None  # si alguien se fue al mazo

    def get_jugador(self, nombre: str) -> Jugador:
        if nombre == self.jugador1.nombre:
            return self.jugador1
        return self.jugador2

    def get_oponente(self, nombre: str) -> str:
        if nombre == self.jugador1.nombre:
            return self.jugador2.nombre
        return self.jugador1.nombre

    def jugar_carta(self, nombre: str, carta: Carta) -> dict:
        """
        Un jugador juega una carta en la baza actual.
        Retorna estado: {"baza_completa": bool, "ganador_baza": str|None,
                         "ronda_terminada": bool, "ganador_ronda": str|None}
        """
        jugador = self.get_jugador(nombre)
        self.baza_actual.jugar(jugador, carta)

        resultado = {
            "baza_completa": False,
            "ganador_baza": None,
            "ronda_terminada": False,
            "ganador_ronda": None,
            "parda": False,
        }

        if self.baza_actual.esta_completa():
            ganador = self.baza_actual.resolver(
                self.jugador1.nombre, self.jugador2.nombre
            )
            resultado["baza_completa"] = True
            resultado["ganador_baza"] = ganador
            resultado["parda"] = self.baza_actual.parda

            self.bazas.append(self.baza_actual)
            self._evaluar_ronda()

            if self.terminada:
                resultado["ronda_terminada"] = True
                resultado["ganador_ronda"] = self.ganador_ronda
            else:
                self.baza_actual = Baza()
                # Siguiente turno: ganador de la baza, o mano si parda
                if ganador:
                    self.turno = ganador
                else:
                    self.turno = self.mano
        else:
            # El otro jugador debe jugar
            self.turno = self.get_oponente(nombre)

        return resultado

    def ir_al_mazo(self, nombre: str) -> None:
        """El jugador se va al mazo (fold). El oponente gana la ronda."""
        self.fold = nombre
        self.ganador_ronda = self.get_oponente(nombre)
        self.terminada = True

    def _evaluar_ronda(self) -> None:
        """Determina si la ronda terminó y quién ganó."""
        num_bazas = len(self.bazas)

        if num_bazas < 2:
            return

        ganadas = {}
        ganadas[self.jugador1.nombre] = 0
        ganadas[self.jugador2.nombre] = 0
        primera_ganada_por: str | None = None

        for i, baza in enumerate(self.bazas):
            if baza.ganador:
                ganadas[baza.ganador] += 1
                if i == 0 and primera_ganada_por is None:
                    primera_ganada_por = baza.ganador

        j1 = self.jugador1.nombre
        j2 = self.jugador2.nombre

        # Alguien ganó 2 bazas
        if ganadas[j1] >= 2:
            self.ganador_ronda = j1
            self.terminada = True
            return
        if ganadas[j2] >= 2:
            self.ganador_ronda = j2
            self.terminada = True
            return

        if num_bazas == 2:
            # Si ambas fueron parda, seguimos a la tercera
            if ganadas[j1] == 0 and ganadas[j2] == 0:
                return
            # 1 ganada + 1 parda = ganó el que ganó la no-parda
            if ganadas[j1] == 1 and ganadas[j2] == 0:
                self.ganador_ronda = j1
                self.terminada = True
                return
            if ganadas[j2] == 1 and ganadas[j1] == 0:
                self.ganador_ronda = j2
                self.terminada = True
                return
            # 1-1, vamos a tercera baza
            return

        if num_bazas == 3:
            # Alguien tiene 2 ya revisado arriba
            # Si la tercera es parda
            if self.bazas[2].parda:
                # Gana quien ganó la primera baza, o mano si primera fue parda
                if primera_ganada_por:
                    self.ganador_ronda = primera_ganada_por
                else:
                    self.ganador_ronda = self.mano
            else:
                # La tercera la ganó alguien
                self.ganador_ronda = self.bazas[2].ganador

            self.terminada = True

    def cartas_jugadas(self, nombre: str) -> list[Carta]:
        """Retorna las cartas que un jugador ya jugó en bazas anteriores."""
        jugadas = []
        for baza in self.bazas:
            if nombre in baza.cartas:
                jugadas.append(baza.cartas[nombre])
        if nombre in self.baza_actual.cartas:
            jugadas.append(self.baza_actual.cartas[nombre])
        return jugadas

    def carta_oponente_en_baza_actual(self, nombre: str) -> Carta | None:
        """Retorna la carta del oponente en la baza actual si ya jugó."""
        oponente = self.get_oponente(nombre)
        return self.baza_actual.cartas.get(oponente)
