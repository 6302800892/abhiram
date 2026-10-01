import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, HOME_BY_ROLE, useAuth } from "./auth";
import { Layout } from "./components/Layout";
import { AdminPage } from "./pages/AdminPage";
import { CaseDetailPage } from "./pages/CaseDetailPage";
import { CustomerPage } from "./pages/CustomerPage";
import { HospitalPage } from "./pages/HospitalPage";
import { InsurerPage } from "./pages/InsurerPage";
import { LoginPage } from "./pages/LoginPage";
import type { Role } from "./types";

/** UI-side role gate (the real boundary is the API, NFR-04): wrong role -> own workspace. */
function RequireRole({ role, children }: { role?: Role; children: ReactNode }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/" replace />;
  if (role && session.role !== role) return <Navigate to={HOME_BY_ROLE[session.role]} replace />;
  return <>{children}</>;
}

function Home() {
  const { session } = useAuth();
  return session ? <Navigate to={HOME_BY_ROLE[session.role]} replace /> : <LoginPage />;
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route element={<RequireRole><Layout /></RequireRole>}>
            <Route path="/customer" element={<RequireRole role="CUSTOMER"><CustomerPage /></RequireRole>} />
            <Route path="/hospital" element={<RequireRole role="HOSPITAL"><HospitalPage /></RequireRole>} />
            <Route path="/insurer" element={<RequireRole role="INSURER"><InsurerPage /></RequireRole>} />
            <Route path="/admin" element={<RequireRole role="ADMIN"><AdminPage /></RequireRole>} />
            <Route path="/cases/:caseId" element={<CaseDetailPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
