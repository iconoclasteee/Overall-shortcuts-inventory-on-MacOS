"""Combinations no shortcut claims.

The space of combinations is vast; enumerating all of it would help nobody. Three limits
reduce it to what can actually be assigned:

* **Four modifiers** — ⌃ ⌥ ⇧ ⌘. The Globe key is left out: macOS reserves most of it, and
  almost no software lets you assign it.
* **Physical keys**, named by what they produce without Shift. On a French keyboard the
  number row therefore reads "& é \" ' (": that is the actual keystroke, and showing it
  any other way would describe a shortcut that does not exist.
* **Letters, top row, function keys and arrows** — what software commonly accepts as a
  shortcut key.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model import ALT, CMD, CTRL, SHIFT, render_modifiers

MODIFICATEURS = [("⌃", CTRL), ("⌥", ALT), ("⇧", SHIFT), ("⌘", CMD)]

# Top row of an ANSI/ISO keyboard, in Apple's key-code order.
RANGEE_HAUT = [18, 19, 20, 21, 23, 22, 26, 28, 25, 29]
LETTRES = "abcdefghijklmnopqrstuvwxyz"

# Navigation and editing keys, in the order one likes to read them.
NAVIGATION = ["Espace", "⇥", "⏎", "⌫", "⌦", "⎋", "←", "→", "↑", "↓",
              "⇞", "⇟", "↖", "↘", "Aide"]

# A key whose only job is to modify another keystroke cannot be a shortcut's key; keys
# specific to Japanese keyboards and volume controls cannot be assigned either.
# ⇪ (Caps Lock) is left out along with the modifiers: macOS offers it as a shortcut key
# nowhere, and almost no software accepts it.
EXCLUES = {"⇧", "⌃", "⌘", "⌥", "fn", "⇪",
           "RightCommand", "RightControl", "RightOption", "RightShift",
           "JIS_Eisu", "JIS_Kana", "JIS_KeypadComma",
           "ContextualMenu", "Volume +", "Volume -", "Silence"}


def univers(keyboard):
    """Every assignable key, in a stable reading order.

    Letters, top row, other printable keys, numeric keypad, function keys, then
    navigation. The numeric keypad carries its own codes, distinct from the top row:
    "Keypad 4" and "4" are two different keystrokes, and a shortcut assigned to one does
    not answer the other.
    """
    touches, vus, libelles = [], set(), set()

    def ajouter(code):
        if code is None or code in vus:
            return
        nom = keyboard.label(code, 0)
        # Two codes can produce the same character: the French layout exposes "@" and "<"
        # both on the ISO keys and on keys specific to Japanese keyboards, absent from a
        # French one. Since nothing tells them apart on screen, offering both would offer a
        # combination nobody can aim at. We keep the first one encountered.
        if not nom or nom in EXCLUES or nom in libelles:
            return
        vus.add(code)
        libelles.add(nom)
        touches.append(code)

    for lettre in LETTRES:
        trouve = keyboard.by_char.get(lettre)
        if trouve and not trouve[1]:          # reachable without Shift
            ajouter(trouve[0])
    for code in RANGEE_HAUT:
        ajouter(code)
    # The rest of the layout's printing keys — punctuation included.
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
    """Every combination of `nombre` modifiers, in Apple's order."""
    jeux = []
    for masque in range(1, 1 << len(MODIFICATEURS)):
        bits = [MODIFICATEURS[i] for i in range(len(MODIFICATEURS)) if masque & (1 << i)]
        if len(bits) == nombre:
            jeux.append(sum(bit for _, bit in bits))
    return jeux


def calculer(keyboard, occupees):
    """One single cross-table, all key counts together.

    Modifier sets form the columns, grouped by key count; keys form the rows. A cell
    carries the whole combination when it is free, and nothing otherwise — so that it can
    be read and copied as is.

    A row with no free cell at all is left out: keeping it would lengthen the table without
    teaching anything.

    The key names its row by what it produces **without Shift**, but the cell shows the
    combination the way macOS writes it — with Shift, the shifted character is what
    appears, as everywhere else in this page.

    Five-key combinations are counted separately rather than listed: at that length there
    are always some left, and an inventory of them teaches nothing.
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
