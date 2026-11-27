import React from "react";
import useDocusaurusContext from "@docusaurus/useDocusaurusContext";

export default function DemoLink({ children, sources = false }) {
  const { siteConfig } = useDocusaurusContext();
  const { demoUrl } = siteConfig.customFields;

  return <a href={sources ? new URL("sources/", demoUrl).href : demoUrl}>{children}</a>;
}
