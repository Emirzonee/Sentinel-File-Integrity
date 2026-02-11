"""
Sentinel — File Integrity Monitor (FIM)

Takes a snapshot of file hashes in a directory, then compares
against that baseline to detect modifications, deletions, and
new files. Useful for detecting unauthorized changes on servers.

Usage:
    python sentinel.py init [directory]
    python sentinel.py check [directory]
    python sentinel.py check [directory] --report report.txt
"""

import hashlib
import os
import sys
import json
import argparse
from datetime import datetime

BASELINE_FILE = "baseline.json"
CHUNK_SIZE = 4096

# skip these by default
IGNORED = {BASELINE_FILE, "sentinel.py", ".git", "__pycache__", ".DS_Store"}


def hash_file(filepath, algo="sha256"):
    """
    Hash a file in chunks so large files don't blow up RAM.
    Supports sha256 and md5.
    """
    h = hashlib.new(algo)
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (FileNotFoundError, PermissionError, OSError):
        return None


def scan_directory(target_dir):
    """Walk a directory and hash every file, skipping ignored names."""
    results = {}
    count = 0

    for root, dirs, files in os.walk(target_dir):
        # skip ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORED]

        for fname in files:
            if fname in IGNORED:
                continue

            fpath = os.path.join(root, fname)
            digest = hash_file(fpath)

            if digest:
                # store relative path for portability
                rel = os.path.relpath(fpath, target_dir)
                results[rel] = {
                    "hash": digest,
                    "size": os.path.getsize(fpath),
                }
                count += 1
                sys.stdout.write(f"\r  Scanned {count} files...")
                sys.stdout.flush()

    print()
    return results


def load_baseline(target_dir):
    """Load existing baseline from JSON."""
    path = os.path.join(target_dir, BASELINE_FILE)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_baseline(target_dir, data):
    """Save baseline snapshot to JSON."""
    path = os.path.join(target_dir, BASELINE_FILE)
    payload = {
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "file_count": len(data),
        "files": data,
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def cmd_init(args):
    """Create or update the baseline snapshot."""
    target = args.directory
    print(f"[*] Initializing baseline for: {os.path.abspath(target)}")

    start = datetime.now()
    files = scan_directory(target)
    elapsed = datetime.now() - start

    path = save_baseline(target, files)
    print(f"[+] Baseline saved: {path}")
    print(f"[+] {len(files)} files indexed in {elapsed.total_seconds():.1f}s")


def cmd_check(args):
    """Compare current state against the baseline."""
    target = args.directory
    baseline = load_baseline(target)

    if baseline is None:
        print(f"[!] No baseline found. Run 'sentinel.py init' first.")
        sys.exit(1)

    print(f"[*] Checking integrity against baseline ({baseline['file_count']} files)")
    print(f"[*] Baseline created: {baseline['created']}")
    print("-" * 50)

    saved_files = baseline["files"]
    current_files = scan_directory(target)

    modified = []
    deleted = []
    added = []

    # check for modifications and deletions
    for fpath, info in saved_files.items():
        if fpath not in current_files:
            deleted.append(fpath)
        elif current_files[fpath]["hash"] != info["hash"]:
            old_size = info["size"]
            new_size = current_files[fpath]["size"]
            modified.append((fpath, old_size, new_size))

    # check for new files
    for fpath in current_files:
        if fpath not in saved_files:
            added.append(fpath)

    # display results
    for f in modified:
        print(f"  [MODIFIED]  {f[0]}  ({f[1]}B -> {f[2]}B)")
    for f in deleted:
        print(f"  [DELETED]   {f}")
    for f in added:
        print(f"  [NEW]       {f}")

    print("-" * 50)
    total = len(modified) + len(deleted) + len(added)

    if total == 0:
        print("[+] All files verified. No changes detected.")
    else:
        print(f"[!] {total} issue(s): {len(modified)} modified, {len(deleted)} deleted, {len(added)} new")

    # write report if requested
    if args.report:
        write_report(args.report, baseline, modified, deleted, added)

    if total > 0:
        sys.exit(1)


def write_report(path, baseline, modified, deleted, added):
    """Write a text report of the integrity check."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w") as f:
        f.write(f"Sentinel Integrity Report — {now}\n")
        f.write(f"Baseline from: {baseline['created']}\n")
        f.write("=" * 45 + "\n\n")

        f.write(f"Modified: {len(modified)}\n")
        for item in modified:
            f.write(f"  {item[0]}  ({item[1]}B -> {item[2]}B)\n")

        f.write(f"\nDeleted: {len(deleted)}\n")
        for item in deleted:
            f.write(f"  {item}\n")

        f.write(f"\nNew files: {len(added)}\n")
        for item in added:
            f.write(f"  {item}\n")

    print(f"[+] Report saved: {path}")


def main():
    parser = argparse.ArgumentParser(description="Sentinel — File Integrity Monitor")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="create baseline snapshot")
    p_init.add_argument("directory", nargs="?", default=".",
                        help="directory to monitor (default: current)")

    p_check = sub.add_parser("check", help="verify files against baseline")
    p_check.add_argument("directory", nargs="?", default=".",
                         help="directory to check (default: current)")
    p_check.add_argument("--report", help="save report to file")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "init":
        cmd_init(args)
    elif args.command == "check":
        cmd_check(args)


if __name__ == "__main__":
    main()