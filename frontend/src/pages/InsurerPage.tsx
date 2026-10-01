import { useState } from "react";
import { api } from "../api";
import { CaseTable } from "../components/CaseTable";
import { ReportsPanel } from "../components/ReportsPanel";
import { ErrorAlert, Field, Notice, Panel, SelectField } from "../components/ui";
import { useAction, useLoad } from "../hooks";
import type { CaseSummary, PreAuth, QueueItem } from "../types";

const DECISIONS = ["APPROVED", "PARTIALLY_APPROVED", "REJECTED", "QUERY_RAISED"];
const MANUAL_REASONS = ["PA-APPROVED-MANUAL", "PA-PARTIAL-MANUAL", "PA-REJECTED-MANUAL", "PA-QUERY-DOCUMENTS"];

function DecisionRow({ item, onDone }: { item: QueueItem; onDone: (p: PreAuth) => void }) {
  const [status, setStatus] = useState(DECISIONS[0]);
  const [reason, setReason] = useState(MANUAL_REASONS[0]);
  const [amount, setAmount] = useState("");
  const { busy, error, run } = useAction();

  async function record() {
    const body = { status, reason_codes: [reason], approved_amount: status === "PARTIALLY_APPROVED" ? amount : undefined };
    const result = await run(() => api.post<PreAuth>(`/api/preauths/${item.preauth_id}/decisions`, body));
    if (result) onDone(result);
  }

  return (
    <tr>
      <td>{item.case_number}</td>
      <td>{item.hospital_code}</td>
      <td>{item.diagnosis_code}</td>
      <td className="num">{item.estimated_cost}</td>
      <td className="num">{item.age_hours} h</td>
      <td className="decide">
        <SelectField label="Decision" options={DECISIONS} value={status} onChange={(e) => setStatus(e.target.value)} />
        <SelectField label="Reason code" options={MANUAL_REASONS} value={reason} onChange={(e) => setReason(e.target.value)} />
        {status === "PARTIALLY_APPROVED" && (
          <Field label="Approved amount" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)} />
        )}
        <button type="button" disabled={busy} onClick={() => void record()}>Record decision</button>
        <ErrorAlert message={error} />
      </td>
    </tr>
  );
}

export function InsurerPage() {
  const queue = useLoad(() => api.get<QueueItem[]>("/api/adjudication/queue"));
  const cases = useLoad(() => api.get<CaseSummary[]>("/api/cases"));
  const [notice, setNotice] = useState<string | null>(null);

  function decided(p: PreAuth) {
    setNotice(`${p.case_number} is now ${p.status}`);
    void queue.reload();
    void cases.reload();
  }

  return (
    <>
      <h1>Adjudication queue</h1>
      <Notice message={notice} />
      <ErrorAlert message={queue.error} />
      <Panel title="Pending pre-authorizations">
        {(queue.data ?? []).length === 0 ? <p className="muted">Queue is empty.</p> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Case</th><th>Hospital</th><th>Diagnosis</th><th>Estimate</th><th>Age</th><th>Decision</th></tr></thead>
              <tbody>{(queue.data ?? []).map((q) => <DecisionRow key={q.preauth_id} item={q} onDone={decided} />)}</tbody>
            </table>
          </div>
        )}
      </Panel>
      <Panel title="All cases">
        <CaseTable cases={cases.data ?? []} />
      </Panel>
      <ReportsPanel />
    </>
  );
}
