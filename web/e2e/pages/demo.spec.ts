import { expect, test } from "@playwright/test";

test("compiled camera wall and recordings work without a server API", async ({
  page,
  baseURL,
}) => {
  const failures: string[] = [];
  if (!baseURL) throw new Error("Configure the packaged Pages base URL");
  const origin = new URL(baseURL).origin;
  page.on("pageerror", (error) => failures.push(error.message));
  page.on("request", (request) => {
    if (!request.url().startsWith(origin + "/")) failures.push(request.url());
  });
  page.on("response", (response) => {
    if (response.status() >= 400) failures.push(response.url());
  });

  await page.goto("demo/");
  for (const camera of [
    "fortieth_street",
    "downtown_skywalk",
    "bay_bridge",
    "twelfth_avenue",
    "pacific_coast",
    "ninth_avenue",
  ]) {
    const preview = page.locator(`img[src*="/${camera}/latest.webp"]`).first();
    await expect(preview).toBeVisible();
    await expect(preview).toHaveJSProperty("complete", true);
    expect(
      await preview.evaluate((image: HTMLImageElement) => image.naturalWidth),
    ).toBeGreaterThan(0);
  }
  await page.goto("demo/#fortieth_street");
  await expect
    .poll(() => page.locator("video").evaluate((video) => video.currentTime))
    .toBeGreaterThan(0);
  await page.goto("demo/birdseye/");
  await expect
    .poll(() => page.locator("video").evaluate((video) => video.currentTime))
    .toBeGreaterThan(0);

  const events = "demo/events/?cameras=twelfth_avenue&labels=person";
  await page.goto(events);
  const play = page.getByRole("button", { name: "Play", exact: true });
  await expect(play).toHaveCount(1);
  await play.click();
  await expect
    .poll(() => page.locator("video").evaluate((video) => video.currentTime))
    .toBeGreaterThan(0.5);
  await expect(page).toHaveURL(new URL(events, baseURL).href);
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.locator("video")).toHaveCount(0);

  await page.getByRole("link", { name: "Cameras", exact: true }).click();
  await page.goBack();
  await expect(page).toHaveURL(new URL(events, baseURL).href);
  await expect(play).toHaveCount(1);
  expect(failures).toEqual([]);
});

test("documentation provides local search and the HTTP reference", async ({
  page,
}) => {
  await page.goto("./");
  const search = page.getByRole("combobox", { name: "Search" });
  await page.getByLabel("Search", { exact: true }).click();
  await search.fill("idle_scan_interval");
  const result = page
    .getByRole("option", { name: /idle_scan_interval.*Camera Configuration/i })
    .first();
  await expect(result).toBeVisible();
  await result.click();
  await expect(page).toHaveURL(
    /\/configuration\/cameras\/?(?:\?[^#]*)?#idle-scan-interval/,
  );

  await page.goto("integrations/api/");
  await page.getByRole("link", { name: "HTTP API reference" }).click();
  await expect(
    page.getByRole("heading", { name: "HeisenCam HTTP API" }),
  ).toBeVisible();
});
