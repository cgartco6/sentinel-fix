#!/usr/bin/env python3
"""
Sovereign Sentinel: Self-Healing Agentic Codebase Engine
======================================================
A zero-dependency drop-in code auditor and repair system.
Utilizes SQLite local memory, AST syntactic checking, and adaptive anti-pattern
learning powered directly by the Gemini 2.5 Flash Preview API.
"""

import os
import sys
import json
import sqlite3
import re
import ast
import time
import urllib.request
import urllib.error
from typing import List, Dict, Tuple, Optional, Any

# =====================================================================
# AGENTIC SYSTEM INSTRUCTIONS
# =====================================================================
INSPECTOR_SYSTEM = (
    "You are an elite Static Code & Architecture Auditor.\n"
    "Your role is to inspect code blocks for:\n"
    "1. Syntax correctness and total completeness (strict check against partial code stub patterns).\n"
    "2. Missing imports or unreferenced local packages.\n"
    "3. Structural errors, empty placeholder blocks, dangling elements, or lazy implementation shortcuts.\n\n"
    "You must respond strictly with a valid JSON document matching this schema:\n"
    "{\n"
    "  \"is_broken\": true,\n"
    "  \"confidence_score\": 0.95,\n"
    "  \"issues\": [\"Detailed description of syntax issue\", \"Missing export for function X\"],\n"
    "  \"structural_gaps\": [\"Needs module import 'math'\", \"Missing class implementation stubs\"]\n"
    "}\n"
    "Do not output any introductory or explanatory text. Output only raw, valid JSON."
)

ARTISAN_SYSTEM = (
    "You are a Master Software Engineer specializing in zero-defect structural programming.\n"
    "Your mission is to write absolute, production-grade, long-form, working source code.\n\n"
    "CRITICAL DIRECTIVES:\n"
    "- NEVER write comments like '// TODO: implement later', '# Code here...', or use ellipses.\n"
    "- Write every single class, method, variable, imports list, and processing block in full detail.\n"
    "- Do not invent APIs; match the established repository structure and import patterns exactly.\n"
    "- Output ONLY the clean, rewritten source code wrapped in standard markdown triple backticks. Do not add explanations."
)

RECONCILER_SYSTEM = (
    "You are an AI Memory Keeper.\n"
    "Your job is to study a failed code correction attempt and synthesize a 'Lesson Learned'.\n"
    "Analyze the broken attempt, study the parser's syntax validation errors, and draft a short, "
    "clear design principle explaining how to avoid this bug in the future. Keep it brief and logical."
)


# =====================================================================
# LOCAL SQLITE MEMORY SYSTEM
# =====================================================================
class SentinelMemory:
    """Manages the agent's long-term memory of positive and negative coding patterns."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Table to store successful coding layout structures
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS good_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_context TEXT,
                    key_signature TEXT UNIQUE,
                    solved_code TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Table to store failures (Anti-Patterns) and synthesized lessons
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anti_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_context TEXT,
                    error_signature TEXT UNIQUE,
                    broken_code TEXT,
                    lessons_learned TEXT,
                    occurrence_count INTEGER DEFAULT 1
                )
            """)
            conn.commit()

    def store_success(self, file_path: str, code: str):
        """Saves or updates a successfully verified file pattern."""
        key_signature = os.path.basename(file_path)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO good_patterns (file_context, key_signature, solved_code, frequency)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(key_signature) DO UPDATE SET
                    solved_code=excluded.solved_code,
                    frequency=frequency + 1,
                    last_applied=CURRENT_TIMESTAMP
            """, (file_path, key_signature, code))
            conn.commit()

    def store_anti_pattern(self, file_path: str, broken_code: str, error_msg: str, lesson: str):
        """Stores a failure signature alongside lessons to serve as real-time guardrails."""
        error_sig = f"{os.path.basename(file_path)}::{error_msg[:120]}"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO anti_patterns (file_context, error_signature, broken_code, lessons_learned, occurrence_count)
                VALUES (?, ?, ?, ?, 1)
                ON CONFLICT(error_signature) DO UPDATE SET
                    broken_code=excluded.broken_code,
                    lessons_learned=excluded.lessons_learned,
                    occurrence_count=occurrence_count + 1
            """, (file_path, error_sig, broken_code, lesson))
            conn.commit()

    def retrieve_relevant_patterns(self, file_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Fetches dynamic success and error contextual history for similar files."""
        file_name = os.path.basename(file_path)
        ext = os.path.splitext(file_name)[1]
        
        good = []
        bad = []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Fetch similar successes
            cursor.execute(
                "SELECT * FROM good_patterns WHERE file_context LIKE ? OR file_context LIKE ? ORDER BY frequency DESC LIMIT 2",
                (f"%{file_name}%", f"%{ext}")
            )
            good = [dict(row) for row in cursor.fetchall()]

            # Fetch relevant failures
            cursor.execute(
                "SELECT * FROM anti_patterns WHERE file_context LIKE ? OR file_context LIKE ? ORDER BY occurrence_count DESC LIMIT 2",
                (f"%{file_name}%", f"%{ext}")
            )
            bad = [dict(row) for row in cursor.fetchall()]
            
        return good, bad


# =====================================================================
# INTEGRATION AGENT & API CONNECTOR
# =====================================================================
class GeminiAgentClient:
    """Zero-dependency Gemini API HTTP connector with exponential backoff routing."""
    
    def __init__(self, api_key: str, temperature: float = 0.1):
        self.api_key = api_key
        self.temperature = temperature
        self.model = "gemini-2.5-flash-preview-09-2025"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def query_brain(self, prompt: str, system_instruction: str, json_mode: bool = False) -> str:
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": self.temperature,
            }
        }

        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # Exponential Backoff Retry Loop (Retries up to 5 times)
        backoff_delay = [1.0, 2.0, 4.0, 8.0, 16.0]
        
        for attempt in range(len(backoff_delay) + 1):
            try:
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    return res_data["candidates"][0]["content"]["parts"][0]["text"]
            except urllib.error.HTTPError as e:
                # Handle rate limiting (HTTP 429) silently with backoff
                if e.code == 429 and attempt < len(backoff_delay):
                    time.sleep(backoff_delay[attempt])
                    continue
                raise RuntimeError(f"Gemini API request failed with code {e.code}: {e.read().decode('utf-8')}")
            except Exception as e:
                if attempt < len(backoff_delay):
                    time.sleep(backoff_delay[attempt])
                    continue
                raise RuntimeError(f"Sovereign Sentinel lost network connection: {str(e)}")
        
        raise RuntimeError("Sovereign Sentinel API Connection Error: Maximum retry limit reached.")


# =====================================================================
# SYSTEM PARSERS & FILE SANITIZERS
# =====================================================================
class CodeValidator:
    """Validates structural soundness of code variations before saving."""
    
    @staticmethod
    def validate_file(file_path: str, code: str) -> Tuple[bool, str]:
        if file_path.endswith(".py"):
            try:
                ast.parse(code)
                return True, "AST parsed successfully."
            except SyntaxError as e:
                err_detail = f"Line {e.lineno}, Col {e.offset}: {e.msg}\n-> {e.text}"
                return False, f"Python Syntax Error: {err_detail}"
            except Exception as e:
                return False, f"AST Engine exception: {str(e)}"
                
        elif file_path.endswith(".json"):
            try:
                json.loads(code)
                return True, "JSON schema parsed successfully."
            except json.JSONDecodeError as e:
                return False, f"JSON Parsing Error: {str(e)}"
                
        elif file_path.endswith((".js", ".ts", ".jsx", ".tsx")):
            # Fast, basic brace balancer for web framework configurations
            open_curly = code.count("{")
            close_curly = code.count("}")
            if open_curly != close_curly:
                return False, f"Brace Unbalance: Contains {open_curly} '{{' and {close_curly} '}}'."
                
        return True, "Code passed structural baseline checks."


# =====================================================================
# MASTER SENTINEL ENGINE ORCHESTRATOR
# =====================================================================
class SentinelEngine:
    """The core engine orchestrating repository analysis, memory lookup, and repairs."""
    
    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.engine_dir = os.path.join(self.workspace_root, "_sentinel_engine")
        os.makedirs(self.engine_dir, exist_ok=True)
        
        self.config = self._load_or_create_config()
        
        # Verify API Key availability
        api_key = os.getenv("GEMINI_API_KEY", self.config.get("gemini_api_key", ""))
        if not api_key:
            print("[FATAL ERROR] GEMINI_API_KEY environment variable is not defined.")
            print("Please set your API key by running:")
            print("  export GEMINI_API_KEY='your-api-key-here'")
            print("Or update the config.json inside the '_sentinel_engine' directory.")
            sys.exit(1)
            
        self.config["gemini_api_key"] = api_key
        self.memory = SentinelMemory(os.path.join(self.engine_dir, self.config["db_name"]))
        self.llm = GeminiAgentClient(api_key, self.config["temperature"])

    def _load_or_create_config(self) -> Dict[str, Any]:
        config_path = os.path.join(self.engine_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_target_files(self) -> List[str]:
        """Crawls target paths using exclusion and target file configurations."""
        target_files = []
        exclude_dirs = set(self.config.get("exclude_dirs", []))
        extensions = tuple(self.config.get("allowed_extensions", []))
        
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith(extensions):
                    rel_path = os.path.relpath(os.path.join(root, file), self.workspace_root)
                    target_files.append(rel_path)
        return target_files

    def extract_pure_code(self, response_text: str) -> str:
        """Strips structural markdown markers, extracting compile-ready code blocks."""
        pattern = r"
http://googleusercontent.com/immersive_entry_chip/0

---

### ⚡ To Run the Module
Execute the script from your root project path by running:
```bash
export GEMINI_API_KEY="your-actual-api-key"
python3 _sentinel_engine/sentinel.py
