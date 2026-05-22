# dupescan

**Tiny duplicate‑detector & auto‑renamer**

- **What it does**: Scans a target folder (or watches it live), finds files with identical content (SHA‑256 hash), moves duplicates to a `duplicates/` sub‑folder, and if a duplicate’s name already exists there it auto‑renames it (`name (1).ext`, `name (2).ext`, …).
- **Why it’s useful**: Prevents storage bloat, cleans up naming collisions, and can push a Telegram notification so you never miss a duplicate.
- **Features**:
  - Fast hash‑based duplicate detection (single‑pass, low memory).
  - Auto‑rename on name clash.
  - Optional **Telegram bot** integration for proactive alerts.
  - One‑command install via `pip` (or run the single script directly).
  - Zero‑config mode works out‑of‑the‑box.

## Installation
```bash
# Option 1: Run directly (no install)
python3 dupescan.py --help

# Option 2: Install as a CLI package
pip install git+https://github.com/yourusername/dupescan.git
```

## Usage
```bash
# Scan once and clean duplicates
python3 dupescan.py scan /path/to/folder

# Watch a folder continuously (uses watchdog if available)
python3 dupescan.py watch /path/to/folder

# Enable Telegram notifications (set env vars or config file)
export TELEGRAM_BOT_TOKEN="<your_bot_token>"
export TELEGRAM_CHAT_ID="<your_chat_id>"
python3 dupescan.py scan /path/to/folder --notify
```

## Configuration (optional)
Create a `dupescan.yaml` in the same directory as the script:
```yaml
notify:
  telegram:
    token: "YOUR_BOT_TOKEN"
    chat_id: "YOUR_CHAT_ID"
scan:
  min_size_kb: 1   # ignore files smaller than this
  hash_algo: sha256
```
If the YAML file is missing, environment variables are used; otherwise defaults apply.

## How it works (quick spec)
1. **Collect** list of files recursively.
2. **Hash** each file (default SHA‑256) – uses a streaming read to keep memory low.
3. **Group** files by hash; groups >1 are duplicates.
4. **Move** duplicates to `<target>/duplicates/`.
5. **Rename** on clash: `<name> (n).ext` where *n* increments until a free name appears.
6. **Notify** (if enabled): send a short message to the configured Telegram chat.

## License
MIT – see `LICENSE`.

---
*Built with a love for proactive duplicate detection, auto‑rename on clash, and concise actionable specs.*