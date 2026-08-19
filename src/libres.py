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

# Touches de navigation et d'édition, dans l'ordre où on aime les lire.
NAVIGATION = ["Espace", "⇥", "⏎", "⌫", "⌦", "⎋", "←", "→", "↑", "↓",
              "⇞", "⇟", "↖", "↘", "Aide"]

# Une touche qui ne sert qu'à modifier une autre frappe ne peut pas être la touche
# d'un raccourci ; les touches propres aux claviers japonais et les commandes de
# volume ne s'attribuent pas davantage.
# ⇪ (Verrouillage majuscule) est écarté avec les modificateurs : macOS ne le propose
# comme touche de raccourci nulle part, et presque aucun logiciel ne l'accepte.
EXCLUES = {"⇧", "⌃", "⌘", "⌥", "fn", "⇪",
           "RightCommand", "RightControl", "RightOption", "RightShift",
           "JIS_Eisu", "JIS_Kana", "JIS_KeypadComma",
           "ContextualMenu", "Volume +", "Volume -", "Silence"}


def univers(keyboard):
    """Toutes les touches attribuables, dans un ordre de lecture stable.

    Lettres, rangée du haut, autres touches imprimables, pavé numérique, touches de
    fonction, puis navigation. Le pavé numérique porte ses propres codes, distincts
    de la rangée du haut : « Pavé 4 » et « 4 » sont deux frappes différentes, et un
    raccourci attribué à l'une ne répond pas à l'autre.
    """
    touches, vus, libelles = [], set(), set()

    def ajouter(code):
        if code is None or code in vus:
            return
        nom = keyboard.label(code, 0)
        # Deux codes peuvent produire le même caractère : la disposition française
        # donne « @ » et « < » à la fois sur les touches ISO et sur des touches
        # propres aux claviers japonais, absentes d'un clavier français. Comme rien
        # ne les distingue à l'affichage, proposer les deux offrirait une combinaison
        # que personne ne peut viser. On garde la première rencontrée.
        if not nom or nom in EXCLUES or nom in libelles:
            return
        vus.add(code)
        libelles.add(nom)
        touches.append(code)

    for lettre in LETTRES:
        trouve = keyboard.by_char.get(lettre)
        if trouve and not trouve[1]:          # atteignable sans Maj
            ajouter(trouve[0])
    for code in RANGEE_HAUT:
        ajouter(code)
    # Le reste des touches imprimantes de la disposition — ponctuation comprise.
    for code in sorted(keyboard.by_code):
        if code not in keyboard.keypad:
            ajouter(code)
    for code in sorted(keyboard.keypad):
        ajouter(code)
    for code, nom in sorted(keyboard.names.items(),
                            key=lambda kv: int(kv[1][1:]) if kv[1][1:].isdigit() else 0):
        if nom.startswith("F") and nom[1:].isdigit():
            ajouter(code)
    par_nom = {nom: code for code, nom in keyboard.names.items()}
    for nom in NAVIGATION:
        ajouter(par_nom.get(nom))
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
    """Un seul tableau à double entrée, tous nombres de touches confondus.

    Les jeux de modificateurs font les colonnes, regroupés par nombre de touches ;
    les touches font les lignes. Une case porte la combinaison entière quand elle est
    libre, rien sinon — de sorte qu'elle se lise et se recopie telle quelle.

    Une ligne dont aucune case n'est libre est omise : la garder allongerait le
    tableau sans rien apprendre.

    La touche nomme la ligne par ce qu'elle produit **sans Maj**, mais la case affiche
    la combinaison telle que macOS l'écrit — avec Maj, c'est le caractère décalé qui
    apparaît, comme partout ailleurs dans cette page.

    Les combinaisons à cinq touches sont comptées à part, sans être listées : à cette
    longueur il en reste toujours, et un inventaire n'y apprend rien.
    """
    touches = univers(keyboard)
    colonnes, groupes = [], []
    for nombre in (1, 2, 3):
        jeux = _jeux_de_modificateurs(nombre)
        groupes.append({"touches": nombre + 1, "n": len(jeux)})
        colonnes.extend({"mods": render_modifiers(m), "masque": m} for m in jeux)

    lignes, totaux = [], {g["touches"]: 0 for g in groupes}
    for code in touches:
        nom = keyboard.label(code, 0)
        if not nom:
            continue
        cases, rang = [], 0
        for groupe in groupes:
            for colonne in colonnes[rang:rang + groupe["n"]]:
                masque = colonne["masque"]
                libelle = keyboard.label(code, masque)
                if not libelle or f"{masque}:k{code}" in occupees:
                    cases.append(None)
                else:
                    cases.append(render_modifiers(masque) + libelle)
                    totaux[groupe["touches"]] += 1
            rang += groupe["n"]
        if any(cases):
            lignes.append({"touche": nom, "cases": cases})

    for groupe in groupes:
        groupe["total"] = totaux[groupe["touches"]]

    quatre = _jeux_de_modificateurs(4)[0]
    cinq = sum(1 for code in touches
               if keyboard.label(code, quatre) and f"{quatre}:k{code}" not in occupees)

    return {"colonnes": [{"mods": c["mods"]} for c in colonnes],
            "groupes": groupes, "lignes": lignes, "cinq": cinq}
