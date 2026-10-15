# updatett

One command to update this workstation's global terminal tools. It shows
before/after versions, keeps going if a tool fails, and exits nonzero if any did.
Update command output is hidden; failures show an exit code. The table below
summarizes how each tool is updated.

![updatett demo](assets/updatett-demo.gif)

## Tools

| Tool | Update command |
| --- | --- |
| uv | `uv self update` |
| Ruff | `uv tool upgrade ruff` |
| ty | `uv tool upgrade ty` |
| Claude CLI | `claude update` |
| OpenAI Codex | `codex update` |
| nvm | Check out the latest release tag ([manual upgrade](https://github.com/nvm-sh/nvm#manual-upgrade)) |
| Node.js (LTS) | Install the latest LTS, move global packages, make it the default |
| npm | `nvm install-latest-npm` |
| Wrangler | `npm install -g wrangler@latest` |
| 1Password CLI | `op update`, then verify the signature and replace the binary |

## Notes

- **1Password:** the download's signature is verified before the binary is
  replaced, and the old binary is restored if anything fails. If another `op`
  command is running, the update fails; run it again later.
- **Node:** if the current default Node environment is in use, its update fails;
  retry when it is idle. The old default is removed only after the new one is
  verified. Other Node versions are kept. Afterwards, run `nvm use default` in
  already open terminals.
- **npm:** only Wrangler's known install scripts (`esbuild`, `workerd`,
  `fsevents`) may run, and no npm or Wrangler log files are written.
- **Not managed:** desktop apps, project dependencies, Python runtimes, Corepack.
  No Homebrew.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/),
[Claude CLI](https://code.claude.com/docs/en/setup),
[Codex CLI](https://developers.openai.com/codex/cli),
[1Password CLI](https://www.1password.dev/cli/get-started) and
[nvm](https://github.com/nvm-sh/nvm#installing-and-updating) from their official
sources, then:

```sh
uv tool install ruff@latest
uv tool install ty@latest
nvm install --lts --latest-npm
nvm alias default "$(nvm current)"
nvm use default
npm install -g wrangler@latest --allow-scripts=esbuild,workerd,fsevents --strict-allow-scripts --logs-max=0
```

Missing tools are reported as failures, not installed.

## Install and run

```sh
cp updatett /usr/local/bin/updatett
chmod +x /usr/local/bin/updatett
updatett
```

Copy it again after changing it. To remove it: `rm /usr/local/bin/updatett`.

## Verification

```sh
zsh -n updatett
uv run --python 3.14 tests/test_updatett.py
ruff check --no-cache tests
ruff format --check --no-cache tests
ty check tests
```

The tests use fake tools in a temporary directory and never update anything.
