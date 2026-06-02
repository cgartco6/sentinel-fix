# ========== OS AUTO-DETECTION & ADAPTIVE FIXES ==========
import platform
import subprocess
from pathlib import Path

class OSAdaptiveRepair:
    """Detects host OS and applies platform-appropriate fixes only."""
    
    def __init__(self):
        self.system = platform.system().lower()  # windows, linux, darwin
        self.os_name = {
            "windows": "Windows",
            "linux": "Linux",
            "darwin": "macOS"
        }.get(self.system, "Unknown")
        
        # Shell script extensions by OS
        self.valid_scripts = {
            "windows": [".bat", ".cmd", ".ps1"],
            "linux": [".sh", ".bash", ".zsh"],
            "darwin": [".sh", ".bash", ".zsh"]
        }
        
        self.invalid_scripts = {
            "windows": [".sh", ".bash", ".zsh"],
            "linux": [".bat", ".cmd", ".ps1"],
            "darwin": [".bat", ".cmd", ".ps1"]
        }
        
        # Line endings
        self.line_ending = "\r\n" if self.system == "windows" else "\n"
        
    def log_os_info(self):
        """Print OS detection results."""
        print(f"[OS DETECTION] Running on: {self.os_name} ({self.system})")
        print(f"[OS DETECTION] Valid script extensions: {', '.join(self.valid_scripts[self.system])}")
        print(f"[OS DETECTION] Will ignore: {', '.join(self.invalid_scripts[self.system])}")
        
    def is_script_valid_for_os(self, file_path: Path) -> bool:
        """Check if a script file is compatible with current OS."""
        ext = file_path.suffix.lower()
        if ext in self.invalid_scripts[self.system]:
            return False
        return True
    
    def get_shebang_for_os(self) -> str:
        """Return appropriate shebang line for current OS."""
        if self.system == "windows":
            return "@echo off\r\nrem Windows batch file\r\n"
        else:
            return "#!/bin/bash\n\n"
    
    def fix_line_endings_by_os(self, content: str) -> str:
        """Convert line endings to OS-appropriate format."""
        # First normalize to \n, then convert to OS-specific
        normalized = content.replace('\r\n', '\n').replace('\r', '\n')
        if self.system == "windows":
            return normalized.replace('\n', '\r\n')
        return normalized
    
    def get_python_command(self) -> str:
        """Return correct Python command for OS."""
        if self.system == "windows":
            return "python"
        else:
            return "python3"
    
    def get_path_separator(self) -> str:
        return "\\" if self.system == "windows" else "/"
    
    def should_create_shell_script(self, script_name: str) -> bool:
        """Only create shell scripts that match the OS."""
        if self.system == "windows" and script_name.endswith((".sh", ".bash")):
            return False
        if self.system != "windows" and script_name.endswith((".bat", ".cmd")):
            return False
        return True

# Initialize global OS adapter
os_adapter = OSAdaptiveRepair()

# ========== MODIFY EXISTING FUNCTIONS TO USE OS ADAPTER ==========
def rewrite_algorithm_with_os_awareness(file_path: Path, old_content: str, algo_type: str, detected_name: str) -> Optional[str]:
    """
    Wrapper that ensures rewritten code uses OS-appropriate conventions.
    Call this instead of the original rewrite_algorithm.
    """
    # Call original rewrite_algorithm (assume you rename it to _rewrite_algorithm_core)
    new_content = _rewrite_algorithm_core(file_path, old_content, algo_type, detected_name)
    
    if new_content:
        # Fix line endings for OS
        new_content = os_adapter.fix_line_endings_by_os(new_content)
        
        # For shell scripts, ensure correct shebang
        if file_path.suffix.lower() in ['.sh', '.bash', '.bat', '.cmd']:
            lines = new_content.split('\n')
            if lines and (lines[0].startswith('#!') or lines[0].startswith('@echo')):
                # Already has shebang, keep it
                pass
            else:
                new_content = os_adapter.get_shebang_for_os() + new_content
    
    return new_content

# ========== ENHANCED FILE SCANNER (SKIPS INVALID SCRIPTS) ==========
def scan_files_os_aware() -> List[Path]:
    """Only process files that make sense on current OS."""
    all_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in ['_repair_backups', '.git', 'node_modules', '__pycache__']]
        for file in files:
            file_path = Path(root) / file
            # Skip incompatible scripts
            if file_path.suffix.lower() in os_adapter.invalid_scripts[os_adapter.system]:
                log(f"Skipping {file_path} - incompatible with {os_adapter.os_name}", "OS_SKIP")
                continue
            all_files.append(file_path)
    return all_files

# ========== AUTO-GENERATE OS-SPECIFIC SCRIPTS ==========
def create_os_specific_run_script():
    """Create a run script appropriate for the current OS."""
    script_name = "run_repo.bat" if os_adapter.system == "windows" else "run_repo.sh"
    script_path = REPO_ROOT / script_name
    
    if script_path.exists():
        return  # Don't overwrite existing
    
    if os_adapter.system == "windows":
        content = f"""@echo off
REM Auto-generated run script for Windows
echo Starting {REPO_ROOT.name}...
{os_adapter.get_python_command()} repair_engine_algo.py
if %errorlevel% neq 0 (
    echo Error occurred!
    pause
)
"""
    else:
        content = f"""#!/bin/bash
# Auto-generated run script for {os_adapter.os_name}
echo "Starting {REPO_ROOT.name}..."
{os_adapter.get_python_command()} repair_engine_algo.py
if [ $? -ne 0 ]; then
    echo "Error occurred!"
    exit 1
fi
"""
    
    script_path.write_text(content, encoding='utf-8')
    if os_adapter.system != "windows":
        script_path.chmod(0o755)  # Make executable on Linux/macOS
    
    log(f"Created OS-specific run script: {script_name}", "OS_ADAPT")

# ========== INTEGRATE INTO MAIN ==========
def main_with_os_adaptation():
    """Enhanced main with OS detection."""
    os_adapter.log_os_info()
    log(f"OS-adaptive mode enabled - only applying compatible fixes", "INFO")
    
    # Create backup dir
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Scan only compatible files
    all_files = scan_files_os_aware()
    log(f"Found {len(all_files)} OS-compatible files", "INFO")
    
    # Create OS-appropriate run script
    create_os_specific_run_script()
    
    # Rest of repair logic (from original main)...
    # (Copy your existing repair loop here)
    # Example:
    repaired = 0
    for file_path in all_files:
        result = repair_file(file_path)  # Your existing function
        if result["repaired"]:
            repaired += 1
            log(f"Repaired: {file_path}", "REPAIR")
    
    log(f"Done. Repaired {repaired} files on {os_adapter.os_name}", "INFO")

# ========== QUICK TEST COMMAND ==========
if __name__ == "__main__":
    # Run OS detection test
    print("\n" + "="*50)
    print("OS ADAPTATION TEST")
    print("="*50)
    os_adapter.log_os_info()
    print(f"\nPython command: {os_adapter.get_python_command()}")
    print(f"Path separator: {os_adapter.get_path_separator()}")
    print(f"Line ending: {'CRLF' if os_adapter.line_ending == '\\r\\n' else 'LF'}")
    print("="*50)
    
    # Uncomment to run full repair:
    # main_with_os_adaptation()
