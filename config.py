"""
Configuración del juego El Malevo — Truco Argentino.

Cambiar INTERFAZ para elegir modo de juego:
  - "cli"  → interfaz de terminal (texto)
  - "gui"  → interfaz gráfica (Pygame)
"""

INTERFAZ = "gui"

"""
Registro de IAs disponibles.

Cada entrada mapea un nombre corto al path completo de la clase (módulo.Clase).
Para agregar una IA nueva, solo hay que agregar una línea acá.
"""

IA_REGISTRY: dict[str, str] = {
    "aleatoria":  "truco.AI.ai_random.RandomAI",
    "barrio_v1":  "truco.AI.ai_barrio_v1.AiBarrioV1",
    "barrio_agresiva":  "truco.AI.ai_barrio_agresiva.AiBarrioAgresiva",
    "barrio_v2": "truco.AI.ai_barrio_v2.AiBarrioV2",
    "barrio_v3": "truco.AI.ai_barrio_v3.AiBarrioV3",
}

# IA utilizada para jugador vs CPU (debe ser una clave de IA_REGISTRY)
IA_MODEL = "barrio_v3"

# -- Arena (python arena.py) ------------------------------

ARENA_PARTIDAS = 1000
ARENA_IA_1 = "barrio_v2"
ARENA_IA_2 = "barrio_v3"
ARENA_ELO_K = 5

# -- Round Robin (python round_robin.py) ------------------

ROUND_ROBIN_IAS: list[str] = ["aleatoria", "barrio_v1", "barrio_agresiva", "barrio_v2", "barrio_v3"]
ROUND_ROBIN_PARTIDAS = 1000  # partidas por enfrentamiento
ROUND_ROBIN_ELO_K = 5

# -- Helper: instanciar IA por nombre ---------------------

def crear_ia(nombre: str):
    """Instancia una IA a partir de su nombre en IA_REGISTRY."""
    classpath = IA_REGISTRY.get(nombre)
    if classpath is None:
        disponibles = list(IA_REGISTRY.keys())
        raise ValueError(f"IA desconocida: {nombre!r}. Disponibles: {disponibles}")

    modulo_path, clase_nombre = classpath.rsplit(".", 1)

    import importlib
    modulo = importlib.import_module(modulo_path)
    cls = getattr(modulo, clase_nombre)
    return cls()
