import { demoBuild } from "@/env";

declare global {
  interface Window {
    baseUrl?: string;
  }
}

export const basePath = demoBuild
  ? import.meta.env.BASE_URL
  : window.baseUrl || "/";
export const baseUrl = new URL(basePath, window.location.origin).href;
