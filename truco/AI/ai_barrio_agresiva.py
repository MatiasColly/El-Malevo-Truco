"""
IA de Barrio para el Truco Argentino.

Simula un jugador humano con heurísticas y un grado de aleatoriedad.
Subclase de AIInterface definida en ai_interface.py.
"""

from __future__ import annotations

import random

from ..ai_interface import AIInterface



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
#   gs["manos_baza"]  list[str]  — quién fue mano (jugó primero) en cada baza
#       completada, desde tu perspectiva: "yo" u "oponente".
#       Mismo largo que gs["bazas"]. Lista vacía antes de terminar la 1ra baza.
#   Ejemplo:
#       gs["manos_baza"] == ["yo", "oponente"]       → vos arrancaste la 1ra,
#                                                       el oponente arrancó la 2da
#
# PUNTAJES:
#   gs["puntos_propios"]   int  — tus puntos actuales
#   gs["puntos_oponente"]  int  — puntos del oponente
#   gs["puntos_objetivo"]  int  — 30 (constante)
#   gs["envido_propio"]    int  — tu mejor envido (20+ si tenés par del mismo palo)
#
# ESTADO DE LA RONDA:
#   gs["es_mano"]           bool  — True si jugás primero en la BAZA ACTUAL
#                                   (cambia cada baza según quién la ganó)
#   gs["es_mano_ronda"]     bool  — True si sos mano de la ronda: jugaste
#                                   primero en la 1ra baza y ganás empates de envido
#   gs["es_mi_turno"]       bool  — True si te toca jugar ahora
#   gs["nivel_truco"]       int   — 0=sin cantar, 1=truco, 2=retruco, 3=vale4
#   gs["envido_disponible"] bool  — True si todavía se puede cantar envido
#   gs["envido_secuencia"]  list[str] — cantos de envido ya realizados esta ronda
#       []                         → no se cantó nada aún
#       ["envido"]                 → se cantó envido, pendiente respuesta
#       ["envido", "real_envido"]  → escalada en curso
#       ["envido", "falta_envido"] → etc. (ver ENVIDO_TABLA en truco_engine.py)
#   gs["envido_en_juego"]   int | None — puntos que gana quien dice quiero
#       None si no hay envido cantado aún en esta ronda
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

class AiBarrioAgresiva(AIInterface):
    """IA de barrio, hecha a mano, a la vieja escuela."""

    def elegir_accion(self, game_state: dict) -> dict:
        mano = game_state.get("mano", [])
        acciones = game_state.get("acciones_disponibles", [])
        cartas_jugadas_oponente = game_state.get("cartas_jugadas_oponente", [])
        ultima_carta_oponente = cartas_jugadas_oponente[-1:]
        soy_mano = game_state.get("es_mano", False)
        bazas = game_state.get("bazas", [])

        self._log("Mano: ", mano)
        self._log("Soy Mano: ", soy_mano)
        self._log("Cartas oponente: ", cartas_jugadas_oponente)

        # ------------- Evalúo Envido ------------- #

        if len(bazas) == 0:

            if [a for a in acciones if a == "envido" or a == "real_envido" or a == "falta_envido"]:

                envido_propio = game_state.get("envido_propio", 0)
                prob_cantar_envido = self._envido_propio_a_probabilidades(envido_propio, soy_mano)
                self._log("Probabilidad de cantar envido:", prob_cantar_envido, ", puntos envido:", envido_propio)

                if self._probabilidad_a_decision(prob_cantar_envido):
                    if self._probabilidad_a_decision(0.25):
                        return {"tipo": "real_envido"}
                    else:
                        return {"tipo": "envido"}

        # ------------- Evalúo Truco ------------- #

        if self.canto_truco(game_state):
            if [a for a in acciones if a == "truco"]:
                return {"tipo": "truco"}
            elif [a for a in acciones if a == "retruco"]:
                return {"tipo": "retruco"}
            elif [a for a in acciones if a == "vale cuatro"]:
                return {"tipo": "vale cuatro"}

        # ------------- Baza 1: ------------- #

        if len(bazas) == 0:

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
            elif bazas[0] == "parda":
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

    # ----------------- Sección lógica del envido -------------------------- #
    """
    Lógica: Ufff, parece un spaghetti code, pero es simple:
    - En base a en que momento estamos del envido, asigno una probabilidad de querer o no querer en funcion de los 
    puntos que tengo. Lo numero los saque completamente a ojimetro, tratando de representar como jugaria yo.
    - En los casos que se puede cantar mas, primero me fijo si me gustan, y despues evaluo de nuevo si cantaria mas.
    - Si estamos en falta envido, seguimos una logica extra para estos casos
    - No canto nunca falta envido, re cagón. Hay que complejizar mas la logica para que valga la pena cantarlo, queda
    para otro dia (posiblemente nunca lo haga jaja..)
    """
    def responder_envido(self, game_state: dict) -> dict:

        envido_propio = game_state.get("envido_propio", 0)
        envido_secuencia = game_state.get("envido_secuencia", 0)
        envido_en_juego = game_state.get("envido_en_juego", 0)

        self._log("Envido propio:", envido_propio)
        self._log("Envido secuencia:", envido_secuencia)

        if "falta_envido" in envido_secuencia:
            if envido_en_juego == 1:
                return {"tipo": "quiero"}
            # Hacemos estos truquitos para que no responda otra cosa, que no sea quiero/no quiero. Y evaluamos normal
            elif envido_en_juego <= 3:
                envido_en_juego = 3
                pass
            elif envido_en_juego <= 5:
                envido_en_juego = 5
                pass
            else:
                probabilidad_de_querer = self.interpolate(envido_propio, 31, 33, 0.3, 1.0)
                if self._probabilidad_a_decision(probabilidad_de_querer):
                    return {"tipo": "quiero"}
                else:
                    return {"tipo": "no_quiero"}

        # Envido
        if envido_en_juego == 2:

            if envido_propio <= 20:
                probabilidad_de_querer = 0
            elif envido_propio <= 25:
                probabilidad_de_querer = 0.3
            elif envido_propio <= 26:
                probabilidad_de_querer = 0.4
            elif envido_propio >= 30:
                probabilidad_de_querer = 1.0
            else:
                probabilidad_de_querer = self.interpolate(envido_propio, 27, 30, 0.70, 1.0)

            if self._probabilidad_a_decision(probabilidad_de_querer):
                if envido_propio <= 27:
                    probabilidad_de_subir = 0.07
                else:
                    probabilidad_de_subir = self.interpolate(envido_propio, 28, 33, 0.07, 1.0)

                # La mitad de las veces elegimos uno u otro
                if self._probabilidad_a_decision(probabilidad_de_subir):
                    if self._probabilidad_a_decision(0.5):
                        return {"tipo": "real_envido"}
                    else:
                        return {"tipo": "envido"}
                else:
                    return {"tipo": "quiero"}
            else:
                return {"tipo": "no_quiero"}

        # Real Envido
        elif envido_en_juego == 3:

            if envido_propio <= 20:
                probabilidad_de_querer = 0
            elif envido_propio <= 25:
                probabilidad_de_querer = 0.3
            elif envido_propio <= 26:
                probabilidad_de_querer = 0.4
            elif envido_propio >= 30:
                probabilidad_de_querer = 1.0
            else:
                probabilidad_de_querer = self.interpolate(envido_propio, 27, 30, 0.70, 1.0)

            if self._probabilidad_a_decision(probabilidad_de_querer):
                return {"tipo": "quiero"}
            else:
                return {"tipo": "no_quiero"}

        # Envido, Envido
        elif envido_en_juego == 4:

            if envido_propio <= 20:
                probabilidad_de_querer = 0.0
            elif envido_propio <= 27:
                probabilidad_de_querer = 0.05
            else:
                probabilidad_de_querer = self.interpolate(envido_propio, 28, 33, 0.20, 1.0)

            if self._probabilidad_a_decision(probabilidad_de_querer):
                if envido_propio <= 30:
                    probabilidad_de_subir = 0
                else:
                    probabilidad_de_subir = self.interpolate(envido_propio, 31, 33, 0.30, 1.0)

                if self._probabilidad_a_decision(probabilidad_de_subir):
                    return {"tipo": "real_envido"}
                else:
                    return {"tipo": "quiero"}
            else:
                return {"tipo": "no_quiero"}

        # Envido, Real Envido
        elif envido_en_juego == 5:

            if envido_propio <= 27:
                probabilidad_de_querer = 0.0
            else:
                probabilidad_de_querer = self.interpolate(envido_propio, 28, 33, 0.10, 1.0)

            if self._probabilidad_a_decision(probabilidad_de_querer):
                return {"tipo": "quiero"}
            else:
                return {"tipo": "no_quiero"}

        # Envido, Envido, Real Envido
        elif envido_en_juego == 7:
            
            if envido_propio <= 30:
                probabilidad_de_querer = 0.0
            else:
                probabilidad_de_querer = self.interpolate(envido_propio, 31, 33, 0.30, 1.0)

            if self._probabilidad_a_decision(probabilidad_de_querer):
                return {"tipo": "quiero"}
            else:
                return {"tipo": "no_quiero"}

        # No debería caer aca
        else:
            self._log("Cayo! Que paso??")
            return {"tipo": "no_quiero"}

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
            if puntos <= 20:
                return 0.5
            else:
                return self.interpolate(puntos, 20, 33, 0.5, 0.85)
        else:
            if puntos <= 7:
                return 0.5
            elif puntos <= 30:
                return self.interpolate(puntos, 20, 30, 0.5, 1.0)
            else:
                return 1.0

    @staticmethod
    def interpolate(value, in_min, in_max, out_min, out_max):
        return out_min + (value - in_min) * (out_max - out_min) / (in_max - in_min)

    @staticmethod
    def _probabilidad_a_decision(probabilidad: float) -> bool:
        return random.random() < probabilidad

    # ----------------- Seccion logica de mano/truco -------------------------- #

    """
    Lógica: Muy simple si me cantan en primera, evalúo cantarle envido; si la veo muy bien le subo y si no 
    evalúo proporcional a la mano
    """
    def responder_truco(self, game_state: dict) -> dict:

        bazas = game_state.get("bazas", [])
        acciones = game_state.get("acciones", [])
        soy_mano = game_state.get("es_mano", False)
        mano = game_state.get("mano", [])
        cartas_jugadas_oponente = game_state.get("cartas_jugadas_oponente", [])
        cartas_jugadas_propias = game_state.get("cartas_jugadas_propias", [])
        ultima_carta_propia = cartas_jugadas_propias[-1:]
        ultima_carta_oponente = cartas_jugadas_oponente[-1:]
        manos_baza = game_state.get("manos_baza", [])
        es_mi_turno = game_state.get("es_mi_turno", False)

        chance_de_ganar = self._estimar_chance_de_ganar(mano, bazas, soy_mano, ultima_carta_oponente,
                                                        cartas_jugadas_propias, es_mi_turno)

        self._log("Mano:", mano)
        self._log("Truco del humano. Chance de ganar la ronda:", chance_de_ganar)

        # Código duplicado! Si me quieren meter truco en primera me fijo si le puedo meter envido
        if len(bazas) == 0:

            if [a for a in acciones if a == "envido" or a == "real_envido" or a == "falta_envido"]:

                envido_propio = game_state.get("envido_propio", 0)
                prob_cantar_envido = self._envido_propio_a_probabilidades(envido_propio, soy_mano)
                self._log("Probabilidad de cantar envido:", prob_cantar_envido, ", puntos envido:", envido_propio)

                if self._probabilidad_a_decision(prob_cantar_envido):
                    if self._probabilidad_a_decision(0.25):
                        return {"tipo": "real_envido"}
                    else:
                        return {"tipo": "envido"}

        if chance_de_ganar >= 0.75:
            if len(mano) != 0:
                if [a for a in acciones if a == "retruco"]:
                    return {"tipo": "retruco"}
                elif [a for a in acciones if a == "vale cuatro"]:
                    return {"tipo": "vale cuatro"}
                else:
                    return {"tipo": "quiero"}
            # Si ya jugue todas no quiero subir, no tiene sentido
            else:
                return {"tipo": "quiero"}

        if chance_de_ganar <= 0.3:
            return {"tipo": "no_quiero"}

        if self._probabilidad_a_decision(chance_de_ganar):
            return {"tipo": "quiero"}

        return {"tipo": "no_quiero"}

    """ Lógica: 
    - Jugamos 40% de la veces la carta mas alta (opción que mas gana pero después no se puede mentir mucho). 
    - Jugamos 20% de las veces la carta del medio (peor opción, pero evita ser predecible)
    - Jugamos 40% de las veces la carta mas baja (opción decente, permite juga a amenazar mas adelante)
    """
    def _elegir_primera_carta(self, mano) -> dict:
        mano_ordenada = sorted(mano, key=lambda c: c.get("poder", 0))
        if self._probabilidad_a_decision(0.4):
            self._log("Elijo la carta mas alta")
            return mano_ordenada[2]
        elif self._probabilidad_a_decision(0.66666):
            self._log("Elijo la carta mas baja")
            return mano_ordenada[0]
        else:
            self._log("Elijo la carta del medio")
            return mano_ordenada[1]

    """ Lógica básica: matamos con lo justo, si no podemos jugamos la mas baja """
    @staticmethod
    def _matar_con_lo_justo(mano, ultima_carta_oponente) -> list:
        mano_ordenada = sorted(mano, key=lambda c: c.get("poder", 0))
        for carta in mano_ordenada:
            if carta["poder"] > ultima_carta_oponente[0]["poder"]:
                return [True, carta]
        return [False, mano_ordenada[0]]

    @staticmethod
    def _carta_a_indice (mano, carta) -> int:
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
            self._log("Dejo la grande, voy por la baja")
            return mano_ordenada[0]

        elif self._probabilidad_a_decision(0.3):
            self._log("Elijo la carta mas alta")
            return mano_ordenada[1]
        else:
            self._log("Elijo la carta mas baja")
            return mano_ordenada[0]

    def canto_truco(self, game_state: dict) -> bool:
        mano = game_state.get("mano", [])
        cartas_jugadas_oponente = game_state.get("cartas_jugadas_oponente", [])
        cartas_jugadas_propias = game_state.get("cartas_jugadas_propias", [])
        ultima_carta_propia = cartas_jugadas_propias[-1:]
        ultima_carta_oponente = cartas_jugadas_oponente[-1:]
        soy_mano = game_state.get("es_mano", False)
        bazas = game_state.get("bazas", [])
        manos_baza = game_state.get("manos_baza", [])
        es_mi_turno = game_state.get("es_mi_turno", False)

        chance_de_ganar = self._estimar_chance_de_ganar(mano, bazas, soy_mano, ultima_carta_oponente,
                                                        ultima_carta_propia, es_mi_turno)
        self._log("Chance de ganar la ronda:", chance_de_ganar)

        if len(bazas) == 0:
            # Si tenemos cartas muy feas, podemos mentir para correrlo. Si tenemos muy buenas, podemos cantarle rapido
            # para hacerlo entrar desde el principio
            if chance_de_ganar <= 0.15 or chance_de_ganar >= 0.9:
                return self._probabilidad_a_decision(0.15)

        elif len(bazas) == 1:
            # No voy a cantar aca, si pude cantar en primera sin revelar más info
            if bazas[0] == "yo" and manos_baza[0] == "oponente":
                return False

            # Perdí primera, pero voy a ganar las próximas dos
            if bazas[0] == "oponente" and chance_de_ganar >= 0.85:
                return True

            # La mejor situación para correrlo si no me queda nada
            if bazas[0] == "yo" and chance_de_ganar <= 0.25:
                return True

            # Canto porque me quedaron 2 cartas muy altas
            if bazas[0] == "yo" and sum(carta["poder"] >= 9 for carta in mano) == 2:
                return True

            # Pongo alguna chance de cantar proporcional a mi mano
            return self._probabilidad_a_decision(chance_de_ganar - 0.3)

        else:
            # No voy a cantar aca, si pude cantar en segunda sin revelar más info
            if soy_mano:
                return False

            else:
                # Si sé que gano, canto siempre
                if chance_de_ganar >= 0.5:  # Si está bien la logica aca la chance es 0.0 o 1.0
                    return True

                else:
                    # No le miento por que me va a querer
                    if ultima_carta_oponente[0]['poder'] >= 9:  # 10 = cualquier 2
                        return False

                    # Carta fea, le cantamos si o si
                    if ultima_carta_oponente[0]['poder'] <= 4:  # 4 = 7 basto / 7 copa
                        return True

                    return self._probabilidad_a_decision(0.5)

                # Como dato de color: Pensando en toda esta logica me di cuenta de que si ganas primera, siempre jugás
                # la última carta de la partida. Clave ganar primera che!

        return False

    def _estimar_chance_de_ganar(self, mano, bazas, soy_mano, ultima_carta_oponente,
                                 ultima_carta_propia, es_mi_turno) -> float:

        ya_ganadas = sum(elemento == "yo" for elemento in bazas)
        ya_perdidas = sum(elemento == "oponente" for elemento in bazas)

        mano_sorted = sorted(mano, key=lambda c: c.get("poder", 0))

        # Primero simulo matar la carta de él, posteriormente estimo el poder restante
        if not soy_mano and es_mi_turno:
            la_mato, carta = self._matar_con_lo_justo(mano, ultima_carta_oponente)
            if la_mato:
                ya_ganadas = ya_ganadas + 1
                mano_sorted.remove(carta)
            else:
                ya_perdidas = ya_perdidas + 1
                mano_sorted.remove(carta)

            # Resultados certeros por la estimación de jugar ahora
            if ya_ganadas == 2:
                self._log("Ganada certera")
                return 1.0

            if ya_perdidas == 2:
                self._log("Perdida certera")
                return 0.0

        # Baza 1, 2 o 3, ya gané la primera baza, y tengo otra buena
        if ya_ganadas == 1 and any(carta["poder"] == 14 for carta in mano_sorted):  # 14 = 1 de espada
            return 1.0
        if ya_ganadas == 1 and any(carta["poder"] >= 13 for carta in mano_sorted):  # 13 = 1 de basto
            return 0.95
        if ya_ganadas == 1 and any(carta["poder"] >= 11 for carta in mano_sorted):  # 11 = 7 de oro
            return 0.9
        if ya_ganadas == 1 and any(carta["poder"] >= 10 for carta in mano_sorted):  # 10 = cualquier 3
            return 0.85
        if ya_ganadas == 1 and any(carta["poder"] >= 9 for carta in mano_sorted):  # 9 = cualquier 2
            return 0.8

        # Necesito dos decentes para ganar las rondas que quedan
        if ya_perdidas == 1 and any(carta["poder"] <= 4 for carta in mano_sorted):  # 4 = 7 de basto / 7 de copa
            return 0.1

        # Baza 1, 2 o 3, tengo 2 buenas cartas
        if sum(carta["poder"] >= 11 for carta in mano_sorted) >= 2:
            return 0.9
        if sum(carta["poder"] >= 9 for carta in mano_sorted) >= 2:
            return 0.8

        # Caso de que ya jugué todas y me tiran truco
        if len(mano_sorted) == 0:
            return self.interpolate(ultima_carta_propia[0]['poder'], 1, 14, 0.0, 1.0)

        # Baza 1, 2 o 3, estimo aproximadamente el poder de mi mano restante por promedio
        suma_de_poder = 0
        for carta in mano_sorted:
            suma_de_poder = suma_de_poder + carta['poder']

        suma_de_poder = suma_de_poder / len(mano_sorted) / 14 # 14 = Poder Máximo

        return suma_de_poder


