# Ce qu'il faut savoir avant de lancer cet outil

Cet inventaire ne peut pas fonctionner sans deux choses inhabituelles : l'autorisation
la plus large que macOS sache accorder, et l'ouverture automatique de vos applications.
Ce fichier explique ce que cela implique, et ce que produit l'outil.

Il ne décrit aucune machine en particulier. Les constats propres à une installation
n'ont pas leur place dans un dépôt public.

---

## 1. L'autorisation d'accessibilité est la permission la plus large de macOS

Elle ne se limite pas à « voir les menus ». Elle permet de **lire le contenu des
fenêtres de n'importe quelle application et de piloter son interface** — cliquer, taper,
choisir dans un menu. C'est le niveau d'accès dont a besoin un enregistreur de frappe.

Le point décisif est **à qui** vous l'accordez.

- Accordée au **terminal**, macOS l'étend à *tout* ce que ce terminal exécute : chaque
  script, chaque installation de paquet, chaque commande copiée depuis un forum,
  aujourd'hui et pour toujours.
- Accordée à **`ShortcutHarvester.app`**, elle ne concerne que ce programme.

C'est précisément pour rendre ce choix possible que le projet compile une application
plutôt qu'un simple script.

**Mais il faut être honnête sur ce que la passe complète demande.** `run.sh` exécute le
binaire directement depuis le shell, et macOS attribue alors le droit au processus
responsable — le terminal. En pratique, un scan de toutes les applications suppose donc
le plus souvent d'avoir autorisé son terminal. Ouvrir et refermer les applications, en
revanche, ne demande aucune permission : c'est la lecture des menus qui l'exige.

Accordez cette autorisation **le temps de la passe, puis retirez-la**. `run.sh` vous le
rappelle à la fin d'une passe qui a ouvert des applications, et se tait quand
l'autorisation appartient bien au bundle — auquel cas il n'y a rien à retirer.

## 2. Ouvrir automatiquement toutes vos applications n'est pas anodin

Les raccourcis d'une application n'existent que dans sa barre de menu, une fois
l'application lancée. Une passe complète ouvre donc, une par une, la quasi-totalité de
vos applications, puis referme **uniquement celles qu'elle a ouvertes**, et jamais de
force.

Le programme tient une liste d'exclusion pour les applications dont le simple lancement
a un effet indésirable : un assistant qui ferme la session, un outil qui déclenche une
capture d'écran au démarrage. **C'est une liste de cas connus, construite au fil des
découvertes** — pas un jugement porté sur chaque application installée. Le risque qui
reste, c'est celle dont personne n'a encore catalogué le comportement au lancement.

Trois précautions :

- Avant la première passe complète, listez les cibles sans rien ouvrir :
  `bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester --all --dry-run`.
  Lisez la liste et écartez ce qui vous inquiète.
- Lancez la passe à un moment où voir des fenêtres surgir est acceptable, et où rien
  n'est en cours d'édition non enregistrée.
- Attendez-vous à ce que clients de synchronisation, VPN et vérificateurs de licence se
  connectent au réseau. Une passe complète, c'est un réveil simultané de tout votre parc
  logiciel.

## 3. La page produite est un portrait de votre machine

`out/` est ignoré par git, et c'est délibéré. La page contient l'inventaire de **tous
les logiciels installés**, le nom de la machine, des chemins absolus incluant votre nom
de compte, et surtout **le contenu de vos menus** : titres de signets de navigateur,
noms de macros d'automatisation, intitulés de scripts personnels.

L'inventaire logiciel seul est déjà une information précieuse pour qui vous viserait :
il révèle quel gestionnaire de mots de passe vous utilisez, quel VPN, quel outil
d'entreprise. C'est une carte de ce qu'il faut cibler.

Ne joignez jamais cette page à un rapport de bogue, à un partage de fichiers ou à une
conversation avec un assistant en ligne. Le rapport Markdown contient les mêmes données
sous une forme encore plus facile à indexer. Pour montrer un problème, montrez une
capture recadrée d'une ligne.

## 4. Restreindre l'accès aux fichiers produits

Depuis la version courante, `run.sh` place `out/` en accès exclusif à son propriétaire.
Si vous avez lancé une passe avec une version antérieure, corrigez-le une fois :

```bash
chmod -R go-rwx out
```

Ce détail compte sur une machine partagée — poste familial, Mac d'entreprise avec un
compte d'administration séparé, agent de gestion. La sortie dérive de dossiers qu'Apple
protège en accès exclusif ; la laisser lisible par les autres comptes annulerait cette
protection.

## 5. Les commandes à copier-coller : relisez-les

La page ne lance rien elle-même. Elle fabrique le texte d'une commande que vous copiez
dans un terminal — parce que l'autorisation d'accessibilité est hors de portée d'une
page web, et qu'il vaut mieux qu'il en soit ainsi.

Cette commande est assemblée à partir de données lues sur votre machine : les
identifiants des applications que vous cochez, le chemin du projet. Ces valeurs sont
citées pour le shell, apostrophes comprises, de sorte qu'une espace ou un caractère
inattendu dans un identifiant ne puisse pas découper la commande ni en ouvrir une autre.

Cela dit : **le bouton « copier » ne dispense pas de lire.** C'est le seul endroit du
projet où une donnée venue du système devient une instruction que vous exécutez.

C'est aussi pourquoi la commande énumère chaque identifiant d'application plutôt que de
renvoyer à un fichier : ce que vous collez est ce qui s'exécute, et rien ne s'exécute
qui ne soit écrit là. Une forme abrégée serait plus agréable à lire et strictement moins
sûre — l'effet réel dépendrait d'un fichier pouvant changer entre la copie et
l'exécution.

La commande affichée est recalculée à chaque modification de la sélection ; le
presse-papiers, lui, garde ce qu'on y a mis. Copiez juste avant de coller.

## 6. Le balayage des préférences ouvre bien plus que des raccourcis

Pour trouver les raccourcis globaux, l'outil ouvre **l'intégralité** du dossier de
préférences de l'utilisateur. Il ne peut pas faire autrement : chaque application range
ses raccourcis à sa façon, et une liste d'applications connues raterait silencieusement
la suivante.

Ce dossier contient bien autre chose que des raccourcis. Beaucoup d'applications y
stockent en clair des jetons d'authentification, des clés d'API et des clés de licence,
faute d'utiliser le trousseau.

Deux choses distinctes, à ne pas confondre :

1. **L'outil ne recopie rien de tout cela.** Il n'extrait que des champs de forme très
   précise — un code de touche et un masque de modificateurs — et ne conserve que le
   *nom* de la clé, jamais sa valeur.
2. **Mais il les ouvre.** Ce que cela vous apprend dépasse cet outil : *n'importe quel
   programme lancé sous votre compte* peut lire ces secrets, sans autorisation à
   demander. Les permissions de fichier n'y changent rien, puisque vous en êtes le
   propriétaire. Si vous n'aviez jamais regardé ce qui traîne dans vos préférences, le
   passage de cet outil est une bonne occasion de le faire.

## 7. Écrire dans les préférences système, et revenir en arrière

`src/raccourci_systeme.py` sait désactiver un raccourci système, y compris ceux
qu'aucun panneau de réglages n'expose. Rien n'est écrit sans un `--oui` explicite, une
sauvegarde horodatée du domaine complet est faite **avant** la modification, et la
commande exacte de retour arrière est affichée.

Deux réserves à connaître :

- **La sauvegarde est écrite dans `out/`**, le dossier que git ignore et qu'on efface
  pour repartir propre. Copiez-en une hors du projet avant votre première désactivation.
- **Le retour arrière restaure le domaine entier**, pas seulement le raccourci que vous
  aviez touché. Si vous avez modifié d'autres raccourcis entre-temps — par cet outil ou
  par les Réglages Système — restaurer une vieille sauvegarde les annule aussi.
  Restaurez toujours la sauvegarde la plus récente antérieure au changement à défaire.

## 8. Recompiler, c'est ré-accorder

macOS attache l'autorisation d'accessibilité à l'empreinte exacte du programme.
Remplacer le binaire invalide l'autorisation — c'est ce qui interdit à quiconque de
substituer un programme au vôtre pour hériter de vos droits. D'où la nécessité de
retirer puis remettre l'application après chaque `./build.sh`.

Le revers : `build.sh` compile ce qui se trouve dans le fichier source, quel qu'il soit.
La séquence `git pull`, `./build.sh`, puis ré-accorder l'autorisation revient à
**accorder la permission la plus large de macOS à du code que vous venez de télécharger
sans le lire**.

Prenez l'habitude de regarder ce qui a changé — `git diff` sur `src/Harvester.swift` —
avant de reconstruire. C'est le seul moment où votre attention protège vraiment
quelque chose.

---

## Ce que l'outil ne fait pas

Vérifiable dans le code, et utile à savoir pour un logiciel qu'on vous demande
d'autoriser aussi largement :

- **Aucun accès réseau, nulle part.** Ni dans les modules Python, ni dans le code Swift.
  L'outil ne télécharge rien, n'envoie rien, ne téléphone à personne.
- **Aucune commande passée au shell.** Les rares appels à des programmes du système
  passent par une liste d'arguments, jamais par une chaîne interprétée. Pas de
  `shell=True`, pas de `os.system`, pas de `eval`.
- **Les écritures sont confinées à `out/`**, à une exception intentionnelle et
  documentée : la désactivation d'un raccourci système, précédée d'une sauvegarde et
  verrouillée derrière `--oui`.
