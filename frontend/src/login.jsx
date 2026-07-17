import { useState } from "react";
import api from "./api";

export default function Login({ onAuth }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState("login"); // "login" or "register"
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    setError("");
    setBusy(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const res = await api.post(endpoint, { email, password });
      localStorage.setItem("token", res.data.access_token);
      onAuth(); // tell the app we're logged in
    } catch (err) {
      // Show the backend's message if present, else a generic one.
      setError(err.response?.data?.detail || "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <h1 className="brand">Finance<span>Copilot</span></h1>
        <p className="tagline">Ask your money questions in plain English.</p>

        <input
          className="field"
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          className="field"
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        {error && <div className="error">{error}</div>}

        <button className="primary" onClick={submit} disabled={busy}>
          {busy ? "Working..." : mode === "login" ? "Log in" : "Create account"}
        </button>

        <button
          className="switch"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login"
            ? "New here? Create an account"
            : "Have an account? Log in"}
        </button>
      </div>
    </div>
  );
}