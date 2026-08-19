"""Tables de correspondance touches/glyphes — extraites de macOS, jamais écrites à la main.

Source unique de vérité : le fichier BridgeSupport de HIToolbox, présent sur toute
machine macOS. Il contient les énumérations Carbon officielles :
  - kVK_*      : codes de touches virtuels (indépendants de la disposition clavier)
  - kMenu*Glyph: glyphes utilisés par les menus pour les touches non imprimables

On lit ce fichier au lieu de recopier les valeurs : aucune table n'est saisie de mémoire.
Seule la traduction "nom de constante -> symbole affiché" est écrite ici, et elle est
directement déductible du nom (kVK_LeftArrow -> flèche gauche).
"""

import re
from pathlib import Path

BRIDGESUPPORT = Path(
    "/System/Library/Frameworks/Carbon.framework/Versions/A/Frameworks/"
    "HIToolbox.framework/Versions/A/Resources/BridgeSupport/HIToolbox.bridgesupport"
)

_ENUM_RE = re.compile(r"<enum name='([A-Za-z0-9_]+)' value64='(-?\d+)'/>")


def _load_enums(prefix, suffix=""):
    """Retourne {nom_constante: valeur} pour les constantes correspondantes."""
    if not BRIDGESUPPORT.exists():
        raise SystemExit(
            f"Introuvable : {BRIDGESUPPORT}\n"
            "Ce fichier fait partie de macOS. Sans lui, impossible de décoder les "
            "touches sans inventer de valeurs — on s'arrête plutôt que de deviner."
        )
    text = BRIDGESUPPORT.read_text(encoding="utf-8", errors="replace")
    out = {}
    for name, value in _ENUM_RE.findall(text):
        if name.startswith(prefix) and name.endswith(suffix):
            out[name] = int(value)
    return out


# --- Codes de touches virtuels -------------------------------------------------

# Ponctuation : le nom de la constante dit quelle touche c'est.
_PUNCT = {
    "Comma": ",", "Period": ".", "Slash": "/", "Backslash": "\\",
    "Semicolon": ";", "Quote": "'", "LeftBracket": "[", "RightBracket": "]",
    "Grave": "`", "Minus": "-", "Equal": "=",
}

# Touches spéciales : symboles standards de la notation clavier Apple.
_SPECIAL = {
    "Return": "⏎", "Tab": "⇥", "Space": "Espace", "Delete": "⌫",
    "ForwardDelete": "⌦", "Escape": "⎋", "Help": "Aide",
    "Home": "↖", "End": "↘", "PageUp": "⇞", "PageDown": "⇟",
    "LeftArrow": "←", "RightArrow": "→", "UpArrow": "↑",
    "DownArrow": "↓", "CapsLock": "⇪", "Command": "⌘",
    "Shift": "⇧", "Option": "⌥", "Control": "⌃", "Function": "fn",
    "Mute": "Silence", "VolumeUp": "Volume +", "VolumeDown": "Volume -",
    "ISO_Section": "§", "JIS_Yen": "¥", "JIS_Underscore": "_",
}


APPKIT = Path(
    "/System/Library/Frameworks/AppKit.framework/Versions/C/Resources/BridgeSupport"
    "/AppKit.bridgesupport"
)

# Passerelle entre le nom AppKit d'une touche et le libellé que porte la table Carbon.
# Les deux fichiers décrivent la même touche sous deux noms ; c'est une équivalence de
# nommage, pas une valeur recopiée — les codes viennent des fichiers, ici comme ailleurs.
_EQUIVALENCES = {
    "NSUpArrowFunctionKey": "↑", "NSDownArrowFunctionKey": "↓",
    "NSLeftArrowFunctionKey": "←", "NSRightArrowFunctionKey": "→",
    "NSPageUpFunctionKey": "⇞", "NSPageDownFunctionKey": "⇟",
    "NSHomeFunctionKey": "↖", "NSEndFunctionKey": "↘",
    "NSDeleteFunctionKey": "⌦", "NSHelpFunctionKey": "Aide",
}


def function_key_chars():
    """{caractère → libellé de touche} pour ce que macOS écrit en \\UF7xx.

    Une redéfinition utilisateur visant F5 ou une flèche n'est pas rangée par macOS
    sous un caractère imprimable, mais sous un point de code de la zone privée. Sans
    cette table, la touche reste irrésoluble : le raccourci est compté sur son ancienne
    combinaison, et la nouvelle est annoncée libre.
    """
    if not APPKIT.exists():
        return {}
    texte = APPKIT.read_text(encoding="utf-8", errors="replace")
    out = {}
    for nom, valeur in re.findall(r"name='(NS[A-Za-z0-9]*FunctionKey)'[^>]*"
                                  r"value64='(\d+)'", texte):
        fonction = re.fullmatch(r"NSF(\d+)FunctionKey", nom)
        libelle = f"F{fonction.group(1)}" if fonction else _EQUIVALENCES.get(nom)
        if libelle:
            out[chr(int(valeur))] = libelle
    return out


def _keycode_label(name):
    """Traduit un nom de constante kVK_* en libellé affichable."""
    body = name[len("kVK_"):]
    if body.startswith("ANSI_"):
        body = body[len("ANSI_"):]
        if body.startswith("Keypad"):
            rest = body[len("Keypad"):]
            return f"Pavé {rest}" if rest else "Pavé"
        if len(body) == 1:
            return body.upper()
        return _PUNCT.get(body, body)
    if re.fullmatch(r"F\d+", body):
        return body
    return _SPECIAL.get(body, body)


def keycode_labels():
    """{code_virtuel: libellé}. Sur collision, garde le nom le plus court/simple."""
    labels = {}
    for name, code in sorted(_load_enums("kVK_").items()):
        label = _keycode_label(name)
        if code not in labels or len(label) < len(labels[code]):
            labels[code] = label
    return labels


def keypad_codes():
    """Codes des touches du pavé numérique.

    Elles produisent les mêmes caractères que la rangée du haut ; sans les écarter,
    remonter du caractère « 4 » à sa touche tomberait sur le pavé plutôt que sur la
    touche principale.
    """
    return {code for name, code in _load_enums("kVK_ANSI_Keypad").items()}


# --- Glyphes de menu -----------------------------------------------------------

_GLYPH = {
    "TabRight": "⇥", "TabLeft": "⇤", "Enter": "⌤", "Space": "Espace",
    "DeleteRight": "⌦", "DeleteLeft": "⌫", "Return": "⏎",
    "NonmarkingReturn": "⏎", "ReturnR2L": "⏎", "Escape": "⎋",
    "Clear": "⌧", "PageUp": "⇞", "PageDown": "⇟", "CapsLock": "⇪",
    "LeftArrow": "←", "RightArrow": "→", "UpArrow": "↑",
    "DownArrow": "↓", "NorthwestArrow": "↖", "SoutheastArrow": "↘",
    "Help": "Aide", "Power": "⏻", "Eject": "⏏", "ContextualMenu": "☰",
    "Command": "⌘", "Shift": "⇧", "Option": "⌥", "Control": "⌃",
    "LeftArrowDashed": "←", "RightArrowDashed": "→",
    "UpArrowDashed": "↑", "DownwardArrowDashed": "↓",
}


def glyph_labels():
    """{numéro_de_glyphe: libellé}. Les glyphes non pertinents (0, blanc) sont exclus."""
    labels = {}
    for name, code in sorted(_load_enums("kMenu", "Glyph").items()):
        body = name[len("kMenu"):-len("Glyph")]
        if body in ("Null", "Blank", "ItemDataCmdKey", "AttrUsePencil"):
            continue
        if re.fullmatch(r"F\d+", body):
            labels[code] = body
        elif body in _GLYPH:
            labels[code] = _GLYPH[body]
    return labels


# --- Correspondance glyphe de menu → code de touche ---

# Les menus décrivent les touches sans caractère par un glyphe, les outils tiers par un
# code de touche. Sans passerelle, ⌃⇥ vu dans un menu et ⌃⇥ vu chez Keyboard Maestro
# restent deux choses différentes — et le conflit passe inaperçu.
#
# La passerelle se fait par **nom de constante**, pas par valeur : les deux
# énumérations viennent du même fichier système. Seuls les noms qui divergent sont
# listés ici, et ils le sont sous forme de noms, pas de nombres.
_GLYPH_ALIAS = {
    "TabRight": "Tab", "TabLeft": "Tab",
    "Return": "Return", "NonmarkingReturn": "Return", "ReturnR2L": "Return",
    "Enter": "ANSI_KeypadEnter", "Clear": "ANSI_KeypadClear",
    "DeleteLeft": "Delete", "DeleteRight": "ForwardDelete",
    "NorthwestArrow": "Home", "SoutheastArrow": "End",
    "LeftArrowDashed": "LeftArrow", "RightArrowDashed": "RightArrow",
    "UpArrowDashed": "UpArrow", "DownwardArrowDashed": "DownArrow",
}


def glyph_to_keycode():
    """{numéro de glyphe: code de touche} pour les touches sans caractère."""
    keycodes = {name[len("kVK_"):]: code for name, code in _load_enums("kVK_").items()}
    mapping = {}
    for name, glyph in _load_enums("kMenu", "Glyph").items():
        body = name[len("kMenu"):-len("Glyph")]
        cible = _GLYPH_ALIAS.get(body, body)
        if cible in keycodes:
            mapping[glyph] = keycodes[cible]
    return mapping


def keycode_symbols():
    """{code de touche: symbole} pour les touches sans caractère (⌤, ⌧, ⏎…).

    Construit en croisant les deux énumérations système : glyphe → code d'un côté,
    glyphe → symbole de l'autre. Aucun symbole n'est écrit à la main ici.
    """
    labels = glyph_labels()
    out = {}
    for glyph, code in glyph_to_keycode().items():
        if glyph in labels:
            out.setdefault(code, labels[glyph])
    return out


if __name__ == "__main__":
    kc, gl = keycode_labels(), glyph_labels()
    print(f"{len(kc)} codes de touches, {len(gl)} glyphes extraits de BridgeSupport")
    print("exemples :", {k: kc[k] for k in list(kc)[:5]})
    print("glyphes  :", {k: gl[k] for k in list(gl)[:8]})
