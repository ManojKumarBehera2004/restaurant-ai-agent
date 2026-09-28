# System Architecture & Technical Design

## AI Restaurant Support & Operations Agent

---

### 1. High-Level Architecture Overview

The system is engineered following a modular, layered architecture that strictly separates:
- **Transport / API Layer (FastAPI)**
- **Agent Orchestrator & Guardrails Layer**
- **LLM Abstraction & Provider Layer (Gemini & Mock)**
- **Tool Execution & Registry Layer**
- **Knowledge Base Retrieval Layer (RAG with ChromaDB)**
- **End-to-End Automation Workflow Layer (Complaint Triage & Ticket Generation)**
- **Persistence & Repository Layer (SQLite / PostgreSQL ready)**
- **Observability, Tracing & Audit Layer**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Web Chat UI & REST Clients                     │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTP / JSON
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application Gateway                        │
│   • /api/agent/chat      • /api/orders/*     • /api/support/tickets        │
│   • /api/health          • /api/rag/search   • /api/debug/simulate-outage  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Security & Guardrails Layer                           │
│   • Prompt Injection & Jailbreak Defense    • Output Credential Scrubbing   │
│   • Input Sanitization & Boundaries         • Authorization Gatekeeper      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Agent Orchestration Layer                            │
│   • Intent Router & Dispatcher              • Multi-Turn Context Manager    │
│   • Tool Calling Budget / Loop Prevention   • Response Grounding Engine     │
└──────────────┬───────────────────────┬──────────────────────┬───────────────┘
               │                       │                      │
               ▼                       ▼                      ▼
┌─────────────────────────┐ ┌──────────────────────┐ ┌────────────────────────┐
│     Tool Registry       │ │    RAG Retriever     │ │  Complaint Automation  │
│ • get_order_status      │ │ • ChromaDB Collection│ │ • Issue Classifier     │
│ • get_order_details     │ │ • Semantic Chunking  │ │ • Sentiment / Urgency  │
│ • cancel_order          │ │ • Top-K & Threshold  │ │ • Structured Ticket    │
│ • create_support_ticket │ │ • Safe Fallback      │ │ • Notification Dispatch│
└──────────────┬──────────┘ └──────────┬───────────┘ └──────────┬─────────────┘
               │                       │                        │
               ▼                       ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       LLM Service Abstraction Layer                         │
│   • BaseLLMService (ABC Interface)                                          │
│   • GeminiLLMService (Official Google Generative AI SDK)                    │
│   • MockLLMService (Deterministic Offline / Test Mode)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Persistence & Repository Layer                        │
│   • OrderRepository         • TicketRepository (Idempotent)                 │
│   • ConversationRepository  • AuditLogRepository                            │
│   • SQLite Database (PostgreSQL ready via SQLAlchemy ORM)                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Core Subsystems

#### 2.1 Agent Reasoning & Execution Flow
1. **Input Inspection**: User input passes through `SecurityGuardrails` detecting prompt injections, system prompt override commands, or bulk extraction exploits.
2. **Intent Routing**: `IntentRouter` categorizes user queries into `ORDER_TRACKING`, `ORDER_DETAILS`, `POLICY_INQUIRY`, `COMPLAINT`, `ORDER_CANCEL`, or `GENERAL`.
3. **Deterministic Tool & RAG Dispatch**:
   - For order status / details, the agent queries the `ToolRegistry` and receives authoritative JSON from `OrderService`.
   - For policy queries, `PolicyRetriever` pulls top-k semantically relevant chunks with score thresholding.
   - For complaints (e.g. payment deducted + order failed), the automated `ComplaintWorkflow` triages the issue, computes sentiment and urgency, and creates a support ticket with deduplication.
4. **Response Grounding & Output Sanitization**: Output is scrubbed for sensitive credentials and returned with full telemetry (latency, token estimate, tool execution trace).

#### 2.2 LLM Provider Abstraction
To avoid vendor lock-in, the codebase relies solely on `BaseLLMService`. Replacing Gemini with Anthropic Claude, OpenAI, or local vLLM requires implementing a single class conforming to:
- `generate_text(prompt, system_instruction)`
- `generate_structured(prompt, system_instruction)`
- `chat_with_tools(messages, system_instruction, tool_definitions)`

#### 2.3 RAG Knowledge Base Architecture
- **Documents**: Markdown files structured in `data/restaurant_policies/` (`cancellation_and_refunds.md`, `delivery_and_tracking.md`, `operating_hours_and_policies.md`, `faqs_and_special_requests.md`).
- **Chunking**: Header-aware semantic chunking preserving document titles and section context.
- **Vector Indexing**: ChromaDB persistent vector store with cosine distance indexing and dual embedding support (Gemini text embeddings + local deterministic TF-IDF embeddings).
- **Safe Fallback**: If retrieved documents have similarity below `RAG_SCORE_THRESHOLD` (0.55), the system declines to speculate and offers support ticket escalation.

#### 2.4 Reliability & Failure Handling
1. **Mock Outage Diagnostics**: Toggleable simulated service outages via `/api/debug/simulate-outage` allowing live validation of failure scenarios.
2. **Deterministic Fallbacks**: Clear error dictionaries returned to the agent if services are unreachable, preventing hallucination.
3. **Idempotent Support Tickets**: Idempotency keys (`customer_id + order_id + category + hash(complaint)`) prevent duplicate ticket creation on workflow retries.
4. **Loop Protection**: Execution bounded by `MAX_AGENT_ITERATIONS` to prevent infinite tool loops.

---

### 3. Observability & Security Architecture

- **Zero-Secret Logging**: `JsonFormatter` applies regex sanitization to scrub API keys, authorization bearer tokens, and passwords from logs.
- **Trace Viewer**: Real-time in-memory and database audit logging tracking tool execution latency and status.
- **Customer Data Boundary**: Direct SQL or bulk harvesting queries are blocked at both application-level regex and repository queries.

---

### 4. Assumptions & System Boundaries

- **Authentication Assumption:** User context is mapped via `session_id` and verified operational order IDs rather than a live external SSO/OAuth2 provider.
- **RAG Embedding Space:** Uses ChromaDB with cosine distance indexing and dual embedding support (Gemini + SHA-256 TF-IDF fallback).
- **Payment & Refund Execution:** Order status and financial records are persisted in SQLite; live bank transfers are gated behind operational ticket approvals.

