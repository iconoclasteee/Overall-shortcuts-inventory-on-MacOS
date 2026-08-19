# What to know before running this tool

This inventory cannot work without two unusual things: the broadest permission macOS can
grant, and launching your applications automatically. This file explains what that means,
and what the tool produces.

It describes no machine in particular. Findings specific to one installation have no
place in a public repository.

---

## 1. Accessibility permission is the broadest macOS grants

It is not limited to "seeing menus". It allows a program to **read the contents of any
application's windows and drive its interface** — click, type, pick from a menu. This is
the level of access a keylogger needs.

What matters is **who** you grant it to.

- Granted to a **terminal**, macOS extends it to *everything* that terminal runs: every
  script, every package install, every command pasted from a forum, today and forever.
- Granted to **`ShortcutHarvester.app`**, it covers that program and nothing else.

Making that choice possible is precisely why this project builds an application rather
than a plain script.

**What decides who macOS grants it to is not the binary being executed, but the
responsible process** — the one that launched it. A binary launched from a terminal makes
the terminal responsible, and it is then the terminal you would have to authorise.

So `run.sh` launches the harvester **through LaunchServices** rather than from the shell.
The bundle is its own responsible process, and no terminal needs the permission — not
even for a full pass. Opening and closing applications requires none anyway: it is
reading the menus that demands it.

If a terminal holds that right regardless — left over from an earlier version of this
tool, or from something else — `run.sh` says so at the end of a pass. Revoke it: for as
long as it stands, every script, every package install, every command pasted from a forum
can read and drive any application.

## 2. Launching all your applications automatically is not harmless

An application's shortcuts exist only in its menu bar, once the application is running. A
full pass therefore opens nearly all of your applications, one by one, then closes
**only the ones it opened**, and never by force.

The program keeps an exclusion list for applications whose mere launch has an unwanted
effect: an assistant that logs you out, a tool that fires a screen capture on startup.
**It is a list of known cases, built as they were discovered** — not a judgement passed on
every installed application. The remaining risk is the one whose launch behaviour nobody
has catalogued yet.

Three precautions:

- Before the first full pass, list the targets without opening anything:
  `bin/ShortcutHarvester.app/Contents/MacOS/ShortcutHarvester --all --dry-run`.
  Read the list and rule out whatever worries you.
- Run the pass at a time when seeing windows appear is acceptable, and when nothing is
  being edited unsaved.
- Expect sync clients, VPNs and licence checkers to reach the network. A full pass wakes
  your entire software estate at once.

## 3. The page it produces is a portrait of your machine

`out/` is git-ignored, and that is deliberate. The page contains an inventory of **every
piece of software installed**, the machine name, absolute paths including your account
name, and above all **the contents of your menus**: browser bookmark titles, automation
macro names, personal script labels.

The software inventory alone is valuable to anyone targeting you: it reveals which
password manager you use, which VPN, which corporate tool. It is a map of what to aim at.

Never attach this page to a bug report, a file share, or a conversation with an online
assistant. The Markdown report holds the same data in a form that is even easier to index.
To show a problem, show a cropped screenshot of a single line.

## 4. Restrict access to the files it produces

As of the current version, `run.sh` makes `out/` owner-only. If you ran a pass with an
earlier version, fix it once:

```bash
chmod -R go-rwx out
```

This matters on a shared machine — a family Mac, a corporate Mac with a separate admin
account, a management agent. The output derives from folders Apple keeps owner-only;
leaving it readable by other accounts would undo that protection.

## 5. The commands you copy and paste: read them

The page runs nothing itself. It builds the text of a command that you copy into a
terminal — because accessibility permission is out of reach of a web page, and it is
better that way.

That command is assembled from data read on your machine: the bundle identifiers of the
applications you tick, the project path. Those values are shell-quoted, apostrophes
included, so that a space or an unexpected character in an identifier cannot split the
command or open a second one.

That said: **the "copy" button does not excuse you from reading.** This is the one place
in the project where data coming from the system becomes an instruction you execute.

It is also why the command spells out every application identifier rather than pointing at
a file: what you paste is what runs, and nothing runs that is not written there. A shorter
form would read more pleasantly and be strictly less safe — its real effect would depend
on a file that could change between the copy and the execution.

The displayed command is recomputed on every change to the selection; the clipboard keeps
whatever you last put in it. Copy right before you paste.

## 6. Sweeping the preferences folder opens far more than shortcuts

To find global hotkeys, the tool opens **the whole** user preferences folder. It cannot do
otherwise: every application stores its shortcuts its own way, and a list of known
applications would silently miss the next one.

That folder holds a great deal more than shortcuts. Many applications store authentication
tokens, API keys and licence keys there in the clear, rather than using the keychain.

Two distinct things, not to be confused:

1. **The tool copies none of it.** It extracts only fields of a very precise shape — a key
   code and a modifier mask — and keeps only the *name* of the key, never its value.
2. **But it opens them.** What that tells you goes beyond this tool: *any program running
   under your account* can read those secrets, with no permission to ask for. File
   permissions change nothing, since you own them. If you have never looked at what sits
   in your preferences, this tool passing through is a good occasion to do so.

## 7. Writing to system preferences, and undoing it

`src/raccourci_systeme.py` can disable a system shortcut, including those no settings
panel exposes. Nothing is written without an explicit `--oui`, a timestamped backup of the
whole domain is taken **before** the change, and the exact command to undo it is printed.

Two caveats:

- **The backup is written to `out/`**, the folder git ignores and that you delete to start
  clean. Copy one outside the project before your first disabling.
- **Undoing restores the entire domain**, not just the shortcut you touched. If you have
  changed other shortcuts in the meantime — through this tool or through System Settings —
  restoring an old backup undoes those too. Always restore the most recent backup that
  predates the change you want to reverse.

## 8. Rebuilding means re-granting

macOS ties accessibility permission to the exact fingerprint of the program. Replacing the
binary invalidates the grant — that is what stops anyone from substituting a program for
yours to inherit your rights. Hence the need to remove and re-add the application after
every `./build.sh`.

The flip side: `build.sh` compiles whatever is in the source file. The sequence `git
pull`, `./build.sh`, then re-granting the permission amounts to **granting the broadest
permission in macOS to code you have just downloaded without reading it**.

Get into the habit of looking at what changed — `git diff` on `src/Harvester.swift` —
before you rebuild. That is the one moment where your attention actually protects
something.

---

## What the tool does not do

Verifiable in the source, and worth knowing about software you are asked to authorise this
broadly:

- **No network access, anywhere.** Neither in the Python modules nor in the Swift code.
  The tool downloads nothing, sends nothing, phones nobody.
- **No command passed to a shell.** The few calls to system programs go through an
  argument list, never an interpreted string. No `shell=True`, no `os.system`, no `eval`.
- **Writes are confined to `out/`**, with one intentional and documented exception:
  disabling a system shortcut, preceded by a backup and locked behind `--oui`.
