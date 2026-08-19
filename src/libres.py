"""Combinaisons qu'aucun raccourci ne revendique.

L'espace des combinaisons est immense ; en énumérer la totalité ne rendrait pas
service. Trois bornes le ramènent à ce qui est réellement attribuable :

* **Quatre modificateurs** — ⌃ ⌥ ⇧ ⌘. La touche Globe est écartée : macOS s'en
  réserve l'essentiel et presque aucun outil ne permet de l'attribuer.
* **Des touches physiques**, désignées par ce qu'elles produisent sans Maj. Sur un
  clavier français, la rangée des chiffres donne donc « & é " ' ( » : c'est la
  frappe réelle, et l'afficher autrement décrirait un raccourci qui n'existe pas.
* **Lettres, rangée du haut, touches de fonction et flèches** — ce qu'un logiciel
  accepte couramment comme touche de raccourci.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model import ALT, CMD, CTRL, SHIFT, render_modifiers

MODIFICATEURS = [("⌃", CTRL), ("⌥", ALT), ("⇧", SHIFT), ("⌘", CMD)]

# Rangée du haut d'un clavier ANSI/ISO, dans l'ordre des codes de touches d'Apple.
RANGEE_HAUT = [18, 19, 20, 21, 23, 22, 26, 28, 25, 29]
LETTRES = "abcdefghijklmnopqrstuvwxyz"
FLECHES = [123, 124, 125, 126]


def univers(keyboard):
    """Touches candidates, dans l'ordre où on veut les lire."""
    touches = []
    vus = set()

    def ajouter(code):
        if code is None or code in vus or code not in keyboard.by_code:
            return
        vus.add(code)
        touches.append(code)

    for lettre in LETTRES:
        trouve = keyboard.by_char.get(lettre)
        if trouve and not trouve[1]:          # atteignable sans Maj
            ajouter(trouve[0])
    for code in RANGEE_HAUT:
        ajouter(code)
    for code, nom in sorted(keyboard.names.items(),
                            key=lambda kv: int(kv[1][1:]) if kv[1][1:].isdigit() else 99):
        if nom.startswith("F") and nom[1:].isdigit():
            vus.add(code)
            touches.append(code)
    for code in FLECHES:
        vus.add(code)
        touches.append(code)
    return touches


def _jeux_de_modificateurs(nombre):
    """Toutes les combinaisons de `nombre` modificateurs, dans l'ordre d'Apple."""
    jeux = []
    for masque in range(1, 1 << len(MODIFICATEURS)):
        bits = [MODIFICATEURS[i] for i in range(len(MODIFICATEURS)) if masque & (1 << i)]
        if len(bits) == nombre:
            jeux.append(sum(bit for _, bit in bits))
    return jeux


def calculer(keyboard, occupees):
    """Sections « n touches », chacune sous forme de tableau à double entrée.

    Les jeux de modificateurs font les colonnes, les touches les lignes. Une case
    porte la combinaison entière quand elle est libre, rien sinon — de sorte qu'elle
    se lise et se recopie telle quelle.

    Une ligne dont aucune case n'est libre est omise : la garder allongerait le
    tableau sans rien apprendre.

    La touche nomme la ligne par ce qu'elle produit **sans Maj**, mais la case
    affiche la combinaison telle que macOS l'écrit — avec Maj, c'est le caractère
    décalé qui apparaît, comme partout ailleurs dans cette page.
    """
    touches = univers(keyboard)
    sections = []
    for nombre in (1, 2, 3, 4):
        jeux = _jeux_de_modificateurs(nombre)
        colonnes = [render_modifiers(mods) for mods in jeux]
        lignes, total = [], 0
        for code in touches:
            nom = keyboard.label(code, 0)
            if not nom:
                continue
            cases = []
            for mods in jeux:
                libelle = keyboard.label(code, mods)
                if not libelle or f"{mods}:k{code}" in occupees:
                    cases.append(None)
                else:
                    cases.append(render_modifiers(mods) + libelle)
            libres = sum(1 for c in cases if c)
            if libres:
                lignes.append({"touche": nom, "cases": cases})
                total += libres
        sections.append({"touches": nombre + 1, "total": total,
                         "colonnes": colonnes, "lignes": lignes})
    return sections
