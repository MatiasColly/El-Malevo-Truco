"""
Descarga las cartas españolas a assets/cards.

Baraja: Heraclio Fournier "Vitoria" (diseño de Augusto Rius, 1889).
Fuente: fotos de Wikimedia Commons por Cantabrucu — CC BY-SA 4.0.
Las fotos vienen sobre un paño verde, así que el script recorta
automáticamente cada carta y la escala a un tamaño uniforme.

Dorso: reverso clásico Fournier ("Atras.png" de Basquetteur y Germarquezm
en Wikimedia Commons) — CC BY-SA 3.0.
"""

import io
import os
import sys
from urllib.parse import quote

import numpy as np
import requests

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402  (necesita SDL_VIDEODRIVER seteado antes)

DEST_DIR = os.path.join(os.path.dirname(__file__), "assets", "cards")

COMMONS_FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"
USER_AGENT = "ElMalevo/1.0 (https://github.com/MatiasColly/El-Malevo)"

DORSO_URL = f"{COMMONS_FILEPATH}Atras.png"

SUIT_MAP = {
    "oro": "Oros",
    "copa": "Copas",
    "espada": "Espadas",
    "basto": "Bastos",
}

# Truco usa 40 cartas: 1-7, 10(sota), 11(caballo), 12(rey)
NUMEROS_TRUCO = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]

ANCHO_DESCARGA = 800  # ancho del thumbnail pedido a Commons
ALTO_FINAL = 560      # alto de la carta procesada


def url_carta(numero: int, palo_commons: str) -> str:
    nombre = f"Heraclio Fournier {numero} {palo_commons}.jpg"
    return f"{COMMONS_FILEPATH}{quote(nombre)}?width={ANCHO_DESCARGA}"


def recortar_carta(surf: pygame.Surface) -> pygame.Surface:
    """Recorta la carta descartando el paño verde de la foto.

    Como las fotos pueden estar levemente rotadas, no alcanza con la caja
    envolvente: se recorta cada lado hacia adentro hasta encontrar una fila o
    columna que sea casi toda blanca (el margen de la carta), lo que deja el
    rectángulo inscripto dentro de la carta.
    """
    arr = pygame.surfarray.array3d(surf).astype(int)  # (w, h, 3)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # Blanco de la carta: brillo alto y sin tinte verdoso (el paño brillante
    # llega a valores altos pero siempre con el canal verde dominante)
    blanco = (r > 110) & (b > 100) & (g - r < 30)

    # Caja envolvente aproximada de la carta
    xs, ys = np.where(blanco)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    sub = blanco[x0:x1 + 1, y0:y1 + 1]

    # Avanzar desde cada borde hasta una fila/columna mayormente blanca.
    # El umbral se ajusta al máximo real por si la carta ocupa poco encuadre.
    col_frac = sub.mean(axis=1)
    row_frac = sub.mean(axis=0)
    umbral_c = min(0.85, col_frac.max() * 0.9)
    umbral_r = min(0.85, row_frac.max() * 0.9)
    cx0 = int(np.argmax(col_frac > umbral_c))
    cx1 = len(col_frac) - 1 - int(np.argmax(col_frac[::-1] > umbral_c))
    cy0 = int(np.argmax(row_frac > umbral_r))
    cy1 = len(row_frac) - 1 - int(np.argmax(row_frac[::-1] > umbral_r))

    # Inset final chico para limpiar el borde
    ix = int((cx1 - cx0) * 0.012)
    iy = int((cy1 - cy0) * 0.01)
    rect = pygame.Rect(
        x0 + cx0 + ix, y0 + cy0 + iy,
        (cx1 - cx0) - 2 * ix, (cy1 - cy0) - 2 * iy,
    )
    return surf.subsurface(rect).copy()


def descargar_carta(numero: int, palo_es: str, palo_commons: str) -> bool:
    dest = os.path.join(DEST_DIR, f"{numero}_{palo_es}.jpg")
    if os.path.exists(dest):
        return True

    url = url_carta(numero, palo_commons)
    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        surf = pygame.image.load(io.BytesIO(resp.content), "carta.jpg").convert(24)
        carta = recortar_carta(surf)
        w, h = carta.get_size()
        final = pygame.transform.smoothscale(
            carta, (int(w * ALTO_FINAL / h), ALTO_FINAL)
        )
        pygame.image.save(final, dest)
        return True
    except Exception as e:
        print(f"\n  Error con {url}: {e}")
        return False


def descargar_dorso() -> bool:
    dest = os.path.join(DEST_DIR, "dorso.png")
    if os.path.exists(dest):
        return True
    try:
        resp = requests.get(DORSO_URL, timeout=15, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"\n  Error descargando dorso: {e}")
        return False


def main() -> None:
    os.makedirs(DEST_DIR, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))

    total = len(NUMEROS_TRUCO) * len(SUIT_MAP) + 1
    ok = 0

    print(f"Descargando {total} cartas a {DEST_DIR}...")

    if descargar_dorso():
        ok += 1

    for palo_es, palo_commons in SUIT_MAP.items():
        for numero in NUMEROS_TRUCO:
            if descargar_carta(numero, palo_es, palo_commons):
                ok += 1
                sys.stdout.write(f"\r  {ok}/{total}")
                sys.stdout.flush()

    print(f"\n  Listo: {ok}/{total} cartas descargadas.")


if __name__ == "__main__":
    main()
