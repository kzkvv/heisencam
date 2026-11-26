# Two-camera demonstration

Run `docker compose up -d` in this directory and open `http://127.0.0.1:8972`. To choose another port, set `HEISENCAM_PORT`. Set `HEISENCAM_IMAGE` to a locally built candidate, an immutable SHA tag or an image digest. Use `docker compose down` to stop the demo.

Both camera inputs are local ten-second H.264 loops made from real archival USGS webcam stills. Playback needs no camera account or external stream. The configuration enables recording with one day of continuous retention. The SQLite database and recordings use dedicated Docker volumes. The internal administrator UI is published on loopback. Enable native authentication and use port 8971 when adapting the deployment for network access.

| Demo camera | Observatory and capture | Usage |
| --- | --- | --- |
| South rim | USGS Hawaiian Volcano Observatory, S2cam, Kīlauea summit. [Image and credit](https://www.usgs.gov/media/images/s2cam-image-eruption-kilauea-summit) | Public domain. Adapted to 960 × 540. |
| West rim | USGS Hawaiian Volcano Observatory, KWcam, 4 January 2021. [Image and credit](https://www.usgs.gov/media/images/jan-4-kilauea-volcano-summit-eruption-image-kwcam-webcam) | Public domain. Adapted to 960 × 540. |

The landing page screenshot shows this demo. The source photographs document different dates and viewpoints. USGS supplies the imagery and has no affiliation with HeisenCam.
