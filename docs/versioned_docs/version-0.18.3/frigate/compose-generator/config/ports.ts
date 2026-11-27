/**
 * AUTO-GENERATED FILE — do not edit directly.
 * Source: config.yaml
 * To update, edit the YAML file and run: npm run build:config
 */

import type { PortConfig } from "./types";

export const ports: PortConfig[] = [
    {
      "id": "8971",
      "host": 8971,
      "container": 8971,
      "protocol": "tcp",
      "description": "Authenticated UI and API access (default HTTPS)",
      "defaultEnabled": true,
      "warningContent": "This is the access port for HeisenCam. Closing it means you will no longer be able to access the instance.",
      "warningWhen": "unchecked"
    },
    {
      "id": "8554",
      "host": 8554,
      "container": 8554,
      "protocol": "tcp",
      "description": "Access RTSP feeds from go2rtc",
      "defaultEnabled": true
    },
    {
      "id": "8555-tcp",
      "host": 8555,
      "container": 8555,
      "protocol": "tcp",
      "description": "WebRTC over TCP",
      "defaultEnabled": true
    },
    {
      "id": "8555-udp",
      "host": 8555,
      "container": 8555,
      "protocol": "udp",
      "description": "WebRTC over UDP",
      "defaultEnabled": true
    },
    {
      "id": "1984",
      "host": 1984,
      "container": 1984,
      "protocol": "tcp",
      "description": "Go2RTC Web UI",
      "defaultEnabled": false
    }
  ];

/** Lookup map for quick access by ID */
export const portMap: Map<string, PortConfig> = new Map(ports.map((item) => [item.id, item]));
