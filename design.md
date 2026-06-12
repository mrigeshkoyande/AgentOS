# System Design: Antygravity GraphRAG Memory System

## 1. Architecture Overview
A production-grade Code Knowledge Graph and GraphRAG memory system.

### 1.1 Repository Ingestion Layer
- **Function**: Scan local folders and Git repositories.
- **Languages**: TypeScript, JavaScript, Python, Java, Go, Rust, C++, C#
- **Parsing**: Tree-sitter (AST parsers)
- **Extraction Targets**: Files, Classes, Functions, Interfaces, Imports, Exports, API endpoints, Database models, Environment variables, Dependencies, Test files.

### 1.2 Knowledge Graph Layer (Neo4j)
**Nodes**: Repository, Folder, File, Class, Function, API Route, Database Table, Service, Component.
**Relationships**: IMPORTS, CALLS, EXTENDS, IMPLEMENTS, DEPENDS_ON, CONTAINS, USES, CONNECTS_TO, REFERENCES.

### 1.3 Vector Memory Layer (Qdrant)
Embeddings generated for:
- Files, Classes, Functions
- Documentation, README files, API specifications

### 1.4 Hierarchical Summaries
Summaries generated and stored at:
- Repository, Module, Folder, File, Function levels.

## 2. Retrieval Engine
**Process**:
1. Search graph
2. Traverse connected nodes
3. Retrieve related embeddings
4. Retrieve summaries
5. Rank relevance
6. Return only necessary files

**Constraints**: Target context < 15,000 tokens. Never load entire repository.

## 3. Context Compression
- Semantic chunking
- Hierarchical summaries
- Graph neighborhood retrieval
- Context deduplication
- Token budgeting

## 4. API Design (Fastify)
- `POST /ingest`: Ingest repository
- `GET /search`: Search graph and vectors
- `POST /graph/query`: Execute Cypher queries
- `POST /memory/store`: Store agent memory
- `GET /memory/retrieve`: Retrieve context
- `POST /summarize`: Generate hierarchical summaries
- `GET /repository/status`: Get ingestion status

## 5. Frontend Dashboard (React)
Visualizes:
- Repository graph & Dependency graph
- Search results
- Memory explorer
- Token consumption
- Retrieval traces

## 6. Performance Targets
- Repository size: 1M+ LOC
- Search latency: <2 seconds
- Retrieval: <10,000 tokens average
- Graph traversal: <500ms

## 7. Tech Stack
- Backend: Node.js, Fastify, TypeScript
- Graph DB: Neo4j
- Vector DB: Qdrant
- Parsing: Tree-sitter
- Frontend: React
- Infrastructure: Docker, Kubernetes, CI/CD Pipeline
