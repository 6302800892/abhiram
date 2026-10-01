import { useState } from "react";
import { api } from "../api";
import { ReportsPanel } from "../components/ReportsPanel";
import { ErrorAlert, Field, Notice, Panel, SelectField, StatusBadge } from "../components/ui";
import { useAction, useLoad } from "../hooks";
import type { Hospital, PreAuth } from "../types";

interface AuditRecord {
  id: number;
  actor: string;
  action: string;
  entity_id: number;
  from_status: string;
  to_status: string;
  reason: string;
  occurred_at: string;
}

/** AD-R6 (display only — the API enforces it): auto-rejected by SYSTEM, or an escalated query. */
function overridable(p: PreAuth): boolean {
  const last = p.decisions[p.decisions.length - 1];
  return p.status === "QUERY_RAISED" || (p.status === "REJECTED" && last?.decided_by === "SYSTEM");
}

function OverrideRow({ p, onDone }: { p: PreAuth; onDone: (r: PreAuth) => void }) {
  const [status, setStatus] = useState("APPROVED");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const { busy, error, run } = useAction();

  async function submit() {
    const body = { status, reason, approved_amount: status === "PARTIALLY_APPROVED" ? amount : undefined };
    const result = await run(() => api.post<PreAuth>(`/api/admin/preauths/${p.preauth_id}/override`, body));
    if (result) onDone(result);
  }

  return (
    <tr>
      <td>{p.case_number}</td>
      <td><StatusBadge status={p.status} /></td>
      <td>{p.reason_codes.join(", ")}</td>
      <td className="num">{p.estimated_cost}</td>
      <td className="decide">
        <SelectField label="Override decision" options={["APPROVED", "PARTIALLY_APPROVED"]} value={status}
          onChange={(e) => setStatus(e.target.value)} />
        {status === "PARTIALLY_APPROVED" && (
          <Field label="Override amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        )}
        <Field label="Override reason" value={reason} onChange={(e) => setReason(e.target.value)} />
        <button type="button" disabled={busy} onClick={() => void submit()}>Override</button>
        <ErrorAlert message={error} />
      </td>
    </tr>
  );
}

function NetworkPanel() {
  const hospitals = useLoad(() => api.get<Hospital[]>("/api/admin/hospitals"));
  const { error, run } = useAction();
  async function toggle(h: Hospital) {
    await run(() => api.patch(`/api/admin/hospitals/${h.code}`, { in_network: !h.in_network }));
    await hospitals.reload();
  }
  return (
    <Panel title="Network hospitals">
      <ErrorAlert message={error ?? hospitals.error} />
      <div className="table-wrap">
        <table>
          <thead><tr><th>Code</th><th>Name</th><th>City</th><th>Network</th></tr></thead>
          <tbody>
            {(hospitals.data ?? []).map((h) => (
              <tr key={h.code}>
                <td>{h.code}</td><td>{h.name}</td><td>{h.city}</td>
                <td>
                  <button type="button" className="secondary" onClick={() => void toggle(h)}>
                    {h.in_network ? "Remove from network" : "Add to network"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

export function AdminPage() {
  const preauths = useLoad(() => api.get<PreAuth[]>("/api/preauths"));
  const audit = useLoad(() => api.get<AuditRecord[]>("/api/admin/audit"));
  const [notice, setNotice] = useState<string | null>(null);
  const candidates = (preauths.data ?? []).filter(overridable);

  function overridden(p: PreAuth) {
    setNotice(`${p.case_number} overridden to ${p.status}`);
    void preauths.reload();
    void audit.reload();
  }

  return (
    <>
      <h1>Admin workspace</h1>
      <Notice message={notice} />
      <Panel title="Overrides">
        {candidates.length === 0 ? <p className="muted">No auto-rejected or escalated pre-auths.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Case</th><th>Status</th><th>Reasons</th><th>Estimate</th><th>Override</th></tr></thead>
              <tbody>{candidates.map((p) => <OverrideRow key={p.preauth_id} p={p} onDone={overridden} />)}</tbody>
            </table>
          </div>
        )}
      </Panel>
      <Panel title="Audit log">
        <div className="table-wrap">
          <table>
            <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Pre-auth</th><th>Change</th><th>Reason</th></tr></thead>
            <tbody>
              {(audit.data ?? []).map((a) => (
                <tr key={a.id}>
                  <td>{a.occurred_at}</td><td>{a.actor}</td><td>{a.action}</td><td>#{a.entity_id}</td>
                  <td>{a.from_status} → {a.to_status}</td><td>{a.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
      <NetworkPanel />
      <ReportsPanel />
    </>
  );
}
