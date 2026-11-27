import { fromZonedTime, formatInTimeZone } from "date-fns-tz";
import Providers from "@/context/providers";
import {
  BrowserRouter,
  Navigate,
  Routes,
  Route,
  useParams,
} from "react-router-dom";
import Wrapper from "@/components/Wrapper";
import Sidebar from "@/components/navigation/Sidebar";

import Statusbar from "./components/Statusbar";
import { Suspense, lazy } from "react";
import { Redirect } from "./components/navigation/Redirect";
import { cn } from "./lib/utils";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import useSWR from "swr";
import { FrigateConfig } from "./types/frigateConfig";
import ActivityIndicator from "@/components/indicators/activity-indicator";
import { isRedirectingToLogin } from "@/api/auth-redirect";
import { basePath } from "@/api/baseUrl";

const Live = lazy(() => import("@/pages/Live"));
const Events = lazy(() => import("@/pages/Events"));
const Explore = lazy(() => import("@/pages/Explore"));
const Exports = lazy(() => import("@/pages/Exports"));
const ConfigEditor = lazy(() => import("@/pages/ConfigEditor"));
const System = lazy(() => import("@/pages/System"));
const Settings = lazy(() => import("@/pages/Settings"));
const UIPlayground = lazy(() => import("@/pages/UIPlayground"));
const FaceLibrary = lazy(() => import("@/pages/FaceLibrary"));
const Classification = lazy(() => import("@/pages/ClassificationModel"));
const Chat = lazy(() => import("@/pages/Chat"));
const Logs = lazy(() => import("@/pages/Logs"));
const AccessDenied = lazy(() => import("@/pages/AccessDenied"));
const Replay = lazy(() => import("@/pages/Replay"));

function App() {
  const { data: config } = useSWR<FrigateConfig>("config", {
    revalidateOnFocus: false,
  });

  return (
    <Providers>
      <BrowserRouter basename={basePath}>
        <Wrapper>
          {config?.safe_mode ? <SafeAppView /> : <DefaultAppView />}
        </Wrapper>
      </BrowserRouter>
    </Providers>
  );
}

function DefaultAppView() {
  const { data: config } = useSWR<FrigateConfig>("config", {
    revalidateOnFocus: false,
  });

  // Compute required roles for main routes, ensuring we have config first
  // to prevent race condition where custom roles are temporarily unavailable
  const mainRouteRoles = config?.auth?.roles
    ? Object.keys(config.auth.roles)
    : undefined;

  // Show loading indicator during redirect to prevent React from attempting to render
  // lazy components, which would cause error #426 (suspension during synchronous navigation)
  if (isRedirectingToLogin()) {
    return (
      <div className="size-full overflow-hidden">
        <ActivityIndicator className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" />
      </div>
    );
  }

  return (
    <div className="size-full overflow-hidden">
      <Sidebar />
      <div className="hidden lg:contents">
        <Statusbar />
      </div>
      <div
        id="pageRoot"
        className="absolute inset-x-0 bottom-[env(safe-area-inset-bottom)] top-[calc(3.5rem+env(safe-area-inset-top))] overflow-hidden lg:bottom-8 lg:left-64 lg:top-0"
      >
        <Suspense
          fallback={
            <ActivityIndicator className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" />
          }
        >
          <Routes>
            <Route element={<ProtectedRoute requiredRoles={mainRouteRoles} />}>
              <Route index element={<Live />} />
              <Route path="/review" element={<Events />} />
              <Route path="/events" element={<Explore classic />} />
              <Route
                path="/birdseye"
                element={<Navigate to="/#birdseye" replace />}
              />
              <Route path="/cameras/:camera" element={<ClassicCameraLink />} />
              <Route
                path="/recording/:camera/*"
                element={<ClassicRecordingLink />}
              />
              <Route path="/explore" element={<Explore />} />
              <Route path="/export" element={<Exports />} />
              <Route path="/settings" element={<Settings />} />
            </Route>
            <Route element={<ProtectedRoute requiredRoles={["admin"]} />}>
              <Route path="/system" element={<System />} />
              <Route
                path="/storage"
                element={<Navigate to="/system#storage" replace />}
              />
              <Route path="/config" element={<ConfigEditor />} />
              <Route path="/logs" element={<Logs />} />
              <Route path="/faces" element={<FaceLibrary />} />
              <Route path="/classification" element={<Classification />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/playground" element={<UIPlayground />} />{" "}
              <Route path="/replay" element={<Replay />} />{" "}
            </Route>
            <Route path="/unauthorized" element={<AccessDenied />} />
            <Route path="*" element={<Redirect to="/" />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
}

function ClassicCameraLink() {
  const { camera } = useParams();
  return <Navigate to={`/#${encodeURIComponent(camera ?? "")}`} replace />;
}

function ClassicRecordingLink() {
  const { camera, "*": selection } = useParams();
  const { data: config } = useSWR<FrigateConfig>("config");
  const [date, hour = "00", minute = "00", second = "00"] = (
    selection ?? ""
  ).split("/");
  if (date && !config) {
    return <ActivityIndicator />;
  }
  const timezone =
    config?.ui.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone;
  const clock = `${date}T${[hour, minute, second].map((part) => part.padStart(2, "0")).join(":")}`;
  const instant = date ? fromZonedTime(clock, timezone) : new Date();
  const valid =
    Number.isFinite(instant.getTime()) &&
    (!date ||
      formatInTimeZone(instant, timezone, "yyyy-MM-dd'T'HH:mm:ss") === clock);
  const timestamp = valid ? instant.getTime() / 1000 : Date.now() / 1000;
  const value = `${camera ?? ""}_${Math.floor(timestamp)}`;
  return (
    <Navigate to={`/review?timestamp=${encodeURIComponent(value)}`} replace />
  );
}

function SafeAppView() {
  return (
    <div className="size-full overflow-hidden">
      <div
        id="pageRoot"
        className={cn("absolute bottom-0 left-0 right-0 top-0 overflow-hidden")}
      >
        <Suspense>
          <ConfigEditor />
        </Suspense>
      </div>
    </div>
  );
}

export default App;
