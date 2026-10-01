import { expect, test } from "@playwright/test";
import { seedSettledCase, signIn, USERS } from "./support";

test("AC-01 customer sees sum insured, exclusions and network hospitals", async ({ page }) => {
  await signIn(page, USERS.customer);
  await expect(page.getByRole("heading", { name: "My coverage" })).toBeVisible();
  const policy = page.getByRole("region", { name: "Policy POL-SLV-0001" });
  await expect(policy).toContainText("500000.00");
  await expect(policy).toContainText("Cosmetic surgery");
  const network = page.getByRole("region", { name: "Network hospitals" });
  await expect(network).toContainText("City Care Hospital");
  await expect(network).not.toContainText("Greenfield Clinic");
});

test("AC-07/AC-09 customer sees the timeline, notifications and settlement breakdown", async ({ page, request }) => {
  const pre = await seedSettledCase(request);
  await signIn(page, USERS.customer);
  await expect(page.getByRole("region", { name: "Notifications" })).toContainText(`${pre.case_number}: your cashless case status is now SETTLED`);
  await page.getByRole("link", { name: pre.case_number }).click();
  await expect(page.getByTestId("case-status")).toHaveText("SETTLED");
  const timeline = page.getByRole("region", { name: "Timeline" });
  for (const status of ["PENDING", "APPROVED", "ADMITTED", "DISCHARGED", "SETTLED"]) {
    await expect(timeline).toContainText(status);
  }
  const settlement = page.getByRole("region", { name: "Settlement" });
  await expect(settlement).toContainText("100000.00"); // pre-auth amount
  await expect(settlement).toContainText("90000.00"); // final bill
  await expect(settlement).toContainText("5000.00"); // deductible
  await expect(settlement).toContainText("8500.00"); // co-pay
  await expect(settlement.getByTestId("paid-amount")).toHaveText("76500.00");
});
