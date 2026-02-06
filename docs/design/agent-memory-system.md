# Agent Memory System Design

## Overview

This document presents a comprehensive design for an agent memory system where users can add memories through both a UI and through agent interactions. The design is informed by state-of-the-art research (2025-2026) across frameworks (Letta/MemGPT, LangMem, Google ADK, Mem0, CrewAI), academic papers, and production systems (ChatGPT, Claude, Cursor).

The design is tailored for integration with the **adk-skills** library and Google ADK agents, but the architecture is framework-agnostic.

---

## Table of Contents

1. [Memory Taxonomy](#1-memory-taxonomy)
2. [Architecture Overview](#2-architecture-overview)
3. [Storage Layer](#3-storage-layer)
4. [Memory Lifecycle](#4-memory-lifecycle)
5. [Retrieval System](#5-retrieval-system)
6. [User-Facing Memory (UI)](#6-user-facing-memory-ui)
7. [Agent-Driven Memory](#7-agent-driven-memory)
8. [Multi-Tenancy and Isolation](#8-multi-tenancy-and-isolation)
9. [API Design](#9-api-design)
10. [Integration with adk-skills](#10-integration-with-adk-skills)
11. [Forgetting and Decay](#11-forgetting-and-decay)
12. [Research Summary](#12-research-summary)

---

## 1. Memory Taxonomy

Drawing from cognitive science and modern agent frameworks, the system organizes memory into five functional types:

### 1.1 Working Memory (Short-Term / In-Context)

The agent's active scratchpad — content currently in the LLM's context window (system prompt, recent turns, tool results, injected memories). Bounded by the model's context window. Even with 100K+ token windows, context stuffing degrades quality due to cost, latency, and the "lost in the middle" attention problem.

**Scope**: Single turn / session
**Persistence**: None (ephemeral)
**Storage**: In-memory only

### 1.2 Semantic Memory (Facts / Knowledge)

Generalized factual knowledge — user preferences, domain facts, entity attributes, rules. Abstracts away event-specific context to capture reusable knowledge.

- "The user prefers Python over JavaScript" (semantic)
- "The user's deployment target is Kubernetes on GCP" (semantic)

**Scope**: Cross-session, cross-thread
**Persistence**: Long-term
**Storage**: Vector DB + relational metadata

### 1.3 Episodic Memory (Experiences / Events)

Records of specific past interactions, preserving temporal context (when, where, what happened). Captures the complete chain of thought that led to successful (or failed) outcomes — essentially experience replay.

- "In our Jan 5 conversation, the user asked me to rewrite their JS code in Python and the migration succeeded using approach X" (episodic)

**Scope**: Cross-session
**Persistence**: Long-term (with decay)
**Storage**: Vector DB + timestamps + session references

### 1.4 Procedural Memory (Skills / How-To)

Internalized knowledge of *how* to perform tasks — workflows, rules, behavioral patterns. In adk-skills, this naturally maps to **skills** themselves. Procedural memory can also include dynamically-learned system prompt modifications.

**Scope**: Cross-session, potentially shared across users
**Persistence**: Long-term
**Storage**: Skills registry (existing adk-skills infrastructure) + prompt optimization store

### 1.5 Entity Memory

Structured knowledge about specific entities — people, organizations, projects — and their attributes and relationships.

**Scope**: Cross-session
**Persistence**: Long-term
**Storage**: Graph DB or structured relational store

### How They Interact

```
┌─────────────────────────────────────────────────────┐
│                   WORKING MEMORY                     │
│        (context window: prompt + recent turns        │
│         + retrieved memories + tool results)         │
└────────────┬──────────┬──────────┬──────────────────┘
             │retrieve  │retrieve  │retrieve
             ▼          ▼          ▼
     ┌───────────┐ ┌─────────┐ ┌──────────┐
     │ SEMANTIC   │ │EPISODIC │ │ ENTITY   │
     │ (facts)    │ │(events) │ │(entities)│
     └─────┬─────┘ └────┬────┘ └────┬─────┘
           │consolidate  │            │
           ◄─────────────┘            │
           │              relationships│
           ◄──────────────────────────┘
     ┌─────┴─────┐
     │PROCEDURAL  │
     │(skills,    │
     │ behaviors) │
     └───────────┘
```

Episodic memories consolidate into semantic knowledge over time. Frequently-used semantic knowledge can become procedural (habit formation). Entity memory feeds relationships into semantic memory.

---

## 2. Architecture Overview

### High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│                                                              │
│  ┌─────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │  Web UI      │  │  Agent Tools      │  │  REST API     │  │
│  │  (manage,    │  │  (save_memory,    │  │  (CRUD +      │  │
│  │   browse,    │  │   recall_memory,  │  │   search)     │  │
│  │   search)    │  │   forget_memory)  │  │               │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────┬────────┘  │
│         │                   │                    │           │
└─────────┼───────────────────┼────────────────────┼───────────┘
          │                   │                    │
          ▼                   ▼                    ▼
┌──────────────────────────────────────────────────────────────┐
│                     MEMORY SERVICE LAYER                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                   MemoryManager                          │ │
│  │                                                          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌──────────┐│ │
│  │  │Formation │ │Retrieval │ │Consolidation│ │Forgetting ││ │
│  │  │Engine    │ │Engine    │ │Engine       │ │Engine     ││ │
│  │  └──────────┘ └──────────┘ └────────────┘ └──────────┘│ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐ │
│  │ Embedding Service │  │ Conflict Resolution / Dedup      │ │
│  └──────────────────┘  └──────────────────────────────────┘ │
│                                                              │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                       STORAGE LAYER                          │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │  Vector DB    │  │  Relational   │  │  Graph DB          │ │
│  │  (embeddings, │  │  (metadata,   │  │  (entity relations,│ │
│  │   semantic    │  │   sessions,   │  │   knowledge graph) │ │
│  │   search)     │  │   audit log)  │  │                    │ │
│  └──────────────┘  └──────────────┘  └───────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Separate storage from presentation** — What is persisted vs. what goes into the prompt are independent concerns.
2. **Memory types have different lifecycles** — Semantic, episodic, and procedural memory need different schemas, update mechanisms, and retrieval strategies.
3. **Dual ingestion paths** — User-explicit memories (UI/API) and agent-extracted memories (autonomous) flow through the same pipeline but with different trust levels.
4. **Forgetting is a feature** — Active decay, consolidation, and pruning are first-class operations.
5. **Scoped isolation** — Strict namespace boundaries prevent memory leakage across tenants/users/projects.
6. **Transparency** — Users can inspect, edit, and delete any memory the system holds about them.

---

## 3. Storage Layer

### 3.1 Recommended Hybrid Architecture

No single backend suffices. The recommended production architecture combines three storage tiers:

| Tier | Backend | Purpose | Examples |
|------|---------|---------|----------|
| **Vector** | pgvector, Qdrant, or ChromaDB | Semantic similarity search over embedded memories | Memory retrieval by meaning |
| **Relational** | PostgreSQL (or SQLite for dev) | Structured metadata, sessions, audit logs, memory lifecycle state | Filtering, sorting, TTL enforcement |
| **Graph** (optional) | Neo4j, FalkorDB, or in-app adjacency | Entity relationships, knowledge graph traversal | "What do I know about Project X and its dependencies?" |

### 3.2 Why Hybrid?

Research consistently shows that pure vector search is insufficient:

- **Vector DB** excels at semantic similarity but cannot express temporal ordering, importance hierarchies, or entity relationships.
- **Relational DB** handles structured queries, metadata filtering, and transactional consistency but cannot do semantic similarity.
- **Graph DB** captures entity relationships and enables multi-hop reasoning but is overkill for simple fact storage.

**Mem0** (2025) demonstrates this hybrid approach in production: embeddings in a vector DB, relationships in a graph backend, metadata in a relational store, all orchestrated through a unified memory management layer.

### 3.3 Pragmatic Starting Point

For an MVP integrated with adk-skills (which already has SQLAlchemy support):

| Phase | Vector | Relational | Graph |
|-------|--------|-----------|-------|
| **MVP** | ChromaDB (embedded) | SQLite via SQLAlchemy | None (entity extraction stored as structured JSON) |
| **Production** | pgvector (PostgreSQL extension) | PostgreSQL | Neo4j or FalkorDB |
| **Scale** | Qdrant or Pinecone (managed) | PostgreSQL with partitioning | Neo4j Aura (managed) |

### 3.4 Schema Design

#### Memory Record (Relational)

```python
class MemoryRecord:
    # Identity
    id: UUID
    namespace: str          # "{tenant}/{user}/{project}"
    memory_type: MemoryType # SEMANTIC | EPISODIC | ENTITY | PROCEDURAL

    # Content
    content: str            # The memory text
    summary: str | None     # Compressed version for context injection
    embedding_id: str       # Reference to vector DB entry

    # Metadata
    source: MemorySource    # USER_EXPLICIT | AGENT_EXTRACTED | SYSTEM
    confidence: float       # 0.0-1.0, higher for user-explicit
    importance: float       # 0.0-1.0, LLM-scored or user-set
    tags: list[str]         # Categorical labels
    entity_refs: list[str]  # Referenced entity IDs

    # Lifecycle
    created_at: datetime
    updated_at: datetime
    last_accessed_at: datetime
    access_count: int
    decay_rate: float       # Per-day decay factor
    expires_at: datetime | None  # Hard TTL

    # Provenance
    source_session_id: str | None
    source_message_id: str | None
    created_by: str         # "user" | "agent" | "system"

    # Versioning
    version: int
    previous_version_id: UUID | None
```

#### Entity Record (Relational + Graph)

```python
class EntityRecord:
    id: UUID
    namespace: str
    name: str               # "John Smith"
    entity_type: str        # "person" | "organization" | "project" | ...
    attributes: dict        # {"role": "CTO", "company": "Acme"}
    memory_refs: list[UUID] # Memories mentioning this entity
    created_at: datetime
    updated_at: datetime

class EntityRelation:
    id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relation_type: str      # "works_at" | "manages" | "depends_on"
    attributes: dict
    confidence: float
    source_memory_id: UUID  # Memory this was extracted from
```

---

## 4. Memory Lifecycle

### 4.1 Formation (Creation)

Memories enter the system through two paths:

#### Path A: User-Explicit (UI / API / Natural Language)

```
User action (UI click, API call, or "remember this")
  → Validate content
  → Generate embedding
  → Extract entities (optional)
  → Store with source=USER_EXPLICIT, confidence=1.0
  → Index in vector DB
  → Return confirmation
```

User-explicit memories are treated as ground truth (confidence=1.0) and are never automatically modified or deleted — only the user can change them.

#### Path B: Agent-Extracted (Autonomous)

```
Agent interaction completes
  → Background extraction job triggers (async, "sleep-time")
  → LLM evaluates conversation for memorable content
  → Extracts candidate memories with importance scores
  → Deduplication check against existing memories
  → Conflict resolution (new info vs. existing)
  → Store with source=AGENT_EXTRACTED, confidence=0.7-0.9
  → Index in vector DB
  → (Optional) Surface to user for confirmation
```

Agent-extracted memories have lower default confidence and can be automatically consolidated or pruned. Optionally, they can be surfaced to the user for confirmation (upgrading them to USER_EXPLICIT).

### 4.2 The Hot-Path vs. Sleep-Time Tradeoff

| Approach | Latency Impact | Memory Quality | Use When |
|----------|---------------|----------------|----------|
| **Hot-path** (extract during conversation) | +200-500ms per turn | Lower (time pressure) | Real-time personalization needed |
| **Sleep-time** (extract after conversation) | None | Higher (more deliberate) | Quality > immediacy |
| **Hybrid** (critical facts hot, rest sleep) | +100ms for critical | Best of both | Production systems |

**Recommendation**: Use the hybrid approach. Extract high-importance facts (user preferences, corrections, explicit instructions) on the hot path. Defer episode summarization, entity extraction, and consolidation to background processing.

### 4.3 Update and Conflict Resolution

When new information conflicts with existing memories:

```python
class ConflictStrategy(Enum):
    LATEST_WINS = "latest_wins"       # New memory replaces old
    HIGHEST_CONFIDENCE = "confidence"  # Keep the more confident one
    MERGE = "merge"                    # LLM merges both into one
    KEEP_BOTH = "keep_both"           # Store both, let retrieval decide
    ASK_USER = "ask_user"             # Surface conflict to user
```

**Default strategy by source**:

| New Memory Source | Existing Source | Strategy |
|-------------------|----------------|----------|
| USER_EXPLICIT | Any | LATEST_WINS (user is always right) |
| AGENT_EXTRACTED | USER_EXPLICIT | KEEP_BOTH (never overwrite user) |
| AGENT_EXTRACTED | AGENT_EXTRACTED | MERGE or LATEST_WINS (by confidence) |

### 4.4 Consolidation

Periodic background process that:

1. **Summarizes episodic clusters** — Groups of related episodes are condensed into semantic facts.
2. **Merges duplicate semantics** — Near-duplicate memories are merged into single entries.
3. **Updates entity graphs** — New relationships extracted from recent memories are added to entity records.
4. **Promotes patterns to procedural** — Recurring behavioral patterns are extracted into system prompt modifications.

```
Consolidation Pipeline (runs periodically or on threshold):

  Episodic memories (last N days)
    → Cluster by topic (embedding similarity)
    → For each cluster: LLM summarizes into semantic fact(s)
    → Check for conflicts with existing semantic memories
    → Store new semantic memories, mark episodes as "consolidated"

  Semantic memories (all)
    → Find near-duplicates (embedding similarity > 0.95)
    → LLM merges duplicates into single memory
    → Update references

  Entity mentions (from recent memories)
    → Extract new entities and relationships
    → Merge with existing entity graph
    → Update entity attributes
```

---

## 5. Retrieval System

### 5.1 Multi-Signal Scoring

Following the foundational model from Park et al. ("Generative Agents"), each memory is scored across multiple dimensions:

```
score = α * relevance + β * recency + γ * importance + δ * access_frequency
```

Where:
- **Relevance** (α): Cosine similarity between query embedding and memory embedding
- **Recency** (β): Exponential decay from last access time: `decay_factor^(hours_since_access)`
- **Importance** (γ): LLM-scored or user-assigned importance (0.0-1.0)
- **Access frequency** (δ): Log-normalized access count (frequently-used memories are likely useful)

**Default weights** (tunable per use case): α=0.4, β=0.2, γ=0.3, δ=0.1

### 5.2 Retrieval Pipeline

```
User query / Agent context
    │
    ▼
┌─────────────────────┐
│ 1. Embedding Search  │  Vector DB: top-K by cosine similarity
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 2. Metadata Filter   │  Relational: namespace, type, date range, tags
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 3. Entity Expansion  │  Graph: expand query with related entities
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 4. Multi-Signal Rank │  Combine relevance + recency + importance + frequency
└──────────┬──────────┘
           ▼
┌─────────────────────┐
│ 5. Context Assembly  │  Format top-N memories for prompt injection
└──────────┬──────────┘
           ▼
  Injected into working memory
```

### 5.3 Proactive vs. Reactive Retrieval

Two retrieval patterns (following Google ADK's design):

**Reactive Recall**: The agent explicitly calls a memory tool when it recognizes a knowledge gap.
```python
# Agent decides to search memory
result = recall_memory(query="user's preferred deployment platform")
```

**Proactive Recall (Preloading)**: A preprocessor automatically injects relevant memories before the model is invoked.
```python
# Runs before every agent turn
class MemoryPreloader:
    def preload(self, user_message: str, session: Session) -> list[Memory]:
        """Search memory using the user's message as query.
        Inject top-K relevant memories into the system prompt."""
        relevant = self.memory_service.search(
            query=user_message,
            namespace=session.namespace,
            top_k=5,
            min_relevance=0.3,
        )
        return relevant
```

**Recommendation**: Use both. Proactive recall catches obvious context (user preferences, project settings). Reactive recall handles specific knowledge gaps during complex reasoning.

---

## 6. User-Facing Memory (UI)

### 6.1 Design Principles for User Memory UI

Based on analysis of ChatGPT, Claude, and Cursor's approaches:

1. **Full transparency** — Users see everything the system remembers about them.
2. **Granular control** — Edit, delete, or pin individual memories.
3. **Natural language interface** — "Remember that I prefer TypeScript" works alongside the UI.
4. **Source attribution** — Every memory shows how it was created (user-added vs. agent-extracted).
5. **No surprises** — Agent-extracted memories are either surfaced for confirmation or clearly marked.

### 6.2 UI Components

#### Memory Dashboard

```
┌─────────────────────────────────────────────────────────┐
│  My Memories                                    [+ Add] │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐│
│  │ 🔍 Search memories...                    [Filters ▼]││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  Filter: [All Types ▼] [All Sources ▼] [Date Range ▼]  │
│                                                         │
│  ── Preferences ──────────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Prefers Python for backend, TypeScript for frontend  ││
│  │ 📌 Pinned · Added by you · Jan 15, 2026             ││
│  │                                    [Edit] [Delete]   ││
│  └─────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────┐│
│  │ Uses pytest with --strict-markers flag               ││
│  │ 🤖 Agent-extracted · Confidence: 92% · Feb 1, 2026  ││
│  │                          [Confirm] [Edit] [Dismiss]  ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ── Project Context ──────────────────────────────────  │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Deployment target: GKE cluster in us-central1        ││
│  │ 📌 Pinned · Added by you · Dec 10, 2025             ││
│  │                                    [Edit] [Delete]   ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  ── Recent (Agent-Extracted) ─────────────────────────  │
│  ┌─────────────────────────────────────────────────────┐│
│  │ Had trouble with SQLAlchemy async sessions;          ││
│  │ resolved by using async_sessionmaker                 ││
│  │ 🤖 Agent-extracted · From session abc123 · Feb 3     ││
│  │                          [Confirm] [Edit] [Dismiss]  ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
│  [Load more...]                                         │
│                                                         │
│  ── Settings ──────────────────────────────────────────  │
│  [x] Allow agent to extract memories automatically      │
│  [ ] Require confirmation for agent-extracted memories   │
│  [ ] Enable memory sharing across projects              │
└─────────────────────────────────────────────────────────┘
```

#### Add Memory Modal

```
┌────────────────────────────────────────────┐
│  Add Memory                        [Close] │
│                                            │
│  What should the agent remember?           │
│  ┌────────────────────────────────────────┐│
│  │ I deploy to AWS using CDK with         ││
│  │ TypeScript. Always use us-east-1.      ││
│  └────────────────────────────────────────┘│
│                                            │
│  Type: [Preference ▼]                      │
│  Scope: [All Projects ▼]                   │
│  Pin: [ ] Always include in context        │
│                                            │
│  [Cancel]                       [Save]     │
└────────────────────────────────────────────┘
```

#### In-Chat Memory Notifications

```
┌──────────────────────────────────────────────────────────┐
│ Agent: I've noted that you prefer async SQLAlchemy       │
│ sessions. I'll remember this for future conversations.   │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ 💾 Memory saved: "Prefers async SQLAlchemy sessions  │ │
│ │ with async_sessionmaker"                             │ │
│ │                              [View] [Edit] [Undo]    │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

### 6.3 Natural Language Memory Commands

The agent should recognize and handle memory-related natural language:

| User says | Action |
|-----------|--------|
| "Remember that I prefer X" | Create semantic memory, source=USER_EXPLICIT |
| "Forget that I work at X" | Delete matching memories |
| "What do you remember about me?" | List memories for this user |
| "Update my preference to Y" | Find and update matching memory |
| "Don't remember anything from this conversation" | Exclude session from extraction |
| "Pin the fact about deployment" | Mark memory as always-included |

---

## 7. Agent-Driven Memory

### 7.1 How Agents Decide What to Remember

The agent needs heuristics (and optionally learned policies) to autonomously decide what is worth storing. Based on current research, here is a tiered approach:

#### Tier 1: Rule-Based Extraction (MVP)

```python
EXTRACTION_RULES = [
    # User preferences and corrections
    {"pattern": "user explicitly states a preference", "importance": 0.9},
    {"pattern": "user corrects the agent", "importance": 0.95},
    {"pattern": "user provides personal/project info", "importance": 0.8},

    # Factual knowledge
    {"pattern": "new domain fact learned", "importance": 0.6},
    {"pattern": "API key, endpoint, or config detail", "importance": 0.7},

    # Episodic (experience)
    {"pattern": "successful resolution of a problem", "importance": 0.7},
    {"pattern": "failed approach (to avoid repeating)", "importance": 0.8},

    # Low value (skip)
    {"pattern": "small talk, greetings", "importance": 0.0},
    {"pattern": "transient debugging output", "importance": 0.1},
]
```

#### Tier 2: LLM-Scored Extraction (Recommended)

After each conversation (sleep-time), an LLM evaluates the session:

```python
EXTRACTION_PROMPT = """
Review this conversation and extract memories worth storing.
For each candidate memory, provide:
- content: The fact/experience to remember
- type: SEMANTIC | EPISODIC | ENTITY
- importance: 0.0-1.0 (how likely is this to be useful in future?)
- entities: Any people, projects, or organizations mentioned

Rules:
- DO extract: user preferences, corrections, project context, successful/failed approaches
- DO NOT extract: greetings, transient debugging details, information already in memory
- Prefer concise, reusable facts over verbose session transcripts
- Score importance based on reuse potential, not conversation significance

Existing memories (avoid duplicates):
{existing_memories}

Conversation:
{conversation}
"""
```

#### Tier 3: RL-Trained Policy (Advanced)

Following AgeMem (Jan 2026), expose memory operations as tools and train the agent's memory policy via reinforcement learning:

```python
MEMORY_TOOLS = [
    save_memory(content, type, importance),
    update_memory(memory_id, new_content),
    forget_memory(memory_id),
    consolidate_memories(memory_ids),
]
```

The agent learns through experience which memories improve downstream task performance. This is the state of the art but requires training infrastructure.

### 7.2 Agent Memory Tools

The agent interacts with memory through dedicated tools (following MemGPT/Letta's approach):

```python
def save_memory(content: str, memory_type: str = "semantic",
                importance: float = 0.7, tags: list[str] = []) -> str:
    """Save a new memory for future reference.

    Use this when you learn something about the user, their project,
    or their preferences that would be useful in future conversations.

    Args:
        content: The fact or experience to remember.
        memory_type: One of "semantic" (facts), "episodic" (experiences),
                     "entity" (about a person/org/project).
        importance: How important is this? 0.0 (trivial) to 1.0 (critical).
        tags: Optional categorical tags for organization.

    Returns:
        Confirmation message with memory ID.
    """

def recall_memory(query: str, memory_type: str | None = None,
                  top_k: int = 5, min_relevance: float = 0.3) -> str:
    """Search your memories for relevant information.

    Use this when you need to recall something about the user, their
    preferences, past interactions, or project context.

    Args:
        query: What are you trying to remember?
        memory_type: Filter by type (optional).
        top_k: Maximum number of memories to return.
        min_relevance: Minimum relevance threshold.

    Returns:
        Matching memories with relevance scores.
    """

def update_memory(memory_id: str, new_content: str) -> str:
    """Update an existing memory with new information.

    Use this when you learn updated information that supersedes
    a previous memory.
    """

def forget_memory(memory_id: str, reason: str = "") -> str:
    """Mark a memory for deletion.

    Use this when a memory is no longer accurate or relevant.
    User-created memories require user confirmation to delete.
    """
```

---

## 8. Multi-Tenancy and Isolation

### 8.1 Namespace Hierarchy

```
{tenant} / {user} / {project} / {thread}
   │          │         │          │
   │          │         │          └─ Conversation-scoped (working memory)
   │          │         └─ Project-scoped (most memories live here)
   │          └─ User-scoped (cross-project preferences)
   └─ Tenant-scoped (shared organizational knowledge)
```

### 8.2 Isolation Rules

| Memory Source | Default Scope | Can Widen? | Can Narrow? |
|---------------|---------------|------------|-------------|
| USER_EXPLICIT | Project | Yes (user can set to "all projects") | Yes (single thread) |
| AGENT_EXTRACTED | Project | No (unless user confirms) | No |
| SYSTEM | Tenant | No | No |

### 8.3 Access Control

```python
class MemoryAccess:
    def can_read(self, user: User, memory: Memory) -> bool:
        """User can read memories in their namespace or parent namespaces."""

    def can_write(self, user: User, memory: Memory) -> bool:
        """User can write to their own namespace. Agents write on behalf of users."""

    def can_delete(self, user: User, memory: Memory) -> bool:
        """Users can delete any memory in their namespace.
        Agent-extracted memories can be auto-pruned.
        User-explicit memories require user action."""
```

---

## 9. API Design

### 9.1 Core Service Interface

```python
from abc import ABC, abstractmethod

class MemoryService(ABC):
    """Abstract interface for the memory system.
    Implementations can use different storage backends."""

    @abstractmethod
    async def save(self, memory: MemoryInput, namespace: str) -> MemoryRecord:
        """Create a new memory."""

    @abstractmethod
    async def search(self, query: str, namespace: str,
                     memory_type: MemoryType | None = None,
                     top_k: int = 10,
                     min_relevance: float = 0.0,
                     filters: dict | None = None) -> list[ScoredMemory]:
        """Search memories by semantic similarity + metadata filters."""

    @abstractmethod
    async def get(self, memory_id: str) -> MemoryRecord | None:
        """Get a specific memory by ID."""

    @abstractmethod
    async def update(self, memory_id: str, updates: MemoryUpdate) -> MemoryRecord:
        """Update a memory's content or metadata."""

    @abstractmethod
    async def delete(self, memory_id: str) -> bool:
        """Delete a memory."""

    @abstractmethod
    async def list(self, namespace: str,
                   memory_type: MemoryType | None = None,
                   source: MemorySource | None = None,
                   offset: int = 0, limit: int = 50) -> PaginatedResult:
        """List memories with filtering and pagination (for UI)."""

    @abstractmethod
    async def consolidate(self, namespace: str) -> ConsolidationResult:
        """Run consolidation pipeline for a namespace."""

    @abstractmethod
    async def extract_from_session(self, session_id: str,
                                    conversation: list[Message]) -> list[MemoryRecord]:
        """Extract memories from a completed session (sleep-time)."""
```

### 9.2 REST API (for UI)

```
POST   /api/v1/memories                    # Create memory
GET    /api/v1/memories                    # List memories (paginated, filtered)
GET    /api/v1/memories/:id                # Get specific memory
PATCH  /api/v1/memories/:id                # Update memory
DELETE /api/v1/memories/:id                # Delete memory
POST   /api/v1/memories/search             # Semantic search
POST   /api/v1/memories/:id/pin            # Pin/unpin memory
POST   /api/v1/memories/:id/confirm        # Confirm agent-extracted memory
POST   /api/v1/memories/consolidate        # Trigger consolidation
GET    /api/v1/memories/export             # Export all memories (portability)
POST   /api/v1/memories/import             # Import memories
DELETE /api/v1/memories                    # Bulk delete (with filters)
```

### 9.3 Agent Tool Interface (for ADK integration)

```python
def create_memory_tools(memory_service: MemoryService,
                         namespace: str) -> list[Tool]:
    """Create ADK-compatible tools for agent memory access.

    Returns tools:
    - save_memory: Store a new memory
    - recall_memory: Search memories by semantic similarity
    - update_memory: Modify an existing memory
    - forget_memory: Mark memory for deletion
    """
```

---

## 10. Integration with adk-skills

### 10.1 Extending the Existing Architecture

The adk-skills library already has:
- `SkillsRegistry` for discovery and caching
- `SkillsStore` (SQLAlchemy) for database persistence
- `SkillsAgent` for ADK integration
- Tool creation patterns (`use_skill`, `run_script`, `read_reference`)

Memory integrates as a parallel subsystem:

```python
from adk_skills_agent import SkillsAgent

agent = SkillsAgent(
    name="assistant",
    model="gemini-2.5-flash",
    instruction="You are helpful.",
    skills_directories=["./skills"],

    # NEW: Memory configuration
    memory_service=MemoryService(
        backend="sqlite",  # or "postgresql", "hybrid"
        embedding_model="text-embedding-3-small",
        namespace="tenant/user/project",
    ),
    memory_config=MemoryConfig(
        enable_proactive_recall=True,
        enable_agent_extraction=True,
        extraction_mode="sleep_time",  # or "hot_path" or "hybrid"
        max_context_memories=10,
        auto_pin_user_explicit=True,
    ),
)
```

### 10.2 Memory as a Skill

Alternatively, memory can be packaged as an adk-skill itself:

```yaml
# skills/memory/SKILL.md
---
name: memory-manager
description: Manage agent memory - save, recall, update, and forget information across sessions
version: "1.0"
compatibility: "Python 3.9+"
metadata:
  category: core
  author: system
---

# Memory Manager

You have access to persistent memory that spans across conversations.

## When to Save Memories
- User states a preference or correction
- You learn important project context
- A problem is resolved (save the solution)
- User explicitly asks you to remember something

## When to Recall Memories
- Before making assumptions about user preferences
- When working on a project you've discussed before
- When the user references a past conversation

## Available Tools
- `save_memory(content, type, importance, tags)`
- `recall_memory(query, type, top_k)`
- `update_memory(memory_id, new_content)`
- `forget_memory(memory_id, reason)`
```

This approach is elegant because it leverages the existing adk-skills infrastructure (discovery, validation, tool creation) while adding memory as a first-class capability.

### 10.3 Memory-Aware Skills

Skills can declare memory dependencies:

```yaml
# skills/code-reviewer/SKILL.md
---
name: code-reviewer
description: Review code with context from past reviews
metadata:
  memory_queries:
    - "coding standards and style preferences"
    - "past code review feedback patterns"
  memory_writes:
    - type: episodic
      trigger: "review completed"
      template: "Reviewed {file}: {summary}"
---
```

---

## 11. Forgetting and Decay

### 11.1 Why Forgetting Matters

Systems that accumulate everything without forgetting suffer from:
- **Memory bloat**: Storage costs grow unbounded
- **Retrieval noise**: Too many memories dilute relevance
- **Stale information**: Outdated memories cause incorrect behavior
- **Performance degradation**: Larger indexes are slower to search

### 11.2 Forgetting Mechanisms

#### Time-Based Decay (Ebbinghaus-Inspired)

```python
def compute_salience(memory: MemoryRecord, now: datetime) -> float:
    """Compute current salience using Ebbinghaus forgetting curve.

    salience = importance * decay_factor^(hours_since_access)

    Memories below the threshold are candidates for pruning.
    """
    hours = (now - memory.last_accessed_at).total_seconds() / 3600
    salience = memory.importance * (memory.decay_rate ** hours)
    return salience

PRUNING_THRESHOLD = 0.1  # Memories below this salience are pruned
```

#### Access-Based Reinforcement

Memories that are frequently retrieved have their decay rate reduced (they decay slower). This naturally preserves useful memories and lets unused ones fade.

```python
def on_memory_accessed(memory: MemoryRecord):
    memory.access_count += 1
    memory.last_accessed_at = now()
    # Reduce decay rate (slower decay) for frequently-accessed memories
    memory.decay_rate = min(0.999, memory.decay_rate + 0.001)
```

#### Protection Rules

Some memories are protected from automatic forgetting:

| Memory Property | Protected? | Reason |
|-----------------|------------|--------|
| source=USER_EXPLICIT | Yes | User intentionally created |
| pinned=True | Yes | User explicitly pinned |
| importance >= 0.9 | Partially | Slower decay, but not immune |
| age < 7 days | Yes | Too new to evaluate |

### 11.3 Consolidation as Forgetting

Consolidation is a form of constructive forgetting — individual episodes are compressed into generalized knowledge:

```
5 episodes of "user asked for Python code"
  → consolidated into 1 semantic: "User prefers Python"
  → episodes marked as "consolidated" and eligible for pruning
```

---

## 12. Research Summary

### Frameworks Analyzed

| Framework | Memory Model | Storage | Key Innovation |
|-----------|-------------|---------|----------------|
| **Letta/MemGPT** | 3-tier (core/recall/archival) | pgvector + PostgreSQL | Self-editing memory via LLM tool calls; sleep-time agents |
| **LangMem** | 3-type (semantic/episodic/procedural) | Pluggable (namespace-based) | Memory managers as pure functions; prompt optimization |
| **Google ADK** | 2-tier (session state/long-term) | Firestore / Vertex AI | Proactive vs. reactive recall; magic state prefixes |
| **CrewAI** | 5-type (short/long/entity/contextual/user) | ChromaDB + SQLite | Event system for memory monitoring |
| **Mem0** | Hybrid (vector + graph) | Vector DB + Graph DB | Extraction → update pipeline with conflict resolution |

### Key Research Papers

| Paper | Year | Contribution |
|-------|------|-------------|
| Generative Agents (Park et al.) | 2023 | Foundational retrieval scoring (recency + importance + relevance) |
| MemGPT | 2023 | Virtual context management; LLM-as-OS metaphor |
| Memory in the Age of AI Agents | Dec 2025 | Comprehensive taxonomy and lifecycle survey |
| A-Mem (Agentic Memory) | 2025 | Zettelkasten-inspired self-organizing memory |
| AgeMem | Jan 2026 | RL-trained memory policies; memory operations as tools |
| MemRL | Jan 2026 | Self-evolving agents via runtime RL on episodic memory |

### Product Approaches Analyzed

| Product | User Memory UI | Agent Memory | Storage |
|---------|---------------|-------------|---------|
| **ChatGPT** | Settings panel; in-chat notifications; natural language commands | Automatic extraction with "Memory updated" indicators | Opaque (proprietary) |
| **Claude** | Project-based; CLAUDE.md files; settings panel | File-based; human-readable Markdown | Markdown files (transparent) |
| **Cursor** | .cursor/rules files; settings; memory bank pattern | Preference extraction from chat | File-based (version-controlled) |

### Key Trends (Early 2026)

1. **Heuristic → Learned memory policies** (AgeMem, MemRL)
2. **Vector-only → Hybrid backends** (vector + graph + relational)
3. **Synchronous → Asynchronous memory management** (sleep-time agents)
4. **Opaque → Transparent memory** (user-inspectable, user-controllable)
5. **Single-agent → Multi-agent memory coordination**
6. **Forgetting as a first-class operation** (not a bug, a feature)
7. **Memory as the bottleneck** — model capability is less limiting than memory quality

---

## Appendix: Implementation Roadmap

### Phase 1: MVP
- [ ] `MemoryRecord` model (SQLAlchemy, extending existing db/ patterns)
- [ ] `MemoryService` with SQLite + ChromaDB backend
- [ ] `save_memory` and `recall_memory` agent tools
- [ ] Basic proactive recall (preloader)
- [ ] REST API for CRUD operations
- [ ] Simple memory dashboard UI (list, add, edit, delete)

### Phase 2: Intelligence
- [ ] LLM-based extraction (sleep-time pipeline)
- [ ] Conflict resolution and deduplication
- [ ] Importance scoring
- [ ] Entity extraction and storage
- [ ] In-chat memory notifications
- [ ] Natural language memory commands

### Phase 3: Scale
- [ ] PostgreSQL + pgvector backend
- [ ] Ebbinghaus decay and pruning
- [ ] Consolidation pipeline
- [ ] Graph-based entity relationships (Neo4j)
- [ ] Multi-tenant namespace isolation
- [ ] Memory export/import (portability)

### Phase 4: Advanced
- [ ] RL-trained memory policies (AgeMem-style)
- [ ] Memory-aware skills (skills declare memory dependencies)
- [ ] Cross-agent memory sharing (multi-agent coordination)
- [ ] Memory analytics dashboard
- [ ] A/B testing framework for retrieval strategies
