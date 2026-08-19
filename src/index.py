"""Unified index: every source of shortcuts brought down to one model.

This file is what makes the three questions answerable:
  - where is this combination used?
  - which ones conflict, and who wins?
  - what can I type in this app?

The principle: every shortcut is given a **comparison key** (physical key + modifiers). Two
shortcuts sharing that key are fighting over the same keystroke.
"""

import json
from datetime import datetime
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import global_hotkeys
import free_shortcuts
import overrides as user_overrides
from model import (Binding, Keyboard, ALT, CMD, CTRL, SHIFT, from_ax, rang,
                   render_modifiers, COUCHES)
from tables import glyph_labels, glyph_to_keycode

ROOT = Path(__file__).parent.parent


def load_portees():
    data = json.loads((ROOT / "data" / "scopes.json").read_text(encoding="utf-8"))
    return data["portees"], {"fr": data["libelles"], "en": data.get("libelles_en", data["libelles"])}


def system_bindings(keyboard, portees):
    path = ROOT / "out" / "system-shortcuts.json"
    if not path.exists():
        return []
    found = []
    for entry in json.loads(path.read_text(encoding="utf-8")):
        if not entry["combinaison"]:
            continue  # raccourci existant mais sans combinaison attribuée
        portee = portees.get(entry["identifiant_categorie"], {}).get("portee", "inconnu")
        detail = entry["categorie"] + (" · désactivé" if not entry["actif"] else "")
        if entry.get("double"):
            # Apple does not document this identifier in its reference table: describe
            # the mechanism without asserting the function.
            detail += " · double frappe, fonction non documentée par Apple"
        found.append(Binding(
            mods=entry["mods"], combo=entry["combinaison"], action=entry["nom"],
            source="systeme", couche="systeme", portee=portee, proprietaire="macOS",
            code=entry["code"], actif=entry["actif"], double=entry.get("double", False),
            detail=detail))
    return found


def app_bindings(keyboard, apps_dir):
    """Menu shortcuts, one app at a time, with user redefinitions applied."""
    found, apps = [], []
    glyphes = glyph_labels()
    glyphe_vers_code = glyph_to_keycode()
    for path in sorted(Path(apps_dir).glob("*.json")):
        try:
            app = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"⚠️  illisible, ignoré : {path.name}")
            continue
        # A truncated record (interrupted mid-write) is valid but incomplete JSON: better
        # to skip it than to fail the whole index.
        if not isinstance(app, dict) or "statut" not in app or "bundleID" not in app:
            print(f"⚠️  incomplet, ignoré : {path.name}")
            continue
        fiche = {k: app.get(k) for k in
                 ("nom", "bundleID", "version", "categorie", "statut", "detail",
                  "lance_par_nous")}
        # The record does not date the harvest; its write time does. `--sources` does not
        # rewrite records, so that time really is the last actual read.
        fiche["scanne_le"] = datetime.fromtimestamp(
            path.stat().st_mtime).strftime("%Y-%m-%d %Hh%M")
        fiche["raccourcis"] = len(app.get("raccourcis") or [])
        apps.append(fiche)
        if app["statut"] != "ok":
            continue
        redefinis = user_overrides.load(app["bundleID"])
        seen = set()
        for ordre, item in enumerate(app["raccourcis"]):
            mods = from_ax(item["modificateurs"])
            char = item.get("caractere") or ""
            code = None
            if char.strip() and char.isprintable():
                code, besoin_maj = keyboard.resoudre(char)
                if besoin_maj:
                    mods |= SHIFT
            glyphe = item.get("glyphe")
            if code is None and glyphe is not None:
                # Bring the glyph back to its physical key: that is what allows a ⌃⇥ from
                # a menu to be compared with a ⌃⇥ from a third-party tool.
                code = glyphe_vers_code.get(glyphe)
            if code is None and glyphe is None:
                continue
            label = keyboard.label(code, mods) if code is not None else None
            if label is None and glyphe is not None:
                label = glyphes.get(glyphe)
            if label is None and char.strip() and char.isprintable():
                # macOS has recent glyphs the Carbon table does not know (🌐 for the Globe
                # key, 🎤 for dictation). The app supplies the symbol in that case: better
                # to show it than to display a number.
                label = char
            combo = render_modifiers(mods) + (label or f"glyphe-{glyphe}")

            leaf = user_overrides.normalise_title(item["chemin"].split(" > ")[-1])
            detail = ""
            if leaf in redefinis:
                # A redefinition changes the keystroke, not just its label: without
                # recomputing modifiers and key code, conflict detection would keep
                # reasoning about the old combination.
                combo = redefinis[leaf][1]
                prefixe, touche = user_overrides.decomposer(redefinis[leaf][2])
                mods = ((SHIFT if "$" in prefixe else 0) | (CTRL if "^" in prefixe else 0)
                        | (ALT if "~" in prefixe else 0) | (CMD if "@" in prefixe else 0))
                if touche:
                    nouveau, besoin_maj = keyboard.resoudre(touche)
                    # macOS writes function keys and arrows as \UF704…, which the layout
                    # cannot resolve. Keeping the old key code would count the shortcut on
                    # its previous combination and leave the new one announced free. With
                    # no code, the comparison key becomes unique: truer than a false match.
                    code, glyphe = (nouveau, None) if nouveau is not None else (None, None)
                    if besoin_maj:
                        mods |= SHIFT
                detail = "redéfini par l'utilisateur"

            signature = (combo, item["chemin"])
            if signature in seen:
                continue
            seen.add(signature)
            found.append(Binding(
                mods=mods, combo=combo, action=item["chemin"], source="menu",
                couche="menu", portee="app", proprietaire=app["nom"],
                bundle_id=app["bundleID"], code=code, glyphe=glyphe, detail=detail,
                menu=item.get("menu") or item["chemin"].split(" > ")[0], ordre=ordre))
    return found, apps


def gagnant(bindings):
    """Who receives the keystroke, based on the lowest interception layer.

    Honest about its limits: at equal layer, registration order decides and it is written
    in no file. We say "tie" rather than naming someone at random.
    """
    actifs = [b for b in bindings if b.actif]
    if not actifs:
        return {"verdict": "aucun", "texte": "Aucun raccourci actif sur cette combinaison."}
    plus_bas = min(rang(b.couche) for b in actifs)
    contendants = [b for b in actifs if rang(b.couche) == plus_bas]
    couche = contendants[0].couche

    if couche == "menu":
        apps = sorted({b.proprietaire for b in contendants})
        if len(apps) == 1:
            return {"verdict": "unique", "texte": f"Seule {apps[0]} utilise cette combinaison."}
        return {"verdict": "selon_app",
                "texte": "Chaque app garde la sienne : ces raccourcis de menu ne se "
                         "disputent jamais la même frappe, seule l'app au premier plan répond.",
                "gagnants": apps}
    if len(contendants) == 1:
        b = contendants[0]
        return {"verdict": "probable", "gagnants": [b.proprietaire],
                "texte": f"{b.proprietaire} l'emporte probablement. {COUCHES[couche][1]}"}
    noms = sorted({b.proprietaire for b in contendants})
    if len(noms) == 1:
        return {"verdict": "probable", "gagnants": noms,
                "texte": f"{noms[0]} l'emporte probablement. {COUCHES[couche][1]}"}
    return {"verdict": "egalite", "gagnants": noms,
            "texte": f"{', '.join(noms)} s'accrochent au même étage : c'est celui qui "
                     f"s'est enregistré en premier qui gagne, et cet ordre n'est écrit "
                     f"nulle part. {COUCHES[couche][1]}"}


# Share of the apps read beyond which one menu command stops being an app's own command
# and becomes a macOS convention. Measured on one machine: ⌘M "Minimise" is exposed by 81 %
# of apps, the next one by 13 % — the gap is such that the exact threshold has no
# influence.
SEUIL_CONVENTION = 0.5


def load_reglages():
    """Choices made by hand from the page: exclusions and hotkey-tool apps.

    Written by the user, never by the program — its absence is the normal case.
    """
    chemin = ROOT / "out" / "scan-settings.json"
    if not chemin.exists():
        return {}
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"⚠️  {chemin.name} illisible, réglages ignorés")
        return {}
    return donnees if isinstance(donnees, dict) else {}


def build(apps_dir):
    keyboard = Keyboard()
    portees, libelles_portee = load_portees()
    bindings = system_bindings(keyboard, portees)
    menus, apps = app_bindings(keyboard, apps_dir)
    bindings += menus + global_hotkeys.scan_all(keyboard)

    lues = {a["bundleID"] for a in apps if a["statut"] == "ok"}

    groupes = defaultdict(list)
    for b in bindings:
        groupes[b.cle].append(b)

    combinaisons = []
    for cle, membres in groupes.items():
        # A conflict requires at least one global shortcut: the menus of two different
        # apps never meet.
        globaux = [b for b in membres if b.couche != "menu" and b.actif]
        proprietaires = {b.proprietaire for b in membres if b.actif}
        # macOS injects its window commands into every app's menu: the system shortcut and
        # the menu item then name the same command.
        feuilles = {b.action.split(" > ")[-1].casefold().rstrip("… .")
                    for b in membres if b.actif}
        meme_commande = len(feuilles) == 1 and len(proprietaires) > 1
        # A command almost every app exposes is not that app's own: it is a convention
        # macOS installs in every menu bar. The matching system shortcut does the same
        # thing — it does not contest it. The test looks at the share of apps, not at the
        # label: "Minimiser", "Minimize" and "Réduire" name the same command.
        # Guard: the rule holds only if the sole claimant outside menus is macOS itself. A
        # third-party tool seizing ⌘C is still a real conflict — it steals it from every
        # app precisely, and ubiquity makes the reach worse rather than excusing it.
        apps_menu = {b.bundle_id for b in membres if b.actif and b.couche == "menu"}
        tiers = any(b.couche in ("pilote", "capture", "global", "autre")
                    for b in membres if b.actif)
        convention = (bool(lues) and not tiers
                      and len(apps_menu) / len(lues) >= SEUIL_CONVENTION)
        conflit = (len(globaux) >= 1 and len(proprietaires) > 1
                   and not meme_commande and not convention)
        combinaisons.append({
            "cle": cle,
            "combo": membres[0].combo,
            "mods": membres[0].mods,
            "double": any(b.double for b in membres),
            "conflit": conflit,
            "meme_commande": meme_commande,
            "convention": convention,
            "apps_exposant": len(apps_menu),
            "arbitrage": gagnant(membres),
            "usages": [{
                "action": b.action, "proprietaire": b.proprietaire, "source": b.source,
                "couche": b.couche, "portee": b.portee, "bundle_id": b.bundle_id,
                "actif": b.actif, "detail": b.detail, "combo": b.combo,
                "menu": b.menu, "ordre": b.ordre, "double": b.double,
            } for b in sorted(membres, key=lambda b: (rang(b.couche), b.proprietaire))],
        })
    # One order, and it does not depend on the dispute: floating conflicts to the top only
    # served the "Conflicts" page, which already filters them, and disordered "By
    # combination", where one is looking for a precise keystroke.
    #
    # The sort keys on the modifier mask before the string. Sorting the string alone mixes
    # modifier glyphs and key glyphs in the same comparison: "⇧⌫" (U+232B) sorts after
    # "⇧⌘A" (U+2318), and the same modifier set ends up scattered across the list.
    combinaisons.sort(key=lambda c: (c["mods"], c["combo"]))
    catalogue_path = ROOT / "out" / "catalogue.json"
    catalogue = (json.loads(catalogue_path.read_text(encoding="utf-8"))
                 if catalogue_path.exists() else [])

    # "Hotkey tool" apps: those that catch the key before any menu. Observed from what
    # they actually declare, plus the ones the user has designated by hand. Matching is
    # also done by name: Keyboard Maestro registers its shortcuts under its engine's
    # identifier while the installed app is its editor — identifier alone would miss them.
    proprios_outils = {b.proprietaire for b in bindings
                       if b.couche in ("pilote", "capture", "global", "autre")}
    ids_outils = {b.bundle_id for b in bindings
                  if b.couche in ("pilote", "capture", "global", "autre") and b.bundle_id}
    sources = {a["bundleID"] for a in catalogue
               if a["bundleID"] in ids_outils or a["nom"] in proprios_outils}
    sources |= set(load_reglages().get("sources") or [])

    # A combination whose only claimant is disabled is free: what counts is the actual
    # state, not the presence of a line in the inventory.
    occupees = {c["cle"] for c in combinaisons if any(u["actif"] for u in c["usages"])}

    return {
        "apps": apps,
        "catalogue": catalogue,
        "libres": free_shortcuts.calculer(keyboard, occupees),
        "sources": sorted(sources),
        "reglages": load_reglages(),
        "combinaisons": combinaisons,
        "libelles_portee": libelles_portee,
        "couches": {"fr": {k: v[1] for k, v in COUCHES.items()},
                    "en": {k: v[2] for k, v in COUCHES.items()}},
    }


if __name__ == "__main__":
    apps_dir = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "out" / "apps")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "index.json"
    data = build(apps_dir)
    out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    conflits = sum(1 for c in data["combinaisons"] if c["conflit"])
    print(f"✅ {out}")
    print(f"   {len(data['combinaisons'])} combinaisons distinctes, {conflits} en conflit, "
          f"{len(data['apps'])} apps")
