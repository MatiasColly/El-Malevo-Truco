"""
Configuración del juego El Malevo — Truco Argentino.

Cambiar INTERFAZ para elegir modo de juego:
  - "cli"  → interfaz de terminal (texto)
  - "gui"  → interfaz gráfica (Pygame)
"""

INTERFAZ = "gui"

"""
Cambiar la ia utilizada para jugador vs cpu:
  - "aleatoria" → IA aleatoria: elige acciones al azar (para testing y comparación).
  - "barrio_v1"  → IA de Barrio: IA simple basada en reglas, con heurísticas para jugar el truco y el envido.
"""

IA_MODEL = "barrio_v1"

# ── Arena (python arena.py) ──────────────────────────────

ARENA_PARTIDAS = 1000
ARENA_IA_1 = "barrio_v1"
ARENA_IA_2 = "aleatoria"
ARENA_ELO_K = 32
