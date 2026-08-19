# Overall-shortcuts-inventory-on-MacOS

Inventaire complet des raccourcis clavier d'un Mac : le système, puis application par
application, dans un seul document Markdown classé par catégorie.

> ⚠️ **Avant la première passe, lisez [SECURITE.md](SECURITE.md).** Cet outil exige
> l'autorisation d'accessibilité de macOS — la plus large du système — et ouvre
> automatiquement vos applications. Ce fichier explique ce que cela implique et les
> précautions à prendre.

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

**`out/raccourcis.html`** — une page autonome, six vues :

1. **Commandes par menu** — les raccourcis de l'app choisie, dans l'ordre de sa barre
   de menu, puis les raccourcis globaux rangés selon qu'ils agissent *dans* l'app,
   *sur* elle, ou à côté d'elle.
2. **Effet d'une frappe** — part de la touche et non de la commande : pour chaque
   combinaison atteignable dans cette app, qui la reçoit vraiment. Classée par nombre
   de touches.
3. **Conflits** — les combinaisons réclamées par plusieurs preneurs, avec qui gagne
   et pourquoi.
4. **Par combinaison** — chercher une touche ou une commande, et voir partout où elle sert.
5. **Raccourcis libres** — une grille unique à double entrée : les jeux de
   modificateurs en colonnes, groupés par nombre de touches et séparés par un trait ;
   toutes les touches attribuables en lignes, pavé numérique compris. Chaque case libre
   porte la combinaison entière, et un clic la met dans le presse-papiers. Une ligne
   sans aucune case libre est omise ; les combinaisons à cinq touches sont comptées,
   pas listées — à cette longueur il en reste toujours.
6. **Prochain scan** — le tableau des applications installées : version sur le disque,
   version au dernier relevé, statut, date, et trois cases — *scanner*, *exclure*,
   *outil de raccourcis*. Huit vues rapides restreignent la liste (à scanner, jamais
   lues, version majeure, outils de raccourcis, 0 raccourci, illisibles, exclues), et
   se combinent avec la recherche. L'écran ne lance rien : il produit la commande
   exacte à coller dans un terminal, et chaque étape indique si elle exige
   l'autorisation d'accessibilité.

L'interface est disponible en **français et en anglais** (drapeaux en haut à droite,
choix mémorisé). Le contenu lu dans macOS — chemins de menus, noms de commandes,
catégories — reste dans la langue du système et n'est pas traduit : le réécrire
reviendrait à altérer une donnée.

Un filtre unique (application, modificateurs, touche, nombre de touches, libellé)
s'applique aux quatre premières vues. Le filtre par application se désactive : tout est
alors montré, toutes apps confondues. Les deux dernières vues n'ont pas de filtre — une
combinaison libre n'appartient à aucune application, et le tableau du scan a sa propre
recherche.

### Doubles frappes

Certains raccourcis système ne sont pas une combinaison mais une **double frappe** sur
un modificateur seul — la dictée en est l'exemple courant. macOS les stocke avec
`type: "modifier"` et un masque distinguant la touche gauche de la droite (constantes
`NX_DEVICE*KEYMASK` d'IOKit). Les libellés viennent du panneau Clavier lui-même
(`DoubleTapCommandRight` → « Appuyer deux fois sur Commande de droite »). Ces
raccourcis sont marqués « double frappe » dans la page, et comptés comme **une** touche.

**`out/raccourcis.md`** — le même inventaire à plat, versionnable et relisible
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
./run.sh --sources  # ~10 s, n'ouvre aucune application
./run.sh --test     # 6 apps représentatives, pour valider la mécanique
./run.sh --all      # les apps installées
./run.sh --apps com.apple.Safari,com.apple.mail   # une liste précise


# Lister les cibles sans rien lancer :
bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester --all --dry-run
```

`--sources` relit ce qui se lit sans ouvrir d'application : raccourcis système,
préférences des outils, raccourcis redéfinis par l'utilisateur, recensement des apps
installées. Il relit aussi les fiches dont la version a changé, **à condition que
l'application soit déjà ouverte** (`--only-running`) — et refuse d'écraser une fiche
pleine par une fiche vide, une app ouverte sans document exposant moins de commandes.

La passe est **reprenable** : chaque app est écrite dans son propre JSON, une relance
saute ce qui existe déjà. `Ctrl-C` ne perd rien, et arrête aussi le moissonneur — lancé
par LaunchServices, il ne descend pas du shell et l'interruption ne l'atteindrait pas de
lui-même. `--force` refait tout.

Les exclusions et inclusions posées à la main depuis la page vivent dans
`out/reglages-scan.json`, que le moissonneur relit (`--reglages`). Une exclusion
verrouillée — une app dont le lancement déclenche une action destructrice — ne peut pas
être levée depuis la page.

### Options du moissonneur

`run.sh` les assemble ; elles sont listées ici parce que la page produit des commandes
qui les emploient, et qu'on demande de les relire avant de les coller.

| Option | Effet | Ouvre des apps |
|---|---|---|
| `--all` | cible toutes les apps installées non exclues | oui |
| `--bundle-ids a,b,c` | cible cette liste précise | oui |
| `--force` | refait les fiches déjà présentes, au lieu de les sauter | oui |
| `--only-running` | n'agit que sur les apps **déjà ouvertes** | non |
| `--keep-running` | ne referme pas ce qui a été ouvert | oui |
| `--include-games` | garde les jeux, écartés par défaut | oui |
| `--dry-run` | liste les cibles et s'arrête, avant toute écriture | non |
| `--catalogue` | recense les apps installées sur la sortie standard | non |
| `--keymap` | exporte la correspondance touche ↔ caractère | non |
| `--check` | vérifie l'autorisation d'accessibilité et s'arrête | non |
| `--verdict <fichier>` | y écrit le résultat de `--check` | non |
| `--journal <fichier>` | y recopie sortie standard et sortie d'erreur — `open` ne les relaie pas | — |
| `--statut <fichier>` | y écrit le code de sortie — `open` ne le rend pas davantage | — |
| `--reglages <fichier>` | exclusions et inclusions posées à la main | — |
| `--out <dossier>` | où écrire les fiches (`out/apps` par défaut) | — |
| `--timeout <secondes>` | délai par application, 25 s par défaut — il borne l'attente de la barre de menu **et** le parcours de l'arbre | — |

Les modes marqués « non » ne lisent aucune barre de menu : ils n'exigent donc pas
l'autorisation d'accessibilité.

## Autorisation d'accessibilité

Lire les menus d'une autre app l'exige. `run.sh` la vérifie avant de commencer et
s'arrête avec un message clair si elle manque.

macOS n'accorde jamais ce droit au binaire exécuté, mais au **processus responsable** —
celui qui l'a lancé. Un binaire lancé depuis un terminal rend donc le terminal
responsable, et c'est *lui* qu'il faudrait autoriser : le droit s'étendrait alors à tout
ce que ce terminal exécute, aujourd'hui et plus tard.

C'est pourquoi `run.sh` ne lance pas le moissonneur depuis le shell, mais **par
LaunchServices** (`open`). Le bundle est alors son propre processus responsable :
l'autoriser lui seul suffit, et **aucun terminal n'a besoin de quoi que ce soit**.

Le prix du détour : `open` ne rend ni la sortie du programme, ni son code d'erreur. Le
moissonneur recopie donc sa progression dans le fichier passé à `--journal`, que `run.sh`
relaie en direct, et son code de sortie dans celui passé à `--statut`, dont l'apparition
est le seul signal de fin fiable.

### Autoriser le moissonneur

Le bundle est compilé dans le projet, pas installé : il n'apparaît **pas** dans
`/Applications`, et il n'a pas d'icône dans le Dock. Il faut donc aller le chercher.

```bash
open -R bin/ShortcutHarvester.app        # le révèle dans le Finder
```

Ouvrir Réglages Système → **Confidentialité et sécurité** → Accessibilité, puis **faire
glisser l'app depuis la fenêtre du Finder** dans la liste. Le bouton `+` s'ouvre sur
`/Applications` et navigue mal vers un dossier de projet ; le glisser-déposer est plus
sûr.

Vérifier ensuite — en passant par LaunchServices, sans quoi c'est le terminal qu'on
interroge et non le bundle :

```bash
open -n -a "$(pwd)/bin/ShortcutHarvester.app" --args --check --verdict /tmp/verdict
sleep 1 && cat /tmp/verdict          # « accordee » ou « absente »
```

Si la réponse est `absente` alors que l'app figure bien dans la liste, l'entrée date
d'une compilation antérieure : l'autorisation est liée à l'empreinte exacte du binaire,
qu'un aller-retour de l'interrupteur ne réenregistre pas. La retirer avec `−`, puis la
remettre.

### Trois cases, et ce qu'elles veulent dire

- **Scanner** — l'application sera relue à la prochaine passe. Cochée d'office
  lorsqu'elle n'a jamais été lue, ou que le premier nombre de son numéro de version a
  changé. Le programme ne coche jamais rien de lui-même en dehors de cette proposition :
  `run.sh` ne scanne que ce qui est explicitement demandé.
- **Exclure** — l'application est écartée de toute passe, et le choix est conservé dans
  `out/reglages-scan.json`. Quelques exclusions sont verrouillées : celles dont le
  lancement déclenche une action lourde ou destructrice.
- **Outil de raccourcis** — l'application déclare des raccourcis globaux, qui
  l'emportent sur les menus de toutes les autres. La case est cochée **par le
  programme** quand il en a trouvé dans ses préférences : c'est un constat, il ne se
  décoche pas. Les autres cases restent libres, pour désigner une application dont le
  format de rangement n'est pas encore reconnu.

Le statut répond à une question étroite : « la barre de menu était-elle lisible ». Une
lecture qui aboutit sans rien trouver s'affiche donc **0 raccourci** plutôt qu'un « ok »
trompeur — c'est le cas d'une application arrêtée sur un sélecteur de projet, comme des
utilitaires qui n'ont pas de barre de menu classique.

### Ce que la passe complète demande vraiment

Deux gestes distincts, deux exigences distinctes :

| Geste | Autorisation |
|---|---|
| Ouvrir et refermer une application | **aucune** |
| Lire sa barre de menu | accessibilité |

C'est bien `ShortcutHarvester` qui ouvre et referme les applications, sans qu'aucune
permission n'y soit nécessaire. Et comme `run.sh` le lance par LaunchServices, c'est lui
que macOS interroge pour la lecture des menus : **une passe complète ne demande aucune
autorisation au terminal.**

C'était le geste le plus large du projet, et il n'est plus nécessaire. `run.sh` vérifie
donc l'inverse en fin de passe : si le shell d'où il tourne détient malgré tout
l'autorisation d'accessibilité — reste d'une version antérieure de cet outil, ou d'un
autre besoin — il le signale. Tant qu'elle reste accordée, *tout* ce que ce terminal
exécutera pourra lire et piloter n'importe quelle application.

### Où regarder

Réglages Système → Confidentialité et sécurité → Accessibilité. Ce qui mérite une
question, au-delà de ce que vous y avez mis pour ce projet :

- **Terminaux** — Terminal, iTerm2, Warp, Ghostty, kitty, Alacritty, WezTerm, Hyper,
  Tabby, cmux.
- **Éditeurs et environnements de développement**, qui embarquent un terminal :
  Visual Studio Code, Cursor, Zed, Sublime Text, Xcode, les IDE JetBrains, et les
  environnements agentiques, qui exécutent des commandes de leur propre initiative.
- **Outils d'automatisation** qui exécutent des scripts : Keyboard Maestro, Alfred,
  Raycast, Hammerspoon, BetterTouchTool, SwiftBar, Automator, Éditeur de script,
  Raccourcis.

Les outils de la troisième catégorie ont souvent **besoin** de cette autorisation pour
fonctionner — simuler une frappe, piloter une fenêtre. Les y trouver est normal. Ce
qu'il faut en retenir est autre : les scripts qu'ils exécutent en héritent.

### Pourquoi la commande produite est longue

Elle énumère chaque identifiant d'application au lieu de renvoyer à un fichier. C'est
délibéré : **ce que vous collez est ce qui s'exécute.** Trois opérations, toutes
visibles — se placer, écrire les réglages, moissonner cette liste-là puis reconstruire.
Un identifiant anormal s'y verrait.

Une forme abrégée dirait « exécute ce qui se trouve dans ce fichier » : vous colleriez
alors une instruction dont l'effet n'apparaît pas dans le texte collé, et qui dépend
d'un fichier pouvant changer entre la copie et l'exécution. Le gain serait cosmétique,
la perte réelle.

La commande affichée suit la sélection : cocher ou décocher une case la recalcule
aussitôt. Le presse-papiers, lui, garde ce qu'on y a mis — **copiez juste avant de
coller**.

⚠️ **Recompiler change l'identité de code du bundle.** Après un `./build.sh`,
l'autorisation tombe : `run.sh` s'arrête, et il faut retirer puis remettre l'app dans la
liste. C'est une protection — elle interdit de substituer un programme au vôtre pour
hériter de vos droits. Elle implique aussi de regarder ce qui a changé avant de
reconstruire : voir [SECURITE.md](SECURITE.md).

## Ce qui n'est jamais lancé

| Écarté | Pourquoi |
|---|---|
| Jeux et lanceurs de jeux | Plusieurs gigaoctets de chargement pour une barre de menu vide. Détectés par la catégorie déclarée `*games*`, plus Steam qui n'en déclare aucune. `--include-games` les réintègre. |
| `~/Applications` | Dossier d'applications personnel, le plus souvent une bibliothèque de jeux. Réintégré par `--include-games`. |
| `~/Applications (Parallels)` | Passerelles vers un Windows en machine virtuelle — les ouvrir démarrerait la VM. Jamais réintégré. |
| Assistant de migration, Assistant Boot Camp, Time Machine | Les ouvrir ferme la session, lance un partitionnement de disque ou confisque l'écran. |
| Déclencheurs système (Mission Control, Siri, Capture d'écran, Apps, Recopie de l'iPhone) | Ce ne sont pas des applications mais des boutons : aucune barre de menu. Leurs raccourcis sont inventoriés côté système, rien n'est perdu. |
| Désinstalleurs | Reconnus à leur nom (« uninstall », « désinstall »), quel que soit l'éditeur. Rien à inventorier, action destructrice. |

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

## Licence

**GPL-2.0** — voir [LICENSE](LICENSE).

Le modèle de priorité entre couches d'interception, ainsi que la manière de lire les
raccourcis de menu via l'API d'accessibilité, sont repris de
[HotkeyClash](https://github.com/Wunderlandmedia/HotkeyClash) de Wunderlandmedia,
distribué sous GPL-2.0. Ce projet adopte donc la même licence.

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
