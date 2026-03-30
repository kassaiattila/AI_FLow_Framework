import { test, expect } from "@playwright/test";

// Helper: login as admin before each test
async function login(page: import("@playwright/test").Page, username = "admin") {
  await page.goto("/login");
  await page.fill("#username", username);
  await page.fill("#password", username);
  await page.click('button[type="submit"]');
  await page.waitForURL("/");
}

test.describe("Login", () => {
  test("shows login page when not authenticated", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator("h1")).toContainText("AIFlow");
  });

  test("successful login redirects to dashboard", async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL("/");
    await expect(page.locator("h1")).toContainText("AIFlow");
  });

  test("failed login shows error", async ({ page }) => {
    await page.goto("/login");
    await page.fill("#username", "wrong");
    await page.fill("#password", "wrong");
    await page.click('button[type="submit"]');
    await expect(page.locator(".text-red-600")).toBeVisible();
  });
});

test.describe("Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("loads with skill cards", async ({ page }) => {
    await expect(page.locator("text=Process Documentation")).toBeVisible();
    await expect(page.locator("text=Email Intent Processor")).toBeVisible();
    await expect(page.locator("text=Invoice Processor")).toBeVisible();
  });
});

test.describe("Sidebar Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("navigates to each skill page", async ({ page }) => {
    const skills = [
      { label: "Számlák", url: "/skills/invoice_processor" },
      { label: "Email Intent", url: "/skills/email_intent_processor" },
      { label: "RAG Chat", url: "/skills/aszf_rag_chat" },
      { label: "Diagramok", url: "/skills/process_documentation" },
      { label: "Cubix Kurzus", url: "/skills/cubix_course_capture" },
    ];

    for (const skill of skills) {
      await page.click(`text=${skill.label}`);
      await expect(page).toHaveURL(skill.url);
      // Verify page loads without error
      await expect(page.locator("h2")).toBeVisible();
    }
  });

  test("navigates to costs page", async ({ page }) => {
    await page.click("text=Költségek");
    await expect(page).toHaveURL("/costs");
  });

  test("navigates to runs page", async ({ page }) => {
    await page.click("text=Futások");
    await expect(page).toHaveURL("/runs");
  });
});

test.describe("Skill Pages Load", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("email intent processor loads data", async ({ page }) => {
    await page.goto("/skills/email_intent_processor");
    await expect(page.locator("h2")).toContainText("Email Intent Processor");
    // Should load emails from mock data
    await expect(page.locator("table")).toBeVisible({ timeout: 5000 });
  });

  test("RAG chat loads conversations", async ({ page }) => {
    await page.goto("/skills/aszf_rag_chat");
    await expect(page.locator("h2")).toContainText("ASZF RAG Chat");
  });

  test("process documentation loads", async ({ page }) => {
    await page.goto("/skills/process_documentation");
    await expect(page.locator("h2")).toContainText("Process Documentation");
  });

  test("cubix course capture loads", async ({ page }) => {
    await page.goto("/skills/cubix_course_capture");
    await expect(page.locator("h2")).toContainText("Cubix Course Capture");
  });
});

test.describe("RBAC", () => {
  test("viewer sees role badge", async ({ page }) => {
    await login(page, "viewer");
    await expect(page.locator("text=viewer")).toBeVisible();
  });

  test("admin sees admin badge", async ({ page }) => {
    await login(page, "admin");
    await expect(page.locator("text=admin")).toBeVisible();
  });
});
