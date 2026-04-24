import os
import json
import io
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part
from agents.job_research import job_research_agent
from agents.gap_analysis import gap_analysis_agent
from agents.learning_path import learning_path_agent
from agents.roadmap import roadmap_agent
from agents.content_writer import content_writer_agent

load_dotenv()

app = FastAPI(title="Career Reinvention Agent", version="1.0.0")
session_service = InMemorySessionService()
APP_NAME = "career-reinvention-agent"


class AnalyzeRequest(BaseModel):
    resume: str
    target_role: str


async def run_agent(agent, user_id: str, message: str) -> str:
    session = await session_service.create_session(app_name=APP_NAME, user_id=user_id)
    runner = Runner(agent=agent, app_name=APP_NAME, session_service=session_service)
    user_message = Content(role="user", parts=[Part(text=message)])
    result = ""
    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_message):
        if event.is_final_response():
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        result += part.text
            break
    return result


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse-resume")
async def parse_resume(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename.lower()
    try:
        if filename.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(content))
            text = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
            return {"text": text}
        elif filename.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            return {"text": text}
        else:
            raise HTTPException(status_code=400, detail="Only .docx and .pdf files are supported")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def agent_pipeline(resume: str, target_role: str):
    agents_meta = [
        {"id": "job_research",   "name": "Job Research Agent",   "desc": f"Scanning live job postings for {target_role}"},
        {"id": "gap_analysis",   "name": "Gap Analysis Agent",   "desc": "Comparing your background to market requirements"},
        {"id": "learning_path",  "name": "Learning Path Agent",  "desc": "Finding the best courses and certifications"},
        {"id": "roadmap",        "name": "Roadmap Agent",        "desc": "Building your personalized 90-day action plan"},
        {"id": "content_writer", "name": "Content Writer Agent", "desc": "Crafting your LinkedIn makeover"},
    ]
    results = {}
    try:
        yield {"event": "agent_start", "data": json.dumps({"step": 1, **agents_meta[0]})}
        results["job_research"] = await run_agent(job_research_agent, "user", f"Research job requirements for: {target_role}")
        yield {"event": "agent_complete", "data": json.dumps({"step": 1, "id": "job_research"})}

        yield {"event": "agent_start", "data": json.dumps({"step": 2, **agents_meta[1]})}
        results["gap_analysis"] = await run_agent(gap_analysis_agent, "user", f"Analyze skill gaps.\n\nRESUME:\n{resume}\n\nJOB REQUIREMENTS:\n{results['job_research']}")
        yield {"event": "agent_complete", "data": json.dumps({"step": 2, "id": "gap_analysis"})}

        yield {"event": "agent_start", "data": json.dumps({"step": 3, **agents_meta[2]})}
        results["learning_path"] = await run_agent(learning_path_agent, "user", f"Find learning resources.\n\nTARGET: {target_role}\n\nGAPS:\n{results['gap_analysis']}")
        yield {"event": "agent_complete", "data": json.dumps({"step": 3, "id": "learning_path"})}

        yield {"event": "agent_start", "data": json.dumps({"step": 4, **agents_meta[3]})}
        results["roadmap"] = await run_agent(roadmap_agent, "user", f"Create 90-day roadmap.\n\nGAPS:\n{results['gap_analysis']}\n\nRESOURCES:\n{results['learning_path']}")
        yield {"event": "agent_complete", "data": json.dumps({"step": 4, "id": "roadmap"})}

        yield {"event": "agent_start", "data": json.dumps({"step": 5, **agents_meta[4]})}
        results["content_writer"] = await run_agent(content_writer_agent, "user", f"Rewrite LinkedIn.\n\nRESUME:\n{resume}\n\nTARGET: {target_role}\n\nGAPS:\n{results['gap_analysis']}")
        yield {"event": "agent_complete", "data": json.dumps({"step": 5, "id": "content_writer"})}

        yield {"event": "complete", "data": json.dumps({
            "target_role": target_role,
            "sections": {
                "job_research":  results["job_research"],
                "gap_analysis":  results["gap_analysis"],
                "learning_path": results["learning_path"],
                "roadmap":       results["roadmap"],
                "content_writer":results["content_writer"],
            }
        })}
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"message": str(e)})}


@app.post("/analyze-stream")
async def analyze_stream(request: AnalyzeRequest):
    if not request.resume.strip():
        raise HTTPException(400, "Resume cannot be empty")
    if not request.target_role.strip():
        raise HTTPException(400, "Target role cannot be empty")
    return EventSourceResponse(agent_pipeline(request.resume, request.target_role))


@app.get("/", response_class=HTMLResponse)
def root():
    return HTML


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Career Reinvention Agent</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
:root {
  --bg: #060a12;
  --surface: #0c1424;
  --surface2: #111d30;
  --border: #1c2e47;
  --cyan: #00d4ff;
  --purple: #7c3aed;
  --green: #00e87a;
  --amber: #f59e0b;
  --red: #f43f5e;
  --text: #dce8f5;
  --muted: #4e6a8a;
  --font-head: 'Syne', sans-serif;
  --font-body: 'DM Sans', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  font-family: var(--font-body);
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  overflow-x: hidden;
}
body::before {
  content: '';
  position: fixed;
  inset: 0;
  background: 
    radial-gradient(ellipse 60% 40% at 20% 10%, rgba(0,212,255,0.06) 0%, transparent 60%),
    radial-gradient(ellipse 50% 50% at 80% 80%, rgba(124,58,237,0.07) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}

/* ── Layout ── */
.page { position: relative; z-index: 1; max-width: 900px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }

/* ── Header ── */
.header { text-align: center; margin-bottom: 3.5rem; }
.badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-family: var(--font-mono); font-size: 0.7rem; letter-spacing: 0.12em;
  color: var(--cyan); background: rgba(0,212,255,0.08);
  border: 1px solid rgba(0,212,255,0.2); border-radius: 20px;
  padding: 0.3rem 0.9rem; margin-bottom: 1.2rem;
}
.badge::before { content: '●'; animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
h1 {
  font-family: var(--font-head); font-size: clamp(2rem, 5vw, 3.2rem);
  font-weight: 800; line-height: 1.1; margin-bottom: 0.8rem;
  background: linear-gradient(135deg, #fff 0%, var(--cyan) 50%, var(--purple) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.subtitle { color: var(--muted); font-size: 1rem; font-weight: 300; max-width: 500px; margin: 0 auto; }

/* ── Card ── */
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 16px; padding: 1.8rem;
  box-shadow: 0 4px 40px rgba(0,0,0,0.4);
}

/* ── Input Toggle ── */
.input-toggle {
  display: flex; gap: 0.5rem; margin-bottom: 1.4rem;
  background: var(--bg); border-radius: 10px; padding: 4px;
  border: 1px solid var(--border); width: fit-content;
}
.toggle-btn {
  font-family: var(--font-body); font-size: 0.82rem; font-weight: 500;
  padding: 0.45rem 1rem; border-radius: 8px; border: none; cursor: pointer;
  background: transparent; color: var(--muted); transition: all 0.2s;
}
.toggle-btn.active { background: var(--surface2); color: var(--text); }

/* ── Dropzone ── */
.dropzone {
  border: 2px dashed var(--border); border-radius: 12px;
  padding: 2.5rem 1.5rem; text-align: center; cursor: pointer;
  transition: all 0.2s; margin-bottom: 1rem; position: relative;
}
.dropzone:hover, .dropzone.drag-over {
  border-color: var(--cyan); background: rgba(0,212,255,0.04);
}
.dropzone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; }
.dropzone-icon { font-size: 2rem; margin-bottom: 0.6rem; }
.dropzone-text { color: var(--muted); font-size: 0.88rem; }
.dropzone-text span { color: var(--cyan); }
.file-selected {
  display: flex; align-items: center; gap: 0.6rem;
  background: rgba(0,232,122,0.08); border: 1px solid rgba(0,232,122,0.2);
  border-radius: 8px; padding: 0.6rem 1rem; font-size: 0.85rem; margin-bottom: 1rem;
  color: var(--green);
}

/* ── Textarea & Input ── */
textarea, input[type=text] {
  width: 100%; background: var(--bg); border: 1px solid var(--border);
  border-radius: 10px; color: var(--text); font-family: var(--font-body);
  font-size: 0.88rem; padding: 0.85rem 1rem; transition: border-color 0.2s; resize: vertical;
  margin-bottom: 1rem;
}
textarea:focus, input[type=text]:focus { outline: none; border-color: var(--cyan); }
textarea { min-height: 160px; }
label { display: block; font-size: 0.78rem; font-weight: 500; color: var(--muted); margin-bottom: 0.4rem; letter-spacing: 0.05em; text-transform: uppercase; }

/* ── Button ── */
.btn-primary {
  width: 100%; padding: 0.95rem; border: none; border-radius: 10px; cursor: pointer;
  font-family: var(--font-head); font-size: 1rem; font-weight: 700;
  background: linear-gradient(135deg, var(--cyan), var(--purple));
  color: #fff; transition: opacity 0.2s, transform 0.1s; letter-spacing: 0.03em;
}
.btn-primary:hover { opacity: 0.9; transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

/* ── Pipeline ── */
#pipeline { display: none; margin-top: 2rem; }
.pipeline-header { font-family: var(--font-mono); font-size: 0.72rem; color: var(--muted); letter-spacing: 0.1em; margin-bottom: 1.5rem; text-align: center; }
.pipeline-track {
  display: flex; align-items: flex-start; justify-content: center;
  gap: 0; position: relative;
}
.pipeline-step {
  display: flex; flex-direction: column; align-items: center; gap: 0.7rem;
  flex: 1; max-width: 160px;
}
.pipeline-connector {
  flex: 0 0 auto; width: 48px; height: 2px; margin-top: 22px;
  background: var(--border); position: relative; overflow: hidden;
}
.pipeline-connector .fill {
  position: absolute; left: 0; top: 0; height: 100%; width: 0%;
  background: linear-gradient(90deg, var(--cyan), var(--purple));
  transition: width 0.6s ease;
}
.pipeline-connector.done .fill { width: 100%; }

.node {
  width: 44px; height: 44px; border-radius: 50%;
  background: var(--surface2); border: 2px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; position: relative; transition: all 0.3s;
}
.node.active {
  border-color: var(--cyan); box-shadow: 0 0 0 6px rgba(0,212,255,0.1);
  animation: nodeGlow 1.5s infinite;
}
.node.done { border-color: var(--green); background: rgba(0,232,122,0.1); }
.node.done::after {
  content: '✓'; position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; color: var(--green); font-weight: 700;
}
.node.done .node-icon { display: none; }
@keyframes nodeGlow {
  0%,100% { box-shadow: 0 0 0 6px rgba(0,212,255,0.1); }
  50% { box-shadow: 0 0 0 10px rgba(0,212,255,0.2), 0 0 20px rgba(0,212,255,0.3); }
}
.step-name {
  font-family: var(--font-mono); font-size: 0.65rem; color: var(--muted);
  text-align: center; line-height: 1.4; max-width: 100px;
}
.step-name.active { color: var(--cyan); }
.step-name.done { color: var(--green); }
.step-desc {
  font-size: 0.78rem; color: var(--muted); text-align: center; margin-top: 1.2rem;
  min-height: 2rem; transition: all 0.3s; font-style: italic;
}

/* ── Readiness Meter ── */
.readiness-card {
  display: flex; align-items: center; gap: 1.5rem;
  background: var(--surface2); border-radius: 12px; padding: 1.2rem 1.5rem;
  border: 1px solid var(--border); margin-bottom: 1.5rem;
}
.readiness-label { font-family: var(--font-mono); font-size: 0.7rem; color: var(--muted); margin-bottom: 0.4rem; letter-spacing: 0.08em; }
.readiness-value { font-family: var(--font-head); font-size: 1.4rem; font-weight: 700; color: var(--cyan); }
.readiness-bar-wrap { flex: 1; background: var(--border); border-radius: 100px; height: 8px; overflow: hidden; }
.readiness-bar { height: 100%; border-radius: 100px; background: linear-gradient(90deg, var(--cyan), var(--purple)); width: 0; transition: width 1.2s cubic-bezier(0.16,1,0.3,1); }

/* ── Tabs ── */
.tabs { margin-top: 2rem; }
.tab-list {
  display: flex; gap: 0.25rem; overflow-x: auto; padding-bottom: 0.5rem;
  scrollbar-width: none; border-bottom: 1px solid var(--border); margin-bottom: 1.5rem;
}
.tab-list::-webkit-scrollbar { display: none; }
.tab-btn {
  font-family: var(--font-body); font-size: 0.82rem; font-weight: 500;
  padding: 0.55rem 1rem; border: none; background: transparent;
  color: var(--muted); cursor: pointer; white-space: nowrap;
  border-bottom: 2px solid transparent; margin-bottom: -1px; transition: all 0.2s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--cyan); border-bottom-color: var(--cyan); }
.tab-panel { display: none; animation: fadeIn 0.3s ease; }
.tab-panel.active { display: block; }
@keyframes fadeIn { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }

/* ── Content Renderer ── */
.md-content { line-height: 1.75; font-size: 0.9rem; }
.md-content h2 {
  font-family: var(--font-head); font-size: 1.15rem; font-weight: 700;
  color: var(--text); margin: 1.8rem 0 0.7rem; padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}
.md-content h2:first-child { margin-top: 0; }
.md-content h3 { font-family: var(--font-head); font-size: 1rem; font-weight: 600; color: var(--cyan); margin: 1.2rem 0 0.5rem; }
.md-content p { color: var(--muted); margin-bottom: 0.6rem; }
.md-content ul { list-style: none; padding: 0; margin-bottom: 0.8rem; }
.md-content li { color: var(--muted); padding: 0.2rem 0 0.2rem 1.2rem; position: relative; }
.md-content li::before { content: '–'; position: absolute; left: 0; color: var(--cyan); }
.md-content strong { color: var(--text); font-weight: 600; }
.md-content a { color: var(--cyan); text-decoration: none; }
.md-content a:hover { text-decoration: underline; }
.md-content .tag-green { display: inline-block; color: var(--green); font-size: 0.9em; }
.md-content .tag-red { display: inline-block; color: var(--red); font-size: 0.9em; }
.md-content .tag-amber { display: inline-block; color: var(--amber); font-size: 0.9em; }
.md-content blockquote {
  border-left: 3px solid var(--cyan); padding: 0.6rem 1rem;
  background: rgba(0,212,255,0.04); border-radius: 0 8px 8px 0; margin: 0.8rem 0;
  font-style: italic; color: var(--muted);
}
.md-content pre {
  background: var(--bg); border: 1px solid var(--border);
  border-radius: 8px; padding: 1rem; overflow-x: auto;
  font-family: var(--font-mono); font-size: 0.8rem; color: var(--cyan); margin: 0.8rem 0;
}
.week-block {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 0.6rem;
}
.week-block .week-label {
  font-family: var(--font-mono); font-size: 0.68rem; color: var(--purple);
  letter-spacing: 0.1em; margin-bottom: 0.3rem;
}
.week-block .week-title { font-weight: 600; color: var(--text); font-size: 0.9rem; margin-bottom: 0.3rem; }
.week-block .week-detail { color: var(--muted); font-size: 0.82rem; }

/* ── Chart ── */
.chart-wrap { max-width: 340px; margin: 1.5rem auto; }

/* ── Download ── */
.download-bar {
  margin-top: 2rem; padding: 1.5rem;
  background: linear-gradient(135deg, rgba(0,212,255,0.06), rgba(124,58,237,0.06));
  border: 1px solid rgba(0,212,255,0.15); border-radius: 12px;
  display: flex; align-items: center; justify-content: space-between; gap: 1rem;
  flex-wrap: wrap;
}
.download-info { font-size: 0.88rem; }
.download-info strong { font-family: var(--font-head); font-size: 1rem; display: block; margin-bottom: 0.2rem; }
.download-info span { color: var(--muted); font-size: 0.82rem; }
.btn-download {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.7rem 1.4rem; border: 1px solid var(--cyan); border-radius: 8px;
  background: transparent; color: var(--cyan); font-family: var(--font-body);
  font-size: 0.88rem; font-weight: 500; cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.btn-download:hover { background: rgba(0,212,255,0.08); }

/* ── Error ── */
.error-msg { color: var(--red); font-size: 0.85rem; margin-top: 0.8rem; display: none; padding: 0.6rem 1rem; background: rgba(244,63,94,0.08); border-radius: 8px; border: 1px solid rgba(244,63,94,0.2); }

/* ── Print Styles ── */
/* ── Print Styles ── */
@media print {
  * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
  body { background: #fff !important; color: #111 !important; }
  body::before { display: none !important; }
  .input-section, #pipeline, .tab-list, .download-bar, .badge, .header { display: none !important; }
  #results { display: block !important; }
  .readiness-card {
    display: flex !important; background: #f0f4f8 !important;
    border: 1px solid #ccc !important; margin-bottom: 1.5rem;
  }
  .readiness-label { color: #555 !important; }
  .readiness-value { color: #0066cc !important; }
  .readiness-bar-wrap { background: #ddd !important; }
  .readiness-bar { background: #0066cc !important; }
  .tabs { display: block !important; }
  .tab-panel {
    display: block !important; page-break-before: always;
    padding: 1.5rem 0; border-bottom: 2px solid #eee;
  }
  .tab-panel:first-of-type { page-break-before: avoid; }
  .tab-panel::before {
    content: attr(data-title); font-weight: 800; font-size: 1.4rem;
    display: block; margin-bottom: 1rem; color: #111;
    border-bottom: 2px solid #0066cc; padding-bottom: 0.5rem;
  }
  .md-content h2 { color: #111 !important; border-color: #ddd !important; }
  .md-content h3 { color: #0066cc !important; }
  .md-content p { color: #333 !important; }
  .md-content li { color: #333 !important; }
  .md-content li::before { color: #0066cc !important; }
  .md-content strong { color: #111 !important; }
  .md-content a { color: #0066cc !important; }
  .week-block { background: #f5f7fa !important; border-color: #ddd !important; break-inside: avoid; }
  .week-block .week-label { color: #7c3aed !important; }
  .week-block .week-title { color: #111 !important; }
  .week-block .week-detail { color: #444 !important; }
  .chart-wrap { display: none !important; }
  .tag-green { color: #16a34a !important; }
  .tag-red { color: #dc2626 !important; }
  .tag-amber { color: #d97706 !important; }
}
</style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <div class="badge">POWERED BY GOOGLE ADK · 5 AI AGENTS</div>
    <h1>Career Reinvention Agent</h1>
    <p class="subtitle">Drop your resume, name your target role. Five AI agents do the rest.</p>
  </div>

  <!-- Input Card -->
  <div class="card input-section" id="input-section">
    <div class="input-toggle">
      <button class="toggle-btn active" onclick="setMode('text')">Paste Text</button>
      <button class="toggle-btn" onclick="setMode('file')">Upload File</button>
    </div>

    <!-- Text Mode -->
    <div id="text-mode">
      <label>Your Resume / Background</label>
      <textarea id="resume-text" placeholder="Describe your experience, skills, and background..."></textarea>
    </div>

    <!-- File Mode -->
    <div id="file-mode" style="display:none">
      <label>Upload Resume</label>
      <div class="dropzone" id="dropzone">
        <input type="file" id="resume-file" accept=".docx,.pdf" onchange="handleFile(this)">
        <div class="dropzone-icon">📄</div>
        <div class="dropzone-text">Drop your file here or <span>browse</span></div>
        <div class="dropzone-text" style="margin-top:0.3rem;font-size:0.75rem;">.docx and .pdf supported</div>
      </div>
      <div class="file-selected" id="file-selected" style="display:none">
        <span>✅</span><span id="file-name"></span>
      </div>
    </div>

    <label>Target Role</label>
    <input type="text" id="target-role" placeholder="e.g. AI Solutions Architect, ML Engineer, Technical PM">

    <div class="error-msg" id="error-msg"></div>
    <button class="btn-primary" id="analyze-btn" onclick="startAnalysis()">Analyze My Career Transition →</button>
  </div>

  <!-- Pipeline -->
  <div id="pipeline">
    <div class="card">
      <div class="pipeline-header">AGENT ORCHESTRATION PIPELINE</div>
      <div class="pipeline-track">

        <div class="pipeline-step">
          <div class="node" id="node-1"><span class="node-icon">🔍</span></div>
          <div class="step-name" id="step-1-name">Job Research</div>
        </div>
        <div class="pipeline-connector" id="conn-1"><div class="fill"></div></div>

        <div class="pipeline-step">
          <div class="node" id="node-2"><span class="node-icon">📊</span></div>
          <div class="step-name" id="step-2-name">Gap Analysis</div>
        </div>
        <div class="pipeline-connector" id="conn-2"><div class="fill"></div></div>

        <div class="pipeline-step">
          <div class="node" id="node-3"><span class="node-icon">📚</span></div>
          <div class="step-name" id="step-3-name">Learning Path</div>
        </div>
        <div class="pipeline-connector" id="conn-3"><div class="fill"></div></div>

        <div class="pipeline-step">
          <div class="node" id="node-4"><span class="node-icon">🗓</span></div>
          <div class="step-name" id="step-4-name">90-Day Roadmap</div>
        </div>
        <div class="pipeline-connector" id="conn-4"><div class="fill"></div></div>

        <div class="pipeline-step">
          <div class="node" id="node-5"><span class="node-icon">✍️</span></div>
          <div class="step-name" id="step-5-name">LinkedIn Write</div>
        </div>

      </div>
      <div class="step-desc" id="step-desc">Initializing agents...</div>
    </div>
  </div>

  <!-- Results -->
  <div id="results" style="display:none">

    <!-- Readiness meter -->
    <div class="readiness-card" id="readiness-card">
      <div>
        <div class="readiness-label">OVERALL READINESS</div>
        <div class="readiness-value" id="readiness-text">—</div>
      </div>
      <div class="readiness-bar-wrap">
        <div class="readiness-bar" id="readiness-bar"></div>
      </div>
    </div>

    <!-- Chart + Tabs -->
    <div class="tabs">
      <div class="tab-list">
        <button class="tab-btn active" onclick="switchTab('job')">🔍 Job Market</button>
        <button class="tab-btn" onclick="switchTab('gap')">📊 Gap Analysis</button>
        <button class="tab-btn" onclick="switchTab('learn')">📚 Learning Path</button>
        <button class="tab-btn" onclick="switchTab('road')">🗓 90-Day Roadmap</button>
        <button class="tab-btn" onclick="switchTab('linkedin')">✍️ LinkedIn Makeover</button>
      </div>

      <div class="tab-panel active" id="tab-job" data-title="Job Market Research">
        <div class="md-content" id="content-job"></div>
      </div>
      <div class="tab-panel" id="tab-gap" data-title="Gap Analysis">
        <div class="chart-wrap"><canvas id="readiness-chart"></canvas></div>
        <div class="md-content" id="content-gap"></div>
      </div>
      <div class="tab-panel" id="tab-learn" data-title="Learning Path">
        <div class="md-content" id="content-learn"></div>
      </div>
      <div class="tab-panel" id="tab-road" data-title="90-Day Roadmap">
        <div class="md-content" id="content-road"></div>
      </div>
      <div class="tab-panel" id="tab-linkedin" data-title="LinkedIn Makeover">
        <div class="md-content" id="content-linkedin"></div>
      </div>
    </div>

    <!-- Download -->
    <div class="download-bar">
      <div class="download-info">
        <strong>Your Career Report is Ready</strong>
        <span>Download a full PDF copy to keep and share</span>
      </div>
      <button class="btn-download" onclick="downloadPDF()">
        ⬇ Download PDF Report
      </button>
    </div>
  </div>

</div>

<script>
// ── State ──
let inputMode = 'text';
let parsedFileText = '';
let reportData = null;
let chartInstance = null;

// ── Input mode toggle ──
function setMode(mode) {
  inputMode = mode;
  document.querySelectorAll('.toggle-btn').forEach((b,i) => b.classList.toggle('active', (i===0&&mode==='text')||(i===1&&mode==='file')));
  document.getElementById('text-mode').style.display = mode === 'text' ? 'block' : 'none';
  document.getElementById('file-mode').style.display = mode === 'file' ? 'block' : 'none';
}

// ── File handling ──
async function handleFile(input) {
  const file = input.files[0];
  if (!file) return;
  document.getElementById('file-name').textContent = file.name;
  document.getElementById('file-selected').style.display = 'flex';

  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await fetch('/parse-resume', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    parsedFileText = data.text;
  } catch(e) {
    showError('Could not parse file: ' + e.message);
  }
}

// Drag & drop
const dz = document.getElementById('dropzone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
dz.addEventListener('drop', e => {
  e.preventDefault(); dz.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) { document.getElementById('resume-file').files = e.dataTransfer.files; handleFile(document.getElementById('resume-file')); }
});

// ── Start Analysis ──
async function startAnalysis() {
  const role = document.getElementById('target-role').value.trim();
  let resume = inputMode === 'text' ? document.getElementById('resume-text').value.trim() : parsedFileText;

  if (!resume) return showError(inputMode === 'file' ? 'Please upload a file first' : 'Please enter your resume');
  if (!role) return showError('Please enter a target role');
  clearError();

  document.getElementById('analyze-btn').disabled = true;
  document.getElementById('pipeline').style.display = 'block';
  document.getElementById('results').style.display = 'none';
  document.getElementById('pipeline').scrollIntoView({ behavior: 'smooth', block: 'start' });

  try {
    const response = await fetch('/analyze-stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resume, target_role: role })
    });
    if (!response.ok) throw new Error('Failed to start analysis');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            handleEvent(currentEvent, data);
          } catch(_) {}
        }
      }
    }
  } catch(e) {
    showError('Analysis failed: ' + e.message);
    document.getElementById('analyze-btn').disabled = false;
  }
}

// ── Handle SSE Events ──
function handleEvent(event, data) {
  if (event === 'agent_start') {
    const n = document.getElementById(`node-${data.step}`);
    const s = document.getElementById(`step-${data.step}-name`);
    if (n) n.classList.add('active');
    if (s) s.classList.add('active');
    document.getElementById('step-desc').textContent = data.desc;
  }
  else if (event === 'agent_complete') {
    const n = document.getElementById(`node-${data.step}`);
    const s = document.getElementById(`step-${data.step}-name`);
    const c = document.getElementById(`conn-${data.step}`);
    if (n) { n.classList.remove('active'); n.classList.add('done'); }
    if (s) { s.classList.remove('active'); s.classList.add('done'); }
    if (c) c.classList.add('done');
  }
  else if (event === 'complete') {
    reportData = data;
    renderResults(data);
  }
  else if (event === 'error') {
    showError('Agent error: ' + data.message);
    document.getElementById('analyze-btn').disabled = false;
  }
}

// ── Render Results ──
function renderResults(data) {
  const s = data.sections;
  document.getElementById('content-job').innerHTML    = mdToHtml(s.job_research);
  document.getElementById('content-gap').innerHTML    = mdToHtml(s.gap_analysis);
  document.getElementById('content-learn').innerHTML  = mdToHtml(s.learning_path);
  document.getElementById('content-road').innerHTML   = mdToHtml(s.roadmap, true);
  document.getElementById('content-linkedin').innerHTML = mdToHtml(s.content_writer);

  // Parse readiness
  const readinessMap = { 'strong': [95,'Strong'], 'ready': [75,'Ready'], 'developing': [50,'Developing'], 'beginner': [25,'Beginner'] };
  const text = s.gap_analysis.toLowerCase();
  let readiness = [50, 'Developing'];
  for (const [key, val] of Object.entries(readinessMap)) {
    if (text.includes(key)) { readiness = val; break; }
  }
  document.getElementById('readiness-text').textContent = readiness[1];
  setTimeout(() => { document.getElementById('readiness-bar').style.width = readiness[0] + '%'; }, 100);

  // Donut chart
  renderChart(readiness[0]);

  document.getElementById('results').style.display = 'block';
  document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
  document.getElementById('step-desc').textContent = '✅ All agents complete — your report is ready below';
  document.getElementById('analyze-btn').disabled = false;
}

// ── Chart ──
function renderChart(score) {
  const ctx = document.getElementById('readiness-chart').getContext('2d');
  if (chartInstance) chartInstance.destroy();
  chartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [score, 100 - score],
        backgroundColor: ['rgba(0,212,255,0.85)', 'rgba(28,46,71,0.6)'],
        borderWidth: 0, hoverOffset: 0
      }]
    },
    options: {
      cutout: '78%',
      animation: { duration: 1200, easing: 'easeInOutQuart' },
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      }
    },
    plugins: [{
      id: 'centerText',
      beforeDraw(chart) {
        const { ctx, width, height } = chart;
        ctx.save();
        ctx.font = 'bold 2rem Syne, sans-serif';
        ctx.fillStyle = '#00d4ff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(score + '%', width / 2, height / 2);
        ctx.restore();
      }
    }]
  });
}

// ── Tab switching ──
function switchTab(id) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  const map = { job:'tab-job', gap:'tab-gap', learn:'tab-learn', road:'tab-road', linkedin:'tab-linkedin' };
  document.getElementById(map[id]).classList.add('active');
  event.target.classList.add('active');
}

// ── Markdown → HTML ──
function mdToHtml(text, isRoadmap = false) {
  if (!text) return '';
  const lines = text.split('\n');
  let html = '';
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Week blocks for roadmap
    if (isRoadmap && line.match(/^\*{0,2}\s*Week\s+\d+/i)) {
      if (inList) { html += '</ul>'; inList = false; }
      const weekMatch = line.match(/Week\s+(\d+)[:\s–-]*(.*)/i);
      if (weekMatch) {
        let detail = '';
        while (i + 1 < lines.length && lines[i+1].trim() && !lines[i+1].match(/^\*{0,2}\s*Week\s+\d+/i) && !lines[i+1].startsWith('#')) {
          detail += inline(lines[++i].replace(/^\s*[-*]\s*/, '')) + ' ';
        }
        html += `<div class="week-block"><div class="week-label">WEEK ${weekMatch[1]}</div><div class="week-title">${inline(weekMatch[2])}</div><div class="week-detail">${detail.trim()}</div></div>`;
        continue;
      }
    }

    if (line.startsWith('### ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<h3>${inline(line.slice(4))}</h3>`;
    } else if (line.startsWith('## ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<h2>${inline(line.slice(3))}</h2>`;
    } else if (line.startsWith('# ')) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<h2>${inline(line.slice(2))}</h2>`;
    } else if (line.match(/^[\*\-]\s/)) {
      if (!inList) { html += '<ul>'; inList = true; }
      let item = line.replace(/^[\*\-]\s/, '');
      if (item.startsWith('✅')) item = `<span class="tag-green">✅</span> ${item.slice(2)}`;
      else if (item.startsWith('❌')) item = `<span class="tag-red">❌</span> ${item.slice(2)}`;
      else if (item.startsWith('🔄')) item = `<span class="tag-amber">🔄</span> ${item.slice(2)}`;
      html += `<li>${inline(item)}</li>`;
    } else if (line.trim() === '') {
      if (inList) { html += '</ul>'; inList = false; }
    } else if (line.trim()) {
      if (inList) { html += '</ul>'; inList = false; }
      html += `<p>${inline(line)}</p>`;
    }
  }
  if (inList) html += '</ul>';
  return html;
}

function inline(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, `<code style="font-family:var(--font-mono);font-size:0.82em;color:var(--cyan);background:rgba(0,212,255,0.08);padding:0.1em 0.4em;border-radius:4px">$1</code>`)
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');
}

// ── Download PDF ──
function downloadPDF() {
  // Force all tab panels visible before print
  const panels = document.querySelectorAll('.tab-panel');
  panels.forEach(p => p.style.display = 'block');

  setTimeout(() => {
    window.print();
    // Restore after print dialog closes
    setTimeout(() => {
      panels.forEach(p => p.style.display = '');
      // Re-apply active state
      const active = document.querySelector('.tab-panel.active');
      if (!active) document.getElementById('tab-job').style.display = 'block';
    }, 1000);
  }, 150);
}
// ── Utilities ──
function showError(msg) {
  const el = document.getElementById('error-msg');
  el.textContent = msg; el.style.display = 'block';
}
function clearError() {
  document.getElementById('error-msg').style.display = 'none';
}
</script>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)