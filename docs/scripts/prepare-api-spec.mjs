import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import yaml from "js-yaml";

const staticSource = new URL("../static/", import.meta.url);
const sourceSpec = new URL("frigate-api.yaml", staticSource);
const publicStatic = new URL("../.generated/static/", import.meta.url);
const spec = yaml.load(readFileSync(sourceSpec, "utf8"));

const excludedPaths = [
  "/plus/models",
  "/events/{event_id}/plus",
  "/events/{event_id}/false_positive",
  "/{camera_name}/plus/{frame_time}",
];
for (const endpoint of excludedPaths) {
  delete spec.paths[endpoint];
}

const schemas = spec.components.schemas;
delete schemas.EventUploadPlusResponse;
delete schemas.SubmitPlusBody;
delete schemas.EventResponse.properties.plus_id;
schemas.EventResponse.required = schemas.EventResponse.required.filter(
  (field) => field !== "plus_id",
);

rmSync(publicStatic, { recursive: true, force: true });
mkdirSync(publicStatic, { recursive: true });
cpSync(staticSource, publicStatic, {
  recursive: true,
  filter: (source) => source !== fileURLToPath(sourceSpec),
});
writeFileSync(
  new URL("frigate-api.yaml", publicStatic),
  yaml.dump(spec, { lineWidth: -1 }),
);
