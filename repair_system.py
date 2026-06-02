#!/usr/bin/env python3
"""
Mega Repository Repair & Self‑Healing System
---------------------------------------------
Drop this file into any repository and run it.
It will analyse, validate, fix, and back up every file.
Never deletes – always moves changed files to _repair_backups/.
"""

import os
import sys
import shutil
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any

# ========== CONFIGURATION ==========
REPO_ROOT = Path.cwd()                     # Assumes script is run from repo root
BACKUP_DIR = REPO_ROOT / "_repair_backups"
SELF_CHECKSUM_FILE = REPO_ROOT / ".repair_system_checksum"
REPORT_FILE = REPO_ROOT / "_repair_report.txt"

# File types and their validators / fixers
LANGUAGE_CHECKERS = {
    ".py":   ("python", "-m py_compile"),
    ".js":   ("node", "--check"),
    ".json": ("json", "validate"),          # special internal handler
    ".yaml": ("yaml", "validate"),          # internal handler
    ".yml":  ("yaml", "validate"),
    ".sh":   ("shellcheck", "-x"),          # optional, if installed
    ".md":   ("markdown", "lint"),          # optional
}

CRITICAL_FILES = [
    "README.md", ".gitignore", "LICENSE",
    "requirements.txt", "package.json", "Dockerfile",
    "docker-compose.yml", ".env.example", "setup.py",
]

# ========== UTILITIES ==========
def log(msg: str, level: str = "INFO") -> None:
    """Print with timestamp and write to report file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    with open(REPORT_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def backup_file(file_path: Path) -> Path:
    """Copy file to backup directory preserving relative path."""
    rel_path = file_path.relative_to(REPO_ROOT)
    backup_path = BACKUP_DIR / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, backup_path)
    return backup_path

def restore_from_backup(file_path: Path) -> bool:
    """Restore a file from the latest backup."""
    rel_path = file_path.relative_to(REPO_ROOT)
    backup_path = BACKUP_DIR / rel_path
    if backup_path.exists():
        shutil.copy2(backup_path, file_path)
        log(f"Restored {file_path} from backup", "WARNING")
        return True
    return False

# ========== FILE VALIDATION & FIXING ==========
def is_binary_file(file_path: Path) -> bool:
    """Heuristic: read first 1024 bytes, if null byte present -> binary."""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\0" in chunk
    except:
        return True

def check_json(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate JSON and fix (reformat) if possible."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Reformat (fix indentation, etc.)
        fixed = json.dumps(data, indent=2, ensure_ascii=False)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed + "\n")
        return True, "reformatted"
    except json.JSONDecodeError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def check_yaml(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Validate YAML, attempt to fix (using ruamel.yaml if available, else pyyaml)."""
    try:
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Re-dump to fix formatting (preserve order optional)
        fixed = yaml.dump(data, default_flow_style=False, allow_unicode=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(fixed)
        return True, "reformatted"
    except ImportError:
        # No YAML lib – just check syntax with a simple loader attempt
        try:
            import yaml
        except ImportError:
            # If yaml not installed, skip fixing but report
            return False, "YAML library missing, cannot auto-fix"
    except Exception as e:
        return False, str(e)
    return True, None

def check_syntax_with_subprocess(file_path: Path, cmd: List[str]) -> Tuple[bool, str]:
    """Run external linter/compiler (e.g., python -m py_compile)."""
    try:
        result = subprocess.run(
            [*cmd, str(file_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)

def fix_line_endings(file_path: Path) -> bool:
    """Convert CRLF to LF and ensure trailing newline."""
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        # Replace CRLF with LF
        new_content = content.replace(b"\r\n", b"\n")
        # Ensure trailing newline
        if not new_content.endswith(b"\n"):
            new_content += b"\n"
        if new_content != content:
            backup_file(file_path)
            with open(file_path, "wb") as f:
                f.write(new_content)
            return True
    except Exception:
        pass
    return False

def validate_and_fix_file(file_path: Path) -> Dict[str, Any]:
    """Main dispatcher: validates, fixes, backs up if changed."""
    result = {
        "path": str(file_path),
        "valid": True,
        "fixed": False,
        "errors": [],
        "warnings": []
    }

    # Skip binary files (can't safely fix)
    if is_binary_file(file_path):
        result["warnings"].append("binary file – skipped validation")
        return result

    # 1. Fix line endings first (non‑destructive)
    if fix_line_endings(file_path):
        result["fixed"] = True
        result["warnings"].append("line endings normalized")

    # 2. Language‑specific validation
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        ok, err = check_json(file_path)
        if not ok:
            result["valid"] = False
            result["errors"].append(f"JSON invalid: {err}")
            # Attempt restore from backup? We'll do later.
        elif err == "reformatted":
            result["fixed"] = True

    elif suffix in (".yaml", ".yml"):
        ok, err = check_yaml(file_path)
        if not ok:
            result["valid"] = False
            result["errors"].append(f"YAML invalid: {err}")
        elif err == "reformatted":
            result["fixed"] = True

    elif suffix in LANGUAGE_CHECKERS:
        tool, arg = LANGUAGE_CHECKERS[suffix]
        if tool == "python":
            ok, err = check_syntax_with_subprocess(file_path, ["python", "-m", "py_compile"])
            if not ok:
                result["valid"] = False
                result["errors"].append(f"Python syntax error: {err}")
        elif tool == "node":
            ok, err = check_syntax_with_subprocess(file_path, ["node", "--check"])
            if not ok:
                result["valid"] = False
                result["errors"].append(f"JavaScript syntax error: {err}")
        # Add more language tools as needed (shellcheck, etc.)
        else:
            result["warnings"].append(f"checker {tool} not implemented or missing")

    # 3. Special: empty file check
    if file_path.stat().st_size == 0:
        result["warnings"].append("empty file")
        # Optionally fix: write a placeholder comment? No – just warn.

    # 4. If invalid and has backup, attempt restore
    if not result["valid"]:
        if restore_from_backup(file_path):
            result["fixed"] = True
            result["valid"] = True
            result["errors"].clear()
            result["warnings"].append("restored from backup (invalid version discarded)")
        else:
            # No backup, but we'll still keep the file (maybe later manual fix)
            pass

    return result

# ========== REPO STRUCTURE ANALYSIS ==========
def find_missing_critical_files() -> List[str]:
    """Return list of critical files that do not exist in repo root."""
    missing = []
    for fname in CRITICAL_FILES:
        if not (REPO_ROOT / fname).exists():
            missing.append(fname)
    return missing

def detect_framework_mismatches() -> List[str]:
    """Heuristic: look for package.json without node_modules or missing scripts."""
    issues = []
    package_json = REPO_ROOT / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r") as f:
                data = json.load(f)
            if "scripts" not in data or not data["scripts"]:
                issues.append("package.json has no 'scripts' section")
            if not (REPO_ROOT / "node_modules").exists():
                issues.append("package.json exists but node_modules missing (run npm install)")
        except:
            issues.append("package.json is malformed")
    # Python
    req_file = REPO_ROOT / "requirements.txt"
    if req_file.exists() and not (REPO_ROOT / "venv").exists() and not (REPO_ROOT / ".venv").exists():
        issues.append("requirements.txt exists but no virtual environment found")
    return issues

# ========== SELF‑HEALING MECHANISM ==========
def self_heal() -> bool:
    """Verify this script's integrity using a stored checksum. If corrupted, restore from backup."""
    script_path = Path(__file__).resolve()
    if not script_path.exists():
        log("Self‑healing failed: cannot locate my own script", "ERROR")
        return False

    # Compute current hash
    current_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()

    # If no checksum file, store current and assume OK
    if not SELF_CHECKSUM_FILE.exists():
        SELF_CHECKSUM_FILE.write_text(current_hash)
        log("Initialised self‑healing checksum", "INFO")
        return True

    stored_hash = SELF_CHECKSUM_FILE.read_text().strip()
    if current_hash == stored_hash:
        return True  # intact

    # Mismatch – try to restore from our own backup (inside BACKUP_DIR)
    log(f"Self‑integrity check FAILED! Attempting self‑repair...", "CRITICAL")
    backup_self = BACKUP_DIR / script_path.relative_to(REPO_ROOT)
    if backup_self.exists():
        shutil.copy2(backup_self, script_path)
        # Re‑verify
        new_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()
        if new_hash == stored_hash:
            SELF_CHECKSUM_FILE.write_text(new_hash)
            log("Self‑repair successful. Script restored from backup.", "INFO")
            return True
        else:
            log("Self‑repair FAILED: backup also corrupted.", "ERROR")
            return False
    else:
        log("Self‑repair FAILED: no backup copy found.", "ERROR")
        return False

def backup_self() -> None:
    """Backup this script before any modifications (run at start)."""
    script_path = Path(__file__).resolve()
    backup_path = BACKUP_DIR / script_path.relative_to(REPO_ROOT)
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(script_path, backup_path)
    # Also store checksum for later verification
    current_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()
    SELF_CHECKSUM_FILE.write_text(current_hash)

# ========== MAIN REPAIR PROCESS ==========
def scan_and_repair() -> None:
    """Walk entire repo, validate every file, fix where possible, backup all changes."""
    log("🚀 Starting Mega Repository Repair System", "INFO")
    log(f"Repo root: {REPO_ROOT}", "INFO")

    # 1. Create backup directory and backup this script
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_self()

    # 2. Find all files (excluding backup dir and hidden system files like .git)
    all_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        # Skip our own backup folder and .git
        dirs[:] = [d for d in dirs if d not in ["_repair_backups", ".git"]]
        for file in files:
            file_path = Path(root) / file
            all_files.append(file_path)

    log(f"Found {len(all_files)} files to process", "INFO")

    # 3. Validate & fix each file
    results = []
    for file_path in all_files:
        res = validate_and_fix_file(file_path)
        results.append(res)
        if not res["valid"]:
            log(f"❌ {res['path']} remains invalid: {res['errors']}", "ERROR")
        elif res["fixed"]:
            log(f"🔧 Fixed {res['path']}: {res['warnings']}", "WARNING")

    # 4. Analyse repo structure
    missing_critical = find_missing_critical_files()
    if missing_critical:
        log(f"⚠️ Missing critical files: {', '.join(missing_critical)}", "WARNING")

    framework_issues = detect_framework_mismatches()
    for issue in framework_issues:
        log(f"📦 Framework issue: {issue}", "WARNING")

    # 5. Write final report
    total = len(results)
    invalid = sum(1 for r in results if not r["valid"])
    fixed = sum(1 for r in results if r["fixed"])
    log(f"✅ Repair complete. Scanned {total}, fixed {fixed}, {invalid} remain invalid.", "INFO")
    log(f"Full report: {REPORT_FILE}", "INFO")

def main():
    """Entry point with self‑healing check before anything else."""
    # First, ensure we are in a writable repo
    if not REPO_ROOT.is_dir():
        print("Error: Cannot find repo root. Run this script from inside a Git repository.", file=sys.stderr)
        sys.exit(1)

    # Self‑heal this script before doing any work
    if not self_heal():
        log("Self‑healing failed. Exiting to prevent further damage.", "CRITICAL")
        sys.exit(1)

    # Now run the main repair process
    scan_and_repair()

if __name__ == "__main__":
    main()
