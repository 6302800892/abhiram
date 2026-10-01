import { useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { HospitalActions, InsurerActions } from "../components/CaseActions";
import { ErrorAlert, Money, Panel, StatusBadge } from "../components/ui";
import { useLoad } from "../hooks";
import type { CaseDetail, Settlement, TimelineEvent } from "../types";

function SettlementBreakdown({ s }: { s: Settlement }) {
  return (
    <Panel title="Settlement">
      <dl className="facts">
        <dt>Pre-auth amount</dt><dd><Money value={s.pre_auth_amount} /></dd>
        <dt>Buffer</dt><dd>{s.buffer_pct}% (cap <Money value={s.cap} />)</dd>
        <dt>Final bill</dt><dd><Money value={s.final_bill} /></dd>
        <dt>Admissible</dt><dd><Money value={s.admissible} /></dd>
        <dt>Deductible</dt><dd><Money value={s.deductible} /></dd>
        <dt>Co-pay</dt><dd><Money value={s.copay} /></dd>
        <dt>Paid to hospital</dt><dd className="paid" data-testid="paid-amount">{s.settlement_amount}</dd>
        <dt>Payment reference</dt><dd>{s.payment_reference}</dd>
      </dl>
    </Panel>
  );
}

function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <Panel title="Timeline">
      <ol className="timeline">
        {events.map((e, i) => (
          <li key={i}>
            <time>{e.occurred_at}</time>
            <span className="event">{e.event_type.replace("_", " ").toLowerCase()}</span>
            {e.to_status && <StatusBadge status={e.to_status} />}
            {e.note && <span className="muted"> {e.note}</span>}
            <span className="muted"> · {e.actor}</span>
          </li>
        ))}
      </ol>
    </Panel>
  );
}

export function CaseDetailPage() {
  const { caseId } = useParams();
  const { session } = useAuth();
  const detail = useLoad(() => api.get<CaseDetail>(`/api/cases/${caseId}`), [caseId]);
  const timeline = useLoad(() => api.get<TimelineEvent[]>(`/api/cases/${caseId}/timeline`), [caseId]);
  const refresh = () => {
    void detail.reload();
    void timeline.reload();
  };
  const c = detail.data;
  if (!c) return <ErrorAlert message={detail.error} />;

  return (
    <>
      <h1>{c.case_number}</h1>
      <p className="case-meta">
        <StatusBadge status={c.status} testId="case-status" /> {c.member_name} ({c.member_id}) · {c.hospital_name} ·
        policy {c.policy_number}
      </p>
      <div className="grid-2">
        <Panel title="Pre-authorization">
          <dl className="facts">
            <dt>Status</dt><dd><StatusBadge status={c.preauth.status} /></dd>
            <dt>Diagnosis</dt><dd>{c.preauth.diagnosis_code}</dd>
            <dt>Estimated cost</dt><dd><Money value={c.preauth.estimated_cost} /></dd>
            <dt>Approved amount</dt><dd><Money value={c.preauth.approved_amount} /></dd>
            <dt>Reason codes</dt><dd>{c.preauth.reason_codes.join(", ")}</dd>
          </dl>
        </Panel>
        {session?.role === "HOSPITAL" && <HospitalActions detail={c} onChange={refresh} />}
        {session?.role === "INSURER" && <InsurerActions detail={c} onChange={refresh} />}
      </div>
      <div className="grid-2">
        <Panel title="Procedures">
          <ul>{c.procedures.map((p, i) => <li key={i}>{p.procedure_code} — {p.description}</li>)}</ul>
        </Panel>
        <Panel title="Final bills">
          <ul>{c.final_bills.map((b) => <li key={b.version}>v{b.version}: <Money value={b.amount} /> (cap {b.cap})</li>)}</ul>
        </Panel>
      </div>
      {c.settlement && <SettlementBreakdown s={c.settlement} />}
      <Timeline events={timeline.data ?? []} />
    </>
  );
}
