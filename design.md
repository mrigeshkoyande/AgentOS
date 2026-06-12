# System Design: Antygravity GraphRAG Memory Engine

## 1. Architecture Overview
This document outlines the production-grade architecture for Antygravity's Code Knowledge Graph and GraphRAG (Retrieval-Augmented Generation) memory system. The system is designed to ingest multi-language repositories, parse them into structural graphs, and provide sub-second semantic retrieval.

---

## 2. Repository Ingestion & Parsing Layer

The ingestion layer is responsible for converting raw source code into a structured, machine-readable format.

- **AST Parsers**: We utilize **Tree-sitter** for robust, error-tolerant Abstract Syntax Tree parsing.
- **Supported Languages**: TypeScript, JavaScript, Python, Java, Go, Rust, C++, C#.
- **Extraction Targets**:
  - **Structural**: Files, Folders, Classes, Functions, Interfaces, Types.
  - **Relational**: Imports, Exports, Function Calls, Class Extensions.
  - **Contextual**: API Endpoints (e.g., `@app.get()`), Database Models (e.g., SQLAlchemy/Prisma schemas), Environment Variables used.

---

## 3. Knowledge Graph Layer (Neo4j)

The structural blueprint of the repository is stored in **Neo4j**. This allows the agent to execute highly complex relationship queries (e.g., "Find all functions that call `database.connect()` and are exposed via an API route").

### Node Labels
- `Repository`, `Folder`, `File`
- `Class`, `Function`, `Interface`, `Type`
- `ApiRoute`, `DatabaseTable`, `Dependency`

### Relationship Types
- `[:CONTAINS]` -> (Folder contains File, File contains Class)
- `[:IMPORTS]` -> (File imports Dependency/File)
- `[:CALLS]` -> (Function calls Function)
- `[:IMPLEMENTS]` / `[:EXTENDS]` -> (Class implements Interface)
- `[:EXPOSES]` -> (Function exposes ApiRoute)

---

## 4. Vector Memory Layer (Qdrant)

While Neo4j handles structure, **Qdrant** handles semantic meaning. 
- **Embeddings**: We generate vector embeddings for the actual source code of Classes and Functions, as well as docstrings, README files, and API specifications.
- **Chunking Strategy**: We do not chunk blindly by character count. We use **Semantic Chunking** based on AST boundaries (e.g., chunking exactly at the start and end of a function block) to preserve code context.

---

## 5. Hierarchical Summarization

To prevent overwhelming the LLM with massive files, the system employs Hierarchical Summaries using a Map-Reduce approach:
1. **Function Level**: "This function validates a user's email format."
2. **File Level**: "This file contains utilities for user input validation."
3. **Folder Level**: "This folder handles the authentication and security middleware."
4. **Repository Level**: "A Fastify-based backend for an e-commerce platform."

When an agent needs to understand a module, it reads the Folder-level summary first. It only drills down into the File or Function level if the task requires editing that specific logic.

---

## 6. The 6-Step Retrieval Engine

To achieve the < 15,000 token target per query, the retrieval engine executes the following pipeline:
1. **Search Graph**: Identify the entry point node (e.g., `UserController`).
2. **Traverse Graph**: Walk the Neo4j graph 2 hops out to find all dependencies and called functions.
3. **Retrieve Vectors**: Perform a similarity search in Qdrant to find semantically related but structurally disconnected code (e.g., finding the matching frontend React component).
4. **Fetch Summaries**: Grab the hierarchical summaries for the surrounding context.
5. **Relevance Ranking**: Score the retrieved nodes using Cross-Encoder models.
6. **Token Budgeting**: Slice the ranked results to fit strictly under 10,000 - 15,000 tokens, discarding low-priority context.

---

## 7. API Server & Dashboard

### Backend (Node.js + Fastify)
High-performance REST APIs to interact with the memory engine:
- `POST /ingest` - Trigger a repository scan.
- `GET /search` - Combined Graph + Vector search.
- `POST /graph/query` - Execute raw Cypher queries for deep analysis.
- `POST /memory/store` - Agent logs a design decision or architectural rule.

### Frontend Dashboard (React + Vite)
A visual control center for human developers to monitor the agent:
- **Graph Visualizer**: A 3D force-directed graph rendering the Neo4j data.
- **Memory Explorer**: UI to view stored architectural rules and past agent decisions.
- **Retrieval Traces**: A debugging view showing exactly which files the agent pulled for its context window, helping developers understand *why* the agent made a specific coding decision.

---

## 8. Performance Service-Level Agreements (SLAs)
- **Repository Size Capacity**: 1,000,000+ Lines of Code.
- **Graph Traversal Latency**: < 500ms for 3-hop queries.
- **Retrieval Pipeline Latency**: < 2 seconds.
- **Context Size**: < 10,000 tokens average per prompt.
