"""Key/glyph lookup tables — extracted from macOS, never written by hand.

Single source of truth: HIToolbox's BridgeSupport file, present on every macOS machine. It
holds the official Carbon enumerations:
  - kVK_*      : virtual key codes (independent of the keyboard layout)
  - kMenu*Glyph: glyphs menus use for non-printing keys

That file is read rather than its values copied out: no table here is typed from memory.
Only the "constant name -> displayed symbol" translation is written here, and it follows
directly from the name (kVK_LeftArrow -> left arrow).
"""

import re
from pathlib import Path

BRIDGESUPPORT = Path(
    "/System/Library/Frameworks/Carbon.framework/Versions/A/Frameworks/"
    "HIToolbox.framework/Versions/A/Resources/BridgeSupport/HIToolbox.bridgesupport"
)

_ENUM_RE = re.compile(r"<enum name='([A-Za-z0-9_]+)' value64='(-?\d+)'/>")


def _load_enums(prefix, suffix=""):
    """Returns {constant name: value} for the matching constants."""
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


# --- Virtual key codes -------------------------------------------------

# Punctuation: the constant's name says which key it is.
_PUNCT = {
    "Comma": ",", "Period": ".", "Slash": "/", "Backslash": "\\",
    "Semicolon": ";", "Quote": "'", "LeftBracket": "[", "RightBracket": "]",
    "Grave": "`", "Minus": "-", "Equal": "=",
}

# Special keys: standard symbols of Apple's keyboard notation.
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

# Bridge between a key's AppKit name and the label the Carbon table carries. Both files
# describe the same key under two names; this is a naming equivalence, not a copied value —
# the codes come from the files, here as everywhere else.
_EQUIVALENCES = {
    "NSUpArrowFunctionKey": "↑", "NSDownArrowFunctionKey": "↓",
    "NSLeftArrowFunctionKey": "←", "NSRightArrowFunctionKey": "→",
    "NSPageUpFunctionKey": "⇞", "NSPageDownFunctionKey": "⇟",
    "NSHomeFunctionKey": "↖", "NSEndFunctionKey": "↘",
    "NSDeleteFunctionKey": "⌦", "NSHelpFunctionKey": "Aide",
}


def function_key_chars():
    """{character → key label} for what macOS writes as \\UF7xx.

    A user redefinition aimed at F5 or an arrow is not stored by macOS under a printable
    character, but under a private-use code point. Without this table the key stays
    unresolvable: the shortcut is counted on its old combination, and the new one is
    announced free.
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
    """Turns a kVK_* constant name into a displayable label."""
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
    """{virtual code: label}. On collision, keeps the shortest/simplest name."""
    labels = {}
    for name, code in sorted(_load_enums("kVK_").items()):
        label = _keycode_label(name)
        if code not in labels or len(label) < len(labels[code]):
            labels[code] = label
    return labels


def keypad_codes():
    """Key codes of the numeric keypad.

    They produce the same characters as the top row; without setting them aside, going
    back from the character "4" to its key would land on the keypad rather than on the
    main key.
    """
    return {code for name, code in _load_enums("kVK_ANSI_Keypad").items()}


# --- Menu glyphs -----------------------------------------------------------

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
    """{glyph number: label}. Irrelevant glyphs (0, blank) are excluded."""
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


# --- Menu glyph → key code mapping ---

# Menus describe character-less keys by a glyph, third-party tools by a key code. Without
# a bridge, ⌃⇥ seen in a menu and ⌃⇥ seen in Keyboard Maestro remain two different things —
# and the conflict goes unnoticed.
#
# The bridge is made by **constant name**, not by value: both enumerations come from the
# same system file. Only the names that diverge are listed here, and they are listed as
# names, not as numbers.
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
    """{glyph number: key code} for character-less keys."""
    keycodes = {name[len("kVK_"):]: code for name, code in _load_enums("kVK_").items()}
    mapping = {}
    for name, glyph in _load_enums("kMenu", "Glyph").items():
        body = name[len("kMenu"):-len("Glyph")]
        cible = _GLYPH_ALIAS.get(body, body)
        if cible in keycodes:
            mapping[glyph] = keycodes[cible]
    return mapping


def keycode_symbols():
    """{key code: symbol} for character-less keys (⌤, ⌧, ⏎…).

    Built by crossing the two system enumerations: glyph → code on one side, glyph → symbol
    on the other. No symbol is written by hand here.
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
