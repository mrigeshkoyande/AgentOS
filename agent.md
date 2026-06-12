# Antygravity Agent Specification

## Overview
Antygravity is an AI coding agent equipped with a production-grade Code Knowledge Graph and GraphRAG memory system. 

## Capabilities
The agent must understand and navigate repositories containing millions of lines of code while minimizing token usage.

## Memory Systems
- **Long-term memory**: Persistent storage of learned patterns and project context.
- **Session memory**: Temporary storage for the current conversation and context window.
- **Project memory**: Repository-specific knowledge, architecture, and constraints.
- **Architectural memory**: System design patterns and high-level decisions.

## Knowledge Tracking
The agent tracks:
- Previous edits
- Design decisions
- Known bugs
- User preferences
- Active tasks
