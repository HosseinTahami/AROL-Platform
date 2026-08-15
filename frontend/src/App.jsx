import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";

const API = "http://localhost:8001/api";

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
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem("dark") !== "0");

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

  const Navbar = () => (
    <nav className="navbar navbar-expand px-4 mb-4 border-bottom">
      <span className="navbar-brand fw-bold">
        <span className="text-primary">AROL</span> Assistant
      </span>
      <div className="ms-auto d-flex align-items-center gap-2">
        {token && (
          <span className="badge bg-secondary">Machine: {machineId}</span>
        )}
        <button
          className="btn btn-outline-secondary btn-sm"
          onClick={() => setDark((d) => !d)}
        >
          {dark ? "☀" : "🌙"}
        </button>
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
      <>
        <Navbar />
        <div className="container" style={{ maxWidth: 420 }}>
          <div className="card shadow-sm mt-4">
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
              {error && <div className="alert alert-danger mt-3 mb-0">{error}</div>}
            </div>
          </div>
        </div>
      </>
    );
  }

  // ---- Chat screen ----
  return (
    <>
      <Navbar />
      <div className="container" style={{ maxWidth: 820 }}>
        <div
          className="d-flex flex-column gap-3 mb-3 p-2"
          style={{ minHeight: 380, maxHeight: 520, overflowY: "auto" }}
        >
          {messages.length === 0 && (
            <div className="text-muted text-center my-auto">
              <div style={{ fontSize: 40 }}>💬</div>
              Ask about manuals, alarms, or orders for {machineId}.
            </div>
          )}

          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="d-flex justify-content-end">
                <div
                  className="bg-primary text-white rounded-4 px-3 py-2"
                  style={{ maxWidth: "75%", whiteSpace: "pre-wrap" }}
                >
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={i} className="d-flex justify-content-start">
                <div
                  className="card rounded-4 shadow-sm"
                  style={{ maxWidth: "85%" }}
                >
                  <div className="card-body py-2 px-3">
                    {m.agent && (
                      <span
                        className={`badge mb-2 ${
                          m.refused ? "bg-danger" : "bg-info-subtle text-info-emphasis"
                        }`}
                      >
                        {m.refused ? "⛔ Refused" : `🤖 ${m.agent}`}
                      </span>
                    )}
                    <div className="markdown-body">
                      <ReactMarkdown>{m.answer}</ReactMarkdown>
                    </div>
                    {m.sources && m.sources.length > 0 && (
                      <p className="mt-2 mb-0 small text-muted border-top pt-2">
                        📄 Sources: {m.sources.map((s) => `p.${s.page}`).join(", ")}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )
          )}

          {loading && (
            <div className="d-flex justify-content-start">
              <div className="card rounded-4 shadow-sm">
                <div className="card-body py-2 px-3 text-muted">
                  <span className="spinner-border spinner-border-sm me-2" />
                  Thinking…
                </div>
              </div>
            </div>
          )}
        </div>

        <div className="input-group input-group-lg mb-4">
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
          <button className="btn btn-primary px-4" onClick={ask} disabled={loading}>
            Send
          </button>
        </div>
      </div>
    </>
  );
}

export default App;