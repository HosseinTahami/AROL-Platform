import { useState, useEffect } from "react";

const API = "http://localhost:8001/api";

// Read ?machine=... from the URL (the QR-code entry point)
function machineFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("machine") || "MCH-0001";
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const [question, setQuestion] = useState("");
  const [machineId, setMachineId] = useState(machineFromUrl());
  const [messages, setMessages] = useState([]); // chat history
  const [loading, setLoading] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem("dark") === "1");

  // Apply Bootstrap dark/light theme to the whole page
  useEffect(() => {
    document.documentElement.setAttribute("data-bs-theme", dark ? "dark" : "light");
    localStorage.setItem("dark", dark ? "1" : "0");
  }, [dark]);

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
        body: JSON.stringify({ question: myQuestion, machine_id: machineId }),
      });
      const data = await res.json();
      setMessages((m) => [...m, { role: "assistant", ...data }]);
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", answer: "Could not reach the server.", sources: [] },
      ]);
    }
    setLoading(false);
  }

  const themeToggle = (
    <button
      className="btn btn-outline-secondary btn-sm"
      onClick={() => setDark((d) => !d)}
    >
      {dark ? "☀ Light" : "🌙 Dark"}
    </button>
  );

  // ---- Login screen ----
  if (!token) {
    return (
      <div className="container" style={{ maxWidth: 420 }}>
        <div className="d-flex justify-content-end mt-3">{themeToggle}</div>
        <div className="card shadow-sm mt-4">
          <div className="card-body p-4">
            <h3 className="card-title mb-4 text-center">AROL Assistant</h3>
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
            {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}
          </div>
        </div>
      </div>
    );
  }

  // ---- Chat screen ----
  return (
    <div className="container" style={{ maxWidth: 760 }}>
      <div className="d-flex justify-content-between align-items-center mt-4 mb-3">
        <h3 className="mb-0">AROL Assistant</h3>
        <div className="d-flex gap-2">
          {themeToggle}
          <button className="btn btn-outline-secondary btn-sm" onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      <div className="mb-3">
        <span className="badge bg-secondary">Machine: {machineId}</span>
      </div>

      {/* Chat history */}
      <div
        className="border rounded p-3 mb-3"
        style={{ minHeight: 300, maxHeight: 460, overflowY: "auto" }}
      >
        {messages.length === 0 && (
          <p className="text-muted text-center mt-5">
            Ask about manuals, alarms, or orders for machine {machineId}.
          </p>
        )}
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="text-end mb-2">
              <span className="badge bg-primary p-2" style={{ whiteSpace: "pre-wrap" }}>
                {m.text}
              </span>
            </div>
          ) : (
            <div key={i} className="mb-3">
              {m.agent && (
                <span
                  className={`badge mb-1 ${
                    m.refused ? "bg-danger" : "bg-info text-dark"
                  }`}
                >
                  {m.refused ? "Refused" : `Handled by: ${m.agent}`}
                </span>
              )}
              <div className="card">
                <div className="card-body py-2">
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.answer}</div>
                  {m.sources && m.sources.length > 0 && (
                    <p className="mt-2 mb-0 small text-muted">
                      Sources: {m.sources.map((s) => `p.${s.page}`).join(", ")}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        )}
        {loading && (
          <div className="text-muted">
            <span className="spinner-border spinner-border-sm me-2" />
            Thinking…
          </div>
        )}
      </div>

      {/* Input */}
      <div className="input-group">
        <textarea
          className="form-control"
          rows={2}
          placeholder="Type your question…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask();
            }
          }}
        />
        <button className="btn btn-primary" onClick={ask} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;