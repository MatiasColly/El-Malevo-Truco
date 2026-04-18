"""
Interfaz gráfica (Pygame) para El Malevo — Truco Argentino.

Reemplaza terminal_ui cuando config.INTERFAZ == "gui".
"""

from __future__ import annotations

import os
import sys
import time
from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

from truco.jugador import Jugador, JugadorHumano, JugadorAI
from truco.carta import Carta, NOMBRE_NUMERO
from truco.truco_engine import TrucoEngine, NOMBRES_TRUCO, PUNTOS_OBJETIVO
from truco.mesa import Ronda

# ── Constantes de diseño ──────────────────────────────────

ANCHO, ALTO = 1100, 750
FPS = 30

# Colores
VERDE_MESA = (34, 102, 51)
VERDE_OSCURO = (24, 72, 36)
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
AMARILLO = (255, 215, 0)
ROJO = (200, 50, 50)
GRIS = (180, 180, 180)
GRIS_OSCURO = (80, 80, 80)
AZUL = (50, 100, 200)
CREMA = (245, 235, 210)
MARRON = (139, 90, 43)
DORADO = (218, 165, 32)

# Tamaños de carta
CARTA_W, CARTA_H = 90, 140
CARTA_MINI_W, CARTA_MINI_H = 60, 93

# Layout
MANO_Y = ALTO - CARTA_H - 30
MESA_Y = ALTO // 2 - CARTA_H // 2
CPU_Y = 25
SCORE_X = ANCHO - 220

# ── Assets ────────────────────────────────────────────────

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "cards")


class CardRenderer:
    """Carga y cachea las imágenes de cartas."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}
        self._dorso: pygame.Surface | None = None

    def _svg_path(self, numero: int, palo: str) -> str:
        return os.path.join(ASSETS_DIR, f"{numero}_{palo}.svg")

    def _dorso_path(self) -> str:
        return os.path.join(ASSETS_DIR, "dorso.svg")

    def get(self, carta: Carta, size: tuple[int, int] = (CARTA_W, CARTA_H)) -> pygame.Surface:
        key = f"{carta.numero}_{carta.palo}_{size[0]}x{size[1]}"
        if key not in self._cache:
            path = self._svg_path(carta.numero, carta.palo)
            if os.path.exists(path):
                raw = pygame.image.load(path)
                self._cache[key] = pygame.transform.smoothscale(raw, size)
            else:
                self._cache[key] = self._generar_carta(carta, size)
        return self._cache[key]

    def get_dorso(self, size: tuple[int, int] = (CARTA_W, CARTA_H)) -> pygame.Surface:
        key = f"dorso_{size[0]}x{size[1]}"
        if key not in self._cache:
            path = self._dorso_path()
            if os.path.exists(path):
                raw = pygame.image.load(path)
                self._cache[key] = pygame.transform.smoothscale(raw, size)
            else:
                self._cache[key] = self._generar_dorso(size)
        return self._cache[key]

    def _generar_carta(self, carta: Carta, size: tuple[int, int]) -> pygame.Surface:
        """Genera carta procedural si no hay SVG."""
        surf = pygame.Surface(size)
        surf.fill(CREMA)
        pygame.draw.rect(surf, NEGRO, surf.get_rect(), 2, border_radius=6)
        font = pygame.font.SysFont("Arial", size[1] // 4, bold=True)
        nombre = NOMBRE_NUMERO.get(carta.numero, str(carta.numero))
        colores_palo = {"espada": AZUL, "basto": VERDE_OSCURO, "oro": DORADO, "copa": ROJO}
        color = colores_palo.get(carta.palo, NEGRO)
        txt = font.render(f"{nombre}", True, color)
        surf.blit(txt, (6, 4))
        font_sm = pygame.font.SysFont("Arial", size[1] // 6)
        palo_txt = font_sm.render(carta.palo[:3].upper(), True, color)
        surf.blit(palo_txt, (6, 4 + txt.get_height()))
        return surf

    def _generar_dorso(self, size: tuple[int, int]) -> pygame.Surface:
        surf = pygame.Surface(size)
        surf.fill(MARRON)
        pygame.draw.rect(surf, NEGRO, surf.get_rect(), 2, border_radius=6)
        inner = pygame.Rect(6, 6, size[0] - 12, size[1] - 12)
        pygame.draw.rect(surf, DORADO, inner, 2, border_radius=4)
        return surf


# ── Estados del juego ─────────────────────────────────────

class Estado(Enum):
    PLAYER_TURN = auto()
    CPU_THINKING = auto()
    ENVIDO_RESPONSE = auto()
    TRUCO_RESPONSE = auto()
    SHOWING_BAZA = auto()
    SHOWING_ENVIDO = auto()
    SHOWING_MAZO = auto()
    RONDA_FIN = auto()
    GAME_OVER = auto()


# ── Botón ─────────────────────────────────────────────────

class Boton:
    """Un botón clickeable."""

    def __init__(self, rect: pygame.Rect, texto: str, color: tuple = VERDE_OSCURO,
                 color_hover: tuple = (40, 120, 60), color_texto: tuple = BLANCO,
                 visible: bool = True) -> None:
        self.rect = rect
        self.texto = texto
        self.color = color
        self.color_hover = color_hover
        self.color_texto = color_texto
        self.visible = visible
        self.hover = False

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.visible:
            return
        c = self.color_hover if self.hover else self.color
        pygame.draw.rect(screen, c, self.rect, border_radius=8)
        pygame.draw.rect(screen, NEGRO, self.rect, 2, border_radius=8)
        txt = font.render(self.texto, True, self.color_texto)
        tx = self.rect.centerx - txt.get_width() // 2
        ty = self.rect.centery - txt.get_height() // 2
        screen.blit(txt, (tx, ty))

    def check_hover(self, pos: tuple[int, int]) -> None:
        self.hover = self.visible and self.rect.collidepoint(pos)

    def clicked(self, pos: tuple[int, int]) -> bool:
        return self.visible and self.rect.collidepoint(pos)


# ── GUI Principal ─────────────────────────────────────────

class TrucoGUI:
    """Interfaz gráfica completa para el juego de Truco."""

    def __init__(self, engine: TrucoEngine) -> None:
        pygame.init()
        pygame.display.set_caption("El Malevo — Truco Argentino")
        self.screen = pygame.display.set_mode((ANCHO, ALTO))
        self.clock = pygame.time.Clock()
        self.engine = engine
        self.renderer = CardRenderer()

        # Fonts
        self.font_grande = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_medio = pygame.font.SysFont("Arial", 20, bold=True)
        self.font_chico = pygame.font.SysFont("Arial", 16)
        self.font_titulo = pygame.font.SysFont("Arial", 36, bold=True)
        self.font_boton = pygame.font.SysFont("Arial", 17, bold=True)

        # Estado
        self.estado = Estado.PLAYER_TURN
        self.ronda: Ronda | None = None
        self.mensaje: str = ""
        self.mensaje_timer: float = 0
        self.cpu_timer: float = 0
        self.show_timer: float = 0
        self.resultado_envido: dict | None = None
        self.carta_hover: int = -1

        # Envido dialog state
        self.envido_secuencia: list[str] = []
        self.envido_cantor: str = ""
        self.envido_respuestas_validas: list[str] = []
        self.envido_botones: list[Boton] = []

        # Truco dialog state
        self.truco_cantor: str = ""
        self.truco_nivel: str = ""
        self.truco_puede_subir: bool = False
        self.truco_botones: list[Boton] = []

        # Mesa state
        self.carta_jugador_mesa: Carta | None = None
        self.carta_cpu_mesa: Carta | None = None

        # Acciones extra (para botones laterales)
        self._crear_botones_accion()

    def _crear_botones_accion(self) -> None:
        """Crea los botones de acción del panel derecho."""
        x = ANCHO - 200
        y0 = 280
        w, h, gap = 180, 38, 6
        self.btn_envido = Boton(pygame.Rect(x, y0, w, h), "Envido")
        self.btn_real_envido = Boton(pygame.Rect(x, y0 + (h + gap), w, h), "Real Envido")
        self.btn_falta_envido = Boton(pygame.Rect(x, y0 + 2 * (h + gap), w, h), "Falta Envido")
        self.btn_truco = Boton(pygame.Rect(x, y0 + 3 * (h + gap), w, h), "Truco", color=ROJO, color_hover=(230, 70, 70))
        self.btn_mazo = Boton(pygame.Rect(x, y0 + 4 * (h + gap), w, h), "Me voy al mazo", color=GRIS_OSCURO, color_hover=(110, 110, 110))

        self.botones_accion = [
            self.btn_envido, self.btn_real_envido, self.btn_falta_envido,
            self.btn_truco, self.btn_mazo,
        ]

    def run(self) -> None:
        """Bucle principal del juego."""
        self._nueva_ronda()

        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self._handle_hover(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)

            self._update(dt)
            self._draw()
            pygame.display.flip()

        pygame.quit()

    # ── Lógica de ronda ───────────────────────────────────

    def _nueva_ronda(self) -> None:
        self.ronda = self.engine.nueva_ronda()
        self.carta_jugador_mesa = None
        self.carta_cpu_mesa = None
        self.resultado_envido = None
        self.envido_secuencia = []
        self._set_mensaje(f"Nueva ronda — Mano: {self.engine.mano_nombre}")
        self._actualizar_botones()

        if self.ronda.turno == self.engine.jugador2.nombre:
            self.estado = Estado.CPU_THINKING
            self.cpu_timer = 0.8
        else:
            self.estado = Estado.PLAYER_TURN

    def _actualizar_botones(self) -> None:
        """Actualiza visibilidad de los botones de acción."""
        humano = self.engine.jugador1.nombre
        puede_envido = self.engine.puede_cantar_envido()
        puede_truco = self.engine.puede_cantar_truco(humano)

        self.btn_envido.visible = puede_envido
        self.btn_real_envido.visible = puede_envido
        self.btn_falta_envido.visible = puede_envido
        self.btn_truco.visible = puede_truco
        if puede_truco:
            self.btn_truco.texto = self.engine.nombre_siguiente_truco().title()
        self.btn_mazo.visible = True

    def _set_mensaje(self, msg: str, duracion: float = 2.5) -> None:
        self.mensaje = msg
        self.mensaje_timer = duracion

    # ── Update ────────────────────────────────────────────

    # ── Click handling ────────────────────────────────────

    def _handle_hover(self, pos: tuple[int, int]) -> None:
        for btn in self.botones_accion:
            btn.check_hover(pos)
        if self.estado == Estado.ENVIDO_RESPONSE:
            for btn in self.envido_botones:
                btn.check_hover(pos)
        if self.estado == Estado.TRUCO_RESPONSE:
            for btn in self.truco_botones:
                btn.check_hover(pos)

        # Hover sobre cartas del jugador
        self.carta_hover = -1
        if self.estado == Estado.PLAYER_TURN:
            mano = self.engine.jugador1.mano
            rects = self._rects_mano_jugador(mano)
            for i, r in enumerate(rects):
                if r.collidepoint(pos):
                    self.carta_hover = i

    def _handle_click(self, pos: tuple[int, int]) -> None:
        if self.estado == Estado.PLAYER_TURN:
            self._click_player_turn(pos)
        elif self.estado == Estado.ENVIDO_RESPONSE:
            self._click_envido_response(pos)
        elif self.estado == Estado.TRUCO_RESPONSE:
            self._click_truco_response(pos)
        elif self.estado == Estado.GAME_OVER:
            # Click para reiniciar
            self.engine.jugador1.puntos = 0
            self.engine.jugador2.puntos = 0
            self.engine.mano_idx = 0
            self._nueva_ronda()

    def _click_player_turn(self, pos: tuple[int, int]) -> None:
        # Jugar carta
        mano = self.engine.jugador1.mano
        rects = self._rects_mano_jugador(mano)
        for i, r in enumerate(rects):
            if r.collidepoint(pos):
                self._jugador_juega_carta(i)
                return

        # Botones de acción
        if self.btn_envido.clicked(pos) and self.btn_envido.visible:
            self._iniciar_envido(self.engine.jugador1.nombre, "envido")
            return
        if self.btn_real_envido.clicked(pos) and self.btn_real_envido.visible:
            self._iniciar_envido(self.engine.jugador1.nombre, "real_envido")
            return
        if self.btn_falta_envido.clicked(pos) and self.btn_falta_envido.visible:
            self._iniciar_envido(self.engine.jugador1.nombre, "falta_envido")
            return
        if self.btn_truco.clicked(pos) and self.btn_truco.visible:
            self._iniciar_truco(self.engine.jugador1.nombre, self.engine.nombre_siguiente_truco())
            return
        if self.btn_mazo.clicked(pos) and self.btn_mazo.visible:
            self._ir_al_mazo(self.engine.jugador1.nombre)
            return

    # ── Jugar carta ───────────────────────────────────────

    def _jugador_juega_carta(self, indice: int) -> None:
        jugador = self.engine.jugador1
        carta = jugador.jugar_carta(indice)
        self.carta_jugador_mesa = carta
        resultado = self.ronda.jugar_carta(jugador.nombre, carta)

        if resultado["baza_completa"]:
            self._mostrar_resultado_baza(resultado)
        else:
            # CPU debe jugar
            self.estado = Estado.CPU_THINKING
            self.cpu_timer = 0.8

    def _turno_cpu(self) -> None:
        cpu = self.engine.jugador2
        if not isinstance(cpu, JugadorAI):
            return

        game_state = self.engine.get_game_state(cpu.nombre)
        accion = cpu.decidir(game_state)
        tipo = accion.get("tipo", "jugar_carta")

        if tipo == "jugar_carta":
            indice = accion.get("indice", 0)
            if indice < 0 or indice >= len(cpu.mano):
                indice = 0
            carta = cpu.jugar_carta(indice)
            self.carta_cpu_mesa = carta
            self._set_mensaje(f"CPU juega: {carta}")
            resultado = self.ronda.jugar_carta(cpu.nombre, carta)

            if resultado["baza_completa"]:
                self._mostrar_resultado_baza(resultado)
            else:
                self.estado = Estado.PLAYER_TURN
                self._actualizar_botones()

        elif tipo in ("envido", "real_envido", "falta_envido"):
            self._iniciar_envido(cpu.nombre, tipo)

        elif tipo in ("truco", "retruco", "vale cuatro"):
            self._iniciar_truco(cpu.nombre, tipo)

        elif tipo == "mazo":
            self._ir_al_mazo(cpu.nombre)

        else:
            if cpu.tiene_cartas():
                carta = cpu.jugar_carta(0)
                self.carta_cpu_mesa = carta
                self._set_mensaje(f"CPU juega: {carta}")
                resultado = self.ronda.jugar_carta(cpu.nombre, carta)
                if resultado["baza_completa"]:
                    self._mostrar_resultado_baza(resultado)
                else:
                    self.estado = Estado.PLAYER_TURN
                    self._actualizar_botones()

    def _mostrar_resultado_baza(self, resultado: dict) -> None:
        if self.engine.primera_baza:
            self.engine.marcar_primera_baza_jugada()

        ganador = resultado["ganador_baza"]
        parda = resultado["parda"]

        if parda:
            self._set_mensaje("¡Parda! (empate)", 2.0)
        elif ganador:
            self._set_mensaje(f"Gana la baza: {ganador}", 2.0)

        self.estado = Estado.SHOWING_BAZA
        self.show_timer = 1.8

    def _despues_baza(self) -> None:
        self.carta_jugador_mesa = None
        self.carta_cpu_mesa = None

        if self.ronda.terminada:
            self._finalizar_ronda()
        else:
            siguiente = self.ronda.turno
            if siguiente == self.engine.jugador2.nombre:
                self.estado = Estado.CPU_THINKING
                self.cpu_timer = 0.8
            else:
                self.estado = Estado.PLAYER_TURN
                self._actualizar_botones()

    def _finalizar_ronda(self) -> None:
        if self.ronda.ganador_ronda:
            puntos = self.engine.finalizar_ronda(self.ronda.ganador_ronda)
            self._set_mensaje(f"{self.ronda.ganador_ronda} gana la ronda (+{puntos} pts)", 3.0)
        self.estado = Estado.RONDA_FIN
        self.show_timer = 2.5

    # ── Envido ────────────────────────────────────────────

    def _iniciar_envido(self, cantor: str, tipo: str) -> None:
        if not self.engine.puede_cantar_envido():
            self._set_mensaje("No se puede cantar envido ahora.")
            return

        self._set_mensaje(f"¡{cantor} canta {tipo.replace('_', ' ').upper()}!")
        self.envido_secuencia = [tipo]
        self.envido_cantor = cantor
        oponente_nombre = self.engine._oponente_nombre(cantor)
        oponente = self.engine._get_jugador(oponente_nombre)

        if isinstance(oponente, JugadorHumano):
            self._mostrar_envido_dialogo()
        else:
            # CPU responde
            self.estado = Estado.CPU_THINKING
            self.cpu_timer = 1.0
            # Overrride _turno_cpu para manejar respuesta envido
            self._pendiente_envido_cpu_respuesta = True

    def _mostrar_envido_dialogo(self) -> None:
        """Muestra botones de respuesta al envido para el humano."""
        self.envido_respuestas_validas = self.engine.cantos_validos_respuesta_envido(
            self.envido_secuencia
        )
        self.estado = Estado.ENVIDO_RESPONSE
        self._crear_envido_botones()

    def _crear_envido_botones(self) -> None:
        etiquetas = {
            "quiero": "¡Quiero!",
            "no_quiero": "No quiero",
            "envido": "Envido",
            "real_envido": "Real Envido",
            "falta_envido": "Falta Envido",
        }
        cx = ANCHO // 2
        bw, bh = 200, 44
        n = len(self.envido_respuestas_validas)
        # Cards take ~90px, header takes ~70px, so offset buttons by 160
        total_h = n * (bh + 8)
        start_y = ALTO // 2 - total_h // 2 + 80

        self.envido_botones = []
        for i, resp in enumerate(self.envido_respuestas_validas):
            color = VERDE_OSCURO if resp not in ("quiero", "no_quiero") else AZUL
            if resp == "no_quiero":
                color = ROJO
            r = pygame.Rect(cx - bw // 2, start_y + i * (bh + 8), bw, bh)
            self.envido_botones.append(Boton(r, etiquetas.get(resp, resp), color=color))

    def _click_envido_response(self, pos: tuple[int, int]) -> None:
        for i, btn in enumerate(self.envido_botones):
            if btn.clicked(pos):
                respuesta = self.envido_respuestas_validas[i]
                self._procesar_respuesta_envido(respuesta, self.engine.jugador1.nombre)
                return

    def _procesar_respuesta_envido(self, respuesta: str, respondedor: str) -> None:
        if respuesta in ("quiero", "no_quiero"):
            aceptado = respuesta == "quiero"
            pq, pnq = self.engine.calcular_puntos_envido_secuencia(self.envido_secuencia)
            resultado = self.engine.resolver_envido(
                aceptado, self.envido_cantor, pq, pnq
            )
            resultado["nombre_j1"] = self.engine.jugador1.nombre
            resultado["nombre_j2"] = self.engine.jugador2.nombre
            self.resultado_envido = resultado
            self.engine.sumar_puntos(resultado["ganador"], resultado["puntos"])

            if aceptado:
                msg = (f"Envido: {resultado['nombre_j1']}={resultado['envido_j1']}, "
                       f"{resultado['nombre_j2']}={resultado['envido_j2']}. "
                       f"Gana {resultado['ganador']} (+{resultado['puntos']})")
            else:
                msg = f"No quiso. {resultado['ganador']} gana +{resultado['puntos']} de envido."
            self._set_mensaje(msg, 3.0)
            self.estado = Estado.SHOWING_ENVIDO
            self.show_timer = 2.5
        else:
            # Re-canto
            self._set_mensaje(f"¡{respondedor} canta {respuesta.replace('_', ' ').upper()}!")
            self.envido_secuencia.append(respuesta)
            # Swap: ahora el otro debe responder
            self.envido_cantor = respondedor
            oponente_nombre = self.engine._oponente_nombre(respondedor)
            oponente = self.engine._get_jugador(oponente_nombre)

            if isinstance(oponente, JugadorHumano):
                self._mostrar_envido_dialogo()
            else:
                # CPU responde al re-canto
                self._responder_envido_cpu(oponente_nombre)

    def _responder_envido_cpu(self, cpu_nombre: str) -> None:
        cpu = self.engine._get_jugador(cpu_nombre)
        respuestas_validas = self.engine.cantos_validos_respuesta_envido(self.envido_secuencia)
        game_state = self.engine.get_game_state(cpu_nombre)

        if isinstance(cpu, JugadorAI):
            resp = cpu.ai.responder_envido(game_state)
            respuesta = resp.get("tipo", "quiero")
        else:
            respuesta = "quiero"

        if respuesta not in respuestas_validas:
            respuesta = "quiero"

        # Pequeño delay visual para la respuesta CPU
        self._procesar_respuesta_envido(respuesta, cpu_nombre)

    def _continuar_despues_envido(self) -> None:
        self.resultado_envido = None
        self._actualizar_botones()

        if self.ronda.terminada:
            self._finalizar_ronda()
            return

        siguiente = self.ronda.turno
        if siguiente == self.engine.jugador2.nombre:
            self.estado = Estado.CPU_THINKING
            self.cpu_timer = 0.8
        else:
            self.estado = Estado.PLAYER_TURN

    # ── Truco ─────────────────────────────────────────────

    def _iniciar_truco(self, cantor: str, nivel: str) -> None:
        if not self.engine.puede_cantar_truco(cantor):
            self._set_mensaje("No se puede cantar truco ahora.")
            return

        self._set_mensaje(f"¡{cantor} canta {nivel.upper()}!")
        self.truco_cantor = cantor
        self.truco_nivel = nivel
        oponente_nombre = self.engine._oponente_nombre(cantor)
        oponente = self.engine._get_jugador(oponente_nombre)

        self.truco_puede_subir = self.engine.nivel_truco + 1 < 3

        if isinstance(oponente, JugadorHumano):
            self._mostrar_truco_dialogo()
        else:
            self._responder_truco_cpu(oponente_nombre)

    def _mostrar_truco_dialogo(self) -> None:
        self.estado = Estado.TRUCO_RESPONSE
        self._crear_truco_botones()

    def _crear_truco_botones(self) -> None:
        cx = ANCHO // 2
        bw, bh = 200, 44
        opciones = ["quiero", "no_quiero"]
        if self.truco_puede_subir:
            sig = self._nombre_siguiente_truco_str(self.truco_nivel)
            opciones.append(sig)

        etiquetas = {
            "quiero": "¡Quiero!",
            "no_quiero": "No quiero",
            "retruco": "Retruco",
            "vale cuatro": "Vale Cuatro",
        }

        n = len(opciones)
        total_h = n * (bh + 8)
        start_y = ALTO // 2 - total_h // 2

        self.truco_botones = []
        self._truco_opciones = opciones
        for i, op in enumerate(opciones):
            color = AZUL if op == "quiero" else ROJO if op == "no_quiero" else VERDE_OSCURO
            r = pygame.Rect(cx - bw // 2, start_y + i * (bh + 8), bw, bh)
            self.truco_botones.append(Boton(r, etiquetas.get(op, op.title()), color=color))

    def _click_truco_response(self, pos: tuple[int, int]) -> None:
        for i, btn in enumerate(self.truco_botones):
            if btn.clicked(pos):
                respuesta = self._truco_opciones[i]
                self._procesar_respuesta_truco(respuesta, self.engine.jugador1.nombre)
                return

    def _procesar_respuesta_truco(self, respuesta: str, respondedor: str) -> None:
        if respuesta in ("quiero", "no_quiero"):
            aceptado = respuesta == "quiero"
            resultado = self.engine.resolver_truco(aceptado, self.truco_cantor)

            if aceptado:
                self._set_mensaje(f"{respondedor}: ¡Quiero! (vale {resultado['puntos_ronda']} pts)")
            else:
                self._set_mensaje(f"{respondedor}: No quiero. {self.truco_cantor} gana la ronda.")
                self.ronda.ganador_ronda = self.truco_cantor
                self.ronda.terminada = True

            self._actualizar_botones()

            if self.ronda.terminada:
                self.estado = Estado.RONDA_FIN
                self.show_timer = 2.0
                if self.ronda.ganador_ronda:
                    puntos = self.engine.finalizar_ronda(self.ronda.ganador_ronda)
                    self._set_mensaje(
                        f"{self.ronda.ganador_ronda} gana la ronda (+{puntos} pts)", 3.0
                    )
            else:
                siguiente = self.ronda.turno
                if siguiente == self.engine.jugador2.nombre:
                    self.estado = Estado.CPU_THINKING
                    self.cpu_timer = 0.8
                else:
                    self.estado = Estado.PLAYER_TURN
        else:
            # Subir apuesta
            self._set_mensaje(f"¡{respondedor} canta {respuesta.upper()}!")
            self.engine.nivel_truco = self.engine.siguiente_nivel_truco()
            self.engine.truco_cantado_por = respondedor

            self.truco_cantor = respondedor
            self.truco_nivel = respuesta
            self.truco_puede_subir = self.engine.nivel_truco < 3

            oponente_nombre = self.engine._oponente_nombre(respondedor)
            oponente = self.engine._get_jugador(oponente_nombre)

            if isinstance(oponente, JugadorHumano):
                self._mostrar_truco_dialogo()
            else:
                self._responder_truco_cpu(oponente_nombre)

    def _responder_truco_cpu(self, cpu_nombre: str) -> None:
        cpu = self.engine._get_jugador(cpu_nombre)
        game_state = self.engine.get_game_state(cpu_nombre)

        if isinstance(cpu, JugadorAI):
            resp = cpu.ai.responder_truco(game_state)
            respuesta = resp.get("tipo", "quiero")
        else:
            respuesta = "quiero"

        validas = ["quiero", "no_quiero"]
        if self.truco_puede_subir:
            validas.append(self._nombre_siguiente_truco_str(self.truco_nivel))

        if respuesta not in validas:
            respuesta = "quiero"

        self._procesar_respuesta_truco(respuesta, cpu_nombre)

    @staticmethod
    def _nombre_siguiente_truco_str(nivel: str) -> str:
        m = {"truco": "retruco", "retruco": "vale cuatro"}
        return m.get(nivel, "vale cuatro")

    # ── Mazo ──────────────────────────────────────────────

    def _ir_al_mazo(self, nombre: str) -> None:
        self._set_mensaje(f"{nombre} se va al mazo.", 2.5)

        if self.engine.primera_baza and not self.engine.envido_terminado:
            oponente = self.engine._oponente_nombre(nombre)
            self.engine.sumar_puntos(oponente, 2)
            self.engine.envido_terminado = True
            self._set_mensaje(f"{nombre} se va al mazo. {oponente} gana 2 pts de envido.", 3.0)

        self.ronda.ir_al_mazo(nombre)
        self.estado = Estado.SHOWING_MAZO
        self.show_timer = 2.0

    def _continuar_despues_mazo(self) -> None:
        if self.ronda.ganador_ronda:
            puntos = self.engine.finalizar_ronda(self.ronda.ganador_ronda)
            self._set_mensaje(
                f"{self.ronda.ganador_ronda} gana la ronda (+{puntos} pts)", 3.0
            )
        self.estado = Estado.RONDA_FIN
        self.show_timer = 2.5

    # ── Override turno CPU (envido pendiente) ─────────────

    _pendiente_envido_cpu_respuesta: bool = False

    def _turno_cpu_wrapper(self) -> None:
        """Wrapper que chequea si hay envido pendiente antes del turno normal."""
        if self._pendiente_envido_cpu_respuesta:
            self._pendiente_envido_cpu_respuesta = False
            oponente_nombre = self.engine._oponente_nombre(self.envido_cantor)
            self._responder_envido_cpu(oponente_nombre)
        else:
            self._turno_cpu()

    def _update(self, dt: float) -> None:
        if self.mensaje_timer > 0:
            self.mensaje_timer -= dt

        if self.estado == Estado.CPU_THINKING:
            self.cpu_timer -= dt
            if self.cpu_timer <= 0:
                self._turno_cpu_wrapper()

        elif self.estado == Estado.SHOWING_BAZA:
            self.show_timer -= dt
            if self.show_timer <= 0:
                self._despues_baza()

        elif self.estado == Estado.SHOWING_ENVIDO:
            self.show_timer -= dt
            if self.show_timer <= 0:
                self._continuar_despues_envido()

        elif self.estado == Estado.SHOWING_MAZO:
            self.show_timer -= dt
            if self.show_timer <= 0:
                self._continuar_despues_mazo()

        elif self.estado == Estado.RONDA_FIN:
            self.show_timer -= dt
            if self.show_timer <= 0:
                if self.engine.juego_terminado():
                    self.estado = Estado.GAME_OVER
                else:
                    self.engine.alternar_mano()
                    self._nueva_ronda()

    # ── Draw ──────────────────────────────────────────────

    def _draw(self) -> None:
        self.screen.fill(VERDE_MESA)
        self._draw_titulo()
        self._draw_score()
        self._draw_cartas_cpu()
        self._draw_mesa()
        self._draw_cartas_jugador()
        self._draw_botones()
        self._draw_mensaje()
        self._draw_info_truco()

        if self.estado == Estado.ENVIDO_RESPONSE:
            self._draw_dialogo_envido()
        elif self.estado == Estado.TRUCO_RESPONSE:
            self._draw_dialogo_truco()
        elif self.estado == Estado.GAME_OVER:
            self._draw_game_over()

    def _draw_titulo(self) -> None:
        txt = self.font_titulo.render("El Malevo", True, DORADO)
        self.screen.blit(txt, (20, 10))

    def _draw_score(self) -> None:
        j1 = self.engine.jugador1
        j2 = self.engine.jugador2

        # Panel de puntuación
        panel = pygame.Rect(ANCHO - 220, 15, 200, 120)
        pygame.draw.rect(self.screen, VERDE_OSCURO, panel, border_radius=10)
        pygame.draw.rect(self.screen, DORADO, panel, 2, border_radius=10)

        header = self.font_medio.render("PUNTUACIÓN", True, DORADO)
        self.screen.blit(header, (panel.x + panel.w // 2 - header.get_width() // 2, panel.y + 8))

        txt1 = self.font_medio.render(f"{j1.nombre}: {j1.puntos}", True, BLANCO)
        txt2 = self.font_medio.render(f"{j2.nombre}: {j2.puntos}", True, BLANCO)
        self.screen.blit(txt1, (panel.x + 15, panel.y + 40))
        self.screen.blit(txt2, (panel.x + 15, panel.y + 68))

        meta = self.font_chico.render(f"Objetivo: {PUNTOS_OBJETIVO}", True, GRIS)
        self.screen.blit(meta, (panel.x + 15, panel.y + 96))

    def _draw_info_truco(self) -> None:
        """Muestra el nivel de truco actual."""
        if self.engine.nivel_truco > 0:
            nivel_txt = NOMBRES_TRUCO[self.engine.nivel_truco].upper()
            txt = self.font_medio.render(f"🔥 {nivel_txt}", True, AMARILLO)
            self.screen.blit(txt, (ANCHO - 220, 145))

        # Mano indicator
        mano_txt = self.font_chico.render(f"Mano: {self.engine.mano_nombre}", True, GRIS)
        self.screen.blit(mano_txt, (ANCHO - 220, 172))

    def _draw_cartas_cpu(self) -> None:
        """Dibuja las cartas de la CPU (dorso)."""
        cpu = self.engine.jugador2
        n = len(cpu.mano)
        total_w = n * (CARTA_W + 15) - 15
        start_x = (ANCHO - 220) // 2 - total_w // 2

        for i in range(n):
            x = start_x + i * (CARTA_W + 15)
            dorso = self.renderer.get_dorso()
            self.screen.blit(dorso, (x, CPU_Y))

    def _draw_cartas_jugador(self) -> None:
        """Dibuja las cartas del jugador (cara visible)."""
        mano = self.engine.jugador1.mano
        rects = self._rects_mano_jugador(mano)

        for i, (carta, rect) in enumerate(zip(mano, rects)):
            y_offset = -15 if i == self.carta_hover else 0
            img = self.renderer.get(carta)
            self.screen.blit(img, (rect.x, rect.y + y_offset))
            if i == self.carta_hover:
                pygame.draw.rect(self.screen, AMARILLO,
                                 pygame.Rect(rect.x - 2, rect.y + y_offset - 2,
                                             CARTA_W + 4, CARTA_H + 4), 3, border_radius=6)

    def _rects_mano_jugador(self, mano: list[Carta]) -> list[pygame.Rect]:
        n = len(mano)
        if n == 0:
            return []
        total_w = n * (CARTA_W + 20) - 20
        start_x = (ANCHO - 220) // 2 - total_w // 2
        return [
            pygame.Rect(start_x + i * (CARTA_W + 20), MANO_Y, CARTA_W, CARTA_H)
            for i in range(n)
        ]

    def _draw_mesa(self) -> None:
        """Dibuja las cartas jugadas en la mesa."""
        mesa_cx = (ANCHO - 220) // 2
        mesa_cy = ALTO // 2

        # Cartas de bazas anteriores (mini)
        if self.ronda:
            for bi, baza in enumerate(self.ronda.bazas):
                ox = mesa_cx - 200 + bi * 140
                for ji, nombre in enumerate([self.engine.jugador1.nombre, self.engine.jugador2.nombre]):
                    if nombre in baza.cartas:
                        carta = baza.cartas[nombre]
                        img = self.renderer.get(carta, (CARTA_MINI_W, CARTA_MINI_H))
                        y = mesa_cy + (30 if ji == 0 else -CARTA_MINI_H - 30)
                        self.screen.blit(img, (ox, y))

        # Cartas de la baza actual
        if self.carta_jugador_mesa:
            img = self.renderer.get(self.carta_jugador_mesa)
            self.screen.blit(img, (mesa_cx - CARTA_W // 2, mesa_cy + 20))
        if self.carta_cpu_mesa:
            img = self.renderer.get(self.carta_cpu_mesa)
            self.screen.blit(img, (mesa_cx - CARTA_W // 2, mesa_cy - CARTA_H - 20))

    def _draw_botones(self) -> None:
        if self.estado != Estado.PLAYER_TURN:
            return
        for btn in self.botones_accion:
            btn.draw(self.screen, self.font_boton)

    def _draw_mensaje(self) -> None:
        if self.mensaje and self.mensaje_timer > 0:
            txt = self.font_medio.render(self.mensaje, True, BLANCO)
            bg_w = txt.get_width() + 40
            bg_h = txt.get_height() + 16
            bg_x = (ANCHO - 220) // 2 - bg_w // 2
            bg_y = ALTO // 2 - 200

            bg_surf = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, 180))
            self.screen.blit(bg_surf, (bg_x, bg_y))
            pygame.draw.rect(self.screen, DORADO,
                             pygame.Rect(bg_x, bg_y, bg_w, bg_h), 2, border_radius=10)
            self.screen.blit(txt, (bg_x + 20, bg_y + 8))

    def _draw_dialogo_envido(self) -> None:
        """Dibuja el diálogo de respuesta al envido."""
        # Overlay semi-transparente
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        # Panel
        pw, ph = 320, len(self.envido_botones) * 52 + 200
        px = ANCHO // 2 - pw // 2
        py = ALTO // 2 - ph // 2
        pygame.draw.rect(self.screen, VERDE_OSCURO,
                         pygame.Rect(px, py, pw, ph), border_radius=12)
        pygame.draw.rect(self.screen, DORADO,
                         pygame.Rect(px, py, pw, ph), 3, border_radius=12)

        canto_label = self.envido_secuencia[-1].replace("_", " ").upper()
        header = self.font_medio.render(f"Te cantaron {canto_label}", True, AMARILLO)
        self.screen.blit(header, (ANCHO // 2 - header.get_width() // 2, py + 15))

        sub = self.font_chico.render("¿Qué hacés?", True, BLANCO)
        self.screen.blit(sub, (ANCHO // 2 - sub.get_width() // 2, py + 45))

        # Mostrar cartas del jugador en el diálogo
        mano = self.engine.jugador1.mano
        if mano:
            mini_w, mini_h = 50, 78
            total_w = len(mano) * (mini_w + 8) - 8
            sx = ANCHO // 2 - total_w // 2
            sy = py + 68
            for i, c in enumerate(mano):
                img = self.renderer.get(c, (mini_w, mini_h))
                self.screen.blit(img, (sx + i * (mini_w + 8), sy))

        for btn in self.envido_botones:
            btn.draw(self.screen, self.font_boton)

    def _draw_dialogo_truco(self) -> None:
        """Dibuja el diálogo de respuesta al truco."""
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        pw, ph = 320, len(self.truco_botones) * 52 + 80
        px = ANCHO // 2 - pw // 2
        py = ALTO // 2 - ph // 2
        pygame.draw.rect(self.screen, VERDE_OSCURO,
                         pygame.Rect(px, py, pw, ph), border_radius=12)
        pygame.draw.rect(self.screen, DORADO,
                         pygame.Rect(px, py, pw, ph), 3, border_radius=12)

        header = self.font_medio.render(
            f"¡{self.truco_cantor} canta {self.truco_nivel.upper()}!",
            True, AMARILLO,
        )
        self.screen.blit(header, (ANCHO // 2 - header.get_width() // 2, py + 15))

        sub = self.font_chico.render("¿Qué hacés?", True, BLANCO)
        self.screen.blit(sub, (ANCHO // 2 - sub.get_width() // 2, py + 45))

        for btn in self.truco_botones:
            btn.draw(self.screen, self.font_boton)

    def _draw_game_over(self) -> None:
        overlay = pygame.Surface((ANCHO, ALTO), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        ganador = self.engine.ganador_juego()
        if ganador:
            txt1 = self.font_titulo.render(f"¡{ganador.nombre} GANA!", True, DORADO)
            txt2 = self.font_grande.render(f"Puntaje: {ganador.puntos}", True, BLANCO)
            txt3 = self.font_medio.render("Click para jugar de nuevo", True, GRIS)

            cy = ALTO // 2
            self.screen.blit(txt1, (ANCHO // 2 - txt1.get_width() // 2, cy - 60))
            self.screen.blit(txt2, (ANCHO // 2 - txt2.get_width() // 2, cy))
            self.screen.blit(txt3, (ANCHO // 2 - txt3.get_width() // 2, cy + 50))
