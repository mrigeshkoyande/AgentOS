# Antygravity Agent Specifications & Memory Architecture

## 1. Executive Summary
Antygravity is a next-generation AI coding agent specifically designed to navigate, understand, and modify ultra-large codebases (1M+ Lines of Code). Traditional LLM coding agents hit immediate token limits and struggle to maintain global architectural context. Antygravity overcomes this by utilizing a **Graph-Augmented Retrieval-Augmented Generation (GraphRAG)** system, allowing it to surgically pull only the required code context without ever loading the entire repository into its prompt.

## 2. Core Capabilities
- **Massive Scale Navigation**: Seamlessly understands repositories with millions of lines of code.
- **Semantic Code Understanding**: Goes beyond basic keyword search by understanding the Abstract Syntax Tree (AST), knowing exactly which function calls another, which classes implement which interfaces, and where environment variables are utilized.
- **Token Optimization**: Compresses thousands of files into highly dense semantic summaries, ensuring the agent's context window stays below 15,000 tokens while retaining 100% architectural awareness.
- **Self-Healing Memory**: Learns from previous coding sessions. If an agent fixes a bug in one component, it remembers the architectural constraints for future tasks.

---

## 3. The 4-Tier Memory System

Antygravity simulates a senior human engineer's brain by dividing its memory into four distinct layers:

### 3.1. Session Memory (Short-Term)
- **Purpose**: Holds the immediate conversational context and the active coding task.
- **Contents**: The current user prompt, the active files open in the IDE, recent terminal outputs, and the step-by-step execution plan currently underway.
- **Storage**: In-memory (Redis/Fastify State) and cleared after the task is completed or the session is reset.

### 3.2. Project Memory (Mid-Term)
- **Purpose**: Repository-specific knowledge.
- **Contents**: 
  - Directory structures and module boundaries.
  - Active feature flags and environment variables.
  - Test coverage gaps and known technical debt.
- **Storage**: Vectorized in Qdrant and structurally mapped in Neo4j.

### 3.3. Architectural Memory (Long-Term)
- **Purpose**: High-level design patterns and constraints established by the development team.
- **Contents**: 
  - "We use Redux for state management, do not use React Context."
  - "All database queries must go through the Repository layer."
  - "Authentication is handled via JWT; do not build custom session cookies."
- **Storage**: Summarized globally and retrieved via GraphRAG when the agent drafts an implementation plan.

### 3.4. Execution Memory (Experience)
- **Purpose**: A historical log of previous edits, known bugs, and design decisions.
- **Contents**: 
  - "In PR #402, we tried using UUIDs for user IDs but it caused performance issues in the `sessions` table. Reverted to auto-incrementing integers."
- **Storage**: Graph nodes linking specific code files to past GitHub Issues/PRs or internal AgentOS sessions.

---

## 4. Agent Workflow: How Antygravity Answers a Query

When a user asks: *"How does authentication work in this repo?"*

1. **Intent Parsing**: Antygravity identifies that this is a system-wide architectural query.
2. **Graph Traversal**: It queries Neo4j for nodes tagged with `Authentication`, `JWT`, `Login`, or `Security`.
3. **Neighborhood Expansion**: It finds the exact functions (e.g., `verify_token()`) and classes (e.g., `AuthMiddleware`) connected to those nodes.
4. **Vector Similarity**: It pulls the dense vector embeddings of those specific functions from Qdrant to understand the actual code implementation.
5. **Context Assembly**: Instead of pulling the entire 2,000-line `auth.ts` file, it pulls the 50-line `verify_token()` function and the 20-line `AuthMiddleware` class.
6. **Synthesis**: It reads the compressed context and generates a precise, token-efficient answer to the user.
