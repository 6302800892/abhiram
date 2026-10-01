import { expect, test } from "@playwright/test";
import { signIn, USERS } from "./support";

// pw-001 — login routes each role to its own workspace (NFR-04 role separation in the UI).
const WORKSPACES: Array<[string, string, string]> = [
  [USERS.customer, "My coverage", "/customer"],
  [USERS.hospital, "Hospital workspace", "/hospital"],
  [USERS.insurer, "Adjudication queue", "/insurer"],
  [USERS.admin, "Admin workspace", "/admin"],
];

test("login page structure (ARIA snapshot baseline)", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("main")).toMatchAriaSnapshot({ name: "login-page.aria.yml" });
});

for (const [username, heading, path] of WORKSPACES) {
  test(`pw-001 ${username} lands on ${heading}`, async ({ page }) => {
    await signIn(page, username);
    await expect(page.getByRole("heading", { name: heading, level: 1 })).toBeVisible();
    await expect(page).toHaveURL(new RegExp(`${path}$`));
  });
}

test("wrong password shows an error and stays on login", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill(USERS.hospital);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("alert")).toContainText("invalid username or password");
});

test("NFR-04 a hospital user cannot open the admin workspace", async ({ page }) => {
  await signIn(page, USERS.hospital);
  await expect(page.getByRole("heading", { name: "Hospital workspace" })).toBeVisible();
  await page.goto("/admin");
  await expect(page.getByRole("heading", { name: "Hospital workspace" })).toBeVisible();
});

test("sign out clears the session", async ({ page }) => {
  await signIn(page, USERS.customer);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await page.goto("/customer");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
});
