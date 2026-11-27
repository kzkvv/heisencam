/**
 * AUTO-GENERATED FILE — do not edit directly.
 * Source: config.yaml
 * To update, edit the YAML file and run: npm run build:config
 */

import type { HardwareOption } from "./types";

export const hardwareOptions: HardwareOption[] = [
    {
      "id": "usbCoral",
      "label": "USB Coral (TPU)",
      "description": "Enable this if you have a Google Coral USB TPU. Other Coral versions require different device paths.",
      "disabledWhen": [
        "apple-silicon",
        "stable-synaptics"
      ],
      "devices": [
        {
          "host": "/dev/bus/usb",
          "container": "/dev/bus/usb",
          "comment": "USB Coral — modify for other versions"
        }
      ]
    },
    {
      "id": "pcieCoral",
      "label": "PCIe Coral (TPU)",
      "description": "Enable this if you have a Google Coral PCIe/M.2 TPU. You also need to [install the driver](https://github.com/jnicolson/gasket-builder).",
      "disabledWhen": [
        "apple-silicon",
        "stable-synaptics"
      ],
      "devices": [
        {
          "host": "/dev/apex_0",
          "container": "/dev/apex_0",
          "comment": "PCIe Coral — follow driver instructions at https://github.com/jnicolson/gasket-builder"
        }
      ]
    },
    {
      "id": "gpu",
      "label": "Intel/AMD GPU (/dev/dri)",
      "description": "Pass through /dev/dri for GPU hardware acceleration (Intel/AMD).",
      "disabledWhen": [
        "stable-tensorrt-jp6",
        "apple-silicon"
      ],
      "devices": [
        {
          "host": "/dev/dri",
          "container": "/dev/dri",
          "comment": "Intel/AMD GPU hardware acceleration"
        }
      ]
    },
    {
      "id": "intelNpu",
      "label": "Intel NPU (/dev/accel)",
      "description": "Pass through /dev/accel for Intel NPU acceleration.",
      "disabledWhen": [
        "stable-tensorrt-jp6",
        "apple-silicon",
        "stable-rocm",
        "stable-rk",
        "stable-synaptics"
      ],
      "devices": [
        {
          "host": "/dev/accel",
          "container": "/dev/accel",
          "comment": "Intel NPU"
        }
      ]
    },
    {
      "id": "hailo",
      "label": "Hailo NPU (/dev/hailo0)",
      "description": "Pass through /dev/hailo0 for Hailo-8 / Hailo-8L NPU acceleration. You also need to [install the driver](#hailo-8).",
      "disabledWhen": [
        "apple-silicon",
        "stable-synaptics"
      ],
      "devices": [
        {
          "host": "/dev/hailo0",
          "comment": "Hailo NPU"
        }
      ]
    },
    {
      "id": "memryx",
      "label": "MemryX MX3 (/dev/memx0)",
      "description": "Pass through /dev/memx0 for MemryX MX3 NPU acceleration. You also need to [install the driver](#memryx-mx3).",
      "disabledWhen": [
        "apple-silicon",
        "stable-synaptics"
      ],
      "devices": [
        {
          "host": "/dev/memx0",
          "comment": "MemryX MX3 NPU"
        }
      ],
      "volumes": [
        {
          "host": "/run/mxa_manager",
          "container": "/run/mxa_manager",
          "comment": "MemryX manager"
        }
      ]
    },
    {
      "id": "axera",
      "label": "AXERA Accelerator",
      "description": "Pass through AXERA accelerator devices. Requires the [AXCL driver](#axera) to be installed first.",
      "disabledWhen": [
        "apple-silicon",
        "stable-synaptics"
      ],
      "devices": [
        {
          "host": "/dev/axcl_host",
          "comment": "AXERA accelerator device"
        },
        {
          "host": "/dev/ax_mmb_dev",
          "comment": "AXERA MMB device"
        },
        {
          "host": "/dev/msg_userdev",
          "comment": "AXERA message device"
        }
      ],
      "volumes": [
        {
          "host": "/usr/bin/axcl",
          "container": "/usr/bin/axcl",
          "comment": "AXERA binaries"
        },
        {
          "host": "/usr/lib/axcl",
          "container": "/usr/lib/axcl",
          "comment": "AXERA libraries"
        }
      ]
    },
    {
      "id": "video11",
      "label": "Raspberry Pi (/dev/video11)",
      "description": "Pass through /dev/video11 for Raspberry Pi 4B hardware acceleration.",
      "disabledWhen": [
        "stable-tensorrt",
        "stable-tensorrt-jp6",
        "stable-rocm",
        "stable-rk",
        "stable-synaptics",
        "intel",
        "apple-silicon",
        "stable"
      ],
      "devices": [
        {
          "host": "/dev/video11",
          "container": "/dev/video11",
          "comment": "Raspberry Pi 4B"
        }
      ]
    }
  ];

/** Lookup map for quick access by ID */
export const hardwareMap: Map<string, HardwareOption> = new Map(hardwareOptions.map((item) => [item.id, item]));
