# 🚀 Career Reinvention Agent

A multi-agent AI system built with Google ADK that takes your resume 
and target role, then returns a complete career transition plan.

## What It Does

Five AI agents fire in sequence:

| Agent | Job |
|---|---|
| 🔍 Job Research | Searches live job postings for your target role |
| 📊 Gap Analysis | Compares your background to market requirements |
| 📚 Learning Path | Finds the best courses and certs for your gaps |
| 🗓 Roadmap | Builds a personalized 90-day action plan |
| ✍️ Content Writer | Rewrites your LinkedIn headline + summary |

## Live Demo

👉 https://career-reinvention-agent-641611013459.us-central1.run.app

## Tech Stack

- **Google ADK** — Multi-agent orchestration
- **Gemini 2.5 Flash** — LLM powering all agents
- **SerpAPI** — Live Google search for job research
- **FastAPI** — Backend API with SSE streaming
- **Google Cloud Run** — Serverless deployment
- **Python 3.11**

## Run Locally

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/career-reinvention-agent.git
cd career-reinvention-agent
```

**2. Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**3. Set up environment variables**
```bash
cp .env.example .env
# Fill in your API keys
```

**4. Run**
```bash
python3 main.py
```

Open http://localhost:8080

## Environment Variables

| Variable | Where to get it |
|---|---|
| `GOOGLE_API_KEY` | [Google AI Studio](https://aistudio.google.com/apikey) |
| `SERPAPI_KEY` | [SerpAPI](https://serpapi.com) |
| `GOOGLE_CLOUD_PROJECT` | Your GCP project ID |
| `GOOGLE_CLOUD_LOCATION` | e.g. `us-central1` |

## Architecture

User Input (Resume + Target Role)
│
▼
┌─────────────────────┐
│  FastAPI + SSE      │  ← streams progress to UI
└─────────────────────┘
│
▼
┌─────────────────────────────────────────────┐
│           Agent Pipeline                    │
│  1. JobResearchAgent  → live web search     │
│  2. GapAnalysisAgent  → resume vs market    │
│  3. LearningPathAgent → courses + certs     │
│  4. RoadmapAgent      → 90-day plan         │
│  5. ContentWriterAgent→ LinkedIn makeover   │
└─────────────────────────────────────────────┘
│
▼
Tabbed Report + PDF Download

## Deploy to Google Cloud Run

```bash
docker build --platform linux/amd64 -t gcr.io/YOUR_PROJECT/career-agent .
docker push gcr.io/YOUR_PROJECT/career-agent
gcloud run deploy career-reinvention-agent \
  --image gcr.io/YOUR_PROJECT/career-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

## Author

Built by [Rajat Dixit](https://www.linkedin.com/in/YOUR_LINKEDIN) 
as part of a career transition from Frontend Engineer → AI Solutions Architect.

---
⭐ Star this repo if it helped you!