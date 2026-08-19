"""Model shared by every source of shortcuts.

A shortcut comes from places that do not speak the same language: a menu exposes a
character ("V"), Keyboard Maestro a raw key code (9) with a Carbon mask, Apple an NSEvent
mask. Answering "where is this combination used?" means first bringing them all down to
one comparison key.

That key is the **physical key code** plus the modifiers. Going from character to key code
uses the keyboard layout actually in service (`data/keymap.json`, produced by the binary):
on AZERTY, code 41 produces "m" and not ";", so an ANSI table would give wrong matches.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tables import (function_key_chars, keycode_labels, keycode_symbols,
                    keypad_codes)

ROOT = Path(__file__).parent.parent

# Internal representation of the modifiers. Deliberately distinct from the NSEvent, Carbon
# and AX masks: each source has its own, and everything is converted into this one.
SHIFT, CTRL, ALT, CMD, FN = 1, 2, 4, 8, 16
MOD_SYMBOLS = [(CTRL, "⌃"), (ALT, "⌥"), (SHIFT, "⇧"), (CMD, "⌘"), (FN, "fn")]  # ordre Apple


def from_nsevent(mask):
    """NSEvent.ModifierFlags mask (Apple plists, Alfred)."""
    mask = mask or 0
    return ((SHIFT if mask & 0x020000 else 0) | (CTRL if mask & 0x040000 else 0)
            | (ALT if mask & 0x080000 else 0) | (CMD if mask & 0x100000 else 0)
            | (FN if mask & 0x800000 else 0))


def from_carbon(mask):
    """Carbon mask (Keyboard Maestro, CleanShot X, RegisterEventHotKey)."""
    mask = mask or 0
    return ((SHIFT if mask & 512 else 0) | (CTRL if mask & 4096 else 0)
            | (ALT if mask & 2048 else 0) | (CMD if mask & 256 else 0))


def from_ax(mask):
    """Mask of an accessible menu item.

    Command is implicit here: bit 0x08 is what *excludes* it, not what adds it. Bit 0x10
    carries the Globe (fn) key: macOS uses it for modern shortcuts such as 🌐F for full
    screen. Ignoring it indexed those shortcuts under the bare key, where they mixed with
    genuine modifier-less shortcuts.
    """
    mask = mask or 0
    return ((SHIFT if mask & 0x01 else 0) | (ALT if mask & 0x02 else 0)
            | (CTRL if mask & 0x04 else 0) | (0 if mask & 0x08 else CMD)
            | (FN if mask & 0x10 else 0))


def render_modifiers(mods):
    return "".join(sym for bit, sym in MOD_SYMBOLS if mods & bit)


class Keyboard:
    """Active keyboard layout: key code ↔ character, both ways."""

    def __init__(self, path=None):
        chemin = path or ROOT / "out" / "keymap.json"
        if not Path(chemin).exists():
            raise SystemExit(
                f"Disposition clavier introuvable : {chemin}\n"
                "Elle est produite par le moissonneur. Lance ./run.sh --sources,\n"
                "ou directement : bin/ShortcutHarvester.app/Contents/MacOS/"
                "ShortcutHarvester --keymap > out/keymap.json")
        raw = json.loads(Path(chemin).read_text(encoding="utf-8"))
        touches = raw.get("touches", raw)
        self.disposition = raw.get("disposition", "")
        self.identifiant = raw.get("identifiant", "")
        self.by_code = {int(k): v for k, v in touches.items()}
        self.names = keycode_labels()      # libellés des touches sans caractère (F5, ←)
        # Keys macOS names by a private-use code point rather than by a character: that is
        # how it writes a redefinition aimed at F5 or an arrow. Without this bridge they
        # stay unresolvable.
        par_libelle = {nom: code for code, nom in self.names.items()}
        self.by_function = {car: par_libelle[nom]
                            for car, nom in function_key_chars().items()
                            if nom in par_libelle}
        self.symboles = keycode_symbols()  # symboles officiels (⌤, ⌧, ⏎)
        keypad = keypad_codes()
        self.keypad = keypad
        self.by_char = {}
        # Two tie-breaks, in this order.
        # 1. The unshifted level wins: if two keys produce the same character, the one that
        #    reaches it without Shift is the right answer.
        # 2. At equal level, the lower key code wins. Without this, a key absent from the
        #    keyboard would prevail: the French layout exposes "@" and "<" both on the ISO
        #    keys and on keys specific to Japanese keyboards. The bare character and the
        #    shifted character of the SAME key would then point at two different codes, and
        #    two identical shortcuts would stop comparing equal.
        for code in sorted(self.by_code):
            if code in keypad:
                continue
            self.by_char.setdefault(self.by_code[code][1].lower(), (code, True))
        for code in sorted(self.by_code):
            if code in keypad:
                continue
            plain = self.by_code[code][0].lower()
            if plain not in self.by_char or self.by_char[plain][1]:
                self.by_char[plain] = (code, False)

    def label(self, code, mods):
        """Display label. With Shift, Apple shows the shifted character (⇧⌘4)."""
        # The numeric keypad produces the same characters as the top row: showing "1" for
        # both would make the two keystrokes indistinguishable. Its name therefore wins
        # over its character.
        if code in self.keypad:
            # The character comes from the layout, the prefix says where it is typed.
            pair = self.by_code.get(code)
            if pair and pair[0].strip():
                return f"Pavé {pair[0]}"
            symbole = self.symboles.get(code) or self.names.get(code)
            return f"Pavé {symbole}" if symbole else None
        pair = self.by_code.get(code)
        if pair:
            text = pair[1] if mods & SHIFT else pair[0]
            # A key can produce an invisible character (space): its name then speaks more
            # clearly than the character itself.
            if text.strip():
                return text.upper()
        return self.names.get(code)

    def code_for(self, char):
        """Key code producing this character, or None if outside the layout."""
        found = self.by_char.get((char or "").lower())
        return found[0] if found else None

    def resoudre(self, char):
        """(code, Shift needed) to produce this character on this layout.

        An app declares its shortcut by a character — "2" — without saying which keystroke
        produces it. On AZERTY that takes Shift+é: the real keystroke therefore carries a
        Shift the menu does not display.
        """
        found = self.by_char.get((char or "").lower())
        if found:
            return found
        # A function key is never typed with Shift: the second member is false by
        # construction, not by default.
        fonction = self.by_function.get(char or "")
        return (fonction, False) if fonction is not None else (None, False)


@dataclass
class Binding:
    """One shortcut, whatever its origin."""
    mods: int
    combo: str                    # libellé affichable, ex. "⇧⌘4"
    action: str                   # ce que ça fait
    source: str                   # "systeme" | "menu" | "outil"
    couche: str                   # étage d'interception (voir COUCHES)
    portee: str                   # "systeme" | "app" | "app_externe" | "inconnu"
    proprietaire: str             # macOS, Safari, Alfred…
    bundle_id: str = ""
    code: int | None = None       # code de touche physique, si connu
    glyphe: int | None = None     # glyphe de menu, pour les touches sans caractère
    actif: bool = True
    detail: str = ""
    double: bool = False          # double frappe sur un modificateur, pas une combinaison
    menu: str = ""                # menu de premier niveau, pour les éléments de menu
    ordre: int = 0                # rang d'apparition dans la barre de menu
    cle: str = field(default="", init=False)

    def __post_init__(self):
        # Comparison key. A shortcut with neither key code nor glyph is comparable to
        # nothing: it gets a unique key so it can never conflict spuriously.
        if self.code is not None:
            self.cle = f"{self.mods}:k{self.code}"
        elif self.glyphe is not None:
            self.cle = f"{self.mods}:g{self.glyphe}"
        else:
            self.cle = f"{self.mods}:?{self.combo}"


# Interception layers, from highest priority to lowest. Model taken from HotkeyClash
# (GPL-2.0): a key travels up this stack and the first layer that claims it swallows it.
# The order is a reliable heuristic, not a guarantee — at equal layer, registration order
# decides, and that is written nowhere.
COUCHES = {
    "pilote":      (0, "Pilote clavier virtuel (Karabiner) — avant macOS et avant toute app.",
                       "Virtual keyboard driver (Karabiner) — before macOS and before any app."),
    "capture":     (1, "Capture d'événements (Keyboard Maestro, BetterTouchTool) — voit la touche avant les raccourcis système et peut l'avaler.",
                       "Event tap (Keyboard Maestro, BetterTouchTool) — sees the key before system shortcuts and can swallow it."),
    "systeme":     (2, "Raccourci système macOS — passe devant les menus d'app, mais une capture d'événements peut le prendre avant.",
                       "macOS system shortcut — beats app menus, but an event tap can take the key first."),
    "global":      (3, "Raccourci global Carbon (Alfred, CleanShot X) — actif partout, si rien en dessous n'a réclamé la touche.",
                       "Carbon global hotkey (Alfred, CleanShot X) — fires everywhere, if nothing below claimed the key."),
    "autre":       (4, "Outil toujours actif dont on ne connaît pas le point d'accroche.",
                       "Always-on tool whose hook point is unknown."),
    "menu":        (5, "Élément de menu — actif seulement quand l'app est au premier plan.",
                       "Menu item — live only while that app is frontmost."),
}


def rang(couche):
    return COUCHES.get(couche, COUCHES["autre"])[0]
