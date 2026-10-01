import { expect, test } from "@playwright/test";
import { signIn, USERS } from "./support";

// Pixel baselines are OS/font dependent, so they are tagged @visual and excluded in CI
// (npm run test:e2e:ci). ARIA snapshots in login/responsive specs are the cross-platform baseline.
test("@visual login page", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveScreenshot("login.png", { fullPage: true });
});

test("@visual hospital workspace (mobile)", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await signIn(page, USERS.hospital);
  await expect(page.getByRole("heading", { name: "Hospital workspace" })).toBeVisible();
  // Static panels only: the case table grows with data and would change the page height.
  await expect(page.locator(".grid-2").first()).toHaveScreenshot("hospital-mobile-panels.png");
});
