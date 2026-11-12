# agent-forge

`agent-forge` is a command-line interface (CLI) and compiler engine that converts declarative enterprise operational models into production-grade, containerized, deterministic multi-agent architectures paired with an executive Claude-inspired conversational interface.

Rather than building static dashboards or brittle script collections, `agent-forge` allows AI agents and system architects to scaffold, validate, and compile turnkey enterprise AI operating systems with role-based governance, Human-in-the-Loop (HITL) gates, and multi-model tool execution.

---

## Core Features

- **Declarative Enterprise Modeling:** Define an entire enterprise organization (roles, segregation of duties, data sources, third-party connectors, finite-state workflows, and RAG knowledge policies) in structured YAML and Markdown manifests.
- **Deterministic vs Probabilistic Separation:** Business workflows are expressed as finite-state machines (LangGraph/StateGraph), ensuring critical operations (financial transactions, legal contracts, shipments) remain predictable and reproducible.
- **DMZ Perimeter Isolation:** External untrusted inputs (webhooks, public requests, customer emails) are sanitized into typed Pydantic events within an isolated DMZ perimeter before reaching internal back-office orchestrators.
- **Four-Eyes Principle (Segregation of Duties):** Built-in policy enforcement cryptographically guarantees that the initiator of a sensitive action cannot approve their own operation.
- **Safety-Tiered Tool Fabric:** Built-in tool packs (developer, operations, commerce, trade, legal) classified across `read_only`, `mutating_safe`, and `critical_hitl`. Sensitive tools automatically suspend execution until explicit human approval is received.
- **Claude-Inspired Conversational Interface:** Turnkey, warm editorial web interface designed with Sanzō Wada harmonized palettes, editorial serif typography, floating rounded input bars, contextual recommendation chips, and interactive in-chat action cards.
- **Dynamic Settings & Hot Key Reloading:** Built-in settings manager with encrypted key masking supporting Google Gemini (native OpenAI-compatible endpoint), OpenAI, and local Ollama, complete with in-flight connection ping diagnostics and SMTP email configuration.

---

## Architectural Principles

```text
[ External Triggers / Webhooks / User Prompts ]
                       │
                       ▼
             ┌───────────────────┐
             │    DMZ Ingress    │  <- Idempotency Locks (Redis)
             └─────────┬─────────┘  <- Event Sanitization (Pydantic)
                       │
                       ▼
             ┌───────────────────┐
             │  Back-Office FSM  │  <- LangGraph State Machine
             └─────────┬─────────┘  <- Multi-Model Circuit Breaker
                       │
         ┌─────────────┴─────────────┐
         ▼                           ▼
┌──────────────────┐       ┌──────────────────┐
│ Autonomous Tools │       │   HITL Gateway   │  <- Four-Eyes SoD Validation
└──────────────────┘       └─────────┬────────┘
                                     ▼
                           [ Human Approver Sign-off ]
```

1. **Idempotency by Design:** Every event ingress is guarded by unique deduplication keys to prevent duplicate execution across at-least-once message delivery systems.
2. **Circuit Breakers:** Model invocation circuits monitor consecutive failures and trigger automatic fallback or suspension before compounding errors.
3. **Auditability:** Complete execution history and state transitions are snapshotted in checkpointer storage for forensic compliance.

---

## Directory Structure of a Company Manifest

A company is fully specified through five declarative artifacts:

```text
manifest/
├── company.yaml             # Company identity, domain, timezone, HITL default approver
├── org_matrix.yaml          # Roles, permissions, spending thresholds, Four-Eyes rules
├── data_sources.yaml        # Authoritative systems of record and conflict resolution
├── connectors.yaml          # Third-party integrations, rate limits, env credentials
├── workflows/               # Finite state machines for company business processes
│   └── pull_request_delivery.yaml
└── policies/                # Tribal knowledge, procedures, and domain guides for RAG
    ├── dev/
    │   └── commit_guidelines.md
    └── finance/
        └── approval_limits.md
```

---

## Installation

### Prerequisites

- Python 3.14 or later
- [uv](https://github.com/astral-sh/uv) or `pip`
- Docker and Docker Compose (for compiled target deployments)

### Setup

```bash
git clone https://github.com/ind4x/agent-forge.git
cd agent-forge
pip install -e .
```

Alternatively, run with `uv`:

```bash
uv pip install -e .
```

---

## CLI Usage

### 1. Initialize a New Manifest

Scaffolds a clean reference manifest directory ready for enterprise customization:

```bash
agent-forge init ./specs/my_company --name "Acme Corp" --slug "acme-corp"
```

### 2. Validate Manifest Integrity

Verifies Pydantic schema validation, cross-references between roles, SoD rules, and workflow state transitions:

```bash
agent-forge validate ./specs/my_company
```

### 3. Compile the Complete Deployment

Compiles the declarative manifest into a turnkey containerized deployment with FastAPI DMZ, Redis checkpointer, Claude-style interface, and test suite:

```bash
agent-forge build ./specs/my_company --output ./dist/my_company
```

### 4. Inspect Built-in Tool Fabric

Displays all available tool packs, categorized by safety tier:

```bash
agent-forge list-tools
```

---

## Built-in Tool Packs

| Pack | Key Tools | Safety Level | Description |
| :--- | :--- | :--- | :--- |
| **Dev** | `ast_code_auditor`, `test_runner_sandbox`, `conventional_commit_checker` | `read_only` | Code parsing, syntax verification, sandbox test execution |
| **Ops** | `safe_file_writer`, `deploy_production`, `send_client_email` | `critical_hitl` | Safe filesystem writes, production deployments, official emails |
| **Artisan / Trade** | `quote_calculator`, `stock_inventory_lookup`, `business_kpi_summary` | `read_only` / `mutating_safe` | Material cost modeling, stock alerts, VAT calculations |
| **Legal** | `legal_conflict_checker`, `procedural_deadline_calculator`, `case_dossier_lookup`, `legal_code_rag_search`, `fee_convention_generator` | `read_only` / `critical_hitl` | Bar conflict checks, procedural deadlines, dossier lookups, fee conventions |

---

## Compiled Deployment Artifacts

When `agent-forge build` runs, it generates:

- `docker-compose.yml`: PostgreSQL 16 (`pgvector`), Redis 7, and FastAPI application container.
- `core/`:
  - `state.py`: Global enterprise state definition.
  - `checkpointer.py`: In-memory and persistent state checkpointer engine.
  - `llm_client.py`: Multi-provider LLM client (Google Gemini, OpenAI, Ollama).
  - `chat_assistant.py`: Tool-calling assistant loop with HITL action card emission.
  - `settings_manager.py`: Hot configuration manager with masked credential persistence.
  - `dmz_ingress.py`: FastAPI perimeter service with `/api/chat`, `/api/settings`, and `/api/hitl/resolve`.
  - `dashboard.html`: Claude-inspired editorial web interface.
  - `hitl_gateway.py`: Human-in-the-loop pause and approval engine enforcing SoD rules.
  - `resilience.py`: Redis idempotency locks and model circuit breakers.
- `subgraphs/`: Compiled workflow graphs reflecting each defined state machine.
- `tests/`: Automated unit and integration test suite (`test_deployment.py`).
- `deploy.sh`: Turnkey deployment shell script.
- `README_AGENT.md`: Machine-readable specification enabling autonomous AI agents to maintain and extend the compiled system.

---

## Included Reference Manifests

The repository provides reference manifests in `specs/examples/`:

- **Acme Corp (`specs/examples/acme_corp`)**: Software engineering and product organization with code audit, test sandboxing, and peer-reviewed deployment workflows.
- **LexCorp Legal (`specs/examples/lexcorp_legal`)**: Legal practice organization featuring deontological conflict-of-interest screening, procedural deadline calculations, and managing partner fee convention sign-off.

Validate and build any example:

```bash
agent-forge validate ./specs/examples/lexcorp_legal
agent-forge build ./specs/examples/lexcorp_legal --output ./dist/lexcorp_legal
```

---

## Verification & Testing

Execute the test suite:

```bash
pytest -v
```

All 16 test suites verify tool behavior, manifest validation, Pydantic constraints, and compiler generation end-to-end.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Author

- **Author:** Youssef Fellah ([ind4x_](https://github.com/ind4x))
