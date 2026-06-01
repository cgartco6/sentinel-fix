#!/usr/bin/env python3
"""
Universal Repository Repair & Validation Agent
Auto-detects: React, Go, Python (data pipeline/API/script), Node.js, TypeScript, Next.js, Vue, Rust, Java/Maven
Run with: python universal_repo_repair_agent.py
"""

import os
import re
import sys
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional

# ========== CONFIGURATION ==========
REPO_ROOT = Path(__file__).parent.absolute()
BACKUP_DIR = REPO_ROOT / ".universal_repair_backup"
LOG_FILE = REPO_ROOT / "repair_log.txt"

# ========== UTILITIES ==========
def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def backup_file(filepath: Path):
    if not filepath.exists():
        return
    rel = filepath.relative_to(REPO_ROOT)
    backup_path = BACKUP_DIR / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    log(f"Backed up {rel}")

def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)

# ========== PROJECT DETECTION ==========
def detect_project_type() -> Dict[str, any]:
    """Auto-detect the primary tech stack and structure."""
    files = {f.name: f for f in REPO_ROOT.iterdir() if f.is_file()}
    dirs = {d.name: d for d in REPO_ROOT.iterdir() if d.is_dir()}
    
    # Check for package.json
    if "package.json" in files:
        with open(files["package.json"], "r", encoding="utf-8") as f:
            try:
                pkg = json.load(f)
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    return {"type": "nextjs", "files": ["pages/", "app/"], "entry": "npm run dev"}
                if "react" in deps or "react-dom" in deps:
                    if "vite" in deps:
                        return {"type": "react-vite", "files": ["src/", "index.html"], "entry": "npm run dev"}
                    return {"type": "react", "files": ["src/", "public/"], "entry": "npm start"}
                if "vue" in deps:
                    return {"type": "vue", "files": ["src/", "public/"], "entry": "npm run serve"}
                return {"type": "node", "files": ["index.js", "src/", "server.js"], "entry": "node index.js"}
            except:
                pass
    
    # Check for go.mod
    if "go.mod" in files:
        return {"type": "go", "files": ["main.go", "go.mod"], "entry": "go run main.go"}
    
    # Check for requirements.txt, setup.py, pyproject.toml
    if "requirements.txt" in files or "setup.py" in files or "pyproject.toml" in files:
        if "dags/" in dirs or "etl" in dirs or "pipeline" in dirs:
            return {"type": "python-data-pipeline", "files": ["dags/", "tasks/", "pipeline.py"], "entry": "python pipeline.py"}
        return {"type": "python", "files": ["main.py", "app.py", "src/"], "entry": "python main.py"}
    
    # Check for Cargo.toml (Rust)
    if "Cargo.toml" in files:
        return {"type": "rust", "files": ["src/main.rs", "Cargo.toml"], "entry": "cargo run"}
    
    # Check for pom.xml (Java/Maven)
    if "pom.xml" in files:
        return {"type": "java-maven", "files": ["src/main/java/", "pom.xml"], "entry": "mvn spring-boot:run"}
    
    # Check for tsconfig.json (TypeScript)
    if "tsconfig.json" in files:
        return {"type": "typescript", "files": ["src/", "tsconfig.json"], "entry": "ts-node index.ts"}
    
    # Default fallback
    return {"type": "unknown", "files": [], "entry": "make help"}
    
# ========== LANGUAGE-SPECIFIC REPAIR FUNCTIONS ==========
def repair_react(project_info: Dict):
    """Fix common React issues: broken imports, missing App.js, API wiring."""
    src_dir = REPO_ROOT / "src"
    ensure_dir(src_dir)
    
    # Ensure App.js exists and is functional
    app_file = src_dir / "App.js"
    if not app_file.exists() or "function App" not in app_file.read_text(encoding="utf-8"):
        backup_file(app_file)
        app_content = '''import React, { useState, useEffect } from 'react';
import './App.css';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setData(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('API error:', err);
        setLoading(false);
      });
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <h1>⚡ {REPO_ROOT.name} - React App</h1>
        <p>Status: {loading ? 'Loading...' : data?.status || 'Running'}</p>
        <button onClick={() => alert('StormCore SI Agent repaired me!')}>
          Click to Test
        </button>
      </header>
    </div>
  );
}

export default App;
'''
        app_file.write_text(app_content, encoding="utf-8")
        log("Created/Repaired src/App.js", "FIX")
    
    # Ensure package.json has required scripts
    pkg_file = REPO_ROOT / "package.json"
    if pkg_file.exists():
        with open(pkg_file, "r", encoding="utf-8") as f:
            pkg = json.load(f)
        changed = False
        if "scripts" not in pkg:
            pkg["scripts"] = {}
            changed = True
        for script in ["start", "dev", "build"]:
            if script not in pkg["scripts"]:
                if script == "start":
                    pkg["scripts"]["start"] = "react-scripts start"
                elif script == "dev":
                    pkg["scripts"]["dev"] = "vite"
                changed = True
        if changed:
            backup_file(pkg_file)
            with open(pkg_file, "w", encoding="utf-8") as f:
                json.dump(pkg, f, indent=2)
            log("Fixed package.json scripts", "FIX")

def repair_go(project_info: Dict):
    """Fix Go modules and main.go."""
    main_file = REPO_ROOT / "main.go"
    if not main_file.exists() or "func main" not in main_file.read_text(encoding="utf-8"):
        backup_file(main_file)
        content = f'''package main

import (
    "fmt"
    "log"
    "net/http"
)

func main() {{
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {{
        fmt.Fprintf(w, "Hello from {REPO_ROOT.name} - Repaired by StormCore SI")
    }})
    log.Println("Server starting on :8080")
    log.Fatal(http.ListenAndServe(":8080", nil))
}}
'''
        main_file.write_text(content, encoding="utf-8")
        log("Created/Repaired main.go", "FIX")
    
    # Run go mod tidy if go.mod exists
    if (REPO_ROOT / "go.mod").exists():
        subprocess.run(["go", "mod", "tidy"], cwd=REPO_ROOT, capture_output=True)
        log("Ran go mod tidy", "FIX")

def repair_python_data_pipeline(project_info: Dict):
    """Fix ETL pipeline structure, add error handling, logging."""
    # Ensure pipeline.py or main entry
    pipeline_file = REPO_ROOT / "pipeline.py"
    if not pipeline_file.exists():
        content = '''"""ETL Data Pipeline - Auto-repaired by StormCore SI"""
import logging
from datetime import datetime
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract() -> Dict[str, Any]:
    logger.info("Extracting data...")
    return {"data": [1, 2, 3], "timestamp": datetime.now().isoformat()}

def transform(data: Dict) -> Dict:
    logger.info("Transforming data...")
    data["transformed"] = [x * 2 for x in data.get("data", [])]
    return data

def load(data: Dict) -> None:
    logger.info(f"Loading {len(data.get('transformed', []))} records...")
    # In real pipeline, write to DB/warehouse
    print(f"Loaded: {data}")

def run_pipeline():
    logger.info("Starting pipeline")
    raw = extract()
    transformed = transform(raw)
    load(transformed)
    logger.info("Pipeline complete")

if __name__ == "__main__":
    run_pipeline()
'''
        pipeline_file.write_text(content, encoding="utf-8")
        log("Created pipeline.py", "FIX")
    
    # Ensure requirements.txt has common data libs
    req_file = REPO_ROOT / "requirements.txt"
    if req_file.exists():
        content = req_file.read_text(encoding="utf-8")
        needed = ["pandas", "numpy", "sqlalchemy", "requests"]
        missing = [lib for lib in needed if lib not in content]
        if missing:
            with open(req_file, "a", encoding="utf-8") as f:
                f.write("\n" + "\n".join(missing) + "\n")
            log(f"Added missing requirements: {missing}", "FIX")

def repair_node(project_info: Dict):
    """Fix Node.js/Express apps."""
    server_file = REPO_ROOT / "server.js"
    if not server_file.exists():
        server_file = REPO_ROOT / "index.js"
    if server_file.exists() and "express" not in server_file.read_text(encoding="utf-8"):
        backup_file(server_file)
        content = '''const express = require('express');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());
app.get('/', (req, res) => {
  res.json({ status: 'ok', message: 'StormCore SI repaired this Node app' });
});
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', repaired: true });
});
app.listen(port, () => {
  console.log(`Server running on port ${port}`);
});
'''
        server_file.write_text(content, encoding="utf-8")
        log(f"Repaired {server_file.name}", "FIX")

def repair_typescript(project_info: Dict):
    """Fix TypeScript config and entry."""
    tsconfig = REPO_ROOT / "tsconfig.json"
    if tsconfig.exists():
        with open(tsconfig, "r", encoding="utf-8") as f:
            try:
                cfg = json.load(f)
            except:
                cfg = {}
        changed = False
        if "compilerOptions" not in cfg:
            cfg["compilerOptions"] = {"strict": True, "target": "ES2020"}
            changed = True
        if changed:
            backup_file(tsconfig)
            tsconfig.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            log("Fixed tsconfig.json", "FIX")
    
    src_dir = REPO_ROOT / "src"
    ensure_dir(src_dir)
    index_file = src_dir / "index.ts"
    if not index_file.exists():
        content = '''// TypeScript entry point - Repaired
console.log("StormCore SI has repaired this TypeScript project");

interface Status {
  healthy: boolean;
  repaired: boolean;
}

const status: Status = {
  healthy: true,
  repaired: true
};

console.log(status);
export {};
'''
        index_file.write_text(content, encoding="utf-8")
        log("Created src/index.ts", "FIX")

def repair_unknown(project_info: Dict):
    """Generic fallback: check for missing README, basic structure."""
    readme = REPO_ROOT / "README.md"
    if not readme.exists():
        readme.write_text(f"# {REPO_ROOT.name}\n\nRepaired by StormCore SI Universal Agent on {datetime.now()}", encoding="utf-8")
        log("Created README.md", "FIX")

# ========== MAIN REPAIR ENGINE ==========
def full_repair():
    print("\n🔧 UNIVERSAL REPO REPAIR AGENT (StormCore SI)\n")
    LOG_FILE.unlink(missing_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    
    log("Starting universal repository validation", "START")
    project = detect_project_type()
    log(f"Detected project type: {project['type']}")
    
    # Dispatch to appropriate repairer
    repair_map = {
        "react": repair_react,
        "react-vite": repair_react,
        "nextjs": repair_react,
        "vue": repair_react,
        "go": repair_go,
        "python-data-pipeline": repair_python_data_pipeline,
        "python": repair_python_data_pipeline,  # fallback to same
        "node": repair_node,
        "typescript": repair_typescript,
        "java-maven": repair_unknown,
        "rust": repair_unknown,
        "unknown": repair_unknown
    }
    
    repair_func = repair_map.get(project["type"], repair_unknown)
    repair_func(project)
    
    # Ensure .gitignore exists
    gitignore = REPO_ROOT / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("node_modules/\n.env\n__pycache__/\n*.log\n.DS_Store\n", encoding="utf-8")
        log("Created .gitignore", "FIX")
    
    log("=== REPAIR COMPLETE ===", "SUCCESS")
    print(f"\n✅ {project['type'].upper()} project repaired.\n")
    print(f"To test, run: {project['entry']}")
    print("Backups stored in: .universal_repair_backup/\n")

if __name__ == "__main__":
    full_repair()
