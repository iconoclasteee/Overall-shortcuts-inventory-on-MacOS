"""Global hotkeys registered by third-party tools.

They matter because they **win against application menus**: a menu answers only while its
app is frontmost, a global hotkey answers everywhere. Ignoring them would make conflict
detection miss precisely the ones that show up in real use.

Each tool is read from its own configuration, which is never written to. Only the keys
describing a shortcut are extracted: nothing else in the file is walked or kept.
"""

import json
import plistlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from model import Binding, Keyboard, from_carbon, from_nsevent, render_modifiers

ROOT = Path(__file__).parent.parent

HOME = Path.home()


def _combo(keyboard, code, mods):
    label = keyboard.label(code, mods)
    return (render_modifiers(mods) + label) if label else None


def scan_alfred(keyboard):
    """Alfred keeps its shortcuts inside the Alfred.alfredpreferences bundle.

    Layer "global": Alfred goes through RegisterEventHotKey (Carbon).
    """
    base = HOME / "Library/Application Support/Alfred/Alfred.alfredpreferences"
    # prefs.json points at a synced folder (Dropbox, iCloud) when there is one.
    prefs = HOME / "Library/Application Support/Alfred/prefs.json"
    if prefs.exists():
        try:
            current = json.loads(prefs.read_text(encoding="utf-8")).get("current") or ""
            if current:
                candidate = Path(current).expanduser() / "Alfred.alfredpreferences"
                if candidate.exists():
                    base = candidate
        except (json.JSONDecodeError, OSError):
            pass
    if not base.exists():
        return []

    found = []

    def emit(action, spec):
        code, mask = spec.get("key"), spec.get("mod")
        # A single-key shortcut (F19 is common with Alfred) has a null mask: only a
        # missing key code means "unassigned".
        if code is None:
            return
        mods = from_nsevent(mask)
        combo = _combo(keyboard, code, mods)
        if combo:
            found.append(Binding(mods=mods, combo=combo, action=action, source="outil",
                                 couche="global", portee="systeme", proprietaire="Alfred",
                                 bundle_id="com.runningwithcrayons.Alfred", code=code))

    for plist in (base / "preferences").rglob("*.plist"):
        try:
            data = plistlib.loads(plist.read_bytes())
        except Exception:
            continue
        for key, value in data.items():
            if isinstance(value, dict) and "key" in value and "mod" in value:
                emit(f"Alfred — {plist.parent.name} ({key})", value)

    # Workflow hotkey triggers. A disabled workflow registers nothing, and a trigger with
    # no "hotstring" was never given a combination.
    for info in (base / "workflows").glob("*/info.plist"):
        try:
            data = plistlib.loads(info.read_bytes())
        except Exception:
            continue
        if data.get("disabled"):
            continue
        name = data.get("name") or info.parent.name
        for obj in data.get("objects", []):
            if obj.get("type") != "alfred.workflow.trigger.hotkey":
                continue
            config = obj.get("config") or {}
            if not config.get("hotstring"):
                continue
            emit(f"Alfred — workflow « {name} »",
                 {"key": config.get("hotkey"), "mod": config.get("hotmod")})
    return found


def scan_keyboard_maestro(keyboard):
    """Keyboard Maestro: macro library, triggers of type HotKey.

    Layer "capture": its engine intercepts through a CGEventTap, therefore **before**
    system shortcuts. A disabled group or macro registers nothing.
    """
    path = HOME / "Library/Application Support/Keyboard Maestro/Keyboard Maestro Macros.plist"
    if not path.exists():
        return []
    try:
        data = plistlib.loads(path.read_bytes())
    except Exception:
        return []

    found = []
    for group in data.get("MacroGroups", []):
        if group.get("IsActive") is False:
            continue
        for macro in group.get("Macros", []):
            if macro.get("IsActive") is False:
                continue
            name = macro.get("Name") or "(macro sans nom)"
            for trigger in macro.get("Triggers", []):
                if trigger.get("MacroTriggerType") != "HotKey":
                    continue
                code = trigger.get("KeyCode")
                if code is None:
                    continue
                mods = from_carbon(trigger.get("Modifiers"))
                combo = _combo(keyboard, code, mods)
                if not combo:
                    continue
                scope = group.get("Name") or ""
                found.append(Binding(
                    mods=mods, combo=combo,
                    action=f"Keyboard Maestro — {name}" + (f" [{scope}]" if scope else ""),
                    source="outil", couche="capture", portee="systeme",
                    proprietaire="Keyboard Maestro",
                    bundle_id="com.stairways.keyboardmaestro.engine", code=code))
    return found


# --- Generic preferences sweep ------------------------------------------

# Three conventions cover most apps that register a global hotkey:
#   · a {keyCode, modifierFlags} dictionary — NSEvent mask (Rectangle Pro)
#   · a JSON string carrying carbonKeyCode/carbonModifiers — the KeyboardShortcuts
#     library, very widespread (ChatGPT, CleanShot X). Spotted by its content and not by
#     the key's name: every app picks its own prefix, and a hard-coded list of prefixes
#     silently misses the next one.
#   · an NSKeyedArchiver archive, which ShortcutRecorder produces (PopClip)
# Reading them generically rather than app by app surfaces new sources without having to
# anticipate them.
# The pattern below only lightens the displayed label; it never decides whether a key
# counts.
PREFIXE_LIBELLE = re.compile(r"^[A-Za-z]*Shortcuts?_|^LAVA")


def _nom_app(bundle_id, catalogue):
    return catalogue.get(bundle_id, bundle_id)


def _catalogue():
    chemin = ROOT / "out" / "catalogue.json"
    if not chemin.exists():
        return {}
    return {a["bundleID"]: a["nom"] for a in json.loads(chemin.read_text(encoding="utf-8"))}


def _depuis_archive(donnees):
    """Convention 3: shortcuts serialised in an NSKeyedArchiver archive.

    This is what ShortcutRecorder produces, the most widespread shortcut-capture library
    (PopClip and others). The object carries `keyCode` and `modifierFlags` as convention 1
    does, but each value is replaced by a UID pointing into the `$objects` table: without
    dereferencing, all one reads are slot numbers. The mask is still NSEvent's.
    """
    try:
        archive = plistlib.loads(donnees)
    except Exception:
        return None
    if not isinstance(archive, dict) or archive.get("$archiver") != "NSKeyedArchiver":
        return None
    objets = archive.get("$objects") or []

    def resoudre(reference):
        if isinstance(reference, plistlib.UID):
            indice = reference.data
            return objets[indice] if 0 <= indice < len(objets) else None
        return reference

    # One archive can serialise several shortcuts: stopping at the first would make the
    # others disappear with nothing to flag it.
    trouves = []
    for objet in objets:
        if not isinstance(objet, dict) or "keyCode" not in objet:
            continue
        code = resoudre(objet["keyCode"])
        masque = resoudre(objet.get("modifierFlags"))
        if isinstance(code, int) and isinstance(masque, int):
            trouves.append((code, masque))
    return trouves


def scan_preferences(keyboard, ignorer=()):
    """Global hotkeys declared in the preferences, across every app."""
    # A preferences file outlives the uninstall of its app. Without this cross-check
    # against the apps actually installed, active shortcuts would be attributed to absent
    # software — seen with one vendor whose old preferences linger while the installed app
    # carries a different bundle identifier.
    catalogue = _catalogue()
    orphelins = set()
    found = []

    def ajouter(bundle_id, action, code, mods):
        if catalogue and bundle_id not in catalogue:
            orphelins.add(bundle_id)
            return
        combo = _combo(keyboard, code, mods)
        if not combo:
            return
        nom = _nom_app(bundle_id, catalogue)
        found.append(Binding(
            mods=mods, combo=combo, action=f"{nom} — {action}", source="outil",
            couche="global", portee="systeme", proprietaire=nom,
            bundle_id=bundle_id, code=code))

    for chemin in sorted((HOME / "Library/Preferences").glob("*.plist")):
        bundle_id = chemin.stem
        if any(bundle_id.startswith(prefixe) for prefixe in ignorer):
            continue
        try:
            prefs = plistlib.loads(chemin.read_bytes())
        except Exception:
            continue
        if not isinstance(prefs, dict):
            continue

        for cle, valeur in prefs.items():
            # Convention 1: dictionary with an NSEvent mask.
            if isinstance(valeur, dict) and "keyCode" in valeur:
                masque = valeur.get("modifierFlags")
                if valeur.get("keyCode") is not None and masque is not None:
                    ajouter(bundle_id, cle, valeur["keyCode"], from_nsevent(masque))
                continue
            # Convention 3: NSKeyedArchiver archive. Tested before convention 2, which
            # also accepts bytes: the key is claimed here only if the archive really
            # yields a shortcut, otherwise it carries on.
            if isinstance(valeur, bytes):
                archive = _depuis_archive(valeur)
                if archive:
                    for code, masque in archive:
                        ajouter(bundle_id, cle, code, from_nsevent(masque))
                    continue
            # Convention 2: JSON with Carbon masks, recognised by its content.
            # A key suffixed "@context" describes a shortcut valid only in that context —
            # the open panel of a window switcher, for instance. Counting it as global
            # would have it dispute ⌘A or ⌘H with every app, when it only answers while
            # the panel is on screen.
            if "@" in cle:
                continue
            if not isinstance(valeur, (str, bytes)):
                continue
            texte = valeur if isinstance(valeur, str) else valeur.decode("utf-8", "replace")
            if "carbonKey" not in texte:
                continue
            try:
                spec = json.loads(texte)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(spec, dict):
                continue
            code = spec.get("carbonKeyCode", spec.get("carbonKey"))
            if code is None:
                continue
            ajouter(bundle_id, PREFIXE_LIBELLE.sub("", cle), code,
                    from_carbon(spec.get("carbonModifiers")))

    if orphelins:
        print(f"  ℹ️  {len(orphelins)} domaines de préférences sans app installée, "
              f"ignorés : {', '.join(sorted(orphelins))}")
    return found


def scan_all(keyboard=None):
    keyboard = keyboard or Keyboard()
    # Alfred and Keyboard Maestro have formats of their own; everything else goes through
    # the generic sweep, including apps nobody anticipated.
    return (scan_alfred(keyboard) + scan_keyboard_maestro(keyboard)
            + scan_preferences(keyboard,
                               ignorer=("com.runningwithcrayons.Alfred",
                                        "com.stairways.keyboardmaestro")))


if __name__ == "__main__":
    from collections import Counter
    tout = scan_all()
    print(Counter(b.proprietaire for b in tout).most_common(), "\n")
    for binding in sorted(tout, key=lambda b: (b.proprietaire, b.combo)):
        print(f"{binding.couche:8} {binding.combo:12} {binding.action}")
