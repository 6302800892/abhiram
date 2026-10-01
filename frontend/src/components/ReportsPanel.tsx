import { api } from "../api";
import { useLoad } from "../hooks";
import { ErrorAlert, Money, Panel } from "./ui";

interface Summary {
  preauth_turnaround_hours: string | null;
  settlement_volume: { count: number; total_amount: string };
  query_rate_by_hospital: Array<{ hospital_code: string; preauths: number; queried: number; rate: string }>;
  top_diagnoses: Array<{ diagnosis_code: string; label: string; count: number }>;
  loss_ratio_by_product: Array<{ product_code: string; settled_amount: string; premium_total: string; loss_ratio: string }>;
  average_loss_ratio: string | null;
}

export function ReportsPanel() {
  const { data, error } = useLoad(() => api.get<Summary>("/api/reports/summary"));
  return (
    <Panel title="Reports">
      <ErrorAlert message={error} />
      {data && (
        <>
          <dl className="facts kpis">
            <dt>Pre-auth turnaround</dt><dd>{data.preauth_turnaround_hours ?? "—"} h</dd>
            <dt>Settlements</dt><dd>{data.settlement_volume.count} · <Money value={data.settlement_volume.total_amount} /></dd>
            <dt>Average loss ratio</dt><dd>{data.average_loss_ratio ?? "—"}</dd>
          </dl>
          <div className="grid-2">
            <div className="table-wrap">
              <table>
                <caption>Query rate by hospital</caption>
                <thead><tr><th>Hospital</th><th>Pre-auths</th><th>Queried</th><th>Rate</th></tr></thead>
                <tbody>
                  {data.query_rate_by_hospital.map((h) => (
                    <tr key={h.hospital_code}><td>{h.hospital_code}</td><td>{h.preauths}</td><td>{h.queried}</td><td>{h.rate}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-wrap">
              <table>
                <caption>Top diagnoses</caption>
                <thead><tr><th>Code</th><th>Diagnosis</th><th>Count</th></tr></thead>
                <tbody>
                  {data.top_diagnoses.map((d) => (
                    <tr key={d.diagnosis_code}><td>{d.diagnosis_code}</td><td>{d.label}</td><td>{d.count}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <caption>Loss ratio by product</caption>
              <thead><tr><th>Product</th><th>Settled</th><th>Premiums</th><th>Loss ratio</th></tr></thead>
              <tbody>
                {data.loss_ratio_by_product.map((p) => (
                  <tr key={p.product_code}>
                    <td>{p.product_code}</td><td><Money value={p.settled_amount} /></td>
                    <td><Money value={p.premium_total} /></td><td>{p.loss_ratio}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  );
}
