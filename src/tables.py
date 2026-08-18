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


def _keycode_label(name):
    """Traduit un nom de constante kVK_* en libellé affichable."""
    body = name[len("kVK_"):]
    if body.startswith("ANSI_"):
        body = body[len("ANSI_"):]
        if body.startswith("Keypad"):
            rest = body[len("Keypad"):]
            return f"Pave {rest}" if rest else "Pave"
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


# --- Masques de modificateurs --------------------------------------------------

# Constantes NSEvent.ModifierFlags, utilisées par les plists système d'Apple.
NSEVENT_FLAGS = [
    (0x040000, "⌃"),  # Control
    (0x080000, "⌥"),  # Option
    (0x020000, "⇧"),  # Shift
    (0x100000, "⌘"),  # Command
    (0x800000, "fn"),
]


def render_modifiers(mask):
    """Rend un masque NSEvent en symboles, dans l'ordre canonique Apple."""
    return "".join(sym for bit, sym in NSEVENT_FLAGS if mask & bit)


if __name__ == "__main__":
    kc, gl = keycode_labels(), glyph_labels()
    print(f"{len(kc)} codes de touches, {len(gl)} glyphes extraits de BridgeSupport")
    print("exemples :", {k: kc[k] for k in list(kc)[:5]})
    print("glyphes  :", {k: gl[k] for k in list(gl)[:8]})
