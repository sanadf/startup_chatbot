# ArabiAgent — AI Investment Sourcing Agent

ArabiAgent is an AI-powered startup investment research
application built with LangGraph, CrewAI, Linkup, FastAPI,
Streamlit, and a locally hosted Ollama language model.

## Features

- Enter and enhance an investment thesis using CrewAI.
- Discover startups through the Linkup research API.
- Research companies concurrently using LangGraph.
- Collect configurable investment data attributes.
- Assess reported funding-stage matches.
- Generate AI-assisted due diligence reviews.
- Monitor research progress using SSE streaming.
- Compare startups in an interactive Streamlit dashboard.
- Export investment reports as PDF or JSON.

## Technology Stack

- Python 3.12
- FastAPI — Backend API
- Streamlit — Frontend
- LangGraph — Research workflow orchestration
- CrewAI — AI analysis and thesis enhancement
- Ollama — Local language model
- Linkup — Startup discovery and research
- Pydantic — Structured validation
- ReportLab — PDF reports
- pytest — Automated testing

## Installation

1. Clone or download the repository.
2. Create a Python virtual environment.
3. Install dependencies from requirements.txt.
4. Copy .env.example to .env.
5. Configure your Linkup API key.
6. Install Ollama and pull llama3.2:3b.

Example setup commands:

    python3.12 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    cp .env.example .env
    ollama pull llama3.2:3b

Edit .env and insert your actual Linkup API key.

## Running the Application

Start the backend:

    uvicorn backend.main:app --reload

In another terminal, start the frontend:

    streamlit run frontend/app.py

Open http://localhost:8501 in your browser.

The Ollama service must be available for AI features
that use the local model.

## Application Workflow

1. User enters an investment thesis.
2. CrewAI optionally enhances the thesis.
3. Linkup discovers potential startup candidates.
4. LangGraph dispatches parallel company research tasks.
5. Linkup gathers structured information and sources.
6. Funding-stage qualification checks reported matches.
7. CrewAI optionally produces due diligence reviews.
8. Streamlit displays findings and exports reports.

## Running Tests

    python -m pytest tests/ -v

The automated suite includes tests for research
concurrency, failure isolation, funding qualification,
CrewAI integration, and PDF generation.

## Research Reliability

ArabiAgent uses public-source research and AI-generated
analysis. Information may be missing, outdated, or
incorrect.

Funding-stage matches are preliminary classifications,
not proof of investment eligibility. Users should
independently verify important investment claims.

Live Linkup searches can consume API credits.
Automated tests use mocked research where appropriate.

## Current Scope

This version generates downloadable PDF and JSON reports.

Email report delivery is intentionally excluded from
this version. It does not fulfill any assignment
requirement that explicitly mandates SendGrid delivery.

## Security

- Never commit .env or API keys.
- Do not put credentials in source files.
- Use .env.example as the configuration template.
- Review staged files before pushing to GitHub.
