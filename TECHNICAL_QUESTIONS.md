# Technical Review Questions & Answers

## Assessment by Tenacious Techies Private Limited
### Position: AI Automation & Agents Developer

---

### Question 1: When should the agent answer directly and when should it call a tool?
**Answer:**
- **Answer Directly:** The agent should answer directly for conversational pleasantries (e.g., greetings, thanking the user), conversational clarification (e.g., asking for a missing Order ID), or general guidance on what capabilities the agent offers.
- **Call a Tool:** The agent **MUST** call a tool whenever answering requires:
  1. **Dynamic / Authoritative State:** Order status, courier location, order item breakdown, or payment status.
  2. **Side Effects / State Changes:** Cancelling an order, updating delivery instructions, or submitting a formal support ticket.
  3. **External Policy Grounding (RAG):** Searching authoritative restaurant policies regarding cancellations, allergen warnings, or delivery fees.
- **Rule of Thumb:** Any operational factual claim about a specific transaction or restaurant rule must originate from tool execution or retrieved RAG context—never from the LLM's parametric memory.

---

### Question 2: How do you prevent the LLM from hallucinating an order status?
**Answer:**
We prevent hallucination using a multi-layered architectural defense:
1. **System Prompt Grounding Constraints:** Explicit directives informing the model that it does not possess internal operational knowledge and is strictly forbidden from guessing order details.
2. **Deterministic Context Injection:** When an order inquiry is detected (e.g. `ORD-1005`), the tool `get_order_status` executes first against the database. The authoritative JSON result is injected into the model prompt.
3. **Graceful Negative Handling:** If an order does not exist (`ORDER_NOT_FOUND`) or the service is down (`SERVICE_UNAVAILABLE`), the tool returns an explicit error payload: `{"success": false, "error": "Order not found"}`. The prompt instructs the model to state the exact error rather than imagining a status.
4. **Structured Output Validation:** For operational actions, the system requires Pydantic validation of model outputs before any downstream execution occurs.

---

### Question 3: How does your RAG pipeline select relevant knowledge?
**Answer:**
1. **Semantic Document Chunking:** Policy documents in markdown format are split along section headers (`## Heading`) while preserving document-level parent metadata (`# Title > ## Section`).
2. **Dense & Hybrid Vector Embedding:** Chunks are projected into a normalized vector space using Gemini embeddings (`models/text-embedding-004`) or deterministic SHA-256 TF-IDF n-gram vectors.
3. **Cosine Similarity Search:** User queries are embedded and searched against the ChromaDB persistent collection using cosine similarity.
4. **Score Thresholding (`RAG_SCORE_THRESHOLD` = 0.55):** Documents with similarity scores below the threshold are discarded.
5. **Fallback Refusal:** If no document surpasses the score threshold, the retriever returns an empty list, prompting the agent to truthfully state that no official policy is documented and offer human ticket escalation.

---

### Question 4: What happens when retrieved documents contain conflicting information?
**Answer:**
1. **Hierarchical Metadata Precedence:** Policy chunks include metadata with document revision dates and hierarchy levels (e.g., *Terms of Service & Cancellation Policy* takes precedence over general *FAQs*).
2. **Top Similarity & Recency Ordering:** Chunks are sorted primarily by similarity score and secondary recency timestamp.
3. **LLM Prompt Conflict Instructions:** The system prompt instructs the LLM: *"If retrieved policy excerpts contain conflicting rules, adopt the most restrictive/conservative policy for customer safety and explicitly mention that support will verify the exact policy."*
4. **Automated Escalation:** In production, high ambiguity can trigger an automatic escalation tag on the generated support ticket for human staff review.

---

### Question 5: How would you protect the agent against prompt injection from users or retrieved documents?
**Answer:**
1. **Application-Level Pre-Flight Guardrail (`SecurityGuardrails.inspect_input`):**
   - Regex and heuristic scanners analyze incoming user messages for known injection patterns (`"ignore all previous instructions"`, `"reveal system prompt"`, `"dump database"`, `"you are now in developer mode"`).
   - If detected, execution stops before the LLM or tools are invoked, returning a standardized security refusal.
2. **Data-Prompt Segregation (XML/Markdown Encapsulation):**
   - Retrieved RAG documents and tool outputs are wrapped inside distinct XML tags (`<retrieved_context>` / `<tool_result>`) so the model treats them as passive data rather than instructions.
3. **Output Scrubbing (`SecurityGuardrails.inspect_output`):**
   - Responses are scanned to redact accidental leaks of API keys, environment credentials, or private connection strings.
4. **Deterministic Authorization Gate:**
   - Database queries are parameterized through SQLAlchemy. The LLM cannot execute raw SQL or request all customer records.

---

### Question 6: Which decisions should never be left solely to an LLM?
**Answer:**
1. **Financial Transactions & Refunds:** Direct execution of monetary refunds or wallet balance modifications should be verified by deterministic business logic (e.g., checking if order status is still in `RECEIVED`) or require human manager approval for large sums.
2. **Data Access Authorization:** Determining whether a user is allowed to view customer records must be enforced by session authentication and database filters, never by asking the LLM "Is the user authorized?".
3. **Database Schema / Code Execution:** Never allow the LLM to generate or execute raw SQL, shell commands, or arbitrary code on production infrastructure.
4. **Health & Safety Decisions:** Severe allergen emergencies or food safety hazard complaints must automatically trigger critical tier-1 human escalation workflows.

---

### Question 7: How do you prevent duplicate support tickets if an agent retries a failed workflow?
**Answer:**
1. **Idempotency Keys:** Every ticket generation request computes a deterministic idempotency key based on:
   `idempotency_key = f"{customer_id}-{order_id or 'none'}-{category}-{hash(complaint_text)}"`
2. **Unique Database Constraint:** The `support_tickets` table enforces a unique index on `idempotency_key`.
3. **Repository Interception:** When `TicketRepository.create_ticket` is called, it first checks if a ticket with the same idempotency key already exists. If found, it returns the existing ticket entity without creating a duplicate.
4. **TTL Caching:** In high-throughput distributed systems, Redis `SET key value NX EX 300` ensures concurrent retry attempts are deduplicated within a time window.

---

### Question 8: How would you evaluate whether the agent is improving or regressing after prompt/model changes?
**Answer:**
1. **Automated Golden Dataset Regression Suite:**
   - Maintain a curated suite of 50+ golden conversation test cases covering order tracking, policy queries, complaints, injections, and edge cases.
   - Run via Pytest on every PR / deployment.
2. **Deterministic Metric Assertions:**
   - **Tool Calling Accuracy:** Did the agent call `get_order_status` with the exact expected arguments?
   - **Grounding & Citation Rate:** Did the agent cite the correct source file from RAG?
   - **Guardrail Precision / Recall:** Did prompt injection tests trigger the security refusal? Did legitimate questions pass without false positives?
3. **LLM-as-a-Judge Evaluation:**
   - A secondary evaluator model grades agent answers against reference answers for correctness, conciseness, politeness, and adherence to safety guidelines.
4. **Latency & Token Budget Benchmarks:**
   - Automated checks ensuring P95 latency and token consumption remain within budget.

---

### Question 9: How would you scale this architecture for thousands of restaurant conversations?
**Answer:**
1. **Stateless API Tier:** Deploy FastAPI as stateless containerized replicas behind an Application Load Balancer (AWS ALB / Cloud Run / Kubernetes).
2. **Persistent Enterprise Database:** Migrate SQLite to PostgreSQL on AWS RDS / GCP Cloud SQL with connection pooling (e.g. PgBouncer) and read replicas for order tracking.
3. **Distributed Session Storage:** Store multi-turn chat history in Redis with automatic TTL expiration (e.g. 2-hour session cache).
4. **Scalable Vector Database:** Transition ChromaDB to managed vector databases such as Qdrant, Pinecone, or pgvector.
5. **Asynchronous Background Workers:** Offload notification dispatching, webhook delivery, and audit log processing to Celery / Redis Queue (RQ) or AWS SQS.
6. **Smart Model Routing & Caching:** Route simple FAQ/policy queries to `gemini-1.5-flash` with semantic vector response caching, reserving larger reasoning models for complex disputes.

---

### Question 10: Bonus Implementations in this Project
**Answer:**
1. **Human-in-the-Loop Escalation:** `TicketWorkflow.escalate_ticket` allows human supervisors to take over critical tickets with dedicated status transitions (`ESCALATED`, `IN_PROGRESS`, `RESOLVED`).
2. **Session Persistence in SQLite:** Multi-turn conversation turns are stored persistently in the database across user sessions.
3. **Observability & Trace Viewer:** Built-in telemetry capturing tool execution latency, intent classifications, token estimates, and security audit logs viewable in the UI.
4. **Live Failure Diagnostic Simulation:** Toggleable simulated outages (`/api/debug/simulate-outage`) to test tool unavailability in real time.
5. **Dual LLM & Embedding Engine:** Supports official Google Gemini API SDK with an automatic deterministic local mock engine for reproducible testing.
