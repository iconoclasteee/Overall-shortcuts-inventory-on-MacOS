"""Modèle commun à toutes les sources de raccourcis.

Un raccourci vient d'endroits qui ne parlent pas la même langue : un menu expose un
caractère ("V"), Keyboard Maestro un code de touche brut (9) avec un masque Carbon,
Apple un masque NSEvent. Pour répondre à « où cette combinaison est-elle utilisée ? »,
il faut d'abord les ramener tous à une même clé de comparaison.

Cette clé est le **code de touche physique** plus les modificateurs. Le passage
caractère → code de touche se fait avec la disposition clavier réellement active
(`data/keymap.json`, produit par le binaire) : sur AZERTY, le code 41 produit « m »
et non « ; », donc une table ANSI donnerait des correspondances fausses.
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tables import (function_key_chars, keycode_labels, keycode_symbols,
                    keypad_codes)

ROOT = Path(__file__).parent.parent

# Représentation interne des modificateurs. Volontairement distincte des masques
# NSEvent, Carbon et AX : chaque source a le sien, on convertit vers celui-ci.
SHIFT, CTRL, ALT, CMD, FN = 1, 2, 4, 8, 16
MOD_SYMBOLS = [(CTRL, "⌃"), (ALT, "⌥"), (SHIFT, "⇧"), (CMD, "⌘"), (FN, "fn")]  # ordre Apple


def from_nsevent(mask):
    """Masque NSEvent.ModifierFlags (plists Apple, Alfred)."""
    mask = mask or 0
    return ((SHIFT if mask & 0x020000 else 0) | (CTRL if mask & 0x040000 else 0)
            | (ALT if mask & 0x080000 else 0) | (CMD if mask & 0x100000 else 0)
            | (FN if mask & 0x800000 else 0))


def from_carbon(mask):
    """Masque Carbon (Keyboard Maestro, CleanShot X, RegisterEventHotKey)."""
    mask = mask or 0
    return ((SHIFT if mask & 512 else 0) | (CTRL if mask & 4096 else 0)
            | (ALT if mask & 2048 else 0) | (CMD if mask & 256 else 0))


def from_ax(mask):
    """Masque d'un élément de menu accessible.

    Command y est implicite : c'est le bit 0x08 qui l'*exclut*, pas qui l'ajoute.
    Le bit 0x10 porte la touche Globe (fn) : macOS s'en sert pour les raccourcis
    modernes tels que 🌐F pour le plein écran. L'ignorer indexait ces raccourcis
    sous la touche nue, où ils se mélangeaient à de vrais raccourcis sans modificateur.
    """
    mask = mask or 0
    return ((SHIFT if mask & 0x01 else 0) | (ALT if mask & 0x02 else 0)
            | (CTRL if mask & 0x04 else 0) | (0 if mask & 0x08 else CMD)
            | (FN if mask & 0x10 else 0))


def render_modifiers(mods):
    return "".join(sym for bit, sym in MOD_SYMBOLS if mods & bit)


class Keyboard:
    """Disposition clavier active : code de touche ↔ caractère, dans les deux sens."""

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
        # Touches que macOS désigne par un point de code de la zone privée plutôt que
        # par un caractère : c'est ainsi qu'il écrit une redéfinition visant F5 ou une
        # flèche. Sans cette passerelle, elles restent irrésolubles.
        par_libelle = {nom: code for code, nom in self.names.items()}
        self.by_function = {car: par_libelle[nom]
                            for car, nom in function_key_chars().items()
                            if nom in par_libelle}
        self.symboles = keycode_symbols()  # symboles officiels (⌤, ⌧, ⏎)
        keypad = keypad_codes()
        self.keypad = keypad
        self.by_char = {}
        # Deux arbitrages, dans cet ordre.
        # 1. Le niveau non décalé prime : si deux touches produisent le même caractère,
        #    celle qui l'atteint sans Maj est la bonne réponse.
        # 2. À niveau égal, le plus petit code de touche gagne. Sans cela, une touche
        #    absente du clavier l'emporterait : la disposition française donne « @ » et
        #    « < » à la fois sur les touches ISO et sur des touches propres aux claviers
        #    japonais. Le caractère nu et le caractère décalé de la MÊME touche
        #    désigneraient alors deux codes différents, et deux raccourcis identiques
        #    cesseraient de se comparer égaux.
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
        """Libellé d'affichage. Avec Maj, Apple montre le caractère décalé (⇧⌘4)."""
        # Le pavé numérique produit les mêmes caractères que la rangée du haut :
        # afficher « 1 » pour l'un et pour l'autre rendrait les deux frappes
        # indiscernables. Son nom prime donc sur son caractère.
        if code in self.keypad:
            # Le caractère vient de la disposition, le préfixe dit d'où il est tapé.
            pair = self.by_code.get(code)
            if pair and pair[0].strip():
                return f"Pavé {pair[0]}"
            symbole = self.symboles.get(code) or self.names.get(code)
            return f"Pavé {symbole}" if symbole else None
        pair = self.by_code.get(code)
        if pair:
            text = pair[1] if mods & SHIFT else pair[0]
            # Une touche peut produire un caractère invisible (l'espace) : son nom
            # est alors plus parlant que le caractère lui-même.
            if text.strip():
                return text.upper()
        return self.names.get(code)

    def code_for(self, char):
        """Code de touche produisant ce caractère, ou None si hors disposition."""
        found = self.by_char.get((char or "").lower())
        return found[0] if found else None

    def resoudre(self, char):
        """(code, Maj nécessaire) pour produire ce caractère sur cette disposition.

        Une app déclare son raccourci par un caractère — « 2 » — sans dire quelle
        frappe le produit. En AZERTY il faut Maj+é : la frappe réelle comporte donc
        un Maj que le menu n'affiche pas.
        """
        found = self.by_char.get((char or "").lower())
        if found:
            return found
        # Une touche de fonction ne se frappe jamais avec Maj : le second membre est
        # faux par construction, pas par défaut.
        fonction = self.by_function.get(char or "")
        return (fonction, False) if fonction is not None else (None, False)


@dataclass
class Binding:
    """Un raccourci, quelle que soit sa provenance."""
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
        # Clé de comparaison. Un raccourci sans code de touche ni glyphe n'est
        # comparable à rien : il reçoit une clé unique pour ne jamais faussement
        # entrer en conflit.
        if self.code is not None:
            self.cle = f"{self.mods}:k{self.code}"
        elif self.glyphe is not None:
            self.cle = f"{self.mods}:g{self.glyphe}"
        else:
            self.cle = f"{self.mods}:?{self.combo}"


# Étages d'interception, du plus prioritaire au moins prioritaire. Modèle repris de
# HotkeyClash (GPL-2.0) : une touche remonte cette pile et le premier étage qui la
# réclame l'avale. L'ordre est une heuristique fiable, pas une garantie — à égalité
# d'étage, c'est l'ordre d'enregistrement qui tranche, et il n'est écrit nulle part.
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
