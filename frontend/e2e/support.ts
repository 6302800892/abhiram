import { expect, type APIRequestContext, type Page } from "@playwright/test";

// Synthetic seed credentials (seed/seed_data.json). Each journey seeds its own data via the API.
export const PASSWORD = "Demo@1234";
export const USERS = {
  customer: "asha.verma",
  hospital: "cityhosp.desk",
  insurer: "adjudicator.priya",
  admin: "admin.sam",
} as const;

export function isoDate(offsetDays = 0): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export async function token(request: APIRequestContext, username: string): Promise<Record<string, string>> {
  const resp = await request.post("/api/auth/login", { data: { username, password: PASSWORD } });
  expect(resp.ok()).toBeTruthy();
  return { Authorization: `Bearer ${(await resp.json()).token}` };
}

export async function apiPost(request: APIRequestContext, username: string, path: string, data: object) {
  const resp = await request.post(path, { data, headers: await token(request, username) });
  expect(resp.ok(), `${path} -> ${resp.status()} ${await resp.text()}`).toBeTruthy();
  return resp.json();
}

export async function seedPreauth(request: APIRequestContext, diagnosis: string, estimate: string) {
  return apiPost(request, USERS.hospital, "/api/preauths", {
    member_id: "MBR-1001", policy_number: "POL-SLV-0001", diagnosis_code: diagnosis,
    estimated_cost: estimate, expected_admission_date: isoDate(1),
  });
}

export async function seedSettledCase(request: APIRequestContext) {
  const pre = await seedPreauth(request, "I21.9", "100000.00");
  await apiPost(request, USERS.insurer, `/api/preauths/${pre.preauth_id}/decisions`,
    { status: "APPROVED", reason_codes: ["PA-APPROVED-MANUAL"] });
  const c = `/api/cases/${pre.case_id}`;
  await apiPost(request, USERS.hospital, `${c}/admit`, { admitted_on: isoDate(1) });
  await apiPost(request, USERS.hospital, `${c}/final-bill`, { amount: "90000.00" });
  await apiPost(request, USERS.hospital, `${c}/discharge`, { discharged_on: isoDate(3) });
  await apiPost(request, USERS.insurer, `${c}/settle`, {});
  return pre;
}

export async function signIn(page: Page, username: string): Promise<void> {
  await page.goto("/");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Sign in" }).click();
}
