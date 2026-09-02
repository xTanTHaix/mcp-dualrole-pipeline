# 🛡️ MCP Local Auditor & System Architect V2

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Protocol](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-orange.svg)](https://modelcontextprotocol.io/)
[![Runtime](https://img.shields.io/badge/LM%20Studio-Compatible-purple.svg)](https://lmstudio.ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#-license)

A dual-mode, zero-token-cost local engineering engine built on the Model Context Protocol (MCP). It dynamically switches between **Production Code Auditor** (enforcing 10 strict engineering pillars) and **System Architect & Strategist** (generating topologies and execution plans) via local models in LM Studio, backed by a fast AST security filter, dual data sinks (SQLite & DPO-ready JSON logs), and a real-time Discord notification daemon.

---

| 🧩 The MCP Dual-Role Pipeline | ⚙️ Engineering Autonomous Reliability |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/d8b24432-4dd5-4d80-8faa-5cc50453a333" alt="The MCP Dual-Role Pipeline" width="100%"> | <img src="https://github.com/user-attachments/assets/9fbe021e-dc55-4563-ada4-9e268d9a830c" alt="Engineering Autonomous Reliability" width="100%"> |
| *A framework for synchronized, context-aware AI workflows* | *Pairs an Executor with a Critic in a localized environment* |

---

## ✨ Core Capabilities

| Feature | Description |
| :--- | :--- |
| **Zero-Cost Local Critic** | Offloads exhaustive validation loops to local GPUs via LM Studio without spending cloud tokens. |
| **Sub-Millisecond AST Sentinel** | Rejects Python syntax errors and blocks high-risk calls (`eval`, `exec`, `os.system`, `subprocess`) before hitting the LLM. |
| **Dynamic Dual Modes** | Automatically detects whether input is raw code or high-level architecture/specs, executing context-specific validation prompts. |
| **Dual Data Persistence** | Records execution metrics into SQLite (`audit_history.db`) and exports atomic JSON telemetry (`audit_logs/`) suitable for DPO fine-tuning datasets. |
| **Live Discord Telemetry** | Background daemon monitors audit output files in real time and pushes structured embeds directly to Discord. |
| **Dynamic Model Discovery** | Automatically queries LM Studio's active model endpoint, bypassing embedding engines dynamically. |

---

| 🌉 The Standardized Context Bridge | ⚖️ Separation of Concerns: Dual-Role Dynamic |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/d8e5092b-824b-47d0-b972-b9a3be7f3c3e" alt="The Standardized Context Bridge" width="100%"> | <img src="https://github.com/user-attachments/assets/b13a0892-173d-42ef-bca2-df2dfa2c3a9f" alt="Separation of Concerns" width="100%"> |
| *Decoupled Read/Write operations via universal MCP layer* | *Executor (generation) vs Reviewer (zero-temperature validation)* |

---

## 🔄 System Architecture

```text
       [ User Submission / Agent Request via MCP ]
                            │
                            ▼
              [ Stage 1: Fast AST Sentinel ] ─────────────────────────┐
         (Syntax Parse & Danger Call Interception)                    │
                            │ (Valid Code or Specs)                   │ (Syntax / Security
                            ▼                                         │  Violation)
           [ Stage 2: Hybrid Dual-Role LLM ]                          │
           (LM Studio Local Inference Server)                         │
            ├── Role 1: 10-Pillar Code Audit                          │
            └── Role 2: Architecture & Master Plan                    │
                            │                                         │
                            ▼                                         │
               [ Stage 3: Multi-Sink Logger ] <───────────────────────┘
            ├── SQLite DB (Metrics & Analytics)
            └── Atomic JSON Logs (DPO Datasets)
                            │
                            ▼ (File Write Event)
             [ Daemon: Discord Watcher Loop ]
         (Rich Embed Notifications pushed to Webhook)

```

---

## 🎭 Dynamic Dual-Role Modes

The engine routes tasks automatically based on the payload structure passed to `audit_submission`:

### 1. Code Auditor Mode (Activated on Code Submissions)

Audits incoming implementations against 10 strict defensive engineering rules:

* **Logic & Edge Conditions:** Null checks, division by zero, empty collections.
* **Resource Leaks & Performance:** Unclosed context managers, algorithmic bottlenecks.
* **Defensive Boundaries:** Type hints, data contracts via dataclasses, bounded loop guards.
* **Deterministic Contract:** Enforces a rigid feedback schema (`STATUS: APPROVED` or `STATUS: REJECTED`).

---

| 🗺️ Pipeline Architecture Mapping | ⏱️ Chronological Execution Workflow |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/7945c964-c7b0-4f56-8917-f3eb0997c13f" alt="Pipeline Architecture Mapping" width="100%"> | <img src="https://github.com/user-attachments/assets/dfb5a475-f340-46d3-bb42-029f0cc68644" alt="Chronological Execution Workflow" width="100%"> |
| *Orchestrator routing across MCP server and dual agents* | *Ingest → Query → Synthesize → Audit → Output pipeline* |

---

### 2. System Architect & Strategist Mode (Activated on Specs/Plans)

Generates system designs for technical prompts without code:

* **Component Topologies:** Data flow patterns, directory structures, modular interconnects.
* **Preemptive Risk Modeling:** Concurrency bottlenecks, race conditions, failure points.
* **Master Execution Plans:** Step-by-step phased roadmaps ready for direct implementation.

---

## 📡 Real-Time Discord Watcher

`watch_audit_logs.py` runs as an asynchronous observer over the `audit_logs/` directory, dispatching notifications whenever new audit artifacts are produced:

```bash
python watch_audit_logs.py

```

* **Automated Polling:** Tracks `.json` additions with debounce guards.
* **Markdown Formatting:** Renders status tags (`APPROVED`, `REJECTED`), duration metrics, summaries, and issue breakdowns.
* **Zero Configuration Fallback:** Operates headlessly in the background without halting the core MCP pipeline.

---

| 🔄 The Autonomous Refinement Engine | 📦 Data Routing & State Management Payload |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/7e372054-3f1c-40d1-b1b3-d2ab2d2cfc18" alt="Autonomous Refinement Engine" width="100%"> | <img src="https://github.com/user-attachments/assets/aa9928e9-0a51-4bfa-9056-fd7d5f9ab889" alt="State Management Payload" width="100%"> |
| *Continuous feedback loop eliminating hallucination drift* | *Strict turn-based JSON schema preventing infinite loops* |

---

## 🚀 Quick Start

### 1. Prerequisites

* Python 3.10+
* [LM Studio](https://lmstudio.ai/) running an OpenAI-compatible Local Server at `http://localhost:1234/v1`
* Any MCP-compatible host client

### 2. Installation

```bash
# Clone the repository
git clone [https://github.com/xTanThaix/mcp-local-auditor.git](https://github.com/xTanThaix/mcp-local-auditor.git)
cd mcp-local-auditor

# Set up virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

```

### 3. Register with MCP Client

Add the server definition into your client's `mcpServers` configuration (e.g., `mcp_config.json`):

```json
{
  "mcpServers": {
    "lmstudio-auditor": {
      "command": "python",
      "args": ["/path/to/mcp-local-auditor/auditor_bridge.py"]
    }
  }
}

```

### 4. Configure LM Studio

1. Launch **LM Studio** and load an instruction-tuned model (e.g., `Qwen-2.5-Coder`, `DeepSeek-Coder`).
2. Open the **Local Server** tab.
3. Set the port (default: `1234`) and click **Start Server**.

---

| 🏗️ Deployment Dependencies & Infrastructure | 🚀 Pipeline Characteristics & Extensibility |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/f94b0658-bab5-47dd-b0a9-2547062d28dd" alt="Deployment Dependencies" width="100%"> | <img src="https://github.com/user-attachments/assets/c5476f02-ad12-43cb-b2f3-32b3ef952b55" alt="Pipeline Extensibility" width="100%"> |
| *Modular runtime stack connecting local MCP servers with LLMs* | *Guaranteed context alignment and drop-in extensibility* |

---

## 🤖 Agent Loop Protocol

To make your coding assistant iteratively fix its own mistakes, inject this instruction rule into your agent configuration:

```markdown
# Mandatory MCP Code Audit Protocol
Every time code is generated or refactored, you MUST invoke the `audit_submission` tool:
- Arguments: `task_goal`, `output_content`, `strict_rules`
- If STATUS == "REJECTED": Inspect `ACTIONABLE_FEEDBACK`, remediate reported issues, and re-submit.
- If STATUS == "APPROVED": Deliver final verified code to the user.
- Cap recovery loops at a maximum of 5 attempts.

```

---

## 🧪 Test Suite

Run the full pytest suite to validate AST guards, SQLite migrations, and mocked inference pipelines without needing a live LM Studio instance:

```bash
pytest test_auditor.py -v

```

---

## 💖 Support & Donations

If this project helps streamline your local AI engineering workflow, consider supporting development:

* **Ko-fi:** [https://ko-fi.com/xtanthaix](https://ko-fi.com/xtanthaix)
* **GitHub Sponsors:** Available directly via repository profile

---

## 📄 License

Distributed under the MIT License. Free for personal, commercial, and open-source implementation.

```
