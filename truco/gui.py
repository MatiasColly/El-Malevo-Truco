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
VERDE_ZONA = (44, 118, 62)      # zona central de juego
VERDE_PANEL = (18, 52, 28)      # paneles y diálogos
BLANCO = (255, 255, 255)
NEGRO = (0, 0, 0)
AMARILLO = (255, 215, 0)
ROJO = (200, 50, 50)
GRIS = (190, 190, 190)
GRIS_OSCURO = (80, 80, 80)
AZUL = (50, 100, 200)
CREMA = (245, 235, 210)
MARRON = (139, 90, 43)
MARRON_MARCO = (110, 70, 34)    # marco de madera
MARRON_CLARO = (150, 100, 52)
DORADO = (218, 165, 32)
DORADO_SUAVE = (170, 140, 70)

# Tamaños de carta
CARTA_W, CARTA_H = 90, 140
CARTA_MINI_W, CARTA_MINI_H = 60, 93

# Layout
MANO_Y = ALTO - CARTA_H - 30
MESA_Y = ALTO // 2 - CARTA_H // 2
CPU_Y = 25
SCORE_X = ANCHO - 220
MESA_CX = (ANCHO - 220) // 2  # centro horizontal del área de juego (el panel derecho ocupa 220)

# ── Assets ────────────────────────────────────────────────

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "cards")


class CardRenderer:
    """Carga y cachea las imágenes de cartas."""

    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface] = {}
        self._dorso: pygame.Surface | None = None

    def _path_carta(self, numero: int, palo: str) -> str | None:
        for ext in ("jpg", "png", "svg"):
            path = os.path.join(ASSETS_DIR, f"{numero}_{palo}.{ext}")
            if os.path.exists(path):
                return path
        return None

    def _dorso_path(self) -> str | None:
        for ext in ("png", "jpg", "svg"):
            path = os.path.join(ASSETS_DIR, f"dorso.{ext}")
            if os.path.exists(path):
                return path
        return None

    @staticmethod
    def _redondear_esquinas(surf: pygame.Surface) -> pygame.Surface:
        """Aplica esquinas redondeadas a una carta rasterizada (foto)."""
        radio = max(4, surf.get_height() // 16)
        mask = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radio)
        out = surf.convert_alpha()
        out.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return out

    def get(self, carta: Carta, size: tuple[int, int] = (CARTA_W, CARTA_H)) -> pygame.Surface:
        key = f"{carta.numero}_{carta.palo}_{size[0]}x{size[1]}"
        if key not in self._cache:
            path = self._path_carta(carta.numero, carta.palo)
            if path:
                raw = pygame.image.load(path)
                img = pygame.transform.smoothscale(raw, size)
                if not path.endswith(".svg"):
                    img = self._redondear_esquinas(img)
                self._cache[key] = img
            else:
                self._cache[key] = self._generar_carta(carta, size)
        return self._cache[key]

    def get_dorso(self, size: tuple[int, int] = (CARTA_W, CARTA_H)) -> pygame.Surface:
        key = f"dorso_{size[0]}x{size[1]}"
        if key not in self._cache:
            path = self._dorso_path()
            if path:
                raw = pygame.image.load(path)
                img = pygame.transform.smoothscale(raw.convert_alpha(), size)
                if not path.endswith(".svg"):
                    img = self._redondear_esquinas(img)
                self._cache[key] = img
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
        sombra = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 90), sombra.get_rect(), border_radius=10)
        screen.blit(sombra, (self.rect.x, self.rect.y + 3))

        c = self.color_hover if self.hover else self.color
        pygame.draw.rect(screen, c, self.rect, border_radius=10)
        borde = tuple(min(255, x + 55) for x in c)
        pygame.draw.rect(screen, borde, self.rect, 2, border_radius=10)
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
        fuentes = "segoeui,arial"
        self.font_grande = pygame.font.SysFont(fuentes, 28, bold=True)
        self.font_medio = pygame.font.SysFont(fuentes, 20, bold=True)
        self.font_chico = pygame.font.SysFont(fuentes, 15)
        self.font_mini = pygame.font.SysFont(fuentes, 12, bold=True)
        self.font_titulo = pygame.font.SysFont(fuentes, 36, bold=True)
        self.font_boton = pygame.font.SysFont(fuentes, 17, bold=True)
        self.font_puntos = pygame.font.SysFont(fuentes, 26, bold=True)

        # Superficies pre-renderizadas y animación
        self.fondo = self._crear_fondo()
        self._lift = [0.0, 0.0, 0.0]  # elevación animada de cada carta de la mano
        self._sombras: dict[tuple[int, int, int], pygame.Surface] = {}

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
        self.truco_pendiente: bool = False  # True cuando hay truco esperando respuesta tras envido

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
        self.truco_pendiente = False
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
        self.engine.envido_secuencia = [tipo]
        self.envido_secuencia = self.engine.envido_secuencia
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
            if self._verificar_game_over():
                return

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

        if self.truco_pendiente:
            self.truco_pendiente = False
            # El pie (oponente del cantor de truco) responde al truco
            pie_nombre = self.engine._oponente_nombre(self.truco_cantor)
            pie = self.engine._get_jugador(pie_nombre)
            if isinstance(pie, JugadorHumano):
                self._mostrar_truco_dialogo()
            else:
                self._responder_truco_cpu(pie_nombre)
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
        # En primera baza el respondedor puede contra-cantar envido antes de responder al truco
        if self.engine.puede_cantar_envido():
            opciones.extend(["envido", "real_envido", "falta_envido"])

        etiquetas = {
            "quiero": "¡Quiero!",
            "no_quiero": "No quiero",
            "retruco": "Retruco",
            "vale cuatro": "Vale Cuatro",
            "envido": "Envido",
            "real_envido": "Real Envido",
            "falta_envido": "Falta Envido",
        }

        n = len(opciones)
        total_h = n * (bh + 8)
        start_y = ALTO // 2 - total_h // 2

        self.truco_botones = []
        self._truco_opciones = opciones
        for i, op in enumerate(opciones):
            if op == "quiero":
                color = AZUL
            elif op == "no_quiero":
                color = ROJO
            elif op in ("envido", "real_envido", "falta_envido"):
                color = VERDE_OSCURO
            else:
                color = (120, 80, 160)
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

        elif respuesta in ("envido", "real_envido", "falta_envido"):
            # Pie canta envido en respuesta al truco del mano: se resuelve envido primero
            self.truco_pendiente = True
            self._iniciar_envido(respondedor, respuesta)

        else:
            # Subir apuesta
            self._set_mensaje(f"¡{respondedor} canta {respuesta.upper()}!")
            self.engine.nivel_truco = self.engine.siguiente_nivel_truco()
            self.engine.truco_cantado_por = respondedor

            self.truco_cantor = respondedor
            self.truco_nivel = respuesta
            self.truco_puede_subir = self.engine.nivel_truco + 1 < 3

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

    def _verificar_game_over(self) -> bool:
        """Si alguien llegó a 30, transiciona a GAME_OVER inmediatamente."""
        if self.engine.juego_terminado():
            ganador = self.engine.ganador_juego()
            self._set_mensaje(f"¡{ganador.nombre} gana el partido! 🎉", 0)
            self.estado = Estado.GAME_OVER
            return True
        return False

    def _ir_al_mazo(self, nombre: str) -> None:
        self._set_mensaje(f"{nombre} se va al mazo.", 2.5)

        if self.engine.primera_baza and not self.engine.envido_terminado:
            oponente = self.engine._oponente_nombre(nombre)
            self.engine.sumar_puntos(oponente, 1)
            self.engine.envido_terminado = True
            self._set_mensaje(f"{nombre} se va al mazo. {oponente} gana 1 pt de envido.", 3.0)
            if self._verificar_game_over():
                return

        self.ronda.ir_al_mazo(nombre)
        self.estado = Estado.SHOWING_MAZO
        self.show_timer = 2.0

    def _continuar_despues_mazo(self) -> None:
        if self.ronda.ganador_ronda and not self.engine.juego_terminado():
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

        # Animación de elevación de la carta bajo el mouse
        for i in range(len(self._lift)):
            objetivo = 16.0 if (i == self.carta_hover and self.estado == Estado.PLAYER_TURN) else 0.0
            self._lift[i] += (objetivo - self._lift[i]) * min(1.0, dt * 14)

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

    def _crear_fondo(self) -> pygame.Surface:
        """Pre-renderiza el fondo: paño con gradiente, zona de juego y marco de madera."""
        fondo = pygame.Surface((ANCHO, ALTO))

        # Gradiente vertical: más claro hacia el centro de la mesa
        centro_c = (46, 124, 64)
        borde_c = (26, 76, 40)
        for y in range(ALTO):
            t = min(1.0, abs(y - ALTO * 0.45) / (ALTO * 0.55))
            c = tuple(int(centro_c[i] + (borde_c[i] - centro_c[i]) * t) for i in range(3))
            pygame.draw.line(fondo, c, (0, y), (ANCHO, y))

        # Zona central de juego (elipse con costura dorada)
        zona = pygame.Rect(0, 0, 640, 380)
        zona.center = (MESA_CX, ALTO // 2)
        pygame.draw.ellipse(fondo, VERDE_ZONA, zona)
        pygame.draw.ellipse(fondo, (20, 60, 32), zona, 3)
        pygame.draw.ellipse(fondo, DORADO_SUAVE, zona.inflate(16, 16), 2)

        # Marco de madera
        pygame.draw.rect(fondo, MARRON_MARCO, fondo.get_rect(), 12)
        pygame.draw.rect(fondo, MARRON_CLARO, fondo.get_rect().inflate(-6, -6), 3)
        pygame.draw.rect(fondo, (60, 38, 18), fondo.get_rect(), 2)
        return fondo

    def _sombra_carta(self, x: int, y: int, w: int, h: int, alpha: int = 80) -> None:
        """Dibuja una sombra redondeada debajo de una carta (cacheada por tamaño)."""
        key = (w, h, alpha)
        if key not in self._sombras:
            s = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.rect(s, (0, 0, 0, alpha), s.get_rect(), border_radius=10)
            self._sombras[key] = s
        self.screen.blit(self._sombras[key], (x + 4, y + 6))

    def _draw_panel(self, rect: pygame.Rect) -> None:
        """Panel oscuro con sombra y borde dorado (diálogos, marcador)."""
        sombra = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(sombra, (0, 0, 0, 120), sombra.get_rect(), border_radius=14)
        self.screen.blit(sombra, (rect.x + 4, rect.y + 6))
        pygame.draw.rect(self.screen, VERDE_PANEL, rect, border_radius=14)
        pygame.draw.rect(self.screen, DORADO, rect, 3, border_radius=14)

    def _draw(self) -> None:
        self.screen.blit(self.fondo, (0, 0))
        self._draw_titulo()
        self._draw_score()
        self._draw_info_truco()
        self._draw_indicador_turno()
        self._draw_cartas_cpu()
        self._draw_mesa()
        self._draw_cartas_jugador()
        self._draw_botones()
        self._draw_mensaje()

        if self.estado == Estado.ENVIDO_RESPONSE:
            self._draw_dialogo_envido()
        elif self.estado == Estado.TRUCO_RESPONSE:
            self._draw_dialogo_truco()
        elif self.estado == Estado.GAME_OVER:
            self._draw_game_over()

    def _draw_titulo(self) -> None:
        txt = self.font_titulo.render("El Malevo", True, DORADO)
        self.screen.blit(txt, (24, 14))
        sub = self.font_chico.render("Truco Argentino", True, DORADO_SUAVE)
        self.screen.blit(sub, (26, 10 + txt.get_height()))

    def _draw_score(self) -> None:
        j1 = self.engine.jugador1
        j2 = self.engine.jugador2

        panel = pygame.Rect(ANCHO - 220, 15, 200, 158)
        self._draw_panel(panel)

        header = self.font_chico.render(f"PRIMERO A {PUNTOS_OBJETIVO}", True, DORADO_SUAVE)
        self.screen.blit(header, (panel.centerx - header.get_width() // 2, panel.y + 10))

        for idx, j in enumerate((j1, j2)):
            y = panel.y + 38 + idx * 60

            nombre = self.font_chico.render(j.nombre, True, BLANCO)
            self.screen.blit(nombre, (panel.x + 14, y))

            if self.engine.mano_nombre == j.nombre:
                chip_txt = self.font_mini.render("MANO", True, NEGRO)
                chip = pygame.Rect(0, 0, chip_txt.get_width() + 10, chip_txt.get_height() + 4)
                chip.topleft = (panel.x + 14 + nombre.get_width() + 8, y + 1)
                pygame.draw.rect(self.screen, DORADO, chip, border_radius=6)
                self.screen.blit(chip_txt, (chip.x + 5, chip.y + 2))

            pts = self.font_puntos.render(str(j.puntos), True, AMARILLO)
            self.screen.blit(pts, (panel.right - 16 - pts.get_width(), y - 6))

            # Barra de progreso; la marca del medio separa malas de buenas
            barra = pygame.Rect(panel.x + 14, y + 26, panel.w - 28, 8)
            pygame.draw.rect(self.screen, (10, 30, 16), barra, border_radius=4)
            frac = min(1.0, j.puntos / PUNTOS_OBJETIVO)
            if frac > 0:
                fill = pygame.Rect(barra.x, barra.y, max(6, int(barra.w * frac)), barra.h)
                pygame.draw.rect(self.screen, DORADO, fill, border_radius=4)
            mx = barra.x + barra.w // 2
            pygame.draw.line(self.screen, GRIS, (mx, barra.y - 1), (mx, barra.bottom + 1), 1)

    def _draw_info_truco(self) -> None:
        """Muestra el nivel de truco actual como cartel."""
        if self.engine.nivel_truco <= 0:
            return
        nivel_txt = NOMBRES_TRUCO[self.engine.nivel_truco].upper()
        txt = self.font_medio.render(nivel_txt, True, NEGRO)
        badge = pygame.Rect(0, 0, txt.get_width() + 26, txt.get_height() + 12)
        badge.topleft = (ANCHO - 220, 185)
        pygame.draw.rect(self.screen, AMARILLO, badge, border_radius=10)
        pygame.draw.rect(self.screen, (120, 90, 0), badge, 2, border_radius=10)
        self.screen.blit(txt, (badge.x + 13, badge.y + 6))

    def _draw_indicador_turno(self) -> None:
        """Pastilla sobre la mano indicando de quién es el turno."""
        if self.estado == Estado.PLAYER_TURN:
            texto, color = "Tu turno — jugá una carta o cantá", AMARILLO
        elif self.estado == Estado.CPU_THINKING:
            puntos = "." * (1 + int(time.time() * 2) % 3)
            texto, color = f"{self.engine.jugador2.nombre} está pensando{puntos}", GRIS
        else:
            return
        txt = self.font_chico.render(texto, True, color)
        pill = pygame.Rect(0, 0, txt.get_width() + 24, txt.get_height() + 10)
        pill.center = (MESA_CX, MANO_Y - 36)
        s = pygame.Surface(pill.size, pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 110), s.get_rect(), border_radius=pill.h // 2)
        self.screen.blit(s, pill.topleft)
        self.screen.blit(txt, (pill.x + 12, pill.y + 5))

    def _draw_cartas_cpu(self) -> None:
        """Dibuja las cartas de la CPU (dorso)."""
        cpu = self.engine.jugador2
        n = len(cpu.mano)
        total_w = n * (CARTA_W + 15) - 15
        start_x = MESA_CX - total_w // 2

        dorso = self.renderer.get_dorso()
        for i in range(n):
            x = start_x + i * (CARTA_W + 15)
            self._sombra_carta(x, CPU_Y, CARTA_W, CARTA_H, alpha=60)
            self.screen.blit(dorso, (x, CPU_Y))

    def _draw_cartas_jugador(self) -> None:
        """Dibuja las cartas del jugador (cara visible)."""
        mano = self.engine.jugador1.mano
        rects = self._rects_mano_jugador(mano)

        for i, (carta, rect) in enumerate(zip(mano, rects)):
            lift = int(self._lift[i]) if i < len(self._lift) else 0
            x, y = rect.x, rect.y - lift
            self._sombra_carta(x, y, CARTA_W, CARTA_H)
            img = self.renderer.get(carta)
            self.screen.blit(img, (x, y))
            if i == self.carta_hover and self.estado == Estado.PLAYER_TURN:
                pygame.draw.rect(self.screen, AMARILLO,
                                 pygame.Rect(x - 3, y - 3, CARTA_W + 6, CARTA_H + 6),
                                 3, border_radius=8)

    def _rects_mano_jugador(self, mano: list[Carta]) -> list[pygame.Rect]:
        n = len(mano)
        if n == 0:
            return []
        total_w = n * (CARTA_W + 20) - 20
        start_x = MESA_CX - total_w // 2
        return [
            pygame.Rect(start_x + i * (CARTA_W + 20), MANO_Y, CARTA_W, CARTA_H)
            for i in range(n)
        ]

    def _draw_mesa(self) -> None:
        """Dibuja las cartas jugadas en la mesa."""
        mesa_cy = ALTO // 2
        slot_j = pygame.Rect(MESA_CX - CARTA_W // 2, mesa_cy + 20, CARTA_W, CARTA_H)
        slot_cpu = pygame.Rect(MESA_CX - CARTA_W // 2, mesa_cy - CARTA_H - 20, CARTA_W, CARTA_H)

        # Slots fantasma donde caen las cartas de la baza actual
        for rect, carta in ((slot_cpu, self.carta_cpu_mesa), (slot_j, self.carta_jugador_mesa)):
            if carta is None:
                s = pygame.Surface(rect.size, pygame.SRCALPHA)
                pygame.draw.rect(s, (255, 255, 255, 14), s.get_rect(), border_radius=10)
                pygame.draw.rect(s, (255, 255, 255, 45), s.get_rect(), 2, border_radius=10)
                self.screen.blit(s, rect.topleft)

        # Mientras se muestra el resultado, se resalta la carta ganadora
        ganador_baza = None
        if self.estado == Estado.SHOWING_BAZA and self.ronda and self.ronda.bazas:
            ganador_baza = self.ronda.bazas[-1].ganador

        if self.carta_cpu_mesa:
            self._sombra_carta(slot_cpu.x, slot_cpu.y, CARTA_W, CARTA_H)
            self.screen.blit(self.renderer.get(self.carta_cpu_mesa), slot_cpu.topleft)
            if ganador_baza == self.engine.jugador2.nombre:
                pygame.draw.rect(self.screen, AMARILLO, slot_cpu.inflate(8, 8), 3, border_radius=10)
        if self.carta_jugador_mesa:
            self._sombra_carta(slot_j.x, slot_j.y, CARTA_W, CARTA_H)
            self.screen.blit(self.renderer.get(self.carta_jugador_mesa), slot_j.topleft)
            if ganador_baza == self.engine.jugador1.nombre:
                pygame.draw.rect(self.screen, AMARILLO, slot_j.inflate(8, 8), 3, border_radius=10)

        # Bazas anteriores: miniaturas a la izquierda, ganador resaltado
        if not self.ronda:
            return
        bazas = self.ronda.bazas
        if bazas and self.estado == Estado.SHOWING_BAZA:
            bazas = bazas[:-1]  # la última se está mostrando grande en el centro

        nombres = [self.engine.jugador1.nombre, self.engine.jugador2.nombre]
        for bi, baza in enumerate(bazas):
            ox = 42 + bi * (CARTA_MINI_W + 24)
            label = self.font_chico.render(f"{bi + 1}ª", True, GRIS)
            self.screen.blit(label, (ox + CARTA_MINI_W // 2 - label.get_width() // 2,
                                     mesa_cy - CARTA_MINI_H - 32))
            for ji, nombre in enumerate(nombres):
                if nombre not in baza.cartas:
                    continue
                img = self.renderer.get(baza.cartas[nombre], (CARTA_MINI_W, CARTA_MINI_H))
                y = mesa_cy + 8 if ji == 0 else mesa_cy - CARTA_MINI_H - 8
                self._sombra_carta(ox, y, CARTA_MINI_W, CARTA_MINI_H, alpha=50)
                if baza.ganador and baza.ganador != nombre:
                    img = img.copy()
                    velo = pygame.Surface((CARTA_MINI_W, CARTA_MINI_H), pygame.SRCALPHA)
                    velo.fill((0, 0, 0, 110))
                    img.blit(velo, (0, 0))
                self.screen.blit(img, (ox, y))
                if baza.ganador == nombre:
                    pygame.draw.rect(self.screen, DORADO,
                                     pygame.Rect(ox - 2, y - 2, CARTA_MINI_W + 4, CARTA_MINI_H + 4),
                                     2, border_radius=6)

    def _draw_botones(self) -> None:
        if self.estado != Estado.PLAYER_TURN:
            return
        for btn in self.botones_accion:
            btn.draw(self.screen, self.font_boton)

    def _draw_mensaje(self) -> None:
        if not self.mensaje or self.mensaje_timer <= 0:
            return
        txt = self.font_medio.render(self.mensaje, True, BLANCO)
        bg_w = txt.get_width() + 44
        bg_h = txt.get_height() + 18

        toast = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
        pygame.draw.rect(toast, (0, 0, 0, 190), toast.get_rect(), border_radius=12)
        pygame.draw.rect(toast, DORADO, toast.get_rect(), 2, border_radius=12)
        toast.blit(txt, (22, 9))
        if self.mensaje_timer < 0.5:  # fade-out al final
            toast.set_alpha(int(255 * (self.mensaje_timer / 0.5)))
        self.screen.blit(toast, (MESA_CX - bg_w // 2, 180))

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
        self._draw_panel(pygame.Rect(px, py, pw, ph))

        canto_label = self.envido_secuencia[-1].replace("_", " ").upper()
        header = self.font_medio.render(f"Te cantaron {canto_label}", True, AMARILLO)
        self.screen.blit(header, (ANCHO // 2 - header.get_width() // 2, py + 15))

        sub = self.font_chico.render("¿Qué hacés?", True, BLANCO)
        self.screen.blit(sub, (ANCHO // 2 - sub.get_width() // 2, py + 45))

        # Mostrar las 3 cartas: jugadas (grisadas) + en mano (normal)
        cartas_jugadas = (
            self.ronda.cartas_jugadas(self.engine.jugador1.nombre) if self.ronda else []
        )
        cartas_en_mano = self.engine.jugador1.mano
        todas = [(c, True) for c in cartas_jugadas] + [(c, False) for c in cartas_en_mano]

        if todas:
            mini_w, mini_h = 50, 78
            total_w = len(todas) * (mini_w + 8) - 8
            sx = ANCHO // 2 - total_w // 2
            sy = py + 68
            for i, (c, jugada) in enumerate(todas):
                img = self.renderer.get(c, (mini_w, mini_h))
                if jugada:
                    img = img.copy()
                    overlay = pygame.Surface((mini_w, mini_h), pygame.SRCALPHA)
                    overlay.fill((0, 0, 0, 150))
                    img.blit(overlay, (0, 0))
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
        self._draw_panel(pygame.Rect(px, py, pw, ph))

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
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        ganador = self.engine.ganador_juego()
        if not ganador:
            return

        panel = pygame.Rect(0, 0, 460, 250)
        panel.center = (ANCHO // 2, ALTO // 2)
        self._draw_panel(panel)

        txt1 = self.font_titulo.render(f"¡{ganador.nombre} gana!", True, DORADO)
        self.screen.blit(txt1, (panel.centerx - txt1.get_width() // 2, panel.y + 32))

        j1, j2 = self.engine.jugador1, self.engine.jugador2
        marcador = self.font_grande.render(
            f"{j1.nombre} {j1.puntos}  —  {j2.puntos} {j2.nombre}", True, BLANCO
        )
        self.screen.blit(marcador, (panel.centerx - marcador.get_width() // 2, panel.y + 105))

        pygame.draw.line(self.screen, DORADO_SUAVE,
                         (panel.x + 40, panel.y + 165), (panel.right - 40, panel.y + 165), 1)

        # Parpadeo suave del hint
        alpha = 150 + int(105 * abs((time.time() % 1.6) / 0.8 - 1))
        txt3 = self.font_medio.render("Hacé click para jugar de nuevo", True, GRIS)
        txt3.set_alpha(alpha)
        self.screen.blit(txt3, (panel.centerx - txt3.get_width() // 2, panel.y + 185))
