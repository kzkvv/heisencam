import axios, { AxiosError } from "axios";
import { baseUrl } from "@/api/baseUrl";
import { processWsMessage } from "@/api/ws";
import type { FrigateConfig } from "@/types/frigateConfig";
import type { SearchResult } from "@/types/search";
import configSnapshot from "../../e2e/fixtures/mock-data/config-snapshot.json";
import { BASE_STATS } from "../../e2e/fixtures/mock-data/stats";

type DemoCamera = {
  id: string;
  name: string;
  width: number;
  height: number;
  seconds: number;
};

type DemoEvent = {
  id: string;
  camera: string;
  label: string;
  score: number;
  offset: number;
};

type DemoCatalog = {
  cameras: DemoCamera[];
  events: DemoEvent[];
};

let catalog: DemoCatalog;

export function demoEventOffset(id: string) {
  return catalog.events.find((event) => event.id === id)?.offset ?? 0;
}

function makeConfig(cameras: DemoCamera[]): FrigateConfig {
  const snapshot = configSnapshot as unknown as FrigateConfig;
  const template = snapshot.cameras.front_door;
  return {
    ...snapshot,
    camera_controls_locked: true,
    go2rtc: { ...snapshot.go2rtc, streams: {} },
    camera_groups: {},
    birdseye: { ...snapshot.birdseye, enabled: true, width: 1152, height: 496 },
    cameras: Object.fromEntries(
      cameras.map(({ id, name, width, height }, order) => [
        id,
        {
          ...template,
          name: id,
          friendly_name: name,
          enabled: true,
          enabled_in_config: true,
          ui: { ...template.ui, order, dashboard: true },
          live: { ...template.live, streams: { Main: id } },
          detect: { ...template.detect, width, height },
          ffmpeg: { ...template.ffmpeg, inputs: [] },
          zones: {},
        },
      ]),
    ),
  };
}

function matchesEvent(event: SearchResult, params: URLSearchParams) {
  const includes = (key: string, value: string) => {
    const options = [
      ...params.getAll(key),
      ...params.getAll(key + "[]"),
    ].flatMap((entry) => entry.split(","));
    return (
      options.length === 0 || options.includes("all") || options.includes(value)
    );
  };
  const after = Number(params.get("after") ?? "-Infinity");
  const before = Number(params.get("before") ?? "Infinity");
  const score = event.data.score;
  const query = (params.get("query") ?? "").toLowerCase().trim();
  return (
    includes("cameras", event.camera) &&
    includes("labels", event.label) &&
    (!params.has("event_id") || params.get("event_id") === event.id) &&
    (!params.has("has_snapshot") ||
      params.get("has_snapshot") === String(+event.has_snapshot)) &&
    (!params.has("has_clip") ||
      params.get("has_clip") === String(+event.has_clip)) &&
    event.start_time > after &&
    event.start_time < before &&
    score >= Number(params.get("min_score") ?? 0) &&
    score <= Number(params.get("max_score") ?? 1) &&
    (!query ||
      `${event.label} ${event.camera.replaceAll("_", " ")}`.includes(query))
  );
}

function filterEvents(events: SearchResult[], params: URLSearchParams) {
  const sort = params.get("sort");
  const direction = sort === "score_asc" || sort === "date_asc" ? 1 : -1;
  const byScore = sort === "score_asc" || sort === "score_desc";
  const cursor = params.get("cursor_start_time");
  const cursorId = params.get("cursor_event_id");
  const offset = Number(params.get("offset") ?? 0);
  const limit = Number(params.get("limit") ?? 25);
  return events
    .filter((event) => {
      if (!matchesEvent(event, params)) return false;
      if (!cursor || !cursorId || byScore) return true;
      const delta =
        event.start_time - Number(cursor) || event.id.localeCompare(cursorId);
      return delta * direction > 0;
    })
    .sort((a, b) => {
      const delta = byScore
        ? a.data.score - b.data.score
        : a.start_time - b.start_time;
      return direction * (delta || a.id.localeCompare(b.id));
    })
    .slice(offset, offset + limit);
}

export async function installDemoSource() {
  const response = await fetch(`${baseUrl}catalog.json`);
  if (!response.ok) throw new Error("Demo catalog unavailable");
  catalog = (await response.json()) as DemoCatalog;

  const cameras = catalog.cameras.map((camera) => camera.id);
  const config = makeConfig(catalog.cameras);
  const start = Math.floor(Date.now() / 1000) - 90;
  const events: SearchResult[] = catalog.events.map(
    ({ id, camera, label, score, offset }) => ({
      id,
      camera,
      label,
      score: score / 100,
      top_score: score / 100,
      start_time: start + offset,
      end_time:
        start +
        (catalog.cameras.find((entry) => entry.id === camera)?.seconds ?? 16),
      has_snapshot: true,
      has_clip: true,
      zones: [],
      search_source: "thumbnail",
      search_distance: 0,
      data: {
        score: score / 100,
        top_score: score / 100,
        type: "object",
        region: [],
        box: [],
        area: 0,
        ratio: 0,
        average_estimated_speed: 0,
        velocity_angle: 0,
        path_data: [],
      },
    }),
  );

  const stats = {
    ...BASE_STATS,
    detectors: {},
    cameras: Object.fromEntries(
      cameras.map((id) => [id, BASE_STATS.cameras.front_door]),
    ),
    cpu_usages: {},
    service: {
      ...BASE_STATS.service,
      version: "0.18.3",
      latest_version: "0.18.3",
    },
  };
  const send = (topic: string, payload: unknown) =>
    processWsMessage(JSON.stringify({ topic, payload }));
  send(
    "camera_activity",
    JSON.stringify(
      Object.fromEntries(
        cameras.map((id) => [
          id,
          {
            config: {
              enabled: true,
              record: true,
              detect: true,
              snapshots: true,
              motion: true,
              alerts: true,
              detections: true,
            },
            motion: false,
            objects: [],
            audio_detections: [],
          },
        ]),
      ),
    ),
  );
  send("stats", JSON.stringify(stats));
  send(
    "birdseye_layout",
    JSON.stringify(
      Object.fromEntries(
        cameras.map((id, index) => [
          id,
          {
            x: (index % 3) * 384,
            y: Math.floor(index / 3) * 248,
            width: 384,
            height: 248,
          },
        ]),
      ),
    ),
  );

  const api = new URL("api/", baseUrl);
  const routes = new Map<string, unknown>([
    ["config", config],
    ["profile", { username: "demo", role: "viewer", allowed_cameras: cameras }],
    ["stats", stats],
    ["stats/history", [stats]],
    ["version", "0.18.3"],
    ["profiles", { profiles: [], active_profile: null, last_activated: {} }],
    ["labels", ["person", "car"]],
    ["sub_labels", []],
    ["recognized_license_plates", []],
    ["review", []],
    ["go2rtc/streams", {}],
  ]);

  axios.defaults.adapter = async (request) => {
    const url = new URL(axios.getUri(request), baseUrl);
    const path = url.pathname.slice(api.pathname.length);
    const result = (data: unknown) => ({
      data,
      status: 200,
      statusText: "OK",
      headers: {},
      config: request,
    });
    if (
      url.origin !== api.origin ||
      !url.pathname.startsWith(api.pathname) ||
      !["get", "head"].includes(request.method ?? "get")
    ) {
      throw new AxiosError(
        "Demo source is read-only",
        AxiosError.ERR_BAD_REQUEST,
        request,
      );
    }
    if (routes.has(path)) return result(routes.get(path));
    if (path === "events" || path === "events/search") {
      return result(filterEvents(events, url.searchParams));
    }
    if (path.startsWith("events/")) {
      const event = events.find((entry) => path === `events/${entry.id}`);
      if (event) return result(event);
    }
    if (path.startsWith("preview/") || path.endsWith("/attributes"))
      return result([]);
    if (path.startsWith("go2rtc/streams/")) return result({ producers: [] });
    throw new AxiosError(
      "Endpoint unavailable in the demo",
      AxiosError.ERR_BAD_REQUEST,
      request,
    );
  };
}
