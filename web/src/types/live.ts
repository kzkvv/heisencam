export type LivePlayerMode = "webrtc" | "mse" | "jsmpeg" | "debug";
export type VideoResolutionType = {
  width: number;
  height: number;
};

type LiveProducerMetadata = {
  medias?: string[] | null;
};

export type LiveStreamMetadata = {
  producers: LiveProducerMetadata[];
};

export type LivePlayerError = "stalled" | "startup" | "mse-decode";

export type AudioState = Record<string, boolean>;
export type StatsState = Record<string, boolean>;
export type VolumeState = Record<string, number>;

export type PlayerStatsType = {
  streamType: string;
  bandwidth: number;
  latency: number | undefined;
  totalFrames: number;
  droppedFrames: number | undefined;
  decodedFrames: number | undefined;
  droppedFrameRate: number | undefined;
};
