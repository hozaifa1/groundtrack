# AGENTS.md — IBM Bob Agent Directives & Architecture

## Project Overview
This repository is developed for the **AI Builders Challenge with IBM Bob** (August Challenge & Wildcard).

- **Competition Platform**: BeMyApp & IBM SkillsBuild
- **Primary Tool**: IBM Bob (Bob Shell, Agent Mode, Plan Mode, Literate Coding)
- **Supported Integrations**: IBM watsonx.ai, Granite SLMs/LLMs, Docling, LangFlow

## Core Directives for IBM Bob Agents
1. **Context-Aware Development**: When designing and implementing modules, maintain modularity across `src/core`, `src/agents`, and `src/integrations`.
2. **Literate & Explainable Coding**: Document decision rationale, algorithmic steps, and real-world impact clearly in code docstrings and module documentation.
3. **Enterprise Reliability**: Ensure error handling, robust validation, and full type safety across Python and API layers.
4. **Security & Guardrails**: Never hardcode credentials or secrets. Use environment variables via `.env.example`.
5. **Traceability**: Keep changes auditable and aligned with competition criteria.
