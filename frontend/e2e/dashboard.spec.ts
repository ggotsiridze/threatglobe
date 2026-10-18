import { expect, type Page, test } from "@playwright/test";

const statValue = (page: Page, id: string) => page.getByTestId(`stat-${id}`).locator(".stat-value");
const toInt = (s: string | null) => Number((s ?? "").replace(/[^0-9]/g, ""));

test.describe("ThreatGlobe demo dashboard", () => {
  let errors: string[];
  let attackFrames: number;

  test.beforeEach(async ({ page }) => {
    errors = [];
    attackFrames = 0;
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(`console.error: ${m.text()}`);
    });
    page.on("websocket", (ws) => {
      ws.on("framereceived", (f) => {
        if (typeof f.payload === "string" && f.payload.startsWith('{"type":"attack"')) attackFrames += 1;
      });
    });
    await page.goto("/");
  });

  test.afterEach(() => {
    expect(errors, "no fatal browser errors").toEqual([]);
  });

  test("loads, renders the globe, streams attacks and updates counters", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /watching cyber attacks around the world/i })).toBeVisible();
    await expect(page.getByTestId("status-indicator")).toHaveText("DEMO", { timeout: 15_000 });
    await expect(page.getByText("DEMO DATA").first()).toBeVisible();

    // Globe: a WebGL canvas exists, has real size and is not blank.
    const canvas = page.getByTestId("globe").locator("canvas").first();
    await expect(canvas).toBeVisible({ timeout: 20_000 });
    const box = (await canvas.boundingBox())!;
    expect(box.width).toBeGreaterThan(300);
    const hasWebGL = await canvas.evaluate((c: HTMLCanvasElement) => !!(c.getContext("webgl2") || c.getContext("webgl")));
    expect(hasWebGL).toBe(true);
    const shotA = await canvas.screenshot();
    expect(shotA.byteLength).toBeGreaterThan(20_000); // a blank canvas compresses to almost nothing

    // Counters, arcs, feed and WebSocket traffic all change over time.
    const before = toInt(await statValue(page, "events").textContent());
    const firstFeedBefore = await page.getByTestId("feed-item").first().getAttribute("aria-label");
    let maxArcs = 0;
    let feedChanged = false;
    for (let i = 0; i < 24 && !(maxArcs > 0 && feedChanged && attackFrames >= 3); i++) {
      await page.waitForTimeout(500);
      maxArcs = Math.max(maxArcs, Number(await page.getByTestId("globe").getAttribute("data-arcs")));
      const label = await page.getByTestId("feed-item").first().getAttribute("aria-label");
      feedChanged ||= label !== firstFeedBefore;
    }
    expect(attackFrames, "attack messages over WebSocket").toBeGreaterThanOrEqual(3);
    expect(maxArcs, "attack arcs in flight").toBeGreaterThan(0);
    expect(feedChanged, "live feed updated").toBe(true);
    const after = toInt(await statValue(page, "events").textContent());
    expect(after).toBeGreaterThan(before);

    // The globe animates (auto-rotation + arcs): pixels change between frames.
    const shotB = await canvas.screenshot();
    expect(Buffer.compare(shotA, shotB)).not.toBe(0);

    for (const id of ["top-countries", "top-ports", "top-honeypots", "timeline"]) {
      await expect(page.getByTestId(id)).toBeVisible();
    }
    await expect(page.getByTestId("timeline").locator(".recharts-area").first()).toBeVisible();
  });

  test("clicking an attack opens the detail drawer with masked data", async ({ page }) => {
    await page.getByTestId("feed-item").first().click();
    const drawer = page.getByTestId("attack-drawer");
    await expect(drawer).toBeVisible();
    for (const label of ["Timestamp", "Source IP", "Country", "City", "ASN", "Organization", "Protocol", "Target port",
      "Honeypot", "Username", "Password", "Event type", "Risk rating"]) {
      await expect(drawer).toContainText(label);
    }
    const ip = await drawer.locator(".kv-row", { hasText: "Source IP" }).locator("dd").textContent();
    expect(ip).toMatch(/^(\d+\.\d+\.\*\.\*|—)$/);
    await expect(drawer).toContainText(/LOW|MEDIUM|HIGH|CRITICAL/);
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });

  test("replay plays chronologically and the controls work", async ({ page }) => {
    await page.getByRole("tab", { name: "Replay" }).click();
    const position = page.getByTestId("replay-position");
    await expect(position).toHaveText(/^\d+\/[1-9]\d*/, { timeout: 15_000 });
    await expect(page.getByTestId("replay-pause")).toBeVisible(); // autoplay started

    await page.getByRole("button", { name: "10x" }).click();
    await page.waitForTimeout(2500);
    const progress = () => position.textContent().then((t) => Number(t!.split("/")[0]));
    const p1 = await progress();
    expect(p1).toBeGreaterThan(0);

    // Feed in replay shows events newest-first => timestamps descend down the list.
    const times = await page.getByTestId("feed-item").locator(".feed-time").allTextContents();
    expect(times.length).toBeGreaterThan(1);
    expect([...times].sort().reverse()).toEqual(times);

    await page.getByTestId("replay-pause").click();
    const paused = await progress();
    await page.waitForTimeout(1500);
    expect(await progress()).toBe(paused);

    await page.getByTestId("replay-play").click();
    await page.waitForTimeout(1500);
    expect(await progress()).toBeGreaterThan(paused);

    await page.getByTestId("replay-restart").click();
    expect(await progress()).toBeLessThan(paused);

    for (const s of ["1x", "2x", "5x"]) {
      await page.getByRole("button", { name: s }).click();
      await expect(page.getByRole("button", { name: s })).toHaveAttribute("aria-pressed", "true");
    }
    await page.getByRole("tab", { name: "Live stream" }).click();
    await expect(page.getByTestId("replay-controls")).toBeHidden();
  });
});
