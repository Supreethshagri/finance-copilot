import { useState } from "react";
import api from "./api";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from "recharts";

const EXAMPLES = [
  "Show my 3 biggest expenses",
  "Categorize my transactions",
  "Give me insights on my spending",
];

export default function Dashboard({ onLogout, email }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [insights, setInsights] = useState(null);
  const [uploadMsg, setUploadMsg] = useState("");
  const [asking, setAsking] = useState(false);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [error, setError] = useState("");
  const [hasData, setHasData] = useState(false);

  function showError(msg) {
    setError(msg);
    setTimeout(() => setError(""), 4000);
  }

  async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    setUploadMsg("Uploading...");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await api.post("/upload/csv", formData);
      setUploadMsg(res.data.message);
      setHasData(true);
    } catch (err) {
      setUploadMsg("");
      showError(err.response?.data?.detail || "Upload failed.");
    }
  }

  async function ask(q) {
    const query = typeof q === "string" ? q : question;
    if (!query.trim()) return;
    setQuestion(query);
    setAsking(true);
    setAnswer(null);
    try {
      const res = await api.post("/chat/ask", { question: query });
      setAnswer(res.data);
      setHasData(true);
    } catch (err) {
      showError(err.response?.data?.detail || "Request failed.");
    } finally {
      setAsking(false);
    }
  }

  async function loadInsights() {
    setLoadingInsights(true);
    try {
      const res = await api.get("/chat/insights");
      setInsights(res.data);
      setHasData(true);
    } catch (err) {
      showError(err.response?.data?.detail || "Could not load insights.");
    } finally {
      setLoadingInsights(false);
    }
  }

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
      showError("Could not download report.");
    }
  }

  // Only build chart data when rows actually look like transactions.
  const chartData =
    answer?.result?.rows
      ?.filter((r) => r.description !== undefined && r.amount !== undefined)
      .map((r) => ({
        name: (r.description || "").slice(0, 12) || "—",
        amount: Math.abs(r.amount || 0),
      })) || [];

  // Render whatever columns the SQL agent returned, instead of assuming
  // date/description/amount. Handles aggregates (SUM, COUNT) too.
  function renderRows(rows) {
    if (!rows || rows.length === 0) return null;
    const cols = Object.keys(rows[0]).filter((c) => c !== "user_id");
    const isNum = (v) => typeof v === "number";

    // Single value (e.g. SUM) -> show as one big metric, not a table.
    if (rows.length === 1 && cols.length === 1) {
      const key = cols[0];
      const val = rows[0][key];
      return (
        <div className="metric" style={{ maxWidth: 240 }}>
          <span>{key.replace(/_/g, " ")}</span>
          <b className={isNum(val) && val < 0 ? "neg" : "pos"}>
            {isNum(val) ? Math.abs(val).toLocaleString("en-IN") : String(val)}
          </b>
        </div>
      );
    }

    return (
      <table className="txns">
        <thead>
          <tr>
            {cols.map((c) => (
              <th key={c} className={isNum(rows[0][c]) ? "num" : ""}>
                {c.replace(/_/g, " ")}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td
                  key={c}
                  className={
                    isNum(r[c])
                      ? `num ${r[c] < 0 ? "neg" : "pos"}`
                      : c.includes("date")
                      ? "date"
                      : ""
                  }
                >
                  {isNum(r[c]) ? r[c].toLocaleString("en-IN") : String(r[c] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">₹</span>
          Finance<span className="accent">Copilot</span>
        </div>
        <div className="user-chip">
          {email && <span>{email}</span>}
          <button className="ghost" onClick={onLogout}>Log out</button>
        </div>
      </header>

      {/* Hero: ask */}
      <section className="card">
        <div className="card-label">Ask anything about your money</div>
        <div className="askrow">
          <input
            className="field"
            placeholder="How much did I spend on Swiggy?"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
          />
          <button className="primary" onClick={() => ask()} disabled={asking}>
            {asking ? "Thinking..." : "Ask"}
          </button>
        </div>
        <div className="chips">
          {EXAMPLES.map((ex) => (
            <button key={ex} className="chip" onClick={() => ask(ex)}>{ex}</button>
          ))}
        </div>
      </section>

      {/* Loading */}
      {asking && (
        <section className="card">
          <div className="skeleton">
            <div className="sk-row short" />
            <div className="sk-row mid" />
            <div className="sk-row" />
            <div className="sk-row mid" />
          </div>
        </section>
      )}

      {/* Answer */}
      {!asking && answer && (
        <section className="card">
          {answer.route_taken && (
            <div className="route">routed to {answer.route_taken}</div>
          )}

          {renderRows(answer.result?.rows)}

          {answer.result?.insights && (
            <p className="prose">{answer.result.insights}</p>
          )}
          {answer.result?.message && (
            <p className="prose">{answer.result.message}</p>
          )}
          {answer.result?.action === "download_report" && (
            <button
              className="secondary"
              style={{ marginTop: "0.8rem", flex: "none" }}
              onClick={downloadReport}
            >
              Download PDF
            </button>
          )}
          {answer.result?.error && (
            <p className="prose neg">{answer.result.error}</p>
          )}

          {chartData.length > 0 && (
            <div className="chart">
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" tick={{ fill: "#5a6478", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#5a6478", fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      background: "#10131c",
                      border: "1px solid #1e2436",
                      borderRadius: 8,
                      fontSize: 13,
                      color: "#e8ecf5",
                    }}
                  />
                  <Bar dataKey="amount" radius={[4, 4, 0, 0]}>
                    {chartData.map((_, i) => <Cell key={i} fill="#6e78ff" />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </section>
      )}

      {/* Empty state */}
      {!asking && !answer && !hasData && (
        <section className="card">
          <div className="empty">
            <div className="empty-mark">↑</div>
            <h3>Upload a statement to begin</h3>
            <p>Add a CSV below, then ask a question or generate insights.</p>
          </div>
        </section>
      )}

      {/* Insights */}
      {insights && insights.facts && !insights.facts.empty && (
        <div className="facts">
          <div className="metric"><span>Spent</span><b className="neg">{insights.facts.total_spent}</b></div>
          <div className="metric"><span>Income</span><b className="pos">{insights.facts.total_income}</b></div>
          <div className="metric"><span>Net</span><b>{insights.facts.net}</b></div>
        </div>
      )}
      {loadingInsights && (
        <section className="card">
          <div className="skeleton">
            <div className="sk-row mid" />
            <div className="sk-row" />
          </div>
        </section>
      )}
      {insights && insights.insights && (
        <section className="card">
          <div className="card-label">Insights</div>
          <p className="prose">{insights.insights}</p>
        </section>
      )}

      {/* Bottom rail */}
      <div className="rail">
        <section className="card" style={{ marginBottom: 0 }}>
          <div className="card-label">Upload statement</div>
          <p className="hint">CSV with date, description, and amount columns.</p>
          <label className="upload">
            <input type="file" accept=".csv" onChange={handleUpload} hidden />
            Choose CSV
          </label>
          {uploadMsg && <div className="ok">{uploadMsg}</div>}
        </section>

        <section className="card" style={{ marginBottom: 0 }}>
          <div className="card-label">Insights and report</div>
          <p className="hint">Generate a summary or download a PDF report.</p>
          <div className="btnrow">
            <button className="secondary" onClick={loadInsights} disabled={loadingInsights}>
              {loadingInsights ? "Loading..." : "Generate insights"}
            </button>
            <button className="secondary" onClick={downloadReport}>
              Download PDF
            </button>
          </div>
        </section>
      </div>

      {error && <div className="toast-error">{error}</div>}
    </div>
  );
}