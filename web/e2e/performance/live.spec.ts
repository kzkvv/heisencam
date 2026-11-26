import type { Page } from "@playwright/test";
import { expect, test } from "../fixtures/frigate-test";

test.skip(
  process.env.FRIGATE_PERF_LIVE !== "1" || !process.env.FRIGATE_PERF_URL,
  "Opt-in: run this against a configured Frigate with cameras and recordings",
);

async function readyFrameMode(page: Page, player: string): Promise<string> {
  const mode = await page.waitForFunction(
    (selector) => {
      const container = document.querySelector(selector);
      const video = container?.querySelector("video");
      const canvas = container?.querySelector("canvas");
      if (
        video &&
        video.readyState >= 2 &&
        !video.paused &&
        video.offsetWidth > 10
      ) {
        return video.srcObject ? "webrtc" : "video";
      }
      // JSMpeg only shows the canvas after decoding and sizing a frame.
      return canvas && canvas.getBoundingClientRect().width > 10
        ? "jsmpeg"
        : false;
    },
    player,
    { timeout: 20_000 },
  );
  return await mode.jsonValue();
}

test("measure the first visible frame on the real Live, Birdseye and Events views", async ({
  page,
}, testInfo) => {
  test.setTimeout(180_000);

  const configResponse = await page.request.get("/api/config");
  expect(configResponse.ok()).toBe(true);
  const config = await configResponse.json();
  const camera =
    process.env.FRIGATE_PERF_CAMERA ??
    Object.keys(config.cameras).find((name) => config.cameras[name].enabled);
  if (!camera || !config.cameras[camera]?.enabled) {
    throw new Error("Select an enabled camera with FRIGATE_PERF_CAMERA");
  }
  const eventQuery = new URLSearchParams({
    has_clip: "1",
    include_thumbnails: "0",
    limit: "1",
  });
  const requestedEvent = process.env.FRIGATE_PERF_EVENT_ID;
  if (requestedEvent) eventQuery.set("event_id", requestedEvent);
  const events = await page.request.get(`/api/events?${eventQuery}`);
  expect(events.ok()).toBe(true);
  const [event] = (await events.json()) as { id: string }[];
  if (!event)
    throw new Error("Select a playable clip with FRIGATE_PERF_EVENT_ID");
  const version = await page.request.get("/api/version");
  expect(version.ok()).toBe(true);
  const profile = {
    version: await version.text(),
    browser: page.context().browser()?.version(),
    camera,
    eventId: event.id,
    httpCache: "disabled",
    birdseyeEnabled: config.birdseye.enabled,
  };

  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Network.setCacheDisabled", { cacheDisabled: true });
  const timings: Record<string, number[]> = {
    camera: [],
    birdseye: [],
    clip: [],
  };
  const modes: Record<string, string[]> = {
    camera: [],
    birdseye: [],
    clip: [],
  };

  try {
    for (let repeat = 0; repeat < 3; repeat++) {
      await page.goto("about:blank");
      await page.goto(`/#${encodeURIComponent(camera)}`, {
        waitUntil: "domcontentloaded",
      });
      modes.camera.push(await readyFrameMode(page, "#pageRoot [data-camera]"));
      timings.camera.push(
        await page.evaluate(() => Math.round(performance.now())),
      );

      if (config.birdseye.enabled) {
        await page.goto("about:blank");
        await page.goto("/#birdseye", { waitUntil: "domcontentloaded" });
        modes.birdseye.push(await readyFrameMode(page, "#pageRoot"));
        timings.birdseye.push(
          await page.evaluate(() => Math.round(performance.now())),
        );
      }

      await page.goto(`/events?event_id=${encodeURIComponent(event.id)}`, {
        waitUntil: "domcontentloaded",
      });
      const play = page.getByRole("button", { name: "Play", exact: true });
      await expect(play).toBeEnabled({ timeout: 8_000 });
      const started = performance.now();
      await play.click();
      modes.clip.push(await readyFrameMode(page, "#pageRoot [role=tabpanel]"));
      timings.clip.push(Math.round(performance.now() - started));
    }
  } finally {
    await cdp.detach();
    const report = { profile, timings, modes };
    await testInfo.attach("first-frame-ms.json", {
      body: JSON.stringify(report, null, 2),
      contentType: "application/json",
    });
    process.stdout.write(
      `First visible frame, milliseconds: ${JSON.stringify(report)}\n`,
    );
  }

  const configuredBudget = process.env.FRIGATE_PERF_FRAME_BUDGET_MS;
  if (configuredBudget) {
    const budget = Number(configuredBudget);
    expect(Number.isFinite(budget) && budget > 0).toBeTruthy();
    for (const [view, samples] of Object.entries(timings)) {
      if (!samples.length) continue;
      const median = [...samples].sort((a, b) => a - b)[1];
      expect(median, `${view} median first-frame latency`).toBeLessThanOrEqual(
        budget,
      );
    }
  }
});
