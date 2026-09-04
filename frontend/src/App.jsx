import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";

const API = "http://localhost:8001/api";

function machineFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("machine");
}

function parseTraceStates(trace) {
  const state = {
    scope: null,        // "ok" | "refused"
    plannerAgents: [],
    visibility: null,    // "ok" | "refused"
    agentsRan: [],
    synthesis: null,     // "passthrough" | "combined" | null
    refusedAt: null,
  };

  for (const step of trace || []) {
    if (step.startsWith("scope_check")) {
      state.scope = step.includes("refused") ? "refused" : "ok";
      if (state.scope === "refused") state.refusedAt = "scope_check";
    } else if (step.startsWith("planner")) {
      const match = step.match(/\[(.*)\]/);
      if (match) {
        state.plannerAgents = match[1]
          .split(",")
          .map((s) => s.replace(/['"\s]/g, ""))
          .filter(Boolean);
      }
    } else if (step.startsWith("visibility_check")) {
      state.visibility = step.includes("refused") ? "refused" : "ok";
      if (state.visibility === "refused") state.refusedAt = "visibility_check";
    } else if (step.startsWith("agents ran")) {
      const match = step.match(/\[(.*)\]/);
      if (match) {
        state.agentsRan = match[1]
          .split(",")
          .map((s) => s.replace(/['"\s]/g, ""))
          .filter(Boolean);
      }
    } else if (step.startsWith("synthesizer")) {
      state.synthesis = step.includes("passthrough") ? "passthrough" : "combined";
    }
  }
  return state;
}

const AGENT_COLORS = {
  manuals: { fill: "#CECBF6", stroke: "#3C3489", text: "#26215C" },
  operational: { fill: "#9FE1CB", stroke: "#0F6E56", text: "#04342C" },
  commercial: { fill: "#FAC775", stroke: "#854F0B", text: "#412402" },
  diagnosis: { fill: "#F0997B", stroke: "#712B13", text: "#4A1B0C" },
};

function FlowDiagram({ trace }) {
  const s = parseTraceStates(trace);

  const wallStyle = (status) => {
    if (status === "refused") return { fill: "#F7C1C1", stroke: "#A32D2D", text: "#501313" };
    if (status === "ok") return { fill: "#B5D4F4", stroke: "#185FA5", text: "#042C53" };
    return { fill: "#EFEFEF", stroke: "#B4B2A9", text: "#888780" };
  };

  const scopeStyle = wallStyle(s.scope);
  const visStyle = wallStyle(s.visibility);
  const agentList = s.agentsRan.length ? s.agentsRan : s.plannerAgents;

  return (
    <svg width="100%" viewBox="0 0 520 280" style={{ maxWidth: 500 }}>
      <defs>
        <marker id="fd-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M2 1L8 5L2 9" fill="none" stroke="#999" strokeWidth="1.5" />
        </marker>
      </defs>

      {/* scope_check */}
      <rect x="10" y="10" width="150" height="56" rx="8" fill={scopeStyle.fill} stroke={scopeStyle.stroke} strokeWidth="1.5" />
      <text x="85" y="32" textAnchor="middle" fontSize="12" fontWeight="700" fill={scopeStyle.text}>scope check</text>
      <text x="85" y="48" textAnchor="middle" fontSize="10" fill={scopeStyle.text}>
        {s.scope === "refused" ? "wrong company" : s.scope === "ok" ? "company ok" : "company wall"}
      </text>

      <line x1="160" y1="38" x2="180" y2="38" stroke="#999" strokeWidth="1" markerEnd="url(#fd-arrow)" />

      {/* planner */}
      <rect x="180" y="10" width="150" height="56" rx="8" fill="#F4C0D1" stroke="#993556" strokeWidth="1.5" />
      <text x="255" y="32" textAnchor="middle" fontSize="12" fontWeight="700" fill="#4B1528">planner</text>
      <text x="255" y="48" textAnchor="middle" fontSize="9" fill="#4B1528">
        {s.plannerAgents.length ? s.plannerAgents.join(", ") : "-"}
      </text>

      <line x1="330" y1="38" x2="350" y2="38" stroke="#999" strokeWidth="1" markerEnd="url(#fd-arrow)" />

      {/* visibility_check */}
      <rect x="350" y="10" width="150" height="56" rx="8" fill={visStyle.fill} stroke={visStyle.stroke} strokeWidth="1.5" />
      <text x="425" y="32" textAnchor="middle" fontSize="12" fontWeight="700" fill={visStyle.text}>visibility check</text>
      <text x="425" y="48" textAnchor="middle" fontSize="10" fill={visStyle.text}>
        {s.visibility === "refused" ? "role blocked" : s.visibility === "ok" ? "role ok" : "role wall"}
      </text>

      <line x1="425" y1="66" x2="425" y2="100" stroke="#999" strokeWidth="1" markerEnd="url(#fd-arrow)" />

      {/* agents run, one box per agent that actually ran */}
      <text x="425" y="112" textAnchor="middle" fontSize="10" fontWeight="600" fill="#666">agents run</text>
      {agentList.map((agent, i) => {
        const c = AGENT_COLORS[agent] || { fill: "#EFEFEF", stroke: "#B4B2A9", text: "#666" };
        const y = 120 + i * 40;
        return (
          <g key={agent}>
            <rect x="350" y={y} width="150" height="32" rx="6" fill={c.fill} stroke={c.stroke} strokeWidth="1.5" />
            <text x="425" y={y + 20} textAnchor="middle" fontSize="11" fontWeight="700" fill={c.text}>
              {agent}
            </text>
          </g>
        );
      })}

      {agentList.length > 0 && (
        <>
          <line x1="350" y1={120 + (agentList.length - 1) * 40 + 16} x2="330" y2={120 + (agentList.length - 1) * 40 + 16} stroke="#999" strokeWidth="1" markerEnd="url(#fd-arrow)" />

          {/* synthesizer */}
          <rect x="180" y={120 + (agentList.length - 1) * 40} width="150" height="32" rx="6"
                fill="#97C459" stroke="#3B6D11" strokeWidth="1.5" />
          <text x="255" y={120 + (agentList.length - 1) * 40 + 20} textAnchor="middle" fontSize="11" fontWeight="700" fill="#173404">
            {s.synthesis === "passthrough" ? "passthrough" : s.synthesis === "combined" ? "combined" : "synthesizer"}
          </text>
        </>
      )}

      {s.refusedAt && (
        <text x="260" y="260" textAnchor="middle" fontSize="11" fill="#A32D2D" fontWeight="700">
          request refused at {s.refusedAt.replace("_", " ")}
        </text>
      )}
    </svg>
  );
}

function TraceView({ trace }) {
  const [open, setOpen] = useState(false);
  if (!trace || trace.length === 0) return null;

  return (
    <div className="mt-2">
      <button
        className="btn btn-sm btn-outline-secondary py-0 px-2"
        style={{ fontSize: "0.75rem" }}
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "Hide" : "Show"} request flow
      </button>
      {open && (
        <div className="mt-2 p-2 rounded-3">
          <FlowDiagram trace={trace} />
        </div>
      )}
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [machineCheck, setMachineCheck] = useState(null);
  const [question, setQuestion] = useState("");
  const [machineId, setMachineId] = useState(machineFromUrl());
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [me, setMe] = useState(null);
  const [conversationId, setConversationId] = useState(null);

  useEffect(() => {
    if (!token) return setMe(null);
    fetch(`${API}/me/`, { headers: { Authorization: `Token ${token}` } })
      .then((res) => res.json())
      .then(setMe)
      .catch(() => setMe(null));
  }, [token]);

  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", "dark");
    document.body.style.minHeight = "100vh";
  }, []);

  useEffect(() => {
    if (!token || !machineId) {
      setMachineCheck(machineId ? null : { valid: false, reason: "none" });
      return;
    }
    setMachineCheck(null);
    fetch(`${API}/machines/${machineId}/check/`, {
      headers: { Authorization: `Token ${token}` },
    })
      .then((res) => res.json())
      .then(setMachineCheck)
      .catch(() => setMachineCheck({ valid: false, reason: "error" }));
  }, [token, machineId]);

  async function login() {
    setError("");
    try {
      const res = await fetch(`${API}/auth/token/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) return setError("Login failed. Check your credentials.");
      const data = await res.json();
      localStorage.setItem("token", data.token);
      setToken(data.token);
    } catch {
      setError("Could not reach the server.");
    }
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
    setMessages([]);
    setConversationId(null);
    setMe(null);
  }

  async function ask() {
    if (!question.trim()) return;
    const myQuestion = question;
    setQuestion("");
    setMessages((m) => [...m, { role: "user", text: myQuestion }]);
    setLoading(true);
    try {
      const res = await fetch(`${API}/chat/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({
          question: myQuestion,
          machine_id: machineId,
          conversation_id: conversationId,
        }),
      });
      const data = await res.json();
      if (data.conversation_id) setConversationId(data.conversation_id);
      setMessages((m) => [...m, { role: "assistant", ...data }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", answer: "Could not reach the server.", sources: [] },
      ]);
    }
    setLoading(false);
  }

  const Navbar = () => (
    <nav
      className="navbar px-4 border-bottom flex-shrink-0"
      style={{ height: 56 }}
    >
      <span className="navbar-brand fw-bold mb-0">
        <span className="text-primary">AROL</span> Assistant
      </span>
      <div className="ms-auto d-flex align-items-center gap-2">
        {token && machineId && (
          <span className="badge text-bg-secondary">Machine: {machineId}</span>
        )}
        {token && me && (
          <div
            className="position-relative"
            onMouseEnter={(e) =>
              (e.currentTarget.querySelector(".profile-popover").style.display = "block")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.querySelector(".profile-popover").style.display = "none")
            }
          >
            <span className="badge text-bg-primary" style={{ cursor: "default" }}>
              {me.first_name}
            </span>
            <div
              className="profile-popover card shadow position-absolute end-0 mt-2"
              style={{ display: "none", zIndex: 1000, minWidth: 230 }}
            >
              <div className="card-body py-2 px-3">
                <div className="fw-semibold">
                  {me.first_name} {me.last_name}
                </div>
                <div className="small text-muted">{me.email}</div>
                <div className="d-flex align-items-center gap-2 mt-2">
                  <span className="badge text-bg-info">{me.visibility}</span>
                  {me.company && <span className="small text-muted">{me.company}</span>}
                </div>
              </div>
            </div>
          </div>
        )}
        {token && (
          <button className="btn btn-outline-danger btn-sm" onClick={logout}>
            Log out
          </button>
        )}
      </div>
    </nav>
  );

  // ---- Login screen ----
  if (!token) {
    return (
      <div className="d-flex flex-column vh-100">
        <Navbar />
        <div className="d-flex align-items-center justify-content-center flex-grow-1">
          <div className="card shadow" style={{ width: 380 }}>
            <div className="card-body p-4">
              <h4 className="card-title mb-4 text-center">Sign in</h4>
              <input
                className="form-control mb-2"
                placeholder="Username (email)"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
              <input
                type="password"
                className="form-control mb-3"
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && login()}
              />
              <button className="btn btn-primary w-100" onClick={login}>
                Log in
              </button>
              {error && <div className="alert alert-danger mt-3 mb-0 py-2">{error}</div>}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ---- Machine-gated chat screen ----
  return (
    <div className="d-flex flex-column vh-100">
      <Navbar />

      {machineCheck === null ? (
        <div className="d-flex align-items-center justify-content-center flex-grow-1 text-muted">
          Checking machine…
        </div>
      ) : !machineCheck.valid ? (
        <div className="d-flex align-items-center justify-content-center flex-grow-1">
          <div className="alert alert-warning mb-0" style={{ maxWidth: 480 }}>
            {machineCheck.reason === "not_found" && "This machine was not found."}
            {machineCheck.reason === "not_yours" &&
              "This machine does not belong to your company."}
            {machineCheck.reason === "none" &&
              "No machine selected. Please scan a machine's QR code to start."}
            {machineCheck.reason === "error" &&
              "Could not verify this machine right now."}
          </div>
        </div>
      ) : (
        <div className="d-flex flex-column flex-grow-1 overflow-hidden">
          {/* Message list — fills all available space, scrolls independently */}
          <div className="flex-grow-1 overflow-auto">
            <div
              className="d-flex flex-column gap-3 px-3 py-4 mx-auto"
              style={{ maxWidth: 780 }}
            >
              {messages.length === 0 && (
                <div className="text-muted text-center mt-5">
                  <div style={{ fontSize: 42 }}>💬</div>
                  Ask about manuals, alarms, or orders for {machineId}.
                </div>
              )}

              {messages.map((m, i) =>
                m.role === "user" ? (
                  <div key={i} className="d-flex justify-content-end">
                    <div
                      className="bg-primary text-white rounded-4 px-3 py-2"
                      style={{ maxWidth: "72%", whiteSpace: "pre-wrap", textAlign: "left" }}
                    >
                      {m.text}
                    </div>
                  </div>
                ) : (
                  <div key={i} className="d-flex justify-content-start">
                    <div
                      className="card border-0 shadow-sm rounded-4"
                      style={{ maxWidth: "80%", textAlign: "left" }}
                    >
                      <div className="card-body py-2 px-3">
                        {m.agents && m.agents.length > 0 && (
                          <span
                            className={`badge mb-2 ${
                              m.refused ? "text-bg-danger" : "text-bg-info"
                            }`}
                          >
                            {m.refused ? "⛔ Refused" : `🤖 ${m.agents.join(" + ")}`}
                          </span>
                        )}
                        <div className="chat-markdown" style={{ textAlign: "left" }}>
                          <ReactMarkdown>{m.answer}</ReactMarkdown>
                        </div>
                        {m.sources && m.sources.length > 0 && (
                          <p className="mt-2 mb-0 small text-muted border-top pt-2">
                            📄 Sources: {m.sources.map((s) => `p.${s.page}`).join(", ")}
                          </p>
                        )}
                        <TraceView trace={m.trace} />
                      </div>
                    </div>
                  </div>
                )
              )}

              {loading && (
                <div className="d-flex justify-content-start">
                  <div className="card border-0 shadow-sm rounded-4">
                    <div className="card-body py-2 px-3 text-muted">
                      <span className="spinner-border spinner-border-sm me-2" />
                      Thinking…
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Input bar — pinned to the bottom */}
          <div className="border-top flex-shrink-0 py-3">
            <div className="mx-auto px-3" style={{ maxWidth: 780 }}>
              <div className="input-group input-group-lg">
                <textarea
                  className="form-control"
                  rows={1}
                  placeholder="Type your question…"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      ask();
                    }
                  }}
                  style={{ resize: "none" }}
                />
                <button
                  className="btn btn-primary px-4"
                  onClick={ask}
                  disabled={loading}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;