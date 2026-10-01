import { api } from "../api";
import { CaseTable } from "../components/CaseTable";
import { ErrorAlert, Money, Panel } from "../components/ui";
import { useLoad } from "../hooks";
import type { CaseSummary } from "../types";

interface PolicyCoverage {
  policy_number: string;
  product_name: string;
  status: string;
  cover_start: string;
  cover_end: string;
  sum_insured: string;
  remaining_sum_insured: string;
  member_id: string;
  member_name: string;
  exclusions: Array<{ code: string; label: string }>;
}

interface Coverage {
  policies: PolicyCoverage[];
  network_hospitals: Array<{ code: string; name: string; city: string }>;
}

interface Notification {
  case_id: number;
  message: string;
  created_at: string;
}

function PolicyCard({ p }: { p: PolicyCoverage }) {
  return (
    <Panel title={`Policy ${p.policy_number}`}>
      <dl className="facts">
        <dt>Plan</dt><dd>{p.product_name} ({p.status})</dd>
        <dt>Member</dt><dd>{p.member_name} · {p.member_id}</dd>
        <dt>Cover period</dt><dd>{p.cover_start} → {p.cover_end}</dd>
        <dt>Sum insured</dt><dd><Money value={p.sum_insured} /></dd>
        <dt>Remaining</dt><dd><Money value={p.remaining_sum_insured} /></dd>
      </dl>
      <h3>Exclusions</h3>
      <ul>{p.exclusions.map((x) => <li key={x.code}>{x.label} ({x.code})</li>)}</ul>
    </Panel>
  );
}

export function CustomerPage() {
  const coverage = useLoad(() => api.get<Coverage>("/api/customers/me/coverage"));
  const cases = useLoad(() => api.get<CaseSummary[]>("/api/cases"));
  const notes = useLoad(() => api.get<Notification[]>("/api/customers/me/notifications"));
  return (
    <>
      <h1>My coverage</h1>
      <ErrorAlert message={coverage.error ?? cases.error ?? notes.error} />
      <div className="grid-2">
        {(coverage.data?.policies ?? []).map((p) => <PolicyCard key={p.policy_number} p={p} />)}
        <Panel title="Network hospitals">
          <ul>{(coverage.data?.network_hospitals ?? []).map((h) => <li key={h.code}>{h.name}, {h.city}</li>)}</ul>
        </Panel>
      </div>
      <Panel title="My cases">
        <CaseTable cases={cases.data ?? []} />
      </Panel>
      <Panel title="Notifications">
        <ol className="feed">
          {[...(notes.data ?? [])].reverse().map((n, i) => (
            <li key={`${n.case_id}-${i}`}><time>{n.created_at}</time> {n.message}</li>
          ))}
        </ol>
      </Panel>
    </>
  );
}
