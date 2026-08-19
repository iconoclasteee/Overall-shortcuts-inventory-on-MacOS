# Architecture et sources de données

Comment l'inventaire est construit, d'où viennent ses tables, et ce que le dépôt
contient. Pour l'usage courant, voir [Utilisation](utilisation.md).

---

## Pourquoi construire plutôt qu'adopter

| Piste | Pourquoi écartée |
|---|---|
| Lire les bundles `.app` sur le disque | Rien à lire : les menus n'existent qu'en mémoire. Les apps Electron/Qt les construisent par code. |
| Adopter **HotkeyClash** | Ne couvre que les apps déjà lancées, et vise la détection de conflits, pas l'inventaire. Son code de parcours de menus a en revanche servi de référence. |
| Adopter **KeyMinder** / **CheatSheet** / **KeyCue** | Consultation de l'app active uniquement. Pas de document global. |
| Script `osascript` | L'autorisation d'accessibilité porterait sur le terminal entier plutôt que sur un binaire dédié. |

## Qui gagne une combinaison

Une frappe descend une pile et le premier étage qui la réclame l'avale :
pilote clavier (Karabiner) → capture d'événements (Keyboard Maestro) → raccourci
système macOS → raccourci global Carbon (Alfred, CleanShot X) → menu d'application.

L'ordre est fiable. Le départage entre deux outils accrochés au **même** étage ne
l'est pas : il dépend de leur ordre d'enregistrement, que rien sur le disque ne
consigne. L'outil dit « égalité » plutôt que de désigner un gagnant au hasard.
Modèle repris de [HotkeyClash](https://github.com/Wunderlandmedia/HotkeyClash) (GPL-2.0) —
voir la note de licence en fin de fichier.

## Doubles frappes

Certains raccourcis système ne sont pas une combinaison mais une **double frappe** sur
un modificateur seul — la dictée en est l'exemple courant. macOS les stocke avec
`type: "modifier"` et un masque distinguant la touche gauche de la droite (constantes
`NX_DEVICE*KEYMASK` d'IOKit). Les libellés viennent du panneau Clavier lui-même
(`DoubleTapCommandRight` → « Appuyer deux fois sur Commande de droite »). Ces
raccourcis sont marqués « double frappe » dans la page, et comptés comme **une** touche.

**`out/raccourcis.md`** — le même inventaire à plat, versionnable et relisible
hors ligne, groupé par catégorie d'app.

## D'où viennent les données

Aucune table n'est écrite de mémoire — tout est extrait de macOS :

| Donnée | Source sur la machine |
|---|---|
| Les raccourcis système + leurs libellés français | `KeyboardSettings.appex/…/DefaultShortcutsTable.xml` et `DefaultSpacesShortcuts.xml` (bureaux), traduits par `.loctable` |
| État réel (activé, redéfini) | `defaults export com.apple.symbolichotkeys` |
| Codes de touches et glyphes de menu | `HIToolbox.framework/…/BridgeSupport` (énumérations Carbon `kVK_*` et `kMenu*Glyph`) |
| Raccourcis d'app | API d'accessibilité, attributs `AXMenuItemCmdChar` / `CmdGlyph` / `CmdModifiers` |
| Catégorie et version d'app | `LSApplicationCategoryType` et `CFBundleShortVersionString` de chaque `Info.plist` |
| Raccourcis redéfinis par l'utilisateur | `NSUserKeyEquivalents` dans les préférences de chaque app |
| Correspondance touche ↔ caractère | `UCKeyTranslate` sur la disposition clavier active — indispensable en AZERTY, où le code 41 produit « m » et non « ; » |
| Raccourcis globaux tiers | `Alfred.alfredpreferences` et `Keyboard Maestro Macros.plist` pour leurs formats propres ; pour tout le reste, un balayage de `~/Library/Preferences` reconnaissant deux conventions répandues — `{keyCode, modifierFlags}` et les clés `KeyboardShortcuts_*`. Lus, jamais écrits. Un domaine de préférences sans app installée est écarté : un fichier de prefs survit à la désinstallation. |

Les descriptions de rôle des apps, elles, sont écrites à la main dans
`data/app-descriptions.json`. Une app sans description s'affiche « Rôle non
renseigné » plutôt que de recevoir une description plausible mais inventée.

## Structure

```
build.sh              compile bin/ShortcutHarvester.app
run.sh                orchestration : système → apps → rapport
src/tables.py         codes de touches et glyphes, extraits de BridgeSupport
src/system_shortcuts.py   raccourcis système → out/system-shortcuts.json
src/Harvester.swift   moissonneur d'accessibilité → out/apps/<bundle-id>.json
src/report.py         assemblage du Markdown final
src/page.py           page HTML autonome, en français et en anglais
src/libres.py         combinaisons qu'aucun raccourci ne revendique
src/perimees.py       fiches dont la version ne correspond plus à l'installée
src/raccourci_systeme.py  désactive ou réactive un raccourci système
out/reglages-scan.json     exclusions et sources posées à la main (ignoré)
data/app-descriptions.json   amorce des rôles d'app (apps macOS uniquement)
out/app-descriptions.json    rôles des apps installées (propre à la machine, ignoré)
```

## Ce que le dépôt contient, et ce qu'il ne contient pas

Le code est publiable tel quel. Tout ce qui décrit **une machine** est produit dans
`out/`, qui n'est pas versionné :

| Versionné | Ignoré (`out/`) |
|---|---|
| Le code, les tables d'arbitrage (`data/portees.json`) | Les raccourcis lus, app par app |
| Les descriptions d'app renseignées à la main | La page HTML et le rapport Markdown |
| Les identifications établies (`data/raccourcis-connus.json`) | La disposition clavier, le catalogue d'apps installées |
| | Les sauvegardes de `com.apple.symbolichotkeys` |

⚠️ **La page produite est un document personnel.** Elle contient les chemins de menus
réels : titres de favoris du navigateur, noms de macros, nom de la session. Elle n'a
rien à faire dans un dépôt, ni dans un partage de fichiers.

Le dépôt ne dit rien d'une installation particulière : ni le nombre d'apps lues, ni
les logiciels présents, ni les raccourcis désactivés. Les outils tiers ne sont nommés
que là où le code les traite explicitement — Alfred et Keyboard Maestro ont un lecteur
dédié, et chaque convention de stockage est illustrée par l'app qui l'emploie. Partout
ailleurs, le texte dit « outils tiers ». Même règle pour `data/app-descriptions.json` :
sa version versionnée ne décrit que des apps livrées avec macOS, parce qu'une version
complétée reviendrait à publier la liste des logiciels installés.

Les listes d'exclusion, elles, sont versionnées : ce sont des réglages du programme,
pas des données de machine. Elles ne contiennent que des identifiants de composants
macOS et d'outils grand public — aucun identifiant relevé sur une installation
particulière. Les désinstalleurs sont écartés par une règle sur le nom plutôt que par
une liste d'identifiants.

Avant de publier, `./verifier-publication.sh` relit les fichiers versionnés **et
l'historique git** à la recherche de chemins absolus, de noms d'utilisateur, d'adresses
et d'identifiants de machine.
