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

`out/raccourcis-macos.md` :

1. **Raccourcis système** — les ~100 raccourcis macOS, en français, avec leur état
   (défaut / redéfini / désactivé).
2. **Raccourcis par application** — groupés par catégorie, chaque app avec sa version
   et une description de son rôle.
3. **Applications non lisibles** — avec la raison. Jamais d'omission silencieuse.

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
| `~/Applications` | Bibliothèque Steam : 23 jeux sur 25 apps. Réintégré par `--include-games`. |
| `~/Applications (Parallels)` | Passerelles vers un Windows en machine virtuelle — les ouvrir démarrerait la VM. Jamais réintégré. |
| Assistant de migration, Assistant Boot Camp | Les ouvrir ferme la session ou lance un partitionnement de disque. |
| Désinstalleurs | Rien à inventorier, action destructrice. |

## Limites connues

- **Apps à documents** (Word, Pages, Photoshop…) : lues sans document ouvert, leur
  barre de menu est plus pauvre qu'en usage réel. L'inventaire est alors partiel.
  Le rapport le signale app par app.
- **Apps agents** sans barre de menu : rien à lire, signalé en statut `sans_menu`.
- **Apps bloquées au lancement** (licence, connexion) : coupées par le délai et
  signalées en `timeout`.
- Une passe `--all` **lance et quitte les apps une par une**. À faire quand la machine
  n'est pas en cours d'utilisation.

## D'où viennent les données

Aucune table n'est écrite de mémoire — tout est extrait de macOS :

| Donnée | Source sur la machine |
|---|---|
| Les ~100 raccourcis système + leurs libellés français | `KeyboardSettings.appex/…/DefaultShortcutsTable.xml` + `.loctable` |
| État réel (activé, redéfini) | `defaults export com.apple.symbolichotkeys` |
| Codes de touches et glyphes de menu | `HIToolbox.framework/…/BridgeSupport` (énumérations Carbon `kVK_*` et `kMenu*Glyph`) |
| Raccourcis d'app | API d'accessibilité, attributs `AXMenuItemCmdChar` / `CmdGlyph` / `CmdModifiers` |
| Catégorie et version d'app | `LSApplicationCategoryType` et `CFBundleShortVersionString` de chaque `Info.plist` |
| Raccourcis redéfinis par l'utilisateur | `NSUserKeyEquivalents` dans les préférences de chaque app |

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
