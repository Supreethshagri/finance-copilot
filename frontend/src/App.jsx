import { useState } from "react";
import Login from "./Login";
import Dashboard from "./Dashboard";
import "./App.css";

export default function App() {
  // We're "logged in" if a token exists in storage.
  const [authed, setAuthed] = useState(!!localStorage.getItem("token"));

  function logout() {
    localStorage.removeItem("token");
    setAuthed(false);
  }

  if (!authed) return <Login onAuth={() => setAuthed(true)} />;
  return <Dashboard onLogout={logout} />;
}