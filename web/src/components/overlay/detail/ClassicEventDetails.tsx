import { lazy, Suspense } from "react";
import { useTranslation } from "react-i18next";
import { useApiHost } from "@/api";
import ActivityIndicator from "@/components/indicators/activity-indicator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { Event } from "@/types/event";
import type { SearchResult } from "@/types/search";
import { demoBuild } from "@/env";

const EventClip = lazy(() => import("./EventClip"));
const InlineTrackingDetails = lazy(() =>
  import("./TrackingDetails").then((module) => ({
    default: module.InlineTrackingDetails,
  })),
);

const EVENT_TABS = ["clip", "snapshot", "tracking_details"] as const;

export type ClassicEventTab = (typeof EVENT_TABS)[number];

type ClassicEventDetailsProps = {
  event: SearchResult;
  preferredTab: ClassicEventTab;
  onTabChange: (value: ClassicEventTab) => void;
};

export default function ClassicEventDetails({
  event,
  preferredTab,
  onTabChange,
}: ClassicEventDetailsProps) {
  const { t } = useTranslation("views/explore");
  const apiHost = useApiHost();
  const tab = !event.has_clip
    ? "snapshot"
    : demoBuild && preferredTab === "tracking_details"
      ? "clip"
      : preferredTab;
  const tabs = demoBuild
    ? EVENT_TABS.filter((name) => name !== "tracking_details")
    : EVENT_TABS;
  const snapshot =
    event.has_snapshot && !demoBuild
      ? "snapshot.jpg?crop=0&bbox=1"
      : "thumbnail.webp";

  return (
    <Tabs
      value={tab}
      activationMode="manual"
      onValueChange={(value) => onTabChange(value as ClassicEventTab)}
      className="mx-auto mb-3 w-full max-w-6xl"
    >
      <TabsList
        aria-label={t("classic.eventTabs")}
        className="mx-auto flex h-auto w-fit flex-wrap gap-1 bg-transparent p-0"
      >
        {tabs.map((name) => (
          <TabsTrigger
            key={name}
            value={name}
            disabled={name !== "snapshot" && !event.has_clip}
            className="rounded-full px-3 py-2 text-foreground data-[state=active]:bg-blue-600 data-[state=active]:text-white"
          >
            {t(`classic.tabs.${name}`)}
          </TabsTrigger>
        ))}
      </TabsList>

      <TabsContent value="clip" className="aspect-video max-h-[70dvh]">
        <Suspense fallback={<ActivityIndicator />}>
          <EventClip search={event} padding={0} />
        </Suspense>
      </TabsContent>

      <TabsContent value="snapshot">
        <img
          className="mx-auto max-h-[75dvh] max-w-full rounded object-contain"
          src={`${apiHost}api/events/${event.id}/${snapshot}`}
          alt={t("classic.tabs.snapshot")}
        />
      </TabsContent>

      {!demoBuild && (
        <TabsContent value="tracking_details">
          <Suspense fallback={<ActivityIndicator />}>
            <InlineTrackingDetails event={event as unknown as Event} />
          </Suspense>
        </TabsContent>
      )}
    </Tabs>
  );
}
