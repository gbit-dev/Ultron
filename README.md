# Ultron

CLI toolbox + Discord bot.

## CLI

    pip install -e .
    ultron hashscan ./some-folder --json
    ultron fetch https://example.com --json
    ultron recon example.com
    ultron diffscan ./a ./b
    ultron logtail app.log -f -p ERROR

Subcommands:

- hashscan — SHA-256 every file, group duplicates
- fetch — status, title, size for one or more URLs
- recon — DNS (A/AAAA/MX/TXT/NS) + TLS cert info
- diffscan — compare two directories by path + hash
- logtail — filter and follow a log file

## Bot — Ultron

    python -m venv .venv && source .venv/bin/activate
    pip install -r bot/requirements.txt
    cp .env.example .env   # fill DISCORD_TOKEN
    python bot/ultron.py

Slash commands: `/hashscan` (zip upload), `/recon <domain>`.