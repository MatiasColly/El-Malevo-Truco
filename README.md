# El Malevo 🃏

Truco Argentino 1v1 en Python — sin flor, a 30 puntos.

---

## Roadmap

- [x] **Implementar el juego**
  - [x] Motor de reglas (envido, truco, bazas, puntaje)
  - [ ] Pulir detalles a medida que avanza el desarrollo
- [x] **Implementar UI**
  - [x] Interfaz CLI
  - [x] Interfaz gráfica (Pygame + cartas españolas SVG)
  - [ ] Pulir detalles a medida que avanza el desarrollo
- [ ] **Implementar IA básica** *(alias: IA de barrio)*
  Juega simulando decisiones por condicionales. Genera rangos de probabilidad para elegir acciones y cartas. Trata de cantar correctamente cuando tiene buen envido o buena mano, con un grado de aleatoriedad para jugadas impredecibles.
- [ ] **Implementar IA estadística** *(alias: Estudiante de Harvard)*
  Agrega funciones estadísticas para evaluar la calidad de la mano y el envido. Tiene en cuenta las cartas ya jugadas en la ronda.
- [ ] **Implementar Q-Learning**
  Modelo de Q-Learning clásico. Se evalúa contra las IAs anteriores para medir mejora.
- [ ] **Implementar Q-Learning mejorado**
  Se evalúan variantes (Deep Q-Network, CFR, NFSP, PPO u otras) y se implementa la más adecuada para el Truco.
- [ ] **Sumar métricas y análisis del oponente al modelo**
  El modelo registra las jugadas del oponente para estimar su estilo de juego y predecir mejores respuestas. Se acoplará a uno de los modelos de machine learning anteriores.

---

## Reglas del motor

### Modalidad

- **1 vs 1**, sin flor, **a 30 puntos**.
- Se alternan los roles de *mano* (juega primero) y *pie* cada ronda.

### Truco

| Canto | Puntos si quiero | Puntos si no quiero |
|-------|-----------------|---------------------|
| Truco | 2 | 1 |
| Retruco | 3 | 2 |
| Vale cuatro | 4 | 3 |

- Un jugador solo puede subir el truco si no fue él quien cantó el nivel actual.
- Al responder **no quiero**, la ronda termina y el cantor gana los puntos del nivel actual (no del siguiente).
- Si nadie canta truco, la ronda vale 1 punto.

### Envido

| Secuencia cantada | Puntos si quiero | Puntos si no quiero |
|-------------------|-----------------|---------------------|
| Envido | 2 | 1 |
| Real envido | 3 | 1 |
| Falta envido | * | 1 |
| Envido, envido | 4 | 2 |
| Envido, real envido | 5 | 2 |
| Envido, falta envido | * | 2 |
| Real envido, falta envido | * | 3 |
| Envido, envido, real envido | 7 | 5 |
| Envido, envido, falta envido | * | 4 |
| Envido, real envido, falta envido | * | 5 |
| Envido, envido, real envido, falta envido | * | 7 |

**(*) Falta envido** — los puntos son `30 − máximo(puntaje_j1, puntaje_j2)`. Cubre tanto el caso de *las malas* (donde equivale al partido completo) como el de *las buenas* (donde equivale a los puntos que le faltan al que va ganando para llegar a 30). Quien acepta el falta envido le da al ganador exactamente lo necesario para cerrar el partido.

- El envido **solo se puede cantar en la primera baza**, antes de que alguien juegue su segunda carta.
- El cálculo de puntos de envido es automático; **no se puede mentir** con los puntos.
- En caso de empate de envido, gana el jugador que es **mano**.

### Bazas y resolución de ronda

- Cada ronda tiene hasta 3 bazas. Gana la ronda quien gane **2 bazas**.
- **Parda** (empate de baza): el siguiente turno corresponde al jugador que es mano.
- **3 bazas pardas** → gana la ronda el jugador que es **mano**.
- **Baza 1 parda + baza 2 ganada**: gana la ronda quien ganó la baza 2.
- **1-1 + baza 3 parda**: gana la ronda quien ganó la primera baza; si la primera también fue parda, gana el jugador que es mano.

### Irse al mazo

- Un jugador puede irse al mazo en cualquier momento.
- Si se va al mazo **en primera baza sin que se haya cantado envido**, el oponente gana **1 punto de envido**; luego la ronda termina y el oponente gana **1 punto de truco** = **2 puntos en total**.
- Si ya se cantó envido antes de irse al mazo, el punto de envido no se vuelve a otorgar.

### Fin de partida

- Gana el primero en llegar a **30 puntos**.
- La partida termina **inmediatamente** al llegar a 30, sin esperar que finalice la ronda en curso.

---

## Instalación y uso

```bash
pip install pygame requests
python download_assets.py   # descarga las cartas SVG (solo la primera vez)
python main.py
```

Para cambiar entre GUI y CLI editar `config.py`:

```python
INTERFAZ = "gui"   # o "cli"
```

---

## Créditos de assets

Cartas españolas SVG: [gjenkins20/spanish-playing-cards-svg](https://github.com/gjenkins20/spanish-playing-cards-svg) — licencia CC BY-SA 3.0.
