// Response shapes of the MediCard API (money is always a decimal string from the server, NFR-01).

export type Role = "CUSTOMER" | "HOSPITAL" | "INSURER" | "ADMIN";

export interface Session {
  token: string;
  role: Role;
  username: string;
  display_name: string;
}

export interface Decision {
  seq: number;
  status: string;
  approved_amount: string | null;
  reason_codes: string[];
  decided_by: string;
  decided_at: string;
}

export interface PreAuth {
  preauth_id: number;
  case_id: number;
  case_number: string;
  case_status: string;
  hospital_code: string;
  member_id: string;
  policy_number: string;
  diagnosis_code: string;
  diagnosis_label: string;
  estimated_cost: string;
  status: string;
  approved_amount: string | null;
  reason_codes: string[];
  decisions: Decision[];
}

export interface CaseSummary {
  case_id: number;
  case_number: string;
  status: string;
  hospital_code: string;
  hospital_name: string;
  member_id: string;
  member_name: string;
  policy_number: string;
}

export interface Settlement {
  pre_auth_amount: string;
  buffer_pct: string;
  cap: string;
  final_bill: string;
  admissible: string;
  deductible: string;
  copay: string;
  settlement_amount: string;
  payment_reference: string;
  settled_at: string;
}

export interface CaseDetail extends CaseSummary {
  preauth: Pick<PreAuth, "preauth_id" | "status" | "estimated_cost" | "approved_amount" | "diagnosis_code" | "reason_codes">;
  procedures: Array<{ procedure_code: string; description: string; recorded_at: string }>;
  final_bills: Array<{ version: number; amount: string; cap: string; submitted_at: string }>;
  settlement: Settlement | null;
}

export interface TimelineEvent {
  event_type: string;
  from_status: string | null;
  to_status: string | null;
  actor: string;
  occurred_at: string;
  event_date: string | null;
  note: string | null;
}

export interface QueueItem {
  preauth_id: number;
  case_id: number;
  case_number: string;
  hospital_code: string;
  member_id: string;
  diagnosis_code: string;
  estimated_cost: string;
  age_hours: string;
}

export interface Hospital {
  code: string;
  name: string;
  city: string;
  in_network: boolean;
}
