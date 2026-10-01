import { expect, test } from "@playwright/test";
import { seedPreauth, signIn, USERS } from "./support";

test("AC-04 adjudicator approves a pending pre-auth from the queue", async ({ page, request }) => {
  const pre = await seedPreauth(request, "I21.9", "80000.00");
  await signIn(page, USERS.insurer);
  const queue = page.getByRole("region", { name: "Pending pre-authorizations" });
  const row = queue.getByRole("row").filter({ hasText: pre.case_number });
  await expect(row).toBeVisible();
  await row.getByLabel("Decision").selectOption("APPROVED");
  await row.getByLabel("Reason code").selectOption("PA-APPROVED-MANUAL");
  await row.getByRole("button", { name: "Record decision" }).click();
  await expect(page.getByRole("status")).toContainText("APPROVED");
  await expect(queue.getByRole("row").filter({ hasText: pre.case_number })).toHaveCount(0);
});

test("reports are visible to the adjudicator", async ({ page }) => {
  await signIn(page, USERS.insurer);
  const reports = page.getByRole("region", { name: "Reports" });
  await expect(reports).toContainText("Average loss ratio");
  await expect(reports).toContainText("Pre-auth turnaround");
});

test("AC-10 admin overrides an auto-rejected pre-auth and the audit log records it", async ({ page, request }) => {
  const pre = await seedPreauth(request, "Z41.1", "10000.00");
  expect(pre.status).toBe("REJECTED");
  await signIn(page, USERS.admin);
  await expect(page.getByRole("heading", { name: "Admin workspace" })).toBeVisible();
  const row = page.getByRole("region", { name: "Overrides" }).getByRole("row").filter({ hasText: pre.case_number });
  await row.getByLabel("Override decision").selectOption("APPROVED");
  await row.getByLabel("Override reason").fill("Reconstructive surgery after accident");
  await row.getByRole("button", { name: "Override" }).click();
  await expect(page.getByRole("status")).toContainText("APPROVED");
  const audit = page.getByRole("region", { name: "Audit log" });
  await expect(audit).toContainText("PREAUTH_OVERRIDE");
  await expect(audit).toContainText("admin.sam");
  await expect(audit).toContainText("Reconstructive surgery after accident");
});

test("admin can take a hospital out of the network", async ({ page }) => {
  await signIn(page, USERS.admin);
  const row = page.getByRole("region", { name: "Network hospitals" }).getByRole("row").filter({ hasText: "LAKEVIEW" });
  await row.getByRole("button", { name: "Remove from network" }).click();
  await expect(row.getByRole("button", { name: "Add to network" })).toBeVisible();
  await row.getByRole("button", { name: "Add to network" }).click();
  await expect(row.getByRole("button", { name: "Remove from network" })).toBeVisible();
});
