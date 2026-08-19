# Usage

Full guide to the harvester and its modes. For what the tool produces and why, see the
[README](../README.md); for what it asks of your machine, [SECURITY.md](../SECURITY.md).

---

## The modes

```bash
./build.sh          # builds the harvester (once)
./run.sh --sources  # ~10 s, opens no application
./run.sh --test     # 6 representative apps, to validate the mechanics
./run.sh --all      # every installed app
./run.sh --apps com.apple.Safari,com.apple.mail   # a specific list

# List the targets without launching anything:
bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester --all --dry-run
```

`--sources` re-reads everything that can be read without opening an application: system
shortcuts, tool preferences, user-redefined shortcuts, and the census of installed apps.
It also re-reads records whose version has changed, **provided the application is already
running** (`--only-running`) — and refuses to overwrite a full record with an empty one,
since an app opened without a document exposes fewer commands.

A pass is **resumable**: each app is written to its own JSON file, and a re-run skips what
is already there. `Ctrl-C` loses nothing, and also stops the harvester — launched through
LaunchServices, it does not descend from the shell and the interrupt would not reach it on
its own. `--force` redoes everything.

Exclusions and inclusions set by hand from the page live in `out/reglages-scan.json`,
which the harvester reads back (`--reglages`). A locked exclusion — an app whose launch
triggers a destructive action — cannot be lifted from the page.

### Harvester options

`run.sh` assembles them; they are listed here because the page produces commands that use
them, and you are asked to read those commands before pasting them.

| Option | Effect | Opens apps |
|---|---|---|
| `--all` | targets every installed, non-excluded app | yes |
| `--bundle-ids a,b,c` | targets this specific list | yes |
| `--force` | redoes records already present instead of skipping them | yes |
| `--only-running` | acts only on apps **already running** | no |
| `--keep-running` | does not close what it opened | yes |
| `--include-games` | keeps games, skipped by default | yes |
| `--dry-run` | lists the targets and stops, before any write | no |
| `--catalogue` | writes the census of installed apps to standard output | no |
| `--keymap` | exports the key ↔ character mapping | no |
| `--check` | checks accessibility permission and stops | no |
| `--verdict <file>` | writes the result of `--check` there | no |
| `--journal <file>` | copies standard output and standard error there — `open` relays neither | — |
| `--statut <file>` | writes the exit code there — `open` does not return it either | — |
| `--reglages <file>` | exclusions and inclusions set by hand | — |
| `--out <folder>` | where to write the records (`out/apps` by default) | — |
| `--timeout <seconds>` | per-application budget, 25 s by default — it bounds both the wait for the menu bar **and** the walk through its tree | — |

Modes marked "no" read no menu bar: they therefore require no accessibility permission.

⚠️ **Paths passed to the harvester must be absolute.** LaunchServices does not pass on the
working directory: launched by `open`, the program starts at the root of the disk, where
`out/apps` means `/out/apps`. `run.sh` takes care of this; on the command line, you do.
The program now refuses to start rather than open applications only to write nowhere.

## Accessibility permission

Reading another app's menus requires it. `run.sh` checks before starting and stops with a
clear message if it is missing.

macOS never grants that right to the binary being executed, but to the **responsible
process** — the one that launched it. A binary launched from a terminal therefore makes
the terminal responsible, and it is *the terminal* you would have to authorise: the right
would then extend to everything that terminal runs, today and later.

That is why `run.sh` does not launch the harvester from the shell, but **through
LaunchServices** (`open`). The bundle is then its own responsible process: authorising it
alone is enough, and **no terminal needs anything at all**.

The price of the detour: `open` returns neither the program's output nor its exit code. So
the harvester copies its progress into the file passed to `--journal`, which `run.sh`
relays live, and its exit code into the one passed to `--statut`, whose appearance is the
only reliable end-of-run signal.

### Authorising the harvester

The bundle is built inside the project, not installed: it does **not** appear in
`/Applications`, and it has no Dock icon. You have to go and find it.

```bash
open -R bin/ShortcutHarvester.app        # reveals it in the Finder
```

Open System Settings → **Privacy & Security** → Accessibility, then **drag the app from
the Finder window** into the list. The `+` button opens on `/Applications` and navigates
poorly to a project folder; drag and drop is safer.

Then check — going through LaunchServices, otherwise you are asking about the terminal
rather than the bundle:

```bash
rm -f /tmp/verdict                   # otherwise you re-read the previous run's verdict
open -n -a "$(pwd)/bin/ShortcutHarvester.app" --args --check --verdict /tmp/verdict
until [ -f /tmp/verdict ]; do sleep 0.2; done; cat /tmp/verdict   # "accordee" or "absente"
```

If the answer is `absente` while the app is plainly in the list, the entry dates from an
earlier build: the grant is tied to the exact fingerprint of the binary, which toggling
the switch off and on does not re-record. Remove it with `−`, then add it back.

### The three checkboxes, and what they mean

- **Scan** — the application will be re-read on the next pass. Ticked by default when it
  has never been read, or when the first number of its version has changed. The program
  never ticks anything of its own accord beyond that suggestion: `run.sh` scans only what
  is explicitly asked of it.
- **Exclude** — the application is kept out of every pass, and the choice is stored in
  `out/reglages-scan.json`. A few exclusions are locked: those whose launch triggers a
  heavy or destructive action.
- **Hotkey tool** — the application declares global hotkeys, which win over every other
  application's menus. This box is ticked **by the program** when it finds them in the
  app's preferences: it is an observation, and it does not untick. The other boxes stay
  free, so you can flag an application whose storage format is not recognised yet.

The status answers a narrow question: "was the menu bar readable". A read that completes
without finding anything therefore shows **0 shortcuts** rather than a misleading "ok" —
which is the case for an application sitting on a project picker, or for utilities with no
conventional menu bar.

### What a full pass really requires

Two distinct actions, two distinct requirements:

| Action | Permission |
|---|---|
| Opening and closing an application | **none** |
| Reading its menu bar | accessibility |

It is indeed `ShortcutHarvester` that opens and closes the applications, with no permission
needed for that. And since `run.sh` launches it through LaunchServices, it is the harvester
macOS asks about when the menus are read: **a full pass requires no permission from the
terminal.**

That used to be the broadest action in the project, and it is no longer necessary. So
`run.sh` checks the opposite at the end of a pass: if the shell it runs from holds
accessibility permission regardless — left over from an earlier version of this tool, or
from something else — it says so. For as long as it stands, *everything* that terminal runs
can read and drive any application.

### Where to look

System Settings → Privacy & Security → Accessibility. What deserves a question, beyond
what you put there for this project:

- **Terminals** — Terminal, iTerm2, Warp, Ghostty, kitty, Alacritty, WezTerm, Hyper,
  Tabby, cmux.
- **Editors and development environments**, which embed a terminal: Visual Studio Code,
  Cursor, Zed, Sublime Text, Xcode, the JetBrains IDEs, and agentic environments, which
  run commands on their own initiative.
- **Automation tools** that run scripts: Keyboard Maestro, Alfred, Raycast, Hammerspoon,
  BetterTouchTool, SwiftBar, Automator, Script Editor, Shortcuts.

Tools in the third category often **need** this permission to work at all — simulating a
keystroke, driving a window. Finding them there is normal. The point is different: the
scripts they run inherit it.

### Why the generated command is long

It spells out every application identifier instead of pointing at a file. This is
deliberate: **what you paste is what runs.** Three operations, all visible — change
directory, write the settings, harvest that particular list and rebuild. An abnormal
identifier would be visible in it.

A shorter form would say "run whatever is in this file": you would then be pasting an
instruction whose effect does not appear in the pasted text, and which depends on a file
that could change between the copy and the execution. The gain would be cosmetic, the loss
real.

The displayed command follows the selection: ticking or unticking a box recomputes it
immediately. The clipboard, however, keeps whatever you last put in it — **copy right
before you paste**.

⚠️ **Rebuilding changes the bundle's code identity.** After a `./build.sh` the grant
lapses: `run.sh` stops, and you have to remove and re-add the app in the list. This is a
protection — it forbids substituting a program for yours to inherit your rights. It also
means looking at what changed before rebuilding: see [SECURITY.md](../SECURITY.md).

## What is never launched

| Skipped | Why |
|---|---|
| Games and game launchers | Gigabytes of loading for an empty menu bar. Detected by the declared `*games*` category, plus Steam, which declares none. `--include-games` brings them back. |
| `~/Applications` | Personal application folder, most often a game library. Brought back by `--include-games`. |
| `~/Applications (Parallels)` | Gateways to a Windows virtual machine — opening one would boot the VM. Never brought back. |
| Migration Assistant, Boot Camp Assistant, Time Machine | Opening these logs you out, starts a disk partitioning, or takes over the screen. |
| System triggers (Mission Control, Siri, Screenshot, Apps, iPhone Mirroring) | These are not applications but buttons: no menu bar. Their shortcuts are inventoried on the system side, so nothing is lost. |
| Uninstallers | Recognised by name ("uninstall", "désinstall"), whichever vendor. Nothing to inventory, destructive action. |

## Known limits

- **Document-based apps** (Word, Pages, Photoshop…): read without a document open, their
  menu bar is poorer than in real use. The inventory is then partial. The report flags this
  app by app.
- **Agent apps** with no menu bar: nothing to read, reported as status `sans_menu`.
- **Reference keyboard**: combinations describe the built-in keyboard, as `UCKeyTranslate`
  reports it. On AZERTY a digit needs Shift, hence the ⇧ shown on shortcuts an app writes
  as "⌃2". An external keyboard with a numeric keypad gives digits without Shift: the same
  command then answers a shorter keystroke. Matching shortcuts does not depend on this —
  the numeric keypad carries its own key codes, distinct from the top row.
- **Apps blocked at launch** (licence, sign-in): cut off by the timeout and reported as
  `timeout`.
- An `--all` pass **launches and quits apps one by one**: at any moment, exactly one
  application is open because of the tool, with no stolen focus and no visible window. Run
  it when the machine is not in use.
- A `Ctrl-C` closes the application currently being read before returning, if the tool is
  the one that opened it. An application you had opened yourself is never touched, neither
  during the pass nor on interruption.

## Disabling a system shortcut

System Settings → Keyboard → Keyboard Shortcuts shows only the shortcuts Apple documents.
The others live in the same place on disk, but with no interface. For those:

```bash
python3 src/raccourci_systeme.py liste --actifs --inconnus   # what is exposed nowhere
python3 src/raccourci_systeme.py off 62                       # dry run
python3 src/raccourci_systeme.py off 62 --oui                 # apply
```

Nothing is written without `--oui`. A timestamped backup of the whole domain is taken
before any change, and the command to undo it is printed.
