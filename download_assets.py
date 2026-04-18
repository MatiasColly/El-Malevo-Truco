"""
Descarga las cartas españolas en SVG desde GitHub.

Fuente: gjenkins20/spanish-playing-cards-svg (CC BY-SA 3.0)
"""

import os
import sys
import requests

REPO_BASE = "https://raw.githubusercontent.com/gjenkins20/spanish-playing-cards-svg/main"
DEST_DIR = os.path.join(os.path.dirname(__file__), "assets", "cards")

SUIT_MAP = {
    "espada": "swords",
    "basto": "clubs",
    "oro": "coins",
    "copa": "cups",
}

# Truco usa 40 cartas: 1-7, 10(sota), 11(caballo), 12(rey)
NUMEROS_TRUCO = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12]


def nombre_archivo_remoto(numero: int, palo_en: str) -> str:
    return f"card_{palo_en}_{numero:02d}.svg"


def nombre_archivo_local(numero: int, palo_es: str) -> str:
    return f"{numero}_{palo_es}.svg"


def descargar_carta(numero: int, palo_es: str, palo_en: str) -> bool:
    url = f"{REPO_BASE}/{nombre_archivo_remoto(numero, palo_en)}"
    dest = os.path.join(DEST_DIR, nombre_archivo_local(numero, palo_es))

    if os.path.exists(dest):
        return True

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"  Error descargando {url}: {e}")
        return False


def descargar_dorso() -> bool:
    url = f"{REPO_BASE}/card_back.svg"
    dest = os.path.join(DEST_DIR, "dorso.svg")
    if os.path.exists(dest):
        return True
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(resp.content)
        return True
    except Exception as e:
        print(f"  Error descargando dorso: {e}")
        return False


def main() -> None:
    os.makedirs(DEST_DIR, exist_ok=True)
    total = len(NUMEROS_TRUCO) * len(SUIT_MAP) + 1
    ok = 0

    print(f"Descargando {total} cartas a {DEST_DIR}...")

    if descargar_dorso():
        ok += 1

    for palo_es, palo_en in SUIT_MAP.items():
        for numero in NUMEROS_TRUCO:
            if descargar_carta(numero, palo_es, palo_en):
                ok += 1
                sys.stdout.write(f"\r  {ok}/{total}")
                sys.stdout.flush()

    print(f"\n  Listo: {ok}/{total} cartas descargadas.")


if __name__ == "__main__":
    main()
