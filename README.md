# updatett

A small zsh updater for this workstation's global terminal tools. It shows
before/after versions, continues after individual failures, and returns a
nonzero exit status when any tool fails. No update logs are written or kept.
Wrangler's own debug-file logging and npm's debug logs are disabled for this run.

![updatett demo](assets/updatett-demo.gif)

## Tools

| Tool | Update command |
| --- | --- |
| uv (standalone) | `uv self update` |
| Ruff (global uv tool) | `uv tool upgrade ruff` |
| ty (global uv tool) | `uv tool upgrade ty` |
| Claude CLI (native) | `claude update` |
| Codex CLI (standalone) | `codex update` |
| nvm | Fetch official release tags and check out the latest stable release |
| Node.js (default LTS) | Install latest LTS, migrate global packages, retire the old default |
| npm | `nvm install-latest-npm` |
| Wrangler (global npm) | `npm install -g wrangler@latest` |
| 1Password CLI | Download with `op update`, verify and install the signed binary |

1Password's command checks and downloads the official macOS package. The updater
verifies its package signature, extracts the binary without running macOS Installer,
and verifies 1Password's signing identity before replacing the existing executable.
The installed binary must be a regular file writable by your account, as on this
workstation. Its location, owner and permissions are preserved. The updater stops
only the cache daemon, which restarts on the next authenticated use. If another
`op` command is running, the update fails so you can retry when it is finished.
Stable installs stay on stable; prerelease installs check beta.
Downloads and a temporary rollback copy are deleted on exit. An interrupted or
failed replacement restores the previous binary. No installer logs are created.
See the [official installation instructions](https://www.1password.dev/cli/get-started).

Wrangler uses nvm's **default** Node environment. Native CLIs and uv tools in
`~/.local/bin` take precedence over app-bundled executables. Updating these CLIs
does not update the ChatGPT or Claude desktop apps. Project dependencies and
Python runtimes are outside this script's scope. No Homebrew is used.
With npm 12, only the known Wrangler dependency install scripts (`esbuild`,
`workerd`, and `fsevents`) are allowed; unapproved new install scripts fail the update.

nvm is updated using its [documented Git upgrade procedure](https://github.com/nvm-sh/nvm#manual-upgrade).
The updater maintains the default Node at the latest LTS, updates npm, and migrates
global npm packages with nvm. It verifies the replacement before changing the
default and removing the superseded default installation. If that environment is
running software, migration fails so you can retry when it is idle. Other installed
Node versions are retained. After a Node migration, open a new terminal or run
`nvm use default` in existing terminals. Node installer archives are cleared on exit,
including downloads left by earlier installations. npm settings apply only to this
run; packages declaring incompatible Node requirements are rejected. Project files
and dependencies are never updated. nvm's normal migration excludes npm and Corepack;
npm is maintained separately. Corepack is not managed by this updater.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/),
[native Claude CLI](https://code.claude.com/docs/en/setup),
[standalone Codex CLI](https://developers.openai.com/codex/cli), and
[1Password CLI](https://www.1password.dev/cli/get-started) from their official sources.
Install [nvm](https://github.com/nvm-sh/nvm#installing-and-updating) and set up a default LTS Node.
Then install the global uv tools and Wrangler:

```sh
uv tool install ruff@latest
uv tool install ty@latest
nvm install --lts --latest-npm
nvm alias default "$(nvm current)"
nvm use default
npm install -g wrangler@latest --allow-scripts=esbuild,workerd,fsevents --strict-allow-scripts --logs-max=0
```

Missing tools are reported as failures; the updater does not silently install them.
It uses zsh's built-in file lock to prevent simultaneous runs and cancels update
processes and their children on INT/TERM. The empty lock file lives in the user's
temporary directory; the kernel releases its lock automatically on exit.

## Install and run

```sh
cp updatett /usr/local/bin/updatett
chmod +x /usr/local/bin/updatett
updatett
```

Copy the script again after changing it. To remove it:

```sh
rm /usr/local/bin/updatett
```

## Verification

```sh
zsh -n updatett
uv run --python 3.14 tests/test_updatett.py
ruff check --no-cache tests
ruff format --check --no-cache tests
ty check tests
```

The tests use fake tools and temporary directories; they never update installed software.
They use only Python's standard library. uv runs them with Python 3.14; the global
Ruff and ty tools check their style and types. No project environment or third-party
Python dependencies are needed. Python is used only for verification, not by the updater.
