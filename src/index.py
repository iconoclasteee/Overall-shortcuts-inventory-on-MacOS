"""Index unifié : toutes les sources de raccourcis ramenées à un même modèle.

C'est ce fichier qui rend possibles les trois questions posées :
  - où telle combinaison est-elle utilisée ?
  - lesquelles entrent en conflit, et qui gagne ?
  - que puis-je taper dans telle app ?

Le principe : chaque raccourci reçoit une **clé de comparaison** (touche physique +
modificateurs). Deux raccourcis qui partagent cette clé se disputent la même frappe.
"""

import json
from datetime import datetime
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import global_hotkeys
import overrides as user_overrides
from model import (Binding, Keyboard, ALT, CMD, CTRL, SHIFT, from_ax, rang,
                   render_modifiers, COUCHES)
from tables import glyph_labels, glyph_to_keycode

ROOT = Path(__file__).parent.parent


def load_portees():
    data = json.loads((ROOT / "data" / "portees.json").read_text(encoding="utf-8"))
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
            # Apple ne documente pas cet identifiant dans sa table de référence : on
            # décrit le mécanisme sans affirmer la fonction.
            detail += " · double frappe, fonction non documentée par Apple"
        found.append(Binding(
            mods=entry["mods"], combo=entry["combinaison"], action=entry["nom"],
            source="systeme", couche="systeme", portee=portee, proprietaire="macOS",
            code=entry["code"], actif=entry["actif"], double=entry.get("double", False),
            detail=detail))
    return found


def app_bindings(keyboard, apps_dir):
    """Raccourcis de menu, une app à la fois, redéfinitions utilisateur appliquées."""
    found, apps = [], []
    glyphes = glyph_labels()
    glyphe_vers_code = glyph_to_keycode()
    for path in sorted(Path(apps_dir).glob("*.json")):
        try:
            app = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"⚠️  illisible, ignoré : {path.name}")
            continue
        # Une fiche tronquée (interruption en cours d'écriture) est un JSON valide
        # mais incomplet : mieux vaut l'écarter que faire échouer tout l'index.
        if not isinstance(app, dict) or "statut" not in app or "bundleID" not in app:
            print(f"⚠️  incomplet, ignoré : {path.name}")
            continue
        fiche = {k: app.get(k) for k in
                 ("nom", "bundleID", "version", "categorie", "statut", "detail",
                  "lance_par_nous")}
        # La fiche ne date pas le moissonnage ; sa date d'écriture le fait. `--sources`
        # ne réécrit pas les fiches, donc elle désigne bien la dernière lecture réelle.
        fiche["scanne_le"] = datetime.fromtimestamp(
            path.stat().st_mtime).strftime("%Y-%m-%d %Hh%M")
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
                # Ramener le glyphe à sa touche physique : c'est ce qui permet de
                # comparer un ⌃⇥ de menu avec un ⌃⇥ d'outil tiers.
                code = glyphe_vers_code.get(glyphe)
            if code is None and glyphe is None:
                continue
            label = keyboard.label(code, mods) if code is not None else None
            if label is None and glyphe is not None:
                label = glyphes.get(glyphe)
            if label is None and char.strip() and char.isprintable():
                # macOS a des glyphes récents que la table Carbon ne connaît pas
                # (🌐 pour la touche Globe, 🎤 pour la dictée). L'app fournit alors
                # le symbole : mieux vaut le montrer qu'afficher un numéro.
                label = char
            combo = render_modifiers(mods) + (label or f"glyphe-{glyphe}")

            leaf = user_overrides.normalise_title(item["chemin"].split(" > ")[-1])
            detail = ""
            if leaf in redefinis:
                # Une redéfinition change la frappe, pas seulement son libellé : sans
                # recalculer modificateurs et code de touche, la détection de conflits
                # continuerait de raisonner sur l'ancienne combinaison.
                combo = redefinis[leaf][1]
                prefixe, touche = user_overrides.decomposer(redefinis[leaf][2])
                mods = ((SHIFT if "$" in prefixe else 0) | (CTRL if "^" in prefixe else 0)
                        | (ALT if "~" in prefixe else 0) | (CMD if "@" in prefixe else 0))
                if touche:
                    nouveau, besoin_maj = keyboard.resoudre(touche)
                    if nouveau is not None:
                        code, glyphe = nouveau, None
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
    """Qui reçoit la frappe, d'après l'étage d'interception le plus bas.

    Honnête sur ses limites : à égalité d'étage, c'est l'ordre d'enregistrement qui
    tranche et il n'est écrit dans aucun fichier. On dit « égalité » plutôt que de
    désigner un nom au hasard.
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


# Part des apps lues au-delà de laquelle une même commande de menu cesse d'être une
# commande propre à une app pour devenir une convention de macOS. Mesuré sur cette
# machine : ⌘M « Minimiser » est exposé par 81 % des apps, le suivant par 13 % —
# l'écart est tel que le seuil exact n'a aucune influence.
SEUIL_CONVENTION = 0.5


def load_reglages():
    """Choix posés à la main depuis la page : exclusions et apps sources.

    Écrit par l'utilisateur, jamais par le programme — son absence est le cas normal.
    """
    chemin = ROOT / "out" / "reglages-scan.json"
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
        # Un conflit suppose au moins un raccourci global : deux menus d'apps
        # différentes ne se croisent jamais.
        globaux = [b for b in membres if b.couche != "menu" and b.actif]
        proprietaires = {b.proprietaire for b in membres if b.actif}
        # macOS injecte ses commandes de fenêtre dans le menu de chaque app : le
        # raccourci système et l'élément de menu désignent alors la même commande.
        feuilles = {b.action.split(" > ")[-1].casefold().rstrip("… .")
                    for b in membres if b.actif}
        meme_commande = len(feuilles) == 1 and len(proprietaires) > 1
        # Une commande que presque toutes les apps exposent n'est pas la leur : c'est
        # une convention que macOS installe dans chaque barre de menu. Le raccourci
        # système correspondant fait la même chose — il ne la conteste pas. Le test
        # porte sur la proportion d'apps, pas sur le libellé : « Minimiser »,
        # « Minimize » et « Réduire » désignent la même commande.
        # Garde-fou : la règle ne vaut que si le seul prétendant hors menus est macOS
        # lui-même. Qu'un outil tiers s'empare de ⌘C reste un vrai conflit — il le
        # vole justement à toutes les apps, et l'ubiquité en aggrave la portée au
        # lieu de l'excuser.
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
    combinaisons.sort(key=lambda c: (not c["conflit"], c["combo"]))
    catalogue_path = ROOT / "out" / "catalogue.json"
    catalogue = (json.loads(catalogue_path.read_text(encoding="utf-8"))
                 if catalogue_path.exists() else [])

    # Apps « source de raccourcis » : celles qui accrochent la touche avant les menus.
    # Constatées à partir de ce qu'elles déclarent réellement, plus celles que
    # l'utilisateur a désignées à la main. Le rapprochement se fait aussi par nom :
    # Keyboard Maestro enregistre ses raccourcis sous l'identifiant de son moteur,
    # alors que l'app installée est son éditeur — le seul identifiant les manquerait.
    proprios_outils = {b.proprietaire for b in bindings
                       if b.couche in ("pilote", "capture", "global", "autre")}
    ids_outils = {b.bundle_id for b in bindings
                  if b.couche in ("pilote", "capture", "global", "autre") and b.bundle_id}
    sources = {a["bundleID"] for a in catalogue
               if a["bundleID"] in ids_outils or a["nom"] in proprios_outils}
    sources |= set(load_reglages().get("sources") or [])

    return {
        "apps": apps,
        "catalogue": catalogue,
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
