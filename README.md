# AI Builders Challenge with IBM Bob — Project Scaffold

## 🚀 Overview
An intelligent agentic solution built with **IBM Bob** for the **AI Builders Challenge with IBM Bob (2026)**.

## 🎯 Problem Statement
Brief description of the challenge being addressed under the chosen theme:
- **Track**: [Space Exploration AI / Future of Work AI]
- **Core Challenge**: High cognitive load, fragmented data pipelines, and mission-critical decision latency.

## 💡 Solution & Technical Architecture
- **Agentic SDLC & Orchestration**: Built and orchestrated using **IBM Bob**.
- **Model Layer**: Powered by IBM Granite SLMs / watsonx.ai foundation models.
- **Document & Data Ingestion**: Leveraging IBM Docling and structured vector pipelines.
- **Workflow & Automation**: Modular agent design with verification loops.

## 🛠️ Project Structure
```
ibm-bob-challenge/
├── .bob/                  # IBM Bob mode rules (Agent, Plan, Ask)
├── docs/                  # Architecture & design documentation
├── src/
│   ├── agents/            # Specialized agent personas and execution flows
│   ├── api/               # API endpoints & interface contracts
│   ├── core/              # Core business logic and engine algorithms
│   ├── integrations/      # IBM watsonx / Docling / Granite connectors
│   └── main.py            # Main application entry point
├── tests/                 # Unit & integration test suites
├── AGENTS.md              # IBM Bob project instructions & conventions
├── COMPETITION.md         # Competition brief, deadlines, and requirements
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
```

## ⚙️ Getting Started

### 1. Prerequisites
- Python 3.10+
- IBM Bob IDE / Bob Shell access
- (Optional) IBM watsonx API Key

### 2. Installation
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Running the Prototype
```bash
python src/main.py
```

### 4. Running Tests
```bash
pytest tests/
```

## 👥 Real-World Impact
- Measurable efficiency gains and rapid automated reasoning.
- Enterprise-grade governance, auditability, and safety.

## 🏆 Submission Deliverables
- **Demo Video**: [Link to 3-minute demo video]
- **Project URL**: [BeMyApp Project Link]
