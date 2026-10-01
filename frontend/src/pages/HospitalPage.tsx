import { useState, type FormEvent } from "react";
import { api } from "../api";
import { CaseTable } from "../components/CaseTable";
import { ErrorAlert, Field, Panel, StatusBadge } from "../components/ui";
import { useAction, useLoad } from "../hooks";
import type { CaseSummary, PreAuth } from "../types";

interface Eligibility {
  status: string;
  reason_codes: string[];
  remaining_sum_insured: string | null;
}

function EligibilityPanel() {
  const [member, setMember] = useState("");
  const [policy, setPolicy] = useState("");
  const [result, setResult] = useState<Eligibility | null>(null);
  const { busy, error, run } = useAction();

  async function submit(event: FormEvent) {
    event.preventDefault();
    setResult(await run(() => api.post<Eligibility>("/api/eligibility", { member_id: member, policy_number: policy })));
  }

  return (
    <Panel title="Eligibility check">
      <form onSubmit={submit} className="stack">
        <Field label="Member ID" value={member} onChange={(e) => setMember(e.target.value)} required />
        <Field label="Policy number" value={policy} onChange={(e) => setPolicy(e.target.value)} required />
        <button type="submit" disabled={busy}>Check eligibility</button>
      </form>
      <ErrorAlert message={error} />
      {result && (
        <div className="result">
          <StatusBadge status={result.status} testId="eligibility-status" />
          <p>Reason codes: {result.reason_codes.join(", ")}</p>
          {result.remaining_sum_insured && <p>Remaining cover: {result.remaining_sum_insured}</p>}
        </div>
      )}
    </Panel>
  );
}

function PreAuthPanel({ onSubmitted }: { onSubmitted: () => void }) {
  const [form, setForm] = useState({ member_id: "", policy_number: "", diagnosis_code: "", estimated_cost: "",
    expected_admission_date: "", clinical_notes: "" });
  const [result, setResult] = useState<PreAuth | null>(null);
  const { busy, error, run } = useAction();
  const set = (key: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [key]: e.target.value });

  async function submit(event: FormEvent) {
    event.preventDefault();
    const body = { ...form, clinical_notes: form.clinical_notes || undefined };
    const created = await run(() => api.post<PreAuth>("/api/preauths", body));
    if (created) {
      setResult(created);
      onSubmitted();
    }
  }

  return (
    <Panel title="New pre-authorization">
      <form onSubmit={submit} className="stack">
        <Field label="Member ID" value={form.member_id} onChange={set("member_id")} required />
        <Field label="Policy number" value={form.policy_number} onChange={set("policy_number")} required />
        <Field label="Diagnosis code" placeholder="e.g. K35.8" value={form.diagnosis_code} onChange={set("diagnosis_code")} required />
        <Field label="Estimated cost" inputMode="decimal" placeholder="40000.00" value={form.estimated_cost}
          onChange={set("estimated_cost")} required />
        <Field label="Expected admission date" type="date" value={form.expected_admission_date}
          onChange={set("expected_admission_date")} required />
        <Field label="Clinical notes" value={form.clinical_notes} onChange={set("clinical_notes")} />
        <button type="submit" disabled={busy}>Submit pre-auth</button>
      </form>
      <ErrorAlert message={error} />
      {result && (
        <div className="result">
          <p>{result.case_number}: <StatusBadge status={result.status} testId="preauth-status" /></p>
          <p>Reason codes: {result.reason_codes.join(", ")}</p>
          {result.approved_amount && <p>Approved amount: {result.approved_amount}</p>}
        </div>
      )}
    </Panel>
  );
}

export function HospitalPage() {
  const cases = useLoad(() => api.get<CaseSummary[]>("/api/cases"));
  return (
    <>
      <h1>Hospital workspace</h1>
      <div className="grid-2">
        <EligibilityPanel />
        <PreAuthPanel onSubmitted={() => void cases.reload()} />
      </div>
      <Panel title="My cases">
        <ErrorAlert message={cases.error} />
        <CaseTable cases={cases.data ?? []} />
      </Panel>
    </>
  );
}
