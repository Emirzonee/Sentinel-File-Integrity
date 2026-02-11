# Sentinel

File integrity monitoring tool. Takes a SHA-256 snapshot of every file in a directory, then compares against that baseline to detect unauthorized modifications, deletions, and new files.

Think of it as a tripwire for your filesystem. If anything changes, you'll know.

## How It Works

1. **Init** — scans a directory recursively, hashes every file with SHA-256, saves the results as a JSON baseline
2. **Check** — rescans the same directory and compares every hash against the baseline
3. Reports three types of anomalies: modified files (hash mismatch), deleted files (in baseline but missing), and new files (on disk but not in baseline)

## Usage

**Create a baseline:**
```bash
python sentinel.py init /var/www
```
```
[*] Initializing baseline for: /var/www
  Scanned 847 files...
[+] Baseline saved: /var/www/baseline.json
[+] 847 files indexed in 1.2s
```

**Check for changes:**
```bash
python sentinel.py check /var/www
```
```
[*] Checking integrity against baseline (847 files)
--------------------------------------------------
  [MODIFIED]  index.html  (4521B -> 4893B)
  [DELETED]   config/db.conf
  [NEW]       uploads/shell.php
--------------------------------------------------
[!] 3 issue(s): 1 modified, 1 deleted, 1 new
```

**Save a report:**
```bash
python sentinel.py check /var/www --report report.txt
```

## Why File Integrity Monitoring?

Web servers get compromised. Attackers modify files to inject backdoors, delete logs to cover tracks, or drop web shells for persistent access. A FIM tool catches all of this by comparing cryptographic hashes — if even a single byte changes, the hash is completely different.

Real-world tools like OSSEC, Tripwire, and AIDE do the same thing at enterprise scale. This is a lightweight implementation of the same concept.

## How SHA-256 Hashing Works

SHA-256 takes any input (a file, a string, anything) and produces a fixed 64-character hex string. Same input always gives the same output. Change one byte and the output is completely different — there's no way to predict how it will change. This makes it perfect for detecting tampering.

Files are read in 4KB chunks so even multi-gigabyte files can be hashed without loading them entirely into memory.

## Installation

```bash
git clone https://github.com/Emirzonee/Sentinel-File-Integrity.git
cd Sentinel-File-Integrity
```

No external dependencies. Uses only Python standard library.

## Project Structure

```
Sentinel-File-Integrity/
|-- sentinel.py      # Main script
|-- .gitignore
|-- LICENSE
|-- README.md
```

## Use Cases

- Monitor web server document roots for unauthorized changes
- Verify backup integrity before and after transfers
- Detect insider threats on shared file systems
- Compliance auditing (PCI-DSS requires FIM)

## Limitations

- Baseline is stored as plaintext JSON — an attacker with write access could tamper with it too
- No real-time monitoring (runs on-demand, not as a daemon)
- Does not track file permissions or ownership changes

## License

MIT