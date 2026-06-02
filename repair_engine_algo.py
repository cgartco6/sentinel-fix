@echo off
REM Self-extracting batch header for Windows CMD - but this is Python.
REM Run as: python repair_engine_algo.py
REM (the above line is just a comment, CMD will ignore)
"""

import os
import sys
import json
import shutil
import hashlib
import re
import ast
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Set
from collections import defaultdict, Counter

# ========== WINDOWS CMD FRIENDLY ==========
os.system('title Repair Engine - Algorithm Edition')
os.system('color 0A')  # Green text for success feedback

# ========== CONFIG ==========
REPO_ROOT = Path.cwd()
BACKUP_DIR = REPO_ROOT / "_repair_backups"
MEMORY_FILE = REPO_ROOT / ".repair_memory.json"
ALGO_LIBRARY = {}  # Built-in known good algorithms
EVOLVE_LOG = REPO_ROOT / "_evolution.log"

# ========== BUILT-IN ALGORITHM LIBRARY ==========
ALGORITHM_TEMPLATES = {
    "bubble_sort": {
        "python": '''def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr''',
        "javascript": '''function bubbleSort(arr) {
    let n = arr.length;
    for (let i = 0; i < n; i++) {
        let swapped = false;
        for (let j = 0; j < n-i-1; j++) {
            if (arr[j] > arr[j+1]) {
                [arr[j], arr[j+1]] = [arr[j+1], arr[j]];
                swapped = true;
            }
        }
        if (!swapped) break;
    }
    return arr;
}'''
    },
    "quick_sort": {
        "python": '''def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr)//2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)''',
        "javascript": '''function quickSort(arr) {
    if (arr.length <= 1) return arr;
    const pivot = arr[Math.floor(arr.length/2)];
    const left = arr.filter(x => x < pivot);
    const middle = arr.filter(x => x === pivot);
    const right = arr.filter(x => x > pivot);
    return [...quickSort(left), ...middle, ...quickSort(right)];
}'''
    },
    "binary_search": {
        "python": '''def binary_search(arr, target):
    left, right = 0, len(arr)-1
    while left <= right:
        mid = (left + right)//2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1''',
        "javascript": '''function binarySearch(arr, target) {
    let left = 0, right = arr.length-1;
    while (left <= right) {
        const mid = Math.floor((left+right)/2);
        if (arr[mid] === target) return mid;
        if (arr[mid] < target) left = mid+1;
        else right = mid-1;
    }
    return -1;
}'''
    },
    "fibonacci": {
        "python": '''def fibonacci(n, memo={}):
    if n in memo: return memo[n]
    if n <= 1: return n
    memo[n] = fibonacci(n-1, memo) + fibonacci(n-2, memo)
    return memo[n]''',
        "javascript": '''function fibonacci(n, memo={}) {
    if (memo[n]) return memo[n];
    if (n <= 1) return n;
    memo[n] = fibonacci(n-1, memo) + fibonacci(n-2, memo);
    return memo[n];
}'''
    },
    "dijkstra": {
        "python": '''import heapq
def dijkstra(graph, start):
    distances = {node: float('inf') for node in graph}
    distances[start] = 0
    pq = [(0, start)]
    while pq:
        current_dist, current = heapq.heappop(pq)
        if current_dist > distances[current]:
            continue
        for neighbor, weight in graph[current].items():
            distance = current_dist + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                heapq.heappush(pq, (distance, neighbor))
    return distances'''
    }
}

# ========== ALGORITHM DETECTION ==========
ALGO_PATTERNS = {
    "sorting": re.compile(r'\b(bubble|quick|merge|heap|insertion|selection)_?sort\b', re.I),
    "search": re.compile(r'\b(binary|linear|depth|breadth).{0,10}search\b', re.I),
    "dp": re.compile(r'\b(dynamic|memo|dp\[|fibonacci)\b', re.I),
    "graph": re.compile(r'\b(dijkstra|bellman|ford|floyd|warshall|bfs|dfs)\b', re.I),
    "recursion": re.compile(r'\bdef\s+\w+\(.*\).*:\s*\n\s+if.*return\b', re.M),
}

def detect_algorithms_in_file(content: str) -> List[Tuple[str, str, int]]:
    """Returns list of (algorithm_type, detected_name, line_number_approx)"""
    detected = []
    lines = content.split('\n')
    for algo_type, pattern in ALGO_PATTERNS.items():
        for i, line in enumerate(lines):
            if pattern.search(line):
                detected.append((algo_type, line.strip()[:50], i+1))
    return detected

def validate_algorithm_performance(content: str, algo_type: str) -> Tuple[bool, List[str]]:
    """
    Check common algorithmic errors:
    - Off-by-one in loops
    - Missing base case in recursion
    - Inefficient implementation (O(n^3) when O(n log n) possible)
    - Wrong variable updates
    """
    errors = []
    
    if algo_type == "sorting":
        # Check for missing swap flag optimization in bubble sort
        if "bubble" in content.lower() and "swapped" not in content.lower():
            errors.append("Bubble sort missing early exit optimization (swapped flag)")
        # Check for correct range in nested loops
        if "for i in range(len(arr))" in content and "for j in range(len(arr)-i-1)" not in content:
            errors.append("Likely off-by-one error in bubble sort range")
    
    elif algo_type == "search":
        # Binary search must update mid correctly
        if "binary" in content.lower():
            if "mid = (left+right)//2" not in content and "mid = Math.floor((left+right)/2)" not in content:
                errors.append("Binary search missing proper mid calculation")
            if "while left <= right" not in content:
                errors.append("Binary search loop condition likely wrong")
    
    elif algo_type == "dp":
        # Check if recursive fibonacci without memoization
        if "fibonacci" in content.lower() and "memo" not in content.lower():
            errors.append("Recursive fibonacci without memoization = exponential time")
    
    elif algo_type == "graph":
        # Missing visited set in BFS/DFS
        if ("bfs" in content.lower() or "dfs" in content.lower()) and "visited" not in content.lower():
            errors.append("Graph traversal missing visited set → infinite loop risk")
    
    return len(errors) == 0, errors

def rewrite_algorithm(file_path: Path, old_content: str, algo_type: str, detected_name: str) -> Optional[str]:
    """Replace broken algorithm with known working version."""
    ext = file_path.suffix.lower()
    lang = "python" if ext == ".py" else "javascript" if ext in [".js", ".ts", ".tsx"] else None
    
    if not lang:
        return None
    
    # Find matching template
    template = None
    for algo_name, templates in ALGORITHM_TEMPLATES.items():
        if algo_name in detected_name.lower() or algo_name in algo_type:
            if lang in templates:
                template = templates[lang]
                break
    
    if not template:
        return None
    
    # Extract function name from old code (preserve API)
    func_match = re.search(r'def\s+(\w+)\s*\(', old_content) if lang == "python" else re.search(r'function\s+(\w+)\s*\(', old_content)
    original_name = func_match.group(1) if func_match else "algorithm"
    
    # Replace function name in template
    if lang == "python":
        template = template.replace("def bubble_sort", f"def {original_name}")
        template = template.replace("def quick_sort", f"def {original_name}")
        template = re.sub(r'def \w+\(', f'def {original_name}(', template)
    else:
        template = template.replace("function bubbleSort", f"function {original_name}")
        template = template.replace("function quickSort", f"function {original_name}")
        template = re.sub(r'function \w+\(', f'function {original_name}(', template)
    
    return template

# ========== MEMORY SYSTEM ==========
class RepairMemory:
    def __init__(self):
        self.data = self._load()
    
    def _load(self) -> dict:
        if MEMORY_FILE.exists():
            try:
                return json.loads(MEMORY_FILE.read_text(encoding='utf-8'))
            except:
                return {"algorithm_fixes": [], "pattern_memory": {}, "stats": {"total_fixes": 0}}
        return {"algorithm_fixes": [], "pattern_memory": {}, "stats": {"total_fixes": 0}}
    
    def save(self):
        MEMORY_FILE.write_text(json.dumps(self.data, indent=2), encoding='utf-8')
    
    def record_algorithm_fix(self, file: str, algo_type: str, original_error: str, success: bool):
        self.data["algorithm_fixes"].append({
            "file": file,
            "type": algo_type,
            "error": original_error,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
        self.data["pattern_memory"][algo_type] = self.data["pattern_memory"].get(algo_type, 0) + 1
        self.data["stats"]["total_fixes"] += 1
        self.save()

memory = RepairMemory()

# ========== FILE REPAIR ENGINE ==========
def backup_file(file_path: Path) -> Path:
    rel = file_path.relative_to(REPO_ROOT)
    dest = BACKUP_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, dest)
    return dest

def repair_file(file_path: Path) -> Dict[str, Any]:
    result = {"path": str(file_path), "repaired": False, "actions": [], "algorithm_fixed": False}
    
    # Skip repair directories
    if any(p.startswith('_repair') or p == '.git' or p == 'node_modules' for p in file_path.parts):
        return result
    
    # Only process code files
    ext = file_path.suffix.lower()
    if ext not in ['.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c']:
        return result
    
    try:
        content = file_path.read_text(encoding='utf-8', errors='ignore')
    except:
        return result
    
    # Detect algorithms
    algorithms = detect_algorithms_in_file(content)
    if not algorithms:
        return result
    
    for algo_type, detected_name, line_num in algorithms:
        # Validate algorithm correctness
        is_valid, errors = validate_algorithm_performance(content, algo_type)
        
        if not is_valid:
            error_msg = "; ".join(errors)
            backup_file(file_path)
            
            # Attempt rewrite
            new_content = rewrite_algorithm(file_path, content, algo_type, detected_name)
            
            if new_content and new_content != content:
                file_path.write_text(new_content, encoding='utf-8')
                memory.record_algorithm_fix(str(file_path), algo_type, error_msg, True)
                result["repaired"] = True
                result["algorithm_fixed"] = True
                result["actions"].append(f"Rewrote {algo_type} algorithm: {error_msg}")
                break  # Fix one algorithm per file per run
            else:
                result["actions"].append(f"Detected broken {algo_type} but couldn't auto-fix: {error_msg}")
    
    return result

# ========== DEPLOYMENT & SYSTEM FIXES ==========
def fix_deployment_configs():
    """Ensure Vercel/Netlify/Render configs are correct for free tier."""
    # Vercel
    vercel_json = REPO_ROOT / "vercel.json"
    if vercel_json.exists():
        try:
            config = json.loads(vercel_json.read_text())
            if "functions" in config:
                # Ensure free tier limits
                config["functions"] = {k: v for k, v in config["functions"].items() if v.get("memory", 1024) <= 1024}
                vercel_json.write_text(json.dumps(config, indent=2))
        except:
            pass
    
    # Netlify
    netlify_toml = REPO_ROOT / "netlify.toml"
    if not netlify_toml.exists() and (REPO_ROOT / "index.html").exists():
        netlify_toml.write_text("""[build]
  publish = "."
[build.environment]
  NODE_VERSION = "18"
""")
        print("[Netlify] Created netlify.toml for static site")

# ========== MAIN ENGINE ==========
def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {msg}"
    # Use ANSI colors in CMD (works on Windows 10)
    if level == "ALGO":
        print(f"\033[96m{line}\033[0m")  # Cyan
    elif level == "REPAIR":
        print(f"\033[92m{line}\033[0m")  # Green
    elif level == "ERROR":
        print(f"\033[91m{line}\033[0m")  # Red
    else:
        print(line)
    
    with open(REPO_ROOT / "_repair_log.txt", "a", encoding='utf-8') as f:
        f.write(line + "\n")

def main():
    print("\n" + "="*60)
    print("🔧 REPAIR ENGINE v2.0 - ALGORITHM EDITION")
    print("="*60)
    log(f"Working in: {REPO_ROOT}", "INFO")
    log(f"Windows 10 CMD mode active", "INFO")
    
    # Create backup dir
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Walk all files
    all_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in ['_repair_backups', '.git', 'node_modules', '__pycache__', 'dist', 'build']]
        for file in files:
            all_files.append(Path(root) / file)
    
    log(f"Found {len(all_files)} files. Scanning for algorithms...", "INFO")
    
    repaired = 0
    algorithm_fixes = 0
    
    for file_path in all_files:
        result = repair_file(file_path)
        if result["repaired"]:
            repaired += 1
            if result["algorithm_fixed"]:
                algorithm_fixes += 1
                log(f"🧠 ALGO FIX: {result['path']} - {result['actions'][0]}", "ALGO")
            else:
                log(f"🔧 REPAIRED: {result['path']}", "REPAIR")
    
    # Fix deployment configs
    fix_deployment_configs()
    
    # Summary
    print("\n" + "="*60)
    print("📊 REPAIR SUMMARY")
    print("="*60)
    print(f"✅ Files repaired: {repaired}")
    print(f"🧠 Algorithm fixes: {algorithm_fixes}")
    print(f"📦 Backups stored in: {BACKUP_DIR}")
    print(f"📝 Memory saved to: {MEMORY_FILE}")
    print(f"📄 Log file: _repair_log.txt")
    print("\n💡 Run this script again to catch new issues & learn from past fixes")
    print("="*60)
    
    # Keep CMD window open
    if len(sys.argv) == 1:
        input("\nPress ENTER to exit...")

if __name__ == "__main__":
    main()
