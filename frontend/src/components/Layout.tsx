import { NavLink, Outlet } from "react-router-dom";
import { HOME_BY_ROLE, useAuth } from "../auth";

const LABELS = { CUSTOMER: "My coverage", HOSPITAL: "Hospital desk", INSURER: "Adjudication", ADMIN: "Administration" };

export function Layout() {
  const { session, signOut } = useAuth();
  if (!session) return null;
  return (
    <div className="shell">
      <header className="topbar">
        <span className="brand">MediCard</span>
        <nav aria-label="Main" className="nav">
          <NavLink to={HOME_BY_ROLE[session.role]}>{LABELS[session.role]}</NavLink>
        </nav>
        <div className="whoami">
          <span>{session.display_name}</span>
          <span className="role-tag">{session.role}</span>
          <button type="button" className="link-button" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <footer className="footer">Synthetic demo data only · BC-AINE-017</footer>
    </div>
  );
}
