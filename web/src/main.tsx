import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import i18n from "@/utils/i18n";
import "react-i18next";
import { demoBuild } from "@/env";

const element = document.getElementById("root")!;

function renderApp() {
  ReactDOM.createRoot(element).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
}

if (demoBuild) {
  import("@/demo/source")
    .then(({ installDemoSource }) => installDemoSource())
    .then(renderApp)
    .catch(() => {
      element.textContent = i18n.t("demo.loadError", { ns: "common" });
    });
} else {
  renderApp();
}
