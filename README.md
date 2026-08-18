# MacOS-shortcuts-inventory

Inventaire complet des raccourcis clavier d'un Mac : le système, puis application par
application, dans un seul document Markdown classé par catégorie.

## Pourquoi

Aucun outil ne produit cet inventaire. Les outils existants (CheatSheet, KeyCue,
KeyMinder, HotkeyClash) sont des **consultations à la volée** : ils montrent les
raccourcis de l'app active, ou ceux des apps déjà lancées. Aucun ne fabrique le
document exhaustif, versionnable, relisible hors ligne.

La difficulté est réelle et explique ce vide : **les raccourcis d'une app ne sont
écrits nulle part sur le disque.** Ils sont construits en mémoire au lancement, et ne
sont lisibles que dans la barre de menu vivante, via l'API d'accessibilité. Couvrir
les apps installées suppose donc de les lancer une par une pour les lire — c'est ce
que fait ce projet, et c'est ce qu'aucun autre ne fait.

### Alternatives écartées

| Piste | Pourquoi écartée |
|---|---|
| Lire les bundles `.app` sur le disque | Rien à lire : les menus n'existent qu'en mémoire. Les apps Electron/Qt les construisent par code. |
| Adopter **HotkeyClash** | Ne couvre que les apps déjà lancées, et vise la détection de conflits, pas l'inventaire. Son code de parcours de menus a en revanche servi de référence. |
| Adopter **KeyMinder** / **CheatSheet** / **KeyCue** | Consultation de l'app active uniquement. Pas de document global. |
| Script `osascript` | L'autorisation d'accessibilité porterait sur le terminal entier plutôt que sur un binaire dédié. |

## Ce que ça produit

**`out/raccourcis.html`** — une page autonome, quatre vues :

1. **Commandes par menu** — les raccourcis de l'app choisie, dans l'ordre de sa barre
   de menu, puis les raccourcis globaux rangés selon qu'ils agissent *dans* l'app,
   *sur* elle, ou à côté d'elle.
2. **Effet d'une frappe** — part de la touche et non de la commande : pour chaque
   combinaison atteignable dans cette app, qui la reçoit vraiment. Classée par nombre
   de touches.
3. **Conflits** — les combinaisons réclamées par plusieurs preneurs, avec qui gagne
   et pourquoi.
4. **Par combinaison** — cherche une touche ou une commande, vois partout où elle sert.

Un filtre unique (application, modificateurs, touche, nombre de touches, libellé)
s'applique aux quatre vues. Le filtre par application se désactive : tout est alors
montré, toutes apps confondues.

### Doubles frappes

Certains raccourcis système ne sont pas une combinaison mais une **double frappe** sur
un modificateur seul — la dictée en est l'exemple courant. macOS les stocke avec
`type: "modifier"` et un masque distinguant la touche gauche de la droite (constantes
`NX_DEVICE*KEYMASK` d'IOKit). Les libellés viennent du panneau Clavier lui-même
(`DoubleTapCommandRight` → « Appuyer deux fois sur Commande de droite »). Ces
raccourcis sont marqués « double frappe » dans la page, et comptés comme **une** touche.

**`out/raccourcis-macos.md`** — le même inventaire à plat, versionnable et relisible
hors ligne, groupé par catégorie d'app.

### Qui gagne une combinaison

Une frappe descend une pile et le premier étage qui la réclame l'avale :
pilote clavier (Karabiner) → capture d'événements (Keyboard Maestro) → raccourci
système macOS → raccourci global Carbon (Alfred, CleanShot X) → menu d'application.

L'ordre est fiable. Le départage entre deux outils accrochés au **même** étage ne
l'est pas : il dépend de leur ordre d'enregistrement, que rien sur le disque ne
consigne. L'outil dit « égalité » plutôt que de désigner un gagnant au hasard.
Modèle repris de [HotkeyClash](https://github.com/Wunderlandmedia/HotkeyClash) (GPL-2.0) —
voir la note de licence en fin de fichier.

## Utilisation

```bash
./build.sh          # compile le moissonneur (une fois)
./run.sh --test     # 6 apps représentatives, pour valider la mécanique
./run.sh --all      # les apps installées

# Lister les cibles sans rien lancer :
bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester --all --dry-run
```

La passe est **reprenable** : chaque app est écrite dans son propre JSON, une relance
saute ce qui existe déjà. `Ctrl-C` ne perd rien. `--force` refait tout.

## Autorisation d'accessibilité

Lire les menus d'une autre app l'exige. `run.sh` la vérifie avant de commencer et
s'arrête avec un message clair si elle manque.

Si le moissonneur est lancé depuis un terminal qui possède déjà l'autorisation, il en
hérite. Sinon, ajouter `bin/ShortcutHarvester.app` dans Réglages Système →
Confidentialité et sécurité → Accessibilité.

⚠️ **Recompiler change l'identité de code du bundle.** Après un `./build.sh`, une
autorisation accordée explicitement doit être retirée puis remise.

## Ce qui n'est jamais lancé

| Écarté | Pourquoi |
|---|---|
| Jeux et lanceurs de jeux | Plusieurs gigaoctets de chargement pour une barre de menu vide. Détectés par la catégorie déclarée `*games*`, plus Steam qui n'en déclare aucune. `--include-games` les réintègre. |
| `~/Applications` | Emplacement des jeux installés par Steam. Réintégré par `--include-games`. |
| `~/Applications (Parallels)` | Passerelles vers un Windows en machine virtuelle — les ouvrir démarrerait la VM. Jamais réintégré. |
| Assistant de migration, Assistant Boot Camp | Les ouvrir ferme la session ou lance un partitionnement de disque. |
| Désinstalleurs | Rien à inventorier, action destructrice. |

## Limites connues

- **Apps à documents** (Word, Pages, Photoshop…) : lues sans document ouvert, leur
  barre de menu est plus pauvre qu'en usage réel. L'inventaire est alors partiel.
  Le rapport le signale app par app.
- **Apps agents** sans barre de menu : rien à lire, signalé en statut `sans_menu`.
- **Clavier de référence** : les combinaisons décrivent le clavier intégré, tel que
  `UCKeyTranslate` le rapporte. En AZERTY un chiffre demande Maj, d'où les ⇧ affichés
  sur des raccourcis qu'une app note « ⌃2 ». Un clavier externe à pavé numérique donne
  les chiffres sans Maj : la même commande y répond alors à une frappe plus courte.
  Le rapprochement des raccourcis n'en dépend pas — le pavé numérique porte ses propres
  codes de touches, distincts de la rangée du haut.
- **Apps bloquées au lancement** (licence, connexion) : coupées par le délai et
  signalées en `timeout`.
- Une passe `--all` **lance et quitte les apps une par une**. À faire quand la machine
  n'est pas en cours d'utilisation.

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
| Raccourcis globaux tiers | `Alfred.alfredpreferences`, `Keyboard Maestro Macros.plist`, préférences CleanShot X — lus, jamais écrits |

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
data/app-descriptions.json   rôles des apps (curé à la main)
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

Avant de publier, `./verifier-publication.sh` relit les fichiers versionnés **et
l'historique git** à la recherche de chemins absolus, de noms d'utilisateur, d'adresses
et d'identifiants de machine.

## Licence

Le modèle de priorité entre couches d'interception est repris de
[HotkeyClash](https://github.com/Wunderlandmedia/HotkeyClash), sous GPL-2.0. Usage
personnel sans conséquence ; une publication de ce projet poserait la question du
travail dérivé.

## Désactiver un raccourci système

Réglages Système → Clavier → Raccourcis clavier ne montre que les raccourcis
qu'Apple documente. Les autres vivent au même endroit sur le disque, mais sans
interface. Pour ceux-là :

```bash
python3 src/raccourci_systeme.py liste --actifs --inconnus   # ce qui n'est exposé nulle part
python3 src/raccourci_systeme.py off 62                       # essai à blanc
python3 src/raccourci_systeme.py off 62 --oui                 # applique
```

Rien n'est écrit sans `--oui`. Une sauvegarde horodatée du domaine complet est faite
avant toute modification, et la commande de retour en arrière est affichée.
