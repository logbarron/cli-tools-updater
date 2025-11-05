# updatett

A simple zsh script that updates terminal tools with a spinner UI and version tracking.

## What it currently does
Updates uv, Claude CLI, Wrangler, npm packages, and any other tools you configure. 
Shows before/after versions and skips tools that are already up to date.

## Installation
Copy the updatett file to /usr/local/bin and make it executable:
- cp updatett /usr/local/bin/updatett
- chmod +x /usr/local/bin/updatett

## Running it
In Terminal - just type: updatett

That's it. It runs through all your configured tools and updates them.

## Updating the script itself
When you have a new version, just copy it over the old one:
- cp updatett /usr/local/bin/updatett

## Removing it
Delete the file from /usr/local/bin:
- rm /usr/local/bin/updatett

## Adding your own tools
Open the script and find the TOOLS array (around line 65).
Add a line in this format:
"Display Name|command_to_check|version_command|update_command"

Example: "GitHub CLI|gh|gh --version|gh upgrade"

If the tool doesn't have a CLI command (like npm packages), use SKIP_CHECK:
"My Package|SKIP_CHECK|npm list -g mypackage|npm install -g mypackage@latest"
