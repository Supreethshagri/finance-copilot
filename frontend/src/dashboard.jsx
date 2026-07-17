import { useState } from "react";
import api from "./api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

export default function Dashboard({ onLogout }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [insights, setInsights] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // --- Upload a CSV ---
  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setError(""); setUploadMsg("Uploading...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await api.post("/upload/csv", formData);
      setUploadMsg(res.data.message);
    } catch (err) {
      setUploadMsg("");
      setError(err.response?.data?.detail || "Upload failed.");
    }
  }

  // --- Ask a question (supervisor routes it) ---
  async function ask() {
    if (!question.trim()) return;
    setError(""); setBusy(true); setAnswer(null);
    try {
      const res = await api.post("/chat/ask", { question });
      setAnswer(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Request failed.");
    } finally {
      setBusy(false);
    }
  }

  // --- Load insights (analytics agent) ---
  async function loadInsights() {
    setError(""); setBusy(true);
    try {
      const res = await api.get("/chat/insights");
      setInsights(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load insights.");
    } finally {
      setBusy(false);
    }
  }

  // --- Download the PDF report ---
  async function downloadReport() {
    try {
      const res = await api.get("/chat/report", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "expense_report.pdf";
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      setError("Could not download report.");
    }
  }

  // Build chart data from insights facts (category totals live in the SQL rows,
  // but for a simple chart we use the analytics 'facts' if present).
  const chartData =
    answer?.result?.rows?.map((r) => ({
      name: r.description?.slice(0, 12) || "—",
      amount: Math.abs(r.amount || 0),
    })) || [];

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="brand">Finance<span>Copilot</span></h1>
        <button className="ghost" onClick={onLogout}>Log out</button>
      </header>

      <div className="grid">
        {/* Upload */}
        <section className="panel">
          <h2>1 · Upload statement</h2>
          <p className="hint">CSV with date, description, amount columns.</p>
          <label className="upload">
            <input type="file" accept=".csv" onChange={handleUpload} hidden />
            Choose CSV
          </label>
          {uploadMsg && <div className="ok">{uploadMsg}</div>}
        </section>

        {/* Ask */}
        <section className="panel wide">
          <h2>2 · Ask anything</h2>
          <div className="askrow">
            <input
              className="field"
              placeholder="e.g. How much did I spend on Swiggy?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && ask()}
            />
            <button className="primary" onClick={ask} disabled={busy}>
              {busy ? "..." : "Ask"}
            </button>
          </div>

          {answer && (
            <div className="answer">
              <div className="route">routed to: {answer.route_taken}</div>
              {answer.result?.rows && (
                <table className="txns">
                  <thead>
                    <tr><th>Date</th><th>Description</th><th>Amount</th></tr>
                  </thead>
                  <tbody>
                    {answer.result.rows.map((r, i) => (
                      <tr key={i}>
                        <td>{r.txn_date}</td>
                        <td>{r.description}</td>
                        <td className={r.amount < 0 ? "neg" : "pos"}>
                          {r.amount}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {answer.result?.insights && (
                <p className="prose">{answer.result.insights}</p>
              )}
              {answer.result?.message && (
                <p className="prose">{answer.result.message}</p>
              )}
            </div>
          )}

          {chartData.length > 0 && (
            <div className="chart">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fill: "#5a6478", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#5a6478", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#10131c", border: "1px solid #1e2436",
                      borderRadius: 8, fontSize: 13, color: "#e8ecf5",
  }}
/>
                  <Bar dataKey="amount">
                      {chartData.map((_, i) => <Cell key={i} fill="#6e78ff" />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>

        {/* Insights + report */}
        <section className="panel">
          <h2>3 · Insights & report</h2>
          <div className="btnrow">
            <button className="secondary" onClick={loadInsights} disabled={busy}>
              Generate insights
            </button>
            <button className="secondary" onClick={downloadReport}>
              Download PDF
            </button>
          </div>
          {insights && (
            <div className="insights">
              <p className="prose">{insights.insights}</p>
              {insights.facts && !insights.facts.empty && (
                <div className="facts">
                  <div><span>Spent</span><b>{insights.facts.total_spent}</b></div>
                  <div><span>Income</span><b>{insights.facts.total_income}</b></div>
                  <div><span>Net</span><b>{insights.facts.net}</b></div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {error && <div className="toast-error">{error}</div>}
    </div>
  );
}