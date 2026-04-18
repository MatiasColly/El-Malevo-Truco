"""
IA de Barrio para el Truco Argentino.

Simula un jugador humano con heurísticas y un grado de aleatoriedad.
Subclase de AIInterface definida en ai_interface.py.
"""

from __future__ import annotations

import random

from .ai_interface import AIInterface



# ── Referencia de game_state para el desarrollador ───────────────────────────
#
# game_state es un dict que recibís en elegir_accion(), responder_envido() y
# responder_truco(). Todos los valores son de solo lectura (no modificar).
#
# CARTAS EN MANO (las tuyas, aún no jugadas):
#   gs["mano"]  →  list[dict], cada dict tiene:
#       carta["numero"]       int   — 1-7, 10(sota), 11(caballo), 12(rey)
#       carta["palo"]         str   — "espada", "basto", "copa", "oro"
#       carta["poder"]        int   — jerarquía de truco (mayor = más fuerte)
#       carta["valor_envido"] int   — 0 para figuras (10-12), número si no
#   Ejemplo: mano = gs["mano"]; mejor = max(mano, key=lambda c: c["poder"])
#
# CARTAS YA JUGADAS:
#   gs["cartas_jugadas_propias"]   list[dict]  — las que vos ya tiraste
#   gs["cartas_jugadas_oponente"]  list[dict]  — las que tiró el oponente
#   gs["carta_oponente_mesa"]      dict | None — carta del oponente en la
#                                                baza actual (None si aún
#                                                no jugó en esta baza)
#
# BAZAS JUGADAS:
#   gs["bazas"]  list[str]  — resultado de cada baza disputada hasta ahora,
#       desde tu perspectiva: "yo", "oponente" o "parda".
#       Lista vacía si aún no se completó ninguna baza.
#   Ejemplos:
#       gs["bazas"] == []                            → primera baza en curso
#       gs["bazas"] == ["oponente"]                  → oponente ganó la 1ra
#       gs["bazas"] == ["parda", "yo"]               → 1ra parda, 2da para vos
#       gs["bazas"] == ["oponente", "parda", "yo"]   → 1ra oponente, 2da parda, 3ra vos
#
# PUNTAJES:
#   gs["puntos_propios"]   int  — tus puntos actuales
#   gs["puntos_oponente"]  int  — puntos del oponente
#   gs["puntos_objetivo"]  int  — 30 (constante)
#   gs["envido_propio"]    int  — tu mejor envido (20+ si tenés par del mismo palo)
#
# ESTADO DE LA RONDA:
#   gs["es_mano"]           bool  — True si sos mano (jugás primero)
#   gs["es_mi_turno"]       bool  — True si te toca jugar ahora
#   gs["nivel_truco"]       int   — 0=sin cantar, 1=truco, 2=retruco, 3=vale4
#   gs["envido_disponible"] bool  — True si todavía se puede cantar envido
#   gs["puede_cantar_truco"] bool — True si podés subir el truco ahora
#
# ACCIONES DISPONIBLES en este turno:
#   gs["acciones_disponibles"]  list[str]
#   Valores posibles: "jugar_carta", "envido", "real_envido", "falta_envido",
#                     "truco", "retruco", "vale cuatro", "mazo"
#
# RETORNOS esperados:
#   elegir_accion   → {"tipo": "jugar_carta", "indice": 0}  (0-based)
#                     {"tipo": "envido"} / {"tipo": "truco"} / {"tipo": "mazo"} / etc.
#   responder_envido → {"tipo": "quiero"} | {"tipo": "no_quiero"}
#                      | {"tipo": "envido"} | {"tipo": "real_envido"} | {"tipo": "falta_envido"}
#   responder_truco  → {"tipo": "quiero"} | {"tipo": "no_quiero"}
#                      | {"tipo": "retruco"} | {"tipo": "vale cuatro"}
# ─────────────────────────────────────────────────────────────────────────────

# TODO Agregar el evaluate truco, no olvidar
class BarrioAI(AIInterface):
    """IA de barrio, hecha a mano, a la vieja escuela."""

    def elegir_accion(self, game_state: dict) -> dict:
        mano = game_state.get("mano", [])
        acciones = game_state.get("acciones_disponibles", [])
        cartas_jugadas_oponente = game_state.get("cartas_jugadas_oponente", [])
        ultima_carta_oponente = cartas_jugadas_oponente[-1:]
        soy_mano = game_state.get("es_mano", False)
        bazas = game_state.get("bazas", [])

        print("Mano", mano)
        print("Soy Mano", soy_mano)
        print("Cartas oponente", cartas_jugadas_oponente)

        # ------------- Baza 1: ------------- #

        if len(bazas) == 0:

            # ---- Evalúo envido ---- #
            if [a for a in acciones if a == "envido" or a == "real_envido" or a == "falta_envido"]:

                envido_propio = game_state.get("envido_propio", 0)
                prob_cantar_envido = self._envido_propio_a_probabilidades(envido_propio, soy_mano)
                print("Probabilidad de cantar envido:", prob_cantar_envido, ", puntos envido:", envido_propio)

                if self._probabilidad_a_decision(prob_cantar_envido):
                    if self._probabilidad_a_decision(0.25):
                        return {"tipo": "real_envido"}
                    else:
                        return {"tipo": "envido"}

            if soy_mano:
                carta = self._elegir_primera_carta(mano)
            else:
                la_mata, carta = self._matar_con_lo_justo(mano, ultima_carta_oponente)

            return {"tipo": "jugar_carta", "indice": self._carta_a_indice(mano, carta)}

        # ------------- Baza 2: ------------- #

        elif len(bazas) == 1:

            # Si perdí primera o mato o me voy al mazo
            if bazas[0] == "oponente":
                la_mata, carta = self._matar_con_lo_justo(mano, ultima_carta_oponente)
                if la_mata:
                    return {"tipo": "jugar_carta", "indice": self._carta_a_indice(mano, carta)}
                else:
                    return {"tipo": "mazo"}

            # Si fué pardas: si soy mano, juego la mas alta. Si soy pie, mato o me voy al mazo
            elif bazas[0] == "pardas":
                if soy_mano:
                    mano_ordenada = sorted(mano, key=lambda c: c.get("poder", 0))
                    return {"tipo": "jugar_carta", "indice": self._carta_a_indice(mano, mano_ordenada[-1])}
                else:
                    la_mata, carta = self._matar_con_lo_justo(mano, ultima_carta_oponente)
                    if la_mata:
                        # Aca va truco
                        return {"tipo": "jugar_carta", "indice": self._carta_a_indice(mano, carta)}
                    else:
                        return {"tipo": "mazo"}

            else:
                carta = self._elegir_segunda_carta(mano)
                return {"tipo": "jugar_carta", "indice": self._carta_a_indice(mano, carta)}

        # ------------- Baza 3: ------------- #

        else:
            if soy_mano:
                return {"tipo": "jugar_carta", "indice": 0}
            else:
                la_mata, carta = self._matar_con_lo_justo(mano, ultima_carta_oponente)
                if la_mata:
                    # Aca va truco
                    return {"tipo": "jugar_carta", "indice": self._carta_a_indice(mano, carta)}
                else:
                    return {"tipo": "mazo"}


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

    # ----------------- Sección lógica del envido -------------------------- #

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

    """ Lógica: 
            - Siendo mano: 7% es la probabilidad de que mienta si no tiene nada. Escalamos linealmente para que mientras 
            mas puntos tenga, mas chance de que cante envido. No lo ponemos al 100% para 33 asi lo hacemos ir a la pesca
            algunas veces
            - Siendo pie: Asigno mas probabilidades a la mentira ya que el otro no canto nada (15 %). Escalo lineamente
            hasta 100% esta vez por que no me quiero comer los puntos. A partir de 30 canto siempre por que son 
            excelentes puntos
    """
    def _envido_propio_a_probabilidades(self, puntos: int, soy_mano: bool) -> float:
        if soy_mano:
            if puntos <= 7:
                return 0.07
            else:
                return self.interpolate(puntos, 20, 33, 0.07, 0.85)
        else:
            if puntos <= 7:
                return 0.15
            elif puntos <= 30:
                return self.interpolate(puntos, 20, 30, 0.15, 1.0)
            else:
                return 1.0

    @staticmethod
    def interpolate(value, in_min, in_max, out_min, out_max):
        return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)

    @staticmethod
    def _probabilidad_a_decision(probabilidad: float) -> bool:
        return random.random() < probabilidad

    # ----------------- Seccion logica de mano/truco -------------------------- #

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

    """ Lógica: 
    - Jugamos 40% de la veces la carta mas alta (opción que mas gana pero después no se puede mentir mucho). 
    - Jugamos 20% de las veces la carta del medio (peor opción, pero evita ser predecible)
    - Jugamos 40% de las veces la carta mas baja (opción decente, permite juga a amenazar mas adelante)
    """
    def _elegir_primera_carta(self, mano) -> dict:
        mano_ordenada = sorted(mano, key=lambda c: c.get("poder", 0))
        if self._probabilidad_a_decision(0.4):
            print("Elijo la carta mas alta")
            return mano_ordenada[2]
        elif self._probabilidad_a_decision(0.66666):
            print("Elijo la carta mas baja")
            return mano_ordenada[0]
        else:
            print("Elijo la carta del medio")
            return mano_ordenada[1]

    """ Lógica básica: matamos con lo justo, si no podemos jugamos la mas baja """
    @staticmethod
    def _matar_con_lo_justo(mano, ultima_carta_oponente) -> list:
        mano_ordenada = sorted(mano, key=lambda c: c.get("poder", 0))
        for carta in mano_ordenada:
            if carta["poder"] > ultima_carta_oponente[0]["poder"]:
                return [True, carta]
        return [False, mano_ordenada[0]]

    def _carta_a_indice (self, mano, carta) -> int:
        for i, c in enumerate(mano):
            if c == carta:
                return i
        return -1

    """ Lógica: 
        - Si la mas alta es un 3 o mas, no la jugamos, por que hacemos que el oponente se valla rápido
        - Jugamos 30% de la veces la carta mas alta (peor opción, pero evita ser predecible)
        - Jugamos 70% de las veces la carta mas baja (mejor opción, permite saber que tiene la otra persona y definir
        la partida)
        """
    def _elegir_segunda_carta(self, mano) -> dict:
        mano_ordenada = sorted(mano, key=lambda c: c.get("poder", 0))

        if mano_ordenada[1]["poder"] >= 10:
            print("Dejo la grande, voy por la baja")
            return mano_ordenada[0]

        elif self._probabilidad_a_decision(0.3):
            print("Elijo la carta mas alta")
            return mano_ordenada[1]
        else:
            print("Elijo la carta mas baja")
            return mano_ordenada[0]

