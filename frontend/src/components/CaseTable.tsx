import { Link } from "react-router-dom";
import type { CaseSummary } from "../types";
import { StatusBadge } from "./ui";

export function CaseTable({ cases }: { cases: CaseSummary[] }) {
  if (cases.length === 0) return <p className="muted">No cases yet.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr><th>Case</th><th>Member</th><th>Hospital</th><th>Status</th></tr>
        </thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.case_id}>
              <td><Link to={`/cases/${c.case_id}`}>{c.case_number}</Link></td>
              <td>{c.member_name} ({c.member_id})</td>
              <td>{c.hospital_name}</td>
              <td><StatusBadge status={c.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
