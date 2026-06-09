# RAG Architectural Patterns (Retrieval-Augmented Generation)

This document summarizes major Retrieval-Augmented Generation (RAG) architectural patterns, from basic pipelines to advanced agentic systems, including diagrams and a design decision framework.

---

# 1. Naive (Basic) RAG

```mermaid
flowchart LR
A[User Query] --> B[Retrieve Top-K Docs]
B --> C[Insert into Prompt]
C --> D[LLM Generates Answer]
```

**Key Traits:**

* Single retrieval step
* No query refinement
* Fast but noisy

---

# 2. Dense / Semantic RAG

```mermaid
flowchart LR
A[User Query] --> B[Embedding Model]
B --> C[Vector DB Search]
C --> D[Top-K Context]
D --> E[LLM]
```

**Key Traits:**

* Semantic search using embeddings
* Better recall than keyword search

---

# 3. Hybrid RAG

```mermaid
flowchart LR
A[Query] --> B1[Dense Retrieval]
A --> B2[Sparse BM25 Retrieval]
B1 --> C[Merge Results]
B2 --> C
C --> D[LLM]
```

**Key Traits:**

* Combines keyword + semantic search
* More robust retrieval

---

# 4. Rerank-Enhanced RAG

```mermaid
flowchart LR
A[Query] --> B[Retrieve Many Docs]
B --> C[Reranker Model]
C --> D[Top-K Refined Context]
D --> E[LLM]
```

**Key Traits:**

* High precision retrieval
* Cross-encoder or LLM reranking

---

# 5. Multi-Hop RAG

```mermaid
flowchart LR
A[Query] --> B[Retrieve Step 1]
B --> C[Generate Sub-Question]
C --> D[Retrieve Step 2]
D --> E[Combine Context]
E --> F[LLM Answer]
```

**Key Traits:**

* Multi-step reasoning
* Iterative retrieval

---

# 6. Query-Rewriting RAG

```mermaid
flowchart LR
A[User Query] --> B[LLM Query Rewriter]
B --> C[Optimized Query]
C --> D[Retrieval]
D --> E[LLM]
```

**Key Traits:**

* Improves retrieval quality
* Expands/clarifies queries

---

# 7. Hierarchical / Contextual RAG

```mermaid
flowchart LR
A[Query] --> B[Doc Level Retrieval]
B --> C[Section Level]
C --> D[Paragraph Level]
D --> E[LLM]
```

**Key Traits:**

* Multi-granular retrieval
* Efficient context usage

---

# 8. Graph RAG

```mermaid
flowchart LR
A[Query] --> B[Graph Traversal]
B --> C[Related Nodes]
C --> D[Subgraph Context]
D --> E[LLM]
```

**Key Traits:**

* Knowledge graph-based retrieval
* Strong for relationships

---

# 9. Agentic RAG

```mermaid
flowchart LR
A[Query] --> B[LLM Planner]
B --> C{Decide Action}
C -->|Retrieve| D[Vector DB]
C -->|Re-query| B
D --> E[Context Assembly]
E --> F[LLM Response]
```

**Key Traits:**

* Autonomous decision-making
* Iterative reasoning loops

---

# 10. Tool-Augmented RAG

```mermaid
flowchart LR
A[Query] --> B[LLM Router]
B --> C[Tool/API Call]
C --> D[External Data]
D --> E[LLM Synthesis]
```

**Key Traits:**

* Integrates APIs, DBs, web tools
* Beyond document retrieval

---

# 11. Self-Reflective / Corrective RAG

```mermaid
flowchart LR
A[Query] --> B[Initial Answer]
B --> C[Critique Model]
C --> D{Satisfactory?}
D -->|No| E[Re-retrieve]
E --> B
D -->|Yes| F[Final Answer]
```

**Key Traits:**

* Self-evaluation loop
* Reduces hallucinations

---

# 12. Multimodal RAG

```mermaid
flowchart LR
A[Query] --> B[Multimodal Retriever]
B --> C[Text + Image + Audio + Video]
C --> D[Unified Context]
D --> E[LLM]
```

**Key Traits:**

* Cross-modal retrieval
* Rich data understanding

---

# 13. Agentic + Tool + RAG Hybrid

```mermaid
flowchart LR
A[Query] --> B[LLM Orchestrator]
B --> C{Decision Layer}
C --> D[RAG Retrieval]
C --> E[Tool Calls]
D --> F[Context Fusion]
E --> F
F --> G[Final LLM Response]
```

**Key Traits:**

* Most advanced architecture
* Combines tools + retrieval + reasoning

---

# RAG Design Decision Framework

Choosing the right RAG architecture depends on four dimensions:

---

## 1. Query Complexity

* Simple factual queries → Naive / Dense RAG
* Multi-step reasoning → Multi-Hop / Agentic RAG
* Relationship-heavy queries → Graph RAG

---

## 2. Data Type

* Text only → Dense / Hybrid RAG
* Structured + relational → Graph RAG
* Mixed media → Multimodal RAG

---

## 3. Accuracy vs Latency Tradeoff

| Goal             | Recommended Pattern |
| ---------------- | ------------------- |
| Lowest latency   | Naive RAG           |
| Balanced         | Hybrid + Rerank     |
| Highest accuracy | Agentic / Multi-hop |

---

## 4. Tool Requirements

* No external tools → Standard RAG
* APIs / DBs needed → Tool-Augmented RAG
* Complex workflows → Agentic + Tool Hybrid

---

## Practical Recommendation Map

* **Startups / MVPs:** Naive → Hybrid RAG
* **Enterprise search:** Hybrid + Rerank + Query Rewrite
* **AI agents:** Agentic + Tool + RAG
* **Knowledge graphs:** Graph RAG
* **Advanced assistants:** Multimodal + Agentic RAG

---

## Key Insight

Most production systems today are **hybrids**, combining multiple RAG patterns rather than relying on a single architecture.

---

# End of Document
