import { baseUrl } from "@/api/baseUrl";
import { useEffect, useRef, useState } from "react";

type DemoVideoProps = {
  camera: string;
  className?: string;
  startAt?: number;
  loop?: boolean;
  onPlaying?: () => void;
  onResolution?: (resolution: { width: number; height: number }) => void;
};

export default function DemoVideo({
  camera,
  className = "size-full",
  startAt = 0,
  loop = false,
  onPlaying,
  onResolution,
}: DemoVideoProps) {
  const filename =
    camera === "birdseye" ? "birdseye.mp4" : `media/${camera}.mp4`;
  const videoRef = useRef<HTMLVideoElement>(null);
  const [autoplayBlocked, setAutoplayBlocked] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    let mounted = true;
    function start() {
      if (!video) return;
      onResolution?.({ width: video.videoWidth, height: video.videoHeight });
      if (startAt) video.currentTime = startAt;
      void video.play().catch(() => {
        if (mounted) setAutoplayBlocked(true);
      });
    }
    if (video.readyState >= HTMLMediaElement.HAVE_METADATA) start();
    else video.addEventListener("loadedmetadata", start, { once: true });
    return () => {
      mounted = false;
      video.removeEventListener("loadedmetadata", start);
    };
  }, [filename, onResolution, startAt]);

  return (
    <video
      ref={videoRef}
      className={`${className} object-contain`}
      src={baseUrl + filename}
      poster={`${baseUrl}posters/${camera}.webp`}
      controls={!loop || autoplayBlocked}
      loop={loop}
      muted
      playsInline
      autoPlay={!startAt}
      preload="metadata"
      onPlaying={onPlaying}
    />
  );
}
