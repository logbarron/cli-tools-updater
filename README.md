# updatett

A small zsh updater for this workstation's global terminal tools. It shows
before/after versions, continues after individual failures, and returns a
nonzero exit status when any tool fails. No update logs are written or kept.
Wrangler's own debug-file logging and npm's debug logs are disabled for this run.

## Tools

| Tool | Update command |
| --- | --- |
| uv (standalone) | `uv self update` |
| Ruff (global uv tool) | `uv tool upgrade ruff` |
| ty (global uv tool) | `uv tool upgrade ty` |
| Claude CLI (native) | `claude update` |
| Codex CLI (standalone) | `codex update` |
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
Node/Python runtimes are outside this script's scope. No Homebrew is used.
With npm 12, only the known Wrangler dependency install scripts (`esbuild`,
`workerd`, and `fsevents`) are allowed; unapproved new install scripts fail the update.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/),
[native Claude CLI](https://code.claude.com/docs/en/setup),
[standalone Codex CLI](https://developers.openai.com/codex/cli), and
[1Password CLI](https://www.1password.dev/cli/get-started) from their official sources.
Then install the global uv tools and Wrangler:

```sh
uv tool install ruff@latest
uv tool install ty@latest
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
