import { expect, test } from "@playwright/test";
import { apiPost, isoDate, seedPreauth, signIn, USERS } from "./support";

test.beforeEach(async ({ page }) => {
  await signIn(page, USERS.hospital);
  await expect(page.getByRole("heading", { name: "Hospital workspace" })).toBeVisible();
});

test("AC-02 eligibility lookup shows ELIGIBLE and NOT_ELIGIBLE with reason codes", async ({ page }) => {
  const panel = page.getByRole("region", { name: "Eligibility check" });
  await panel.getByLabel("Member ID").fill("MBR-1001");
  await panel.getByLabel("Policy number").fill("POL-SLV-0001");
  await panel.getByRole("button", { name: "Check eligibility" }).click();
  await expect(panel.getByTestId("eligibility-status")).toHaveText("ELIGIBLE");
  await expect(panel).toContainText("ELG-OK");

  await panel.getByLabel("Member ID").fill("MBR-3001");
  await panel.getByLabel("Policy number").fill("POL-SLV-0003");
  await panel.getByRole("button", { name: "Check eligibility" }).click();
  await expect(panel.getByTestId("eligibility-status")).toHaveText("NOT_ELIGIBLE");
  await expect(panel).toContainText("ELG-POLICY-INACTIVE");
  await expect(panel).toContainText("ELG-OUTSIDE-COVER-PERIOD");
});

test("AC-03/AC-05 pre-auth submission shows the auto-decision", async ({ page }) => {
  const panel = page.getByRole("region", { name: "New pre-authorization" });
  await panel.getByLabel("Member ID").fill("MBR-1001");
  await panel.getByLabel("Policy number").fill("POL-SLV-0001");
  await panel.getByLabel("Diagnosis code").fill("K35.8");
  await panel.getByLabel("Estimated cost").fill("40000.00");
  await panel.getByLabel("Expected admission date").fill(isoDate(1));
  await panel.getByRole("button", { name: "Submit pre-auth" }).click();
  await expect(panel.getByTestId("preauth-status")).toHaveText("APPROVED");
  await expect(panel).toContainText("PA-AUTO-APPROVED");
});

test("AC-06/AC-08 hospital runs a case from admission to discharge", async ({ page, request }) => {
  const pre = await seedPreauth(request, "I21.9", "100000.00");
  await apiPost(request, USERS.insurer, `/api/preauths/${pre.preauth_id}/decisions`,
    { status: "APPROVED", reason_codes: ["PA-APPROVED-MANUAL"] });
  await page.reload();
  await page.getByRole("link", { name: pre.case_number }).click();
  await expect(page.getByRole("heading", { name: pre.case_number })).toBeVisible();
  await expect(page.getByTestId("case-status")).toHaveText("PRE_AUTH");

  await page.getByLabel("Admission date").fill(isoDate(1));
  await page.getByRole("button", { name: "Admit patient" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("ADMITTED");

  await page.getByLabel("Procedure code").fill("02703ZZ");
  await page.getByLabel("Procedure description").fill("Coronary angioplasty");
  await page.getByRole("button", { name: "Add procedure" }).click();
  await expect(page.getByRole("region", { name: "Procedures" })).toContainText("02703ZZ");

  await page.getByLabel("Final bill amount").fill("110000.01");
  await page.getByRole("button", { name: "Submit final bill" }).click();
  await expect(page.getByRole("alert")).toContainText("BILL_EXCEEDS_CAP");

  await page.getByLabel("Final bill amount").fill("90000.00");
  await page.getByRole("button", { name: "Submit final bill" }).click();
  await expect(page.getByRole("region", { name: "Final bills" })).toContainText("90000.00");

  await page.getByLabel("Discharge date").fill(isoDate(3));
  await page.getByRole("button", { name: "Discharge patient" }).click();
  await expect(page.getByTestId("case-status")).toHaveText("DISCHARGED");
  await expect(page.getByRole("region", { name: "Timeline" })).toContainText("DISCHARGED");
});
