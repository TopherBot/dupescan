#!/usr/bin/env python3
"""dupescan – tiny duplicate detector & auto‑renamer.

Features:
- Scan a directory for duplicate files (content hash).
- Move duplicates to a `duplicates/` folder.
- Auto‑rename on name clashes.
- Optional Telegram notification.

Usage:
    python dupescan.py scan  /path/to/dir   # one‑shot scan
    python dupescan.py watch /path/to/dir   # live watch (requires watchdog)

All options are available via `--help`.
"""

import argparse
import hashlib
import os
import shutil
import sys
from collections import defaultdict
from pathlib import Path

# Optional telegram support – imported lazily
def _send_telegram(msg: str, token: str, chat_id: str):
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": msg})
    except Exception as e:
        print(f"[Telegram] failed: {e}", file=sys.stderr)

def _load_config():
    """Load minimal config from env vars or a `dupescan.yaml` file.
    Returns a dict with keys: token, chat_id, min_size_kb, hash_algo.
    """
    cfg = {
        "token": os.getenv("TELEGRAM_BOT_TOKEN"),
        "chat_id": os.getenv("TELEGRAM_CHAT_ID"),
        "min_size_kb": int(os.getenv("DUPESCAN_MIN_SIZE_KB", "1")),
        "hash_algo": os.getenv("DUPESCAN_HASH_ALGO", "sha256"),
    }
    # Simple YAML fallback (no external deps)
    try:
        import yaml  # type: ignore
        cfg_path = Path(__file__).with_name("dupescan.yaml")
        if cfg_path.is_file():
            with cfg_path.open() as f:
                y = yaml.safe_load(f) or {}
                notify = y.get("notify", {}).get("telegram", {})
                cfg["token"] = notify.get("token", cfg["token"]) or None
                cfg["chat_id"] = notify.get("chat_id", cfg["chat_id"]) or None
                scan = y.get("scan", {})
                cfg["min_size_kb"] = int(scan.get("min_size_kb", cfg["min_size_kb"]))
                cfg["hash_algo"] = scan.get("hash_algo", cfg["hash_algo"])
    except Exception:
        pass  # ignore missing yaml or lib
    return cfg

def _hash_file(path: Path, algo: str = "sha256") -> str:
    h = hashlib.new(algo)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def _find_duplicates(root: Path, min_size_kb: int, algo: str):
    hash_map = defaultdict(list)
    for file in root.rglob("*"):
        if file.is_file():
            if file.stat().st_size < min_size_kb * 1024:
                continue
            try:
                file_hash = _hash_file(file, algo)
                hash_map[file_hash].append(file)
            except Exception as e:
                print(f"[Error] hashing {file}: {e}", file=sys.stderr)
    # Keep only groups with >1 entry
    return {h: lst for h, lst in hash_map.items() if len(lst) > 1}

def _ensure_unique(dest: Path) -> Path:
    """If dest exists, append (n) before the extension until free."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1

def _process_duplicates(dup_groups, root: Path, notify_cfg):
    dup_dir = root / "duplicates"
    dup_dir.mkdir(exist_ok=True)
    messages = []
    for _hash, files in dup_groups.items():
        # Keep first file in place, move the rest
        original = files[0]
        for dup in files[1:]:
            target = dup_dir / dup.name
            target = _ensure_unique(target)
            try:
                shutil.move(str(dup), str(target))
                msg = f"Moved duplicate {dup} → {target}"
                print(msg)
                messages.append(msg)
            except Exception as e:
                print(f"[Error] moving {dup}: {e}", file=sys.stderr)
    # Notification
    if notify_cfg.get("token") and notify_cfg.get("chat_id"):
        summary = f"dupescan: {len(messages)} duplicate(s) processed in {root}"
        _send_telegram(summary, notify_cfg["token"], notify_cfg["chat_id"])

def cmd_scan(args):
    cfg = _load_config()
    root = Path(args.path).resolve()
    dup_groups = _find_duplicates(root, cfg["min_size_kb"], cfg["hash_algo"])
    if not dup_groups:
        print("No duplicates found.")
        return
    _process_duplicates(dup_groups, root, cfg)

def cmd_watch(args):
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("watch mode requires 'watchdog' package. Install with: pip install watchdog", file=sys.stderr)
        sys.exit(1)

    class DupHandler(FileSystemEventHandler):
        def __init__(self, root):
            self.root = root
            self.cfg = _load_config()
        def on_created(self, event):
            if not event.is_directory:
                # Delay a bit for file to settle
                import time; time.sleep(0.1)
                dup_groups = _find_duplicates(self.root, self.cfg["min_size_kb"], self.cfg["hash_algo"])
                if dup_groups:
                    _process_duplicates(dup_groups, self.root, self.cfg)

    root = Path(args.path).resolve()
    event_handler = DupHandler(root)
    observer = Observer()
    observer.schedule(event_handler, str(root), recursive=True)
    observer.start()
    print(f"Watching {root} – press Ctrl+C to stop")
    try:
        while True:
            import time; time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def main():
    parser = argparse.ArgumentParser(prog="dupescan", description="Detect & clean duplicate files with auto‑rename and optional Telegram alerts.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="One‑time scan and clean")
    scan.add_argument("path", help="Directory to scan")
    scan.set_defaults(func=cmd_scan)
    watch = sub.add_parser("watch", help="Live watch (requires watchdog)")
    watch.add_argument("path", help="Directory to monitor")
    watch.set_defaults(func=cmd_watch)
    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
