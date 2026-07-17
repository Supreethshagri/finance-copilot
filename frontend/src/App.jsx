import { useState } from "react";
import Login from "./Login";
import Dashboard from "./Dashboard";
import "./App.css";

// Decode the email from the JWT payload (middle segment, base64).
function emailFromToken() {
  const token = localStorage.getItem("token");
  if (!token) return "";
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.email || "";
  } catch {
    return "";
  }
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("token"));

  function logout() {
    localStorage.removeItem("token");
    setAuthed(false);
  }

  if (!authed) return <Login onAuth={() => setAuthed(true)} />;
  return <Dashboard onLogout={logout} email={emailFromToken()} />;
}