"""
Motor principal del Truco Argentino.

Gestiona: rondas, envido, truco, puntuación hasta 30 puntos.
"""

from __future__ import annotations

from .carta import Carta
from .mazo import Mazo
from .jugador import Jugador, JugadorHumano, JugadorAI
from .mesa import Ronda

PUNTOS_OBJETIVO = 30

# Niveles de truco y sus puntos
NIVELES_TRUCO = {
    0: 1,  # sin cantar -> vale 1
    1: 2,  # truco -> vale 2
    2: 3,  # retruco -> vale 3
    3: 4,  # vale cuatro -> vale 4
}

NOMBRES_TRUCO = {0: "sin truco", 1: "truco", 2: "retruco", 3: "vale cuatro"}

# Niveles de envido
ENVIDO_ENVIDO = "envido"
ENVIDO_REAL = "real_envido"
ENVIDO_FALTA = "falta_envido"

# Tabla de puntos: secuencia de cantos → (puntos_quiero, puntos_no_quiero)
# None en puntos_quiero = falta envido (se calcula en runtime)
ENVIDO_TABLA: dict[tuple, tuple[int | None, int]] = {
    ("envido",):                                          (2,    1),
    ("real_envido",):                                     (3,    1),
    ("falta_envido",):                                    (None, 1),
    ("envido", "envido"):                                 (4,    2),
    ("envido", "real_envido"):                            (5,    2),
    ("envido", "falta_envido"):                           (None, 2),
    ("real_envido", "falta_envido"):                      (None, 3),
    ("envido", "envido", "real_envido"):                  (7,    5),
    ("envido", "envido", "falta_envido"):                 (None, 4),
    ("envido", "real_envido", "falta_envido"):            (None, 5),
    ("envido", "envido", "real_envido", "falta_envido"):  (None, 7),
}


class TrucoEngine:
    """Motor del juego de truco."""

    def __init__(self, jugador1: Jugador, jugador2: Jugador) -> None:
        self.jugador1 = jugador1
        self.jugador2 = jugador2
        self.mazo = Mazo()
        self.mano_idx: int = 0  # índice del jugador que es mano (alterna)
        self.ronda: Ronda | None = None

        # Estado de la ronda actual
        self.nivel_truco: int = 0
        self.truco_cantado_por: str | None = None
        self.envido_puntos: int = 0  # puntos acumulados de envido
        self.envido_terminado: bool = False
        self.envido_cantado: bool = False
        self.primera_baza: bool = True  # envido solo en primera baza

    @property
    def jugadores(self) -> list[Jugador]:
        return [self.jugador1, self.jugador2]

    @property
    def mano_nombre(self) -> str:
        return self.jugadores[self.mano_idx].nombre

    @property
    def pie_nombre(self) -> str:
        return self.jugadores[1 - self.mano_idx].nombre

    def juego_terminado(self) -> bool:
        return (self.jugador1.puntos >= PUNTOS_OBJETIVO or
                self.jugador2.puntos >= PUNTOS_OBJETIVO)

    def ganador_juego(self) -> Jugador | None:
        if self.jugador1.puntos >= PUNTOS_OBJETIVO:
            return self.jugador1
        if self.jugador2.puntos >= PUNTOS_OBJETIVO:
            return self.jugador2
        return None

    def nueva_ronda(self) -> Ronda:
        """Inicia una nueva ronda: mezcla, reparte, reinicia estado."""
        self.mazo.reset()
        self.jugador1.recibir_cartas(self.mazo.repartir(3))
        self.jugador2.recibir_cartas(self.mazo.repartir(3))

        self.nivel_truco = 0
        self.truco_cantado_por = None
        self.envido_puntos = 0
        self.envido_terminado = False
        self.envido_cantado = False
        self.primera_baza = True

        self.ronda = Ronda(self.jugador1, self.jugador2, self.mano_nombre)
        return self.ronda

    def alternar_mano(self) -> None:
        """Alterna quién es mano para la siguiente ronda."""
        self.mano_idx = 1 - self.mano_idx

    # ── Envido ──────────────────────────────────────────────

    def puede_cantar_envido(self) -> bool:
        """El envido solo se puede cantar en la primera baza, antes de jugar."""
        return self.primera_baza and not self.envido_terminado

    def calcular_puntos_envido_secuencia(self, secuencia: list[str]) -> tuple[int, int]:
        """
        Retorna (puntos_quiero, puntos_no_quiero) para la secuencia de cantos dada.
        Usa la tabla fija; el falta envido se calcula en runtime según puntajes.
        """
        key = tuple(secuencia)
        if key not in ENVIDO_TABLA:
            # Secuencia desconocida: fallback acumulativo seguro
            return (len(secuencia) * 2, len(secuencia))

        q_raw, nq = ENVIDO_TABLA[key]
        q = self._calcular_falta_envido() if q_raw is None else q_raw
        return q, nq

    def _calcular_falta_envido(self) -> int:
        """
        Puntos del falta envido:
        - Ambos en las malas (< 15): puntos para completar las malas (15 - lider)
        - Al menos uno en las buenas (>= 15): puntos para ganar el partido (30 - lider)
        """
        p1 = self.jugador1.puntos
        p2 = self.jugador2.puntos
        lider = max(p1, p2)
        if p1 < 15 and p2 < 15:
            return 15 - lider
        return PUNTOS_OBJETIVO - lider

    def cantos_validos_respuesta_envido(self, secuencia: list[str]) -> list[str]:
        """Retorna los cantos válidos que puede hacer el oponente ante la secuencia."""
        last = secuencia[-1] if secuencia else None
        if last == ENVIDO_FALTA:
            return ["quiero", "no_quiero"]
        if last == ENVIDO_REAL:
            return ["quiero", "no_quiero", "falta_envido"]
        if last == ENVIDO_ENVIDO:
            # Puede re-cantar envido solo si hay menos de 2 envidos en la secuencia
            if secuencia.count(ENVIDO_ENVIDO) < 2:
                return ["quiero", "no_quiero", "envido", "real_envido", "falta_envido"]
            return ["quiero", "no_quiero", "real_envido", "falta_envido"]
        return ["quiero", "no_quiero"]

    def resolver_envido(self, aceptado: bool, cantor: str,
                        puntos_quiero: int, puntos_no_quiero: int) -> dict:
        """
        Resuelve el envido.

        Returns:
            {"aceptado": bool, "ganador": str, "puntos": int,
             "envido_j1": int, "envido_j2": int}
        """
        self.envido_terminado = True
        self.envido_cantado = True

        if not aceptado:
            return {
                "aceptado": False,
                "ganador": cantor,
                "puntos": puntos_no_quiero,
                "envido_j1": 0,
                "envido_j2": 0,
            }

        # Quiero: comparar envido
        e1 = self.jugador1.calcular_envido()
        e2 = self.jugador2.calcular_envido()

        # En empate gana mano
        if e1 > e2:
            ganador = self.jugador1.nombre
        elif e2 > e1:
            ganador = self.jugador2.nombre
        else:
            ganador = self.mano_nombre

        return {
            "aceptado": True,
            "ganador": ganador,
            "puntos": puntos_quiero,
            "envido_j1": e1,
            "envido_j2": e2,
        }

    # ── Truco ──────────────────────────────────────────────

    def puede_cantar_truco(self, nombre: str) -> bool:
        """Un jugador puede subir el truco si no lo cantó él último."""
        if self.nivel_truco >= 3:
            return False
        if self.truco_cantado_por == nombre:
            return False
        return True

    def siguiente_nivel_truco(self) -> int:
        return min(self.nivel_truco + 1, 3)

    def nombre_siguiente_truco(self) -> str:
        return NOMBRES_TRUCO[self.siguiente_nivel_truco()]

    def resolver_truco(self, aceptado: bool, cantor: str) -> dict:
        """
        Resuelve la respuesta al canto de truco.
        
        Returns:
            {"aceptado": bool, "nivel": int, "puntos_ronda": int}
        """
        if aceptado:
            self.nivel_truco = self.siguiente_nivel_truco()
            self.truco_cantado_por = cantor
            return {
                "aceptado": True,
                "nivel": self.nivel_truco,
                "puntos_ronda": NIVELES_TRUCO[self.nivel_truco],
            }
        else:
            # No quiero: el cantor gana los puntos del nivel actual
            puntos = NIVELES_TRUCO[self.nivel_truco]
            return {
                "aceptado": False,
                "nivel": self.nivel_truco,
                "puntos_ronda": puntos,
                "ganador": cantor,
            }

    def puntos_truco_actual(self) -> int:
        return NIVELES_TRUCO[self.nivel_truco]

    # ── Puntuación ─────────────────────────────────────────

    def sumar_puntos(self, nombre: str, puntos: int) -> None:
        jugador = self._get_jugador(nombre)
        jugador.puntos += puntos

    def finalizar_ronda(self, ganador_nombre: str) -> int:
        """Suma los puntos del truco al ganador de la ronda."""
        puntos = self.puntos_truco_actual()
        self.sumar_puntos(ganador_nombre, puntos)
        self.primera_baza = True
        return puntos

    def marcar_primera_baza_jugada(self) -> None:
        """Se llama cuando la primera baza termina."""
        self.primera_baza = False

    # ── Estado del juego para IA ──────────────────────────

    def get_game_state(self, perspectiva: str) -> dict:
        """
        Retorna el estado del juego desde la perspectiva de un jugador.
        Diseñado para consumo por la IA.
        """
        jugador = self._get_jugador(perspectiva)
        oponente = self._get_oponente(perspectiva)

        mano_cartas = [c.to_dict() for c in jugador.mano]
        cartas_jugadas_propias = []
        cartas_jugadas_oponente = []

        if self.ronda:
            cartas_jugadas_propias = [
                c.to_dict() for c in self.ronda.cartas_jugadas(perspectiva)
            ]
            cartas_jugadas_oponente = [
                c.to_dict() for c in self.ronda.cartas_jugadas(oponente.nombre)
            ]

        carta_oponente_mesa = None
        if self.ronda:
            co = self.ronda.carta_oponente_en_baza_actual(perspectiva)
            if co:
                carta_oponente_mesa = co.to_dict()

        acciones = self._acciones_disponibles(perspectiva)

        return {
            "mano": mano_cartas,
            "cartas_jugadas_propias": cartas_jugadas_propias,
            "cartas_jugadas_oponente": cartas_jugadas_oponente,
            "carta_oponente_mesa": carta_oponente_mesa,
            "puntos_propios": jugador.puntos,
            "puntos_oponente": oponente.puntos,
            "nivel_truco": self.nivel_truco,
            "envido_disponible": self.puede_cantar_envido(),
            "puede_cantar_truco": self.puede_cantar_truco(perspectiva),
            "es_mano": perspectiva == self.mano_nombre,
            "es_mi_turno": self.ronda.turno == perspectiva if self.ronda else False,
            "acciones_disponibles": acciones,
            "puntos_objetivo": PUNTOS_OBJETIVO,
        }

    def _acciones_disponibles(self, nombre: str) -> list[str]:
        """Lista las acciones disponibles para un jugador."""
        acciones = []
        jugador = self._get_jugador(nombre)

        if jugador.tiene_cartas():
            acciones.append("jugar_carta")

        if self.puede_cantar_envido():
            acciones.append("envido")
            acciones.append("real_envido")
            acciones.append("falta_envido")

        if self.puede_cantar_truco(nombre):
            acciones.append(NOMBRES_TRUCO[self.siguiente_nivel_truco()])

        acciones.append("mazo")  # siempre puede irse al mazo
        return acciones

    # ── Utilidades ─────────────────────────────────────────

    def _get_jugador(self, nombre: str) -> Jugador:
        if nombre == self.jugador1.nombre:
            return self.jugador1
        return self.jugador2

    def _get_oponente(self, nombre: str) -> Jugador:
        if nombre == self.jugador1.nombre:
            return self.jugador2
        return self.jugador1

    def _oponente_nombre(self, nombre: str) -> str:
        return self._get_oponente(nombre).nombre
