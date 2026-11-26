import type * as Preset from "@docusaurus/preset-classic";
import * as path from "node:path";
import type { Config, PluginConfig } from "@docusaurus/types";
import type * as OpenApiPlugin from "docusaurus-plugin-openapi-docs";

const config: Config = {
  title: "HeisenCam",
  tagline: "NVR With Realtime Object Detection for IP Cameras",
  url: "https://kzkvv.github.io",
  baseUrl: "/heisencam/docs/",
  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "warn",
  favicon: "img/branding/favicon.ico",
  organizationName: "kzkvv",
  projectName: "heisencam",
  themes: [
    "@docusaurus/theme-mermaid",
    "docusaurus-theme-openapi-docs",
  ],
  markdown: {
    mermaid: true,
  },
  i18n: {
    defaultLocale: "en",
    locales: ["en"],
    localeConfigs: {
      en: {
        label: "English",
      },
    },
  },
  themeConfig: {
    docs: {
      sidebar: {
        hideable: true,
      },
    },
    prism: {
      magicComments: [
        {
          className: "theme-code-block-highlighted-line",
          line: "highlight-next-line",
          block: { start: "highlight-start", end: "highlight-end" },
        },
        {
          className: "code-block-error-line",
          line: "highlight-error-line",
        },
      ],
      additionalLanguages: ["bash", "json"],
    },
    languageTabs: [
      {
        highlight: "python",
        language: "python",
        logoClass: "python",
      },
      {
        highlight: "javascript",
        language: "nodejs",
        logoClass: "nodejs",
      },
      {
        highlight: "javascript",
        language: "javascript",
        logoClass: "javascript",
      },
      {
        highlight: "bash",
        language: "curl",
        logoClass: "curl",
      },
      {
        highlight: "rust",
        language: "rust",
        logoClass: "rust",
      },
    ],
    navbar: {
      title: "HeisenCam",
      logo: {
        alt: "HeisenCam",
        src: "img/branding/logo.svg",
        srcDark: "img/branding/logo-dark.svg",
      },
      items: [
        {
          href: "https://github.com/kzkvv/heisencam/tree/heisencam/0.18.3",
          label: "0.18.3",
          position: "left",
        },
        {
          to: "/",
          activeBasePath: "docs",
          label: "Docs",
          position: "left",
        },
        {
          href: "https://kzkvv.github.io/heisencam/",
          label: "Website",
          position: "right",
        },
        {
          href: "https://kzkvv.github.io/heisencam/demo/",
          label: "Demo",
          position: "right",
        },
        {
          type: "localeDropdown",
          position: "right",
          dropdownItemsAfter: [
            {
              label: "简体中文（社区翻译）",
              href: "https://docs.frigate-cn.video",
            },
          ],
        },
        {
          href: "https://github.com/kzkvv/heisencam/tree/heisencam/0.18.3",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Community",
          items: [
            {
              label: "GitHub",
              href: "https://github.com/kzkvv/heisencam",
            },
            {
              label: "Discussions",
              href: "https://github.com/kzkvv/heisencam/discussions",
            },
          ],
        },
      ],
      copyright: `HeisenCam contributors. Based on Frigate by Frigate, Inc.`,
    },
  },
  plugins: [
    path.resolve(__dirname, "plugins", "raw-loader"),
    path.resolve(__dirname, "plugins", "yaml-loader"),
    [
      "docusaurus-plugin-openapi-docs",
      {
        id: "openapi",
        docsPluginId: "classic", // configured for preset-classic
        config: {
          frigateApi: {
            specPath: "static/frigate-api.yaml",
            outputDir: "docs/integrations/api",
            sidebarOptions: {
              groupPathsBy: "tag",
              categoryLinkSource: "tag",
              sidebarCollapsible: true,
              sidebarCollapsed: true,
            },
            showSchemas: true,
          } satisfies OpenApiPlugin.Options,
        },
      },
    ],
  ] as PluginConfig[],
  presets: [
    [
      "classic",
      {
        docs: {
          routeBasePath: "/",
          sidebarPath: "./sidebars.ts",
          // Please change this to your repo.
          editUrl:
            "https://github.com/kzkvv/heisencam/edit/heisencam/0.18.3/docs/",
          sidebarCollapsible: false,
          docItemComponent: "@theme/ApiItem", // Derived from docusaurus-theme-openapi
        },

        theme: {
          customCss: "./src/css/custom.css",
        },
      } satisfies Preset.Options,
    ],
  ],
};

export default async function createConfig() {
  return config;
}
