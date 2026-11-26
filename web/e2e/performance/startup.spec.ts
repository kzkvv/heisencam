import { readFileSync } from "node:fs";
import type { Page } from "@playwright/test";
import { expect, test } from "../fixtures/frigate-test";
import { noSessionStatus } from "../fixtures/mock-data/debug-replay";
import { ReviewPage } from "../pages/review.page";

const snapshotPath = /\/api\/[^/]+\/latest\.(jpg|webp)$/;
const editorAsset = /\/assets\/(ConfigEditor|editor\.main|yaml\.worker)[-.]/;
const eventPlayback = /\/vod\/|\/assets\/(EventClip|GenericVideoPlayer)-/;
const eventTracking =
  /\/api\/(timeline|[^/]+\/recordings)$|\/assets\/TrackingDetails-/;

test.beforeEach(async ({ frigateApp }) => {
  // A configured asset server is allowed, but the fixture must not consume its live streams.
  await frigateApp.page.routeWebSocket("**/live/**", () => {});
});

function collectPaths(page: Page) {
  const paths: string[] = [];
  page.on("request", (request) => paths.push(new URL(request.url()).pathname));
  return paths;
}

// Decoded bytes make the budget independent of the local server's compression.
function scriptBytes(page: Page) {
  return page.evaluate(() =>
    (performance.getEntriesByType("resource") as PerformanceResourceTiming[])
      .filter((entry) => new URL(entry.name).pathname.endsWith(".js"))
      .reduce((total, entry) => total + entry.decodedBodySize, 0),
  );
}

async function expectScriptBudget(page: Page, limitKiB: number) {
  const bytes = await scriptBytes(page);
  expect(bytes).toBeGreaterThan(0);
  expect(bytes).toBeLessThan(limitKiB * 1024);
}

test("Cameras uses a separate startup bundle and still requests visible images", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  await frigateApp.goto("/");
  await expect(
    page.locator("article [data-camera=front_door]").first(),
  ).toBeVisible();
  await expect
    .poll(() => paths.some((path) => snapshotPath.test(path)))
    .toBe(true);
  expect(paths.filter((path) => path === "/api/profile")).toHaveLength(1);
  expect(
    paths.filter((path) => /\/assets\/Live(Camera|Birdseye)View-/.test(path)),
  ).toEqual([]);
  expect(paths.filter((path) => editorAsset.test(path))).toEqual([]);
  expect(
    paths.filter((path) => /\/assets\/(Events|Replay)-/.test(path)),
  ).toEqual([]);
  await expectScriptBudget(page, 2700);
});

test("a direct camera link starts the player without a dashboard or still image", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  await frigateApp.goto("/#front_door");
  await expect(
    page.locator("#pageRoot [data-camera=front_door]"),
  ).toBeVisible();
  await expect(page.locator("#pageRoot [aria-label='Loading…']")).toBeVisible();
  await expect(page.locator("#pageRoot article")).toHaveCount(0);
  expect(paths.filter((path) => snapshotPath.test(path))).toEqual([]);
  expect(
    paths.filter((path) => path.includes("/assets/LiveDashboardView-")),
  ).toEqual([]);
});

test("Birdseye starts without fetching camera thumbnails or the camera grid", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  await frigateApp.goto("/#birdseye");
  await expect(
    page.locator("#pageRoot canvas, #pageRoot video"),
  ).not.toHaveCount(0);
  expect(paths.filter((path) => snapshotPath.test(path))).toEqual([]);
  expect(
    paths.filter((path) => path.includes("/assets/LiveDashboardView-")),
  ).toEqual([]);
  await expectScriptBudget(page, 2300);
});

test("Settings defers config schema, raw paths and form code until needed", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  const schema = JSON.parse(
    readFileSync(
      new URL("../fixtures/mock-data/config-schema.json", import.meta.url),
      "utf8",
    ),
  );
  await page.route("**/api/config/schema.json", (route) =>
    route.fulfill({ json: schema }),
  );
  await frigateApp.goto("/settings");
  await expect(page.locator("#show-camera-groups-desktop")).toBeVisible();
  expect(
    paths.filter((path) =>
      /\/api\/config\/(schema\.json|raw_paths)$/.test(path),
    ),
  ).toEqual([]);
  expect(
    paths.filter(
      (path) =>
        editorAsset.test(path) ||
        path.includes("/assets/ConfigSectionTemplate-"),
    ),
  ).toEqual([]);
  await expectScriptBudget(page, 2400);

  await page.evaluate(async () => {
    await document.fonts.ready;
  });
  await frigateApp.goto("/settings?page=globalDetect&camera=front_door");
  await expect(page.locator("#pageRoot form").first()).toBeVisible();
  expect(paths).toContain("/api/config/schema.json");
});

test("Config starts fetching YAML while the Monaco module is still in flight", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const requests = collectPaths(page);
  let releaseModule!: () => void;
  const held = new Promise<void>((resolve) => {
    releaseModule = resolve;
  });

  await page.route(/\/assets\/editor\.main-.*\.js$/, async (route) => {
    await held;
    await route.continue();
  });

  try {
    await page.goto("/config", { waitUntil: "domcontentloaded" });
    await expect.poll(() => requests.includes("/api/config/raw")).toBe(true);
    await expect
      .poll(() => requests.some((path) => /\/assets\/editor\.main-/.test(path)))
      .toBe(true);
    await expect(page.locator(".monaco-editor .view-lines")).toHaveCount(0);
  } finally {
    releaseModule();
  }

  await expect(page.locator(".monaco-editor .view-lines")).toBeVisible({
    timeout: 15_000,
  });
  const shell = await page.evaluate(() =>
    (performance.getEntriesByType("resource") as PerformanceResourceTiming[])
      .filter((entry) => /\/assets\/ConfigEditor-.*\.js$/.test(entry.name))
      .reduce((sum, entry) => sum + entry.decodedBodySize, 0),
  );
  expect(shell).toBeGreaterThan(0);
  expect(shell).toBeLessThan(128 * 1024);
});

test("Storage does not start loading the General statistics view", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  await page.route("**/api/recordings/storage", (route) =>
    route.fulfill({
      json: { front_door: { usage: 20, usage_percent: 0.1, bandwidth: 2 } },
    }),
  );
  const storage = page.waitForResponse("**/api/recordings/storage");
  const summary = page.waitForResponse("**/api/recordings/summary?*");
  await frigateApp.goto("/system#storage");
  await expect(
    page.getByRole("radio", { name: "Select storage" }),
  ).toHaveAttribute("data-state", "on");
  await Promise.all([
    storage,
    summary,
    page.evaluate(() => document.fonts.ready.then(() => {})),
  ]);
  expect(paths).not.toContain("/api/stats/history");
  expect(
    paths.filter((path) => path.includes("/assets/GeneralMetrics-")),
  ).toEqual([]);
  await frigateApp.goto("/system");
  await expect(
    page.getByRole("radio", { name: "Select general" }),
  ).toHaveAttribute("data-state", "on");
});

test("Review keeps recordings and motion search code out of its list views", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  const review = new ReviewPage(page, true);
  await frigateApp.goto("/review");
  await expect(review.alertsTab).toHaveAttribute("data-state", "on");
  await review.motionTab.click();
  await expect(review.motionTab).toHaveAttribute("data-state", "on");
  expect(
    paths.filter((path) =>
      /\/assets\/(RecordingView|MotionSearchView)-/.test(path),
    ),
  ).toEqual([]);
});

test("Replay skips the configuration editor without an active session", async ({
  frigateApp,
}) => {
  const { page } = frigateApp;
  const paths = collectPaths(page);
  await page.route("**/api/debug_replay/status", (route) =>
    route.fulfill({ json: noSessionStatus() }),
  );
  await frigateApp.goto("/replay");
  await expect(
    page.getByRole("heading", { name: /No Active Debug Replay Session/i }),
  ).toBeVisible();
  expect(
    paths.filter((path) => path.includes("/assets/DebugReplayConfigSheet-")),
  ).toEqual([]);
});

test.describe("Classic events media budgets", () => {
  // Switching tabs or leaving the page cancels in-flight image and playlist requests.
  test.use({
    expectedErrors: [
      /^failed: net::ERR_ABORTED https?:\/\/[^/]+\/(?:vod\/|api\/events\/[^/]+\/snapshot\.jpg)/,
    ],
  });

  test("Events only requests media for the active tab and keeps the preference", async ({
    frigateApp,
  }) => {
    const { page } = frigateApp;
    const paths = collectPaths(page);
    await page.route("**/api/timeline?*", (route) =>
      route.fulfill({ json: [] }),
    );
    await page.route("**/api/*/recordings?*", (route) =>
      route.fulfill({ json: [] }),
    );
    await frigateApp.goto("/events");
    const rows = page.locator("#pageRoot [data-start] button.min-w-0.grow");
    await expect(rows).toHaveCount(3);
    expect(
      paths.filter(
        (path) => eventPlayback.test(path) || eventTracking.test(path),
      ),
    ).toEqual([]);
    expect(
      paths.filter((path) => path.includes("/assets/ClassicEventDetails-")),
    ).toEqual([]);
    await expectScriptBudget(page, 2450);

    // Open a fixture without a clip to choose Snapshot without starting playback.
    await rows.nth(2).click();
    await expect(page.getByRole("tab", { name: "Clip" })).toBeDisabled();
    await expect(page.getByRole("tab", { name: "Snapshot" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await rows.first().click();
    await expect(page.getByRole("tab", { name: "Snapshot" })).toBeVisible();
    await page.getByRole("tab", { name: "Snapshot" }).click();
    await expect(page.getByRole("tabpanel").locator("img")).toBeVisible();

    const trackingRequests = paths.filter((path) =>
      eventTracking.test(path),
    ).length;
    await rows.nth(1).click();
    await expect(page.getByRole("tab", { name: "Snapshot" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(paths.filter((path) => path.startsWith("/vod/backyard/"))).toEqual(
      [],
    );
    expect(paths.filter((path) => eventTracking.test(path))).toHaveLength(
      trackingRequests,
    );

    await page.reload();
    const afterReload = paths.length;
    await rows.nth(1).click();
    await expect(page.getByRole("tab", { name: "Snapshot" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      paths.slice(afterReload).filter((path) => eventPlayback.test(path)),
    ).toEqual([]);

    await page.getByRole("tab", { name: "Tracking Details" }).click();
    await expect.poll(() => paths.includes("/api/timeline")).toBe(true);
  });
});
