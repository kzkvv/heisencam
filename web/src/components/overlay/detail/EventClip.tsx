import { useMemo } from "react";
import { baseUrl } from "@/api/baseUrl";
import { GenericVideoPlayer } from "@/components/player/GenericVideoPlayer";
import { REVIEW_PADDING } from "@/types/review";
import type { SearchResult } from "@/types/search";
import { demoBuild } from "@/env";
import DemoVideo from "@/demo/DemoVideo";
import { demoEventOffset } from "@/demo/source";

type VideoTabProps = {
  search: SearchResult;
  padding?: number;
};

export default function EventClip({
  search,
  padding = REVIEW_PADDING,
}: VideoTabProps) {
  const clipTimeRange = useMemo(() => {
    const startTime = search.start_time - padding;
    const endTime = (search.end_time ?? Date.now() / 1000) + padding;
    return `start/${startTime}/end/${endTime}`;
  }, [search, padding]);

  if (demoBuild) {
    return (
      <DemoVideo camera={search.camera} startAt={demoEventOffset(search.id)} />
    );
  }

  const source = `${baseUrl}vod/${search.camera}/${clipTimeRange}/index.m3u8`;

  return (
    <>
      <span tabIndex={0} className="sr-only" />
      <GenericVideoPlayer source={source} />
    </>
  );
}
