import os
import sys
import ast
import time
import json
import re
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from mcp.server.mcpserver import MCPServer
from openai import OpenAI, APIConnectionError

# ==========================================
# 1. SETUP PATHS, LOGGING & DATABASE
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "audit_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("MCP_Auditor")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = logging.FileHandler(LOG_DIR / "system.log", encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Suppress noisy HTTP client logs to maintain clean MCP stdio stream
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

DB_PATH = BASE_DIR / "audit_history.db"

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                task_goal TEXT,
                output_content TEXT,
                status TEXT,
                category TEXT,
                feedback TEXT,
                duration_sec REAL
            )
        """)
        conn.commit()

init_db()

# ==========================================
# 2. CONFIGURATION & HYBRID DUAL-ROLE PROMPT
# ==========================================
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio", timeout=360.0)

def detect_model_name() -> str:
    """Dynamically detects active models from LM Studio, excluding embedding models."""
    try:
        models = client.models.list()
        if models.data:
            for m in models.data:
                if "embed" not in m.id.lower():
                    return m.id
            return models.data[0].id
    except Exception:
        pass
    return "local-model"

CACHED_MODEL = os.getenv("AUDITOR_MODEL") or detect_model_name()

mcp = MCPServer("LMStudio-DualRole-Pipeline")

HYBRID_SYSTEM_PROMPT = """
You are a Senior Principal Software Engineer & Chief Architect with world-class engineering expertise.
You operate in two dynamic modes, automatically selected based on the user's input:

==============================================
[ROLE 1: CODE AUDITOR] — Activated when programming code is submitted for evaluation.
==============================================
Mandate: Rigorously audit the submitted code against 10 strict engineering pillars:
1. Logic & Edge Cases: Verify boundary conditions, empty containers ([], {}), NoneType handling, ZeroDivision, type mismatches.
2. Performance & Memory: Identify redundant iterations, algorithmic bottlenecks, unclosed resources, memory leaks.
3. Security & Sanitization: Scan for injection vulnerabilities, unsafe deserialization, path traversal, missing sanitization.
4. Clean Architecture & Maintainability: Enforce strict Type Hinting, docstrings, PEP 8 standards, separation of concerns.
5. Absolute Truthfulness: Never fabricate facts, APIs, files, capabilities, or test execution results.
6. Analytical Precision: Explicitly distinguish verified facts from assumptions.
7. Meticulous Step-by-Step Verification: Execute validation systematically without skipping or rushing steps.
8. Strict Stub Management: When referencing unbuilt future components, require minimal interfaces/stubs to prevent runtime ImportErrors.
9. Audit & Verification: Check against security standards, thread safety, race conditions, and system blueprints.
10. Defensive Engineering Guidelines:
    * Production-Quality Python 3: Fully typed, strict data contracts using dataclasses or typed schemas at I/O boundaries.
    * RADS Loop & Iteration Failsafes: All loops and iterations MUST have explicit bounds (max_iterations or timeout_ms) to prevent deadlocks.
    * Structured Error Tracing: Exceptions MUST output structured diagnostic traces (e.g., [ERROR_CODE, MODULE_NAME, VARIABLE_STATES]) for self-healing loops.
    * Lifecycle & Safety: Always use Context Managers (with statements) for file/network I/O and locks.
    * Concurrency Safety: Guarantee lock release and prevent deadlocks/race conditions.
    * Zero Fluff: NO pass, TODO, ..., or truncated logic. Every module must be fully functional.

Required Response Format (Enforce exact structure):
STATUS: [APPROVED or REJECTED]
ISSUES_FOUND:
- [Itemized list of concrete issues, or "None" if clean]
ACTIONABLE_FEEDBACK:
- [Precise, line-specific remediation instructions with secure code snippets]
- [If standards are met, set STATUS to APPROVED and mandate the Axiom Aegis testing framework for rigorous verification.]

==============================================
[ROLE 2: SYSTEM ARCHITECT & STRATEGIST] — Activated when plans, ideas, specs, or questions are submitted.
==============================================
Mandate: Systematically plan, design architectures, and provide high-level technical strategies:
- Design end-to-end data flow, modular directory structures, and component topologies.
- Proactively analyze risks, algorithmic bottlenecks, failure points, and race conditions.
- Propose creative, differentiating architectural features and select optimal Python libraries with technical justifications.
- Synthesize an actionable Master Execution Plan ready for immediate engineering implementation.

Required Response Format:
## 🏗️ SYSTEM ARCHITECTURE & DESIGN
[Detailed component topology, interconnects, and data flows]

## ⚠️ RISK & EDGE CASE ANALYSIS
[Identified vulnerabilities, bottlenecks, and preemptive mitigation strategies]

## 🚀 MASTER EXECUTION PLAN
[Step-by-step roadmap (Step 1, 2, 3) including directory layout and foundational interfaces]
"""

# ==========================================
# 3. ADVANCED AST & SECURITY SENTINEL
# ==========================================
DANGEROUS_CALLS = {"eval", "exec", "__import__"}
DANGEROUS_MODULE_CALLS = {
    "os": {"system", "popen"},
    "subprocess": {"run", "Popen", "call", "check_output"}
}

BACKTICK_DELIMITER = chr(96) * 3

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.security_issues = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and node.func.id in DANGEROUS_CALLS:
            self.security_issues.append(f"Detected dangerous function call '{node.func.id}()' at line {node.lineno}")
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            mod_name = node.func.value.id
            func_name = node.func.attr
            if mod_name in DANGEROUS_MODULE_CALLS and func_name in DANGEROUS_MODULE_CALLS[mod_name]:
                self.security_issues.append(f"Detected high-risk system invocation '{mod_name}.{func_name}()' at line {node.lineno}")
        self.generic_visit(node)

def fast_syntax_check(content: str) -> tuple[bool, str]:
    """Stage 1: Fast-fail syntax validator and AST static security screener."""
    raw_text = content.strip()
    code_block = None

    # Safely extract code block if markdown code fences are present
    if BACKTICK_DELIMITER in raw_text:
        parts = raw_text.split(BACKTICK_DELIMITER)
        if len(parts) >= 3:
            extracted = parts[1].strip()
            if extracted.startswith("python"):
                extracted = extracted[6:].strip()
            code_block = extracted
    elif raw_text.startswith("def ") or raw_text.startswith("import ") or raw_text.startswith("class ") or raw_text.startswith("from "):
        code_block = raw_text

    # If input is natural language / architectural plan, pass directly to LLM
    if not code_block:
        return True, ""

    try:
        parsed_tree = ast.parse(code_block)
    except SyntaxError as e:
        return False, f"Syntax Error at line {e.lineno}: {e.msg}"

    visitor = SecurityVisitor()
    visitor.visit(parsed_tree)
    if visitor.security_issues:
        return False, f"Security Violation: {'; '.join(visitor.security_issues)}"

    return True, ""

# ==========================================
# 4. PERSISTENCE & DATA PIPELINE
# ==========================================
def save_audit_file(goal: str, content: str, rules: str, status: str, category: str, feedback: str, duration: float) -> str:
    """Persists detailed audit telemetry to atomic JSON files for DPO / dataset creation."""
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S_%f")[:19]
    safe_slug = re.sub(r'[^a-zA-Z0-9_\u0E00-\u0E7F]+', '_', goal)[:30].strip('_') or "audit_task"
    filename = f"{timestamp_str}_{status}_{safe_slug}.json"
    filepath = LOG_DIR / filename

    audit_record = {
        "timestamp": now.isoformat(),
        "status": status,
        "category": category,
        "task_goal": goal,
        "strict_rules": rules,
        "duration_sec": round(duration, 3),
        "submitted_content": content,
        "auditor_feedback": feedback
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(audit_record, f, ensure_ascii=False, indent=2)

    return str(filepath)

def save_to_db(goal: str, content: str, status: str, feedback: str, duration: float, category: str = "GENERAL"):
    """Saves high-level audit metrics and outcomes into SQLite."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(audit_logs)")
        cols = [col[1] for col in cursor.fetchall()]
        if "category" not in cols:
            cursor.execute("ALTER TABLE audit_logs ADD COLUMN category TEXT")

        cursor.execute(
            "INSERT INTO audit_logs (timestamp, task_goal, output_content, status, category, feedback, duration_sec) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), goal, content, status, category, feedback, round(duration, 3))
        )
        conn.commit()

# ==========================================
# 5. UNIFIED MCP TOOL ENTRY
# ==========================================
@mcp.tool()
def audit_submission(task_goal: str, output_content: str, strict_rules: str = "") -> str:
    """
    Unified Engine: Functions as both Code Auditor and System Architect in a single MCP tool.
    - Code input: Validates edge cases, logic, and security -> returns STATUS: APPROVED / REJECTED.
    - Architecture / Planning input: Analyzes topology, risks, and provides Master Execution Plan.
    """
    start_time = time.time()
    logger.info("--- [Unified Pipeline Triggered] ---")

    # Stage 1: Static AST & Security Sentinel
    is_valid, static_err = fast_syntax_check(output_content)
    if not is_valid:
        cat = "SECURITY" if "Security Violation" in static_err else "SYNTAX"
        verdict = f"STATUS: REJECTED\nISSUES_FOUND:\n- {static_err}\nACTIONABLE_FEEDBACK:\n- Resolve static syntax or security violations before resubmitting."
        elapsed = time.time() - start_time
        save_to_db(task_goal, output_content, "REJECTED", verdict, elapsed, category=cat)
        save_audit_file(task_goal, output_content, strict_rules, "REJECTED", cat, verdict, elapsed)
        logger.warning(f"Fast-check failed [{cat}]: {static_err}")
        return verdict

    # Stage 2: Inference via Hybrid Dual-Role Prompt
    user_payload = f"[TASK / GOAL]:\n{task_goal}\n\n[CONSTRAINTS / RULES]:\n{strict_rules or 'Standard best practices'}\n\n[INPUT CONTENT]:\n{output_content}"
    category = "LLM_INFERENCE"
    active_model = os.getenv("AUDITOR_MODEL") or detect_model_name()
    try:
        response = client.chat.completions.create(
            model=active_model,
            messages=[
                {"role": "system", "content": HYBRID_SYSTEM_PROMPT},
                {"role": "user", "content": user_payload}
            ],
            temperature=0.4,
            max_tokens=24000
        )

        msg = response.choices[0].message
        verdict = msg.content if (msg.content and msg.content.strip()) else (getattr(msg, "reasoning_content", "") or "No response received")

    except APIConnectionError:
        category = "CONNECTION_ERROR"
        verdict = "STATUS: REJECTED\nISSUES_FOUND:\n- Unable to connect to LM Studio server.\nACTIONABLE_FEEDBACK:\n- Verify that LM Studio is open and the Local Server has been started."
    except Exception as e:
        category = "SYSTEM_ERROR"
        verdict = f"STATUS: REJECTED\nISSUES_FOUND:\n- Internal system error: {str(e)}"

    elapsed = time.time() - start_time

    # Stage 3: Classify outcome and persist records
    if "STATUS: APPROVED" in verdict:
        status = "APPROVED"
        category = "CODE_AUDIT"
    elif "STATUS: REJECTED" in verdict:
        status = "REJECTED"
        category = "CODE_AUDIT"
    else:
        status = "PLANNING"
        category = "SYSTEM_ARCHITECTURE"

    save_to_db(task_goal, output_content, status, verdict, elapsed, category=category)
    save_audit_file(task_goal, output_content, strict_rules, status, category, verdict, elapsed)
    logger.info(f"Pipeline Completed in {elapsed:.2f}s | Status: {status} | Category: {category}")

    return verdict

if __name__ == "__main__":
    mcp.run()