<div align="center">

# Overall-shortcuts-inventory-on-MacOS

**Tous les raccourcis clavier de votre Mac, dans une seule page.**

Le système, les outils tiers, et chaque application installée — lus un par un,
puis rassemblés dans une page qu'on ouvre d'un double-clic.

![macOS 14 ou plus récent](https://img.shields.io/badge/macOS-14%2B-1d1d1f?logo=apple&logoColor=white)
![Licence GPL-2.0](https://img.shields.io/badge/licence-GPL--2.0-0a6b7c)
![Interface en français et en anglais](https://img.shields.io/badge/interface-fran%C3%A7ais%20%7C%20english-6b5b95)
![Aucun accès réseau](https://img.shields.io/badge/acc%C3%A8s%20r%C3%A9seau-aucun-2e7d32)

</div>

> [!WARNING]
> Cet outil exige l'**autorisation d'accessibilité** de macOS et **ouvre automatiquement
> vos applications** pour lire leurs menus. Lisez [SECURITE.md](SECURITE.md) avant la
> première passe : ce qu'il demande, ce qu'il produit, et ce qu'il ne fait pas.

## Le problème

Vous voulez attribuer un raccourci et vous ne savez pas ce qui est déjà pris. Vous en
tapez un, et c'est une autre commande qui répond. Personne ne peut vous dire quelles
touches sont libres sur votre machine.

Aucun outil ne le dit, et pour une raison de fond : **les raccourcis d'une application ne
sont écrits nulle part sur le disque.** Ils sont construits en mémoire à son lancement, et
ne sont lisibles que dans la barre de menu vivante. Les outils existants se contentent
donc de l'application active, ou de celles déjà ouvertes.

Celui-ci les ouvre une par une pour les lire, puis les referme.

## Ce que vous obtenez

Une page HTML **autonome** — aucun serveur, aucune dépendance, elle s'ouvre dans le
navigateur et fonctionne hors ligne. Six vues, en français et en anglais.

| Vue | La question à laquelle elle répond |
|---|---|
| **Commandes par menu** | Qu'est-ce qui est tapable dans cette application ? |
| **Effet d'une frappe** | Si j'appuie là-dessus ici, qui reçoit la touche ? |
| **Conflits** | Qu'est-ce qui se dispute une combinaison, et qui gagne ? |
| **Par combinaison** | Où cette combinaison sert-elle, partout sur la machine ? |
| **Raccourcis libres** | Qu'est-ce qui reste, que je peux attribuer sans rien casser ? |
| **Prochain scan** | Qu'est-ce qui a bougé depuis la dernière fois ? |

La vue **Raccourcis libres** croise les jeux de modificateurs et toutes les touches
attribuables, pavé numérique compris : chaque case libre porte la combinaison entière, et
un clic la met dans le presse-papiers.

Un **rapport Markdown** reprend le même inventaire à plat, versionnable et relisible
hors ligne.

## Démarrer

```bash
git clone https://github.com/iconoclasteee/Overall-shortcuts-inventory-on-MacOS.git
cd Overall-shortcuts-inventory-on-MacOS

./build.sh          # compile le moissonneur (une fois)
./run.sh --sources  # ~10 s, n'ouvre aucune application
open out/raccourcis.html
```

`--sources` donne déjà les raccourcis système, ceux des outils tiers et ceux que vous
avez redéfinis. Pour couvrir vos applications, il faut les ouvrir une par une : la page
fabrique la commande exacte, vous la collez dans un terminal.

Autoriser le moissonneur est un geste à part, décrit dans
[Utilisation](docs/utilisation.md#autorisation-daccessibilité).

## Ce qui rend l'inventaire juste

Trois partis pris qui distinguent cet outil d'une liste recopiée :

- **La disposition clavier fait foi, pas le code de touche.** Une table ANSI donne des
  résultats faux en AZERTY. La correspondance est demandée au système pour la disposition
  réellement en service, aux deux niveaux — avec et sans Maj.
- **Un conflit se tranche par couche d'interception.** Une frappe descend une pile —
  pilote clavier, capture d'événements, raccourci système, raccourci global, menu — et le
  premier étage servi avale la touche. À égalité d'étage, rien sur le disque ne dit qui
  gagne : l'outil annonce « égalité » plutôt que de désigner un vainqueur au hasard.
- **Aucune table n'est écrite de mémoire.** Codes de touches, glyphes de menu, raccourcis
  système et leurs libellés traduits sont extraits des fichiers de macOS lui-même.

Et ce qu'il ne fait pas, vérifiable dans le code : **aucun accès réseau, aucune commande
passée au shell**, écritures confinées à `out/`, qui n'est jamais versionné — la page
produite est un portrait de votre machine.

## Aller plus loin

| | |
|---|---|
| [**SECURITE.md**](SECURITE.md) | Ce que l'outil demande à votre machine, et pourquoi. **À lire avant la première passe.** |
| [**docs/utilisation.md**](docs/utilisation.md) | Modes, options, autorisation d'accessibilité, ce qui n'est jamais lancé, limites connues |
| [**docs/architecture.md**](docs/architecture.md) | D'où viennent les données, comment un conflit est tranché, structure du dépôt |

## Licence

**GPL-2.0** — voir [LICENSE](LICENSE).

Le modèle de priorité entre couches d'interception, ainsi que la manière de lire les
raccourcis de menu via l'API d'accessibilité, sont repris de
[HotkeyClash](https://github.com/Wunderlandmedia/HotkeyClash) de Wunderlandmedia,
distribué sous GPL-2.0. Ce projet adopte donc la même licence.

Alternatives étudiées avant de construire — CheatSheet, KeyCue,
[KeyMinder](https://keyminder.app/), HotkeyClash : toutes sont des consultations à la
volée, aucune ne produit d'inventaire complet. Le détail de l'arbitrage est dans
[docs/architecture.md](docs/architecture.md).
