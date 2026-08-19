"""User-redefined shortcuts (Settings → Keyboard → App Shortcuts).

macOS stores them in each app's preferences, indexed by **menu item title**. The title is
therefore the join key against what accessibility returns — and it is also why a title
that no longer matches (translated app, renamed command) leaves the shortcut inoperative
without flagging anything.
"""

import plistlib
import subprocess

# Cocoa key-equivalent syntax, as written in NSUserKeyEquivalents.
COCOA_MODIFIERS = [("^", "⌃"), ("~", "⌥"), ("$", "⇧"), ("@", "⌘")]


def parse_cocoa_key_equivalent(raw):
    """Turns "@~^$m" into "⌃⌥⇧⌘M".

    The characters @ ~ ^ $ denote modifiers only **as a prefix**: on a French keyboard,
    "$" is a key in its own right. Stripping them everywhere would make the key vanish and
    add a phantom Shift to "⌘$".
    """
    raw = raw or ""
    i = 0
    while i < len(raw) - 1 and raw[i] in "@~^$":
        i += 1
    prefixe, touche = raw[:i], raw[i:]
    mods = "".join(sym for token, sym in COCOA_MODIFIERS if token in prefixe)
    return mods + touche.upper()


def decomposer(raw):
    """(Cocoa modifiers, key) of a key equivalent, kept apart.

    The displayable combination is not enough: comparing a redefinition against other
    shortcuts needs its modifiers and its key separately.
    """
    raw = raw or ""
    i = 0
    while i < len(raw) - 1 and raw[i] in "@~^$":
        i += 1
    return raw[:i], raw[i:]


def normalise_title(title):
    """Brings a menu title and an NSUserKeyEquivalents key into the same shape.

    Both describe the same item but not always identically: a typographic ellipsis against
    three dots, case, whitespace.
    """
    return (title or "").replace("...", "…").rstrip("… ").strip().casefold()


def load(bundle_id):
    """{normalised title: (original title, combination)} for one app."""
    export = subprocess.run(["defaults", "export", bundle_id, "-"], capture_output=True)
    if export.returncode != 0 or not export.stdout:
        return {}
    try:
        prefs = plistlib.loads(export.stdout)
    except Exception:
        return {}
    return {normalise_title(title): (title, parse_cocoa_key_equivalent(value), value)
            for title, value in (prefs.get("NSUserKeyEquivalents") or {}).items()}
