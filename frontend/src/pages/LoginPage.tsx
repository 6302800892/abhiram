import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { HOME_BY_ROLE, useAuth } from "../auth";
import { ErrorAlert, Field } from "../components/ui";
import { useAction } from "../hooks";

const DEMO_ACCOUNTS = [
  ["asha.verma", "Customer"],
  ["cityhosp.desk", "Network hospital"],
  ["adjudicator.priya", "Insurer adjudicator"],
  ["admin.sam", "Insurer admin"],
];

export function LoginPage() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const { busy, error, run } = useAction();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const session = await run(() => signIn(username.trim(), password));
    if (session) navigate(HOME_BY_ROLE[session.role], { replace: true });
  }

  return (
    <main className="login">
      <div className="login-card">
        <h1>MediCard</h1>
        <p className="tagline">Cashless hospitalization &amp; settlement</p>
        <form onSubmit={submit} className="stack">
          <Field label="Username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          <Field label="Password" type="password" autoComplete="current-password" value={password}
            onChange={(e) => setPassword(e.target.value)} required />
          <button type="submit" disabled={busy}>Sign in</button>
          <ErrorAlert message={error} />
        </form>
        <details className="demo">
          <summary>Demo accounts (password Demo@1234)</summary>
          <ul>
            {DEMO_ACCOUNTS.map(([user, role]) => (
              <li key={user}><code>{user}</code> — {role}</li>
            ))}
          </ul>
        </details>
      </div>
    </main>
  );
}
