import { useState, type FormEvent } from "react";
import { api } from "../api";
import { useAction } from "../hooks";
import type { CaseDetail } from "../types";
import { ErrorAlert, Field, Panel } from "./ui";

interface Props {
  detail: CaseDetail;
  onChange: () => void;
}

const today = () => new Date().toISOString().slice(0, 10);

/** Hospital-side case updates (AC-06 / AC-08). The server enforces every rule; the UI only offers them. */
export function HospitalActions({ detail, onChange }: Props) {
  const { busy, error, run } = useAction();
  const [admittedOn, setAdmittedOn] = useState(today());
  const [dischargedOn, setDischargedOn] = useState(today());
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [bill, setBill] = useState("");
  const base = `/api/cases/${detail.case_id}`;

  const act = (path: string, body: object, after?: () => void) => async (event: FormEvent) => {
    event.preventDefault();
    if (await run(() => api.post(`${base}/${path}`, body))) {
      after?.();
      onChange();
    }
  };
  const status = detail.status;

  return (
    <Panel title="Hospital actions">
      <ErrorAlert message={error} />
      {status === "PRE_AUTH" && (
        <form onSubmit={act("admit", { admitted_on: admittedOn })} className="stack">
          <Field label="Admission date" type="date" value={admittedOn} onChange={(e) => setAdmittedOn(e.target.value)} />
          <button type="submit" disabled={busy}>Admit patient</button>
        </form>
      )}
      {status === "ADMITTED" && (
        <form onSubmit={act("procedures", { procedure_code: code, description }, () => { setCode(""); setDescription(""); })}
          className="stack">
          <Field label="Procedure code" value={code} onChange={(e) => setCode(e.target.value)} required />
          <Field label="Procedure description" value={description} onChange={(e) => setDescription(e.target.value)} required />
          <button type="submit" disabled={busy}>Add procedure</button>
        </form>
      )}
      {(status === "ADMITTED" || status === "DISCHARGED") && (
        <form onSubmit={act("final-bill", { amount: bill }, () => setBill(""))} className="stack">
          <Field label="Final bill amount" inputMode="decimal" placeholder="90000.00" value={bill}
            onChange={(e) => setBill(e.target.value)} required />
          <button type="submit" disabled={busy}>Submit final bill</button>
        </form>
      )}
      {status === "ADMITTED" && (
        <form onSubmit={act("discharge", { discharged_on: dischargedOn })} className="stack">
          <Field label="Discharge date" type="date" value={dischargedOn} onChange={(e) => setDischargedOn(e.target.value)} />
          <button type="submit" disabled={busy}>Discharge patient</button>
        </form>
      )}
      {!["PRE_AUTH", "ADMITTED", "DISCHARGED"].includes(status) && <p className="muted">No hospital actions in {status}.</p>}
    </Panel>
  );
}

/** Insurer-side settlement actions (AC-07 / AC-08). */
export function InsurerActions({ detail, onChange }: Props) {
  const { busy, error, run } = useAction();
  const [reason, setReason] = useState("");
  const base = `/api/cases/${detail.case_id}`;
  const post = (path: string, body: object = {}) => async () => {
    if (await run(() => api.post(`${base}/${path}`, body))) onChange();
  };
  const status = detail.status;

  return (
    <Panel title="Insurer actions">
      <ErrorAlert message={error} />
      {(status === "DISCHARGED" || status === "DISPUTED") && (
        <button type="button" disabled={busy} onClick={() => void post("settle")()}>Settle case</button>
      )}
      {status === "DISCHARGED" && (
        <div className="stack">
          <Field label="Dispute reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button type="button" className="secondary" disabled={busy || !reason}
            onClick={() => void post("dispute", { reason })()}>Raise dispute</button>
        </div>
      )}
      {(status === "SETTLED" || status === "DISPUTED") && (
        <button type="button" className="secondary" disabled={busy} onClick={() => void post("close")()}>Close case</button>
      )}
    </Panel>
  );
}
