// CodeInsight AI - Frontend logic (NEW, CodeInsight AI)
const API_BASE = "";
let activeRepoId = localStorage.getItem("ci_active_repo") || null;
let pollTimer = null;

// ---------------- Navigation ----------------
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`view-${btn.dataset.view}`).classList.add("active");
    if (btn.dataset.view === "evaluation" && activeRepoId) loadEvaluation();
  });
});

function setActiveRepo(repoId) {
  activeRepoId = repoId;
  localStorage.setItem("ci_active_repo", repoId);
  document.getElementById("active-repo-hint").textContent = `Active repository: ${repoId}`;
}
if (activeRepoId) {
  document.getElementById("active-repo-hint").textContent = `Active repository: ${activeRepoId}`;
}

// ---------------- Repository Analysis ----------------
document.getElementById("analyze-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const repoUrl = document.getElementById("repo-url").value.trim();
  const branch = document.getElementById("repo-branch").value.trim();
  const errorBox = document.getElementById("analyze-error");
  errorBox.classList.add("hidden");

  try {
    const res = await fetch(`${API_BASE}/api/repository/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_url: repoUrl, branch: branch || null }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to start analysis.");

    setActiveRepo(data.repo_id);
    document.getElementById("status-card").style.display = "block";
    document.getElementById("overview-card").style.display = "none";
    pollStatus(data.repo_id);
  } catch (err) {
    errorBox.textContent = err.message;
    errorBox.classList.remove("hidden");
  }
});

function pollStatus(repoId) {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/repository/${repoId}/status`);
      const data = await res.json();
      document.getElementById("progress-fill").style.width = `${data.progress}%`;
      document.getElementById("status-text").textContent = `${data.status.toUpperCase()} — ${data.detail}`;

      if (data.status === "ready") {
        clearInterval(pollTimer);
        loadOverview(repoId);
      } else if (data.status === "failed") {
        clearInterval(pollTimer);
        document.getElementById("status-text").textContent = `FAILED — ${data.detail}`;
      }
    } catch (err) {
      clearInterval(pollTimer);
    }
  }, 1500);
}

async function loadOverview(repoId) {
  const res = await fetch(`${API_BASE}/api/repository/${repoId}/overview`);
  if (!res.ok) return;
  const o = await res.json();
  const grid = document.getElementById("overview-grid");
  const langs = Object.entries(o.languages).map(([k, v]) => `${k} (${v})`).join(", ");
  grid.innerHTML = `
    <div class="stat"><div class="num">${o.num_files}</div><div class="label">Files</div></div>
    <div class="stat"><div class="num">${o.num_classes}</div><div class="label">Classes/Interfaces</div></div>
    <div class="stat"><div class="num">${o.num_functions}</div><div class="label">Functions/Methods</div></div>
    <div class="stat"><div class="num">${o.num_relationships}</div><div class="label">Graph Relationships</div></div>
    <div class="stat" style="grid-column: span 2"><div class="num" style="font-size:14px">${langs}</div><div class="label">Languages</div></div>
    <div class="stat" style="grid-column: span 2"><div class="num" style="font-size:13px">${o.graph_status}</div><div class="label">Graph Backend</div></div>
    <div class="stat" style="grid-column: span 2"><div class="num" style="font-size:13px">${o.vector_status}</div><div class="label">Vector Store</div></div>
  `;
  document.getElementById("overview-card").style.display = "block";
}

// ---------------- Q&A ----------------
document.getElementById("ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!activeRepoId) {
    alert("Please analyze a repository first (Dashboard tab).");
    return;
  }
  const question = document.getElementById("question-input").value.trim();
  const submitBtn = e.target.querySelector("button");
  submitBtn.disabled = true;
  submitBtn.textContent = "Thinking...";

  try {
    const res = await fetch(`${API_BASE}/api/qa/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo_id: activeRepoId, question }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Failed to get an answer.");
    renderAnswer(data);
    document.getElementById("question-input").value = "";
  } catch (err) {
    alert(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Ask";
  }
});

function renderAnswer(data) {
  const container = document.getElementById("qa-results");
  const block = document.createElement("div");
  block.className = "qa-block";

  const sourcesHtml = data.sources.map(s => `
    <div class="source-item">
      📄 <strong>${s.file_path}</strong>${s.entity_name ? ` — ${s.entity_type || ""} <code>${s.entity_name}</code>` : ""}
      ${s.start_line ? ` (lines ${s.start_line}-${s.end_line})` : ""}
      <span class="badge ${s.retrieval_type}">${s.retrieval_type}</span>
    </div>
  `).join("") || "<p class='hint'>No sources retrieved.</p>";

  const v = data.verification;
  block.innerHTML = `
    <div class="qa-question">Q: ${escapeHtml(data.question)}</div>
    <div class="qa-answer">${escapeHtml(data.answer)}</div>
    <div class="sources"><h4>Retrieved Sources</h4>${sourcesHtml}</div>
    <div class="sources">
      <h4>AI Response Verification</h4>
      <div class="verification">
        <div class="verify-metric"><div class="val">${(v.faithfulness * 100).toFixed(1)}%</div><div class="lbl">Faithfulness</div></div>
        <div class="verify-metric"><div class="val">${(v.answer_relevancy * 100).toFixed(1)}%</div><div class="lbl">Answer Relevancy</div></div>
        <div class="verify-metric"><div class="val">${v.response_time_seconds}s</div><div class="lbl">Response Time</div></div>
      </div>
    </div>
    <div class="feedback-row">
      <span class="hint" style="margin:0">Was this helpful?</span>
      <button data-helpful="1">👍 Helpful</button>
      <button data-helpful="0">👎 Not Helpful</button>
    </div>
  `;

  block.querySelectorAll("[data-helpful]").forEach(btn => {
    btn.addEventListener("click", async () => {
      await fetch(`${API_BASE}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answer_id: data.answer_id, helpful: btn.dataset.helpful === "1" }),
      });
      block.querySelectorAll("[data-helpful]").forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
    });
  });

  container.prepend(block);
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ---------------- Evaluation dashboard ----------------
document.getElementById("refresh-eval").addEventListener("click", loadEvaluation);

async function loadEvaluation() {
  const body = document.getElementById("eval-body");
  if (!activeRepoId) {
    body.innerHTML = "<tr><td colspan='2'>No repository selected yet.</td></tr>";
    return;
  }
  const res = await fetch(`${API_BASE}/api/evaluation/${activeRepoId}/summary`);
  if (!res.ok) {
    body.innerHTML = "<tr><td colspan='2'>No evaluation data yet.</td></tr>";
    return;
  }
  const s = await res.json();
  body.innerHTML = `
    <tr><td>Repository</td><td>${s.repo_name}</td></tr>
    <tr><td>Questions Tested</td><td>${s.questions_tested}</td></tr>
    <tr><td>Average Faithfulness</td><td>${(s.avg_faithfulness * 100).toFixed(1)}%</td></tr>
    <tr><td>Average Answer Relevancy</td><td>${(s.avg_answer_relevancy * 100).toFixed(1)}%</td></tr>
    <tr><td>Average Response Time</td><td>${s.avg_response_time}s</td></tr>
    <tr><td>User Feedback</td><td>👍 ${s.helpful_count} &nbsp; 👎 ${s.not_helpful_count}</td></tr>
  `;
}

// resume polling / overview if a repo was already active from a previous session
if (activeRepoId) {
  loadOverview(activeRepoId).catch(() => {});
}
