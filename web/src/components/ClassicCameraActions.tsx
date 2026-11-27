import useSWR from "swr";
import { FrigateConfig } from "@/types/frigateConfig";
import {
  useDetectState,
  useRecordingsState,
  useSnapshotsState,
} from "@/api/ws";
import { useIsAdmin } from "@/hooks/use-is-admin";
import { CameraConfig } from "@/types/frigateConfig";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LuCamera, LuClapperboard, LuScanLine } from "react-icons/lu";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { demoBuild } from "@/env";

function CameraToggles({ camera }: { camera: CameraConfig }) {
  const { t } = useTranslation("common");
  const { data: config } = useSWR<FrigateConfig>("config");
  const detect = useDetectState(camera.name);
  const record = useRecordingsState(camera.name);
  const snapshot = useSnapshotsState(camera.name);
  const toggles = [
    { name: "detection", state: detect, icon: LuScanLine },
    {
      name: "recordings",
      state: record,
      icon: LuClapperboard,
      disabled: !camera.record.enabled_in_config,
    },
    { name: "snapshots", state: snapshot, icon: LuCamera },
  ];

  return (
    <div className="ml-auto flex">
      {toggles
        .filter(
          ({ name }) => !config?.camera_controls_locked || name === "snapshots",
        )
        .map(({ name, state, icon: Icon, disabled }) => {
          const on = state.payload === "ON";
          return (
            <Button
              key={name}
              size="icon"
              variant="ghost"
              type="button"
              disabled={disabled || !state.payload}
              aria-label={t(`menu.classic.${name}`)}
              title={t(`menu.classic.${name}`)}
              aria-pressed={on}
              onClick={() => state.send(on ? "OFF" : "ON", true)}
            >
              <Icon
                className={cn(
                  "size-5",
                  on ? "text-blue-500" : "text-muted-foreground",
                )}
              />
            </Button>
          );
        })}
    </div>
  );
}

export default function ClassicCameraActions({
  camera,
}: {
  camera: CameraConfig;
}) {
  const { t } = useTranslation("common");
  const isAdmin = useIsAdmin();
  const cameraPath = encodeURIComponent(camera.name);

  return (
    <div className="px-3 pb-2 pt-3 sm:px-4">
      <Link
        to={`/#${cameraPath}`}
        className="block truncate font-semibold hover:underline"
      >
        {camera.friendly_name || camera.name.replaceAll("_", " ")}
      </Link>
      <div className="-ml-2 mt-1 flex flex-wrap items-center">
        <Button variant="ghost" size="sm" asChild>
          <Link to={`/events?cameras=${cameraPath}`}>
            {t("menu.classic.events")}
          </Link>
        </Button>
        {!demoBuild && (
          <Button variant="ghost" size="sm" asChild>
            <Link to={`/recording/${cameraPath}`}>
              {t("menu.classic.recordings")}
            </Link>
          </Button>
        )}
        {isAdmin && <CameraToggles camera={camera} />}
      </div>
    </div>
  );
}
