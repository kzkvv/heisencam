import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { LuMenu } from "react-icons/lu";
import useSWR from "swr";
import Logo from "../Logo";
import AccountSettings from "../menu/AccountSettings";
import GeneralSettings from "../menu/GeneralSettings";
import { Button } from "../ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "../ui/sheet";
import useNavigation, { ID_LIVE } from "@/hooks/use-navigation";
import { useHasFullCameraAccess } from "@/hooks/use-has-full-camera-access";
import { useIsAdmin } from "@/hooks/use-is-admin";
import { cn } from "@/lib/utils";
import { FrigateConfig } from "@/types/frigateConfig";

function Wordmark({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link
      to="/"
      onClick={onNavigate}
      className="flex items-center gap-4 px-2 text-xl font-semibold hover:text-blue-500"
    >
      <Logo className="size-10" />
      HeisenCam
    </Link>
  );
}

function ClassicNavigation({ onNavigate }: { onNavigate?: () => void }) {
  const { t } = useTranslation("common");
  const { data: config } = useSWR<FrigateConfig>("config");
  const isAdmin = useIsAdmin();
  const hasFullCameraAccess = useHasFullCameraAccess();
  const { pathname, hash } = useLocation();
  const modernItems = useNavigation().filter(
    (item) => item.id !== ID_LIVE && item.enabled !== false,
  );

  function item(url: string, title: string, active: boolean) {
    return (
      <Link
        key={url}
        to={url}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        className={cn(
          "block rounded px-2 py-2 text-sm font-semibold hover:bg-blue-500 hover:text-white",
          active && "bg-blue-500/60 text-white",
        )}
      >
        {t(title)}
      </Link>
    );
  }

  const atLive = pathname === "/";
  const birdseye = atLive && hash === "#birdseye";
  const storage = pathname === "/system" && hash === "#storage";

  return (
    <nav className="flex min-h-0 grow flex-col gap-2 overflow-y-auto p-2">
      {item("/", "menu.classic.cameras", atLive && !birdseye)}
      {hasFullCameraAccess &&
        config?.birdseye.enabled &&
        item("/#birdseye", "menu.classic.birdseye", birdseye)}
      {item("/events", "menu.classic.events", pathname === "/events")}
      {isAdmin && (
        <>
          <hr className="-mx-2 border-secondary-highlight" />
          {item("/system#storage", "menu.classic.storage", storage)}
          {item("/system", "menu.system", pathname === "/system" && !storage)}
          {item("/config", "menu.classic.config", pathname === "/config")}
          {item("/logs", "menu.classic.logs", pathname === "/logs")}
        </>
      )}
      <hr className="-mx-2 border-secondary-highlight" />
      {modernItems.map(({ url, title }) => item(url, title, pathname === url))}
      {item("/settings", "menu.settings", pathname === "/settings")}
      {isAdmin &&
        item("/replay", "menu.classic.replay", pathname === "/replay")}
    </nav>
  );
}

export default function Sidebar() {
  const { t } = useTranslation("common");
  const [open, setOpen] = useState(false);

  return (
    <>
      <aside className="absolute inset-y-0 left-0 z-10 hidden w-64 flex-col border-r border-gray-200 bg-white text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 lg:flex">
        <div className="flex h-14 shrink-0 items-center border-b border-secondary-highlight">
          <Wordmark />
        </div>
        <ClassicNavigation />
        <div className="mb-8 flex items-center justify-end gap-3 border-t border-secondary-highlight p-2">
          <GeneralSettings />
          <AccountSettings />
        </div>
      </aside>
      <header className="absolute inset-x-0 top-0 z-10 flex h-14 items-center justify-between border-b border-gray-200 bg-white px-2 dark:border-gray-700 dark:bg-gray-900 lg:hidden">
        <div className="flex items-center">
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label={t("menu.classic.navigation")}
              >
                <LuMenu className="size-6" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              className="flex w-64 flex-col gap-0 bg-white p-0 text-gray-900 dark:bg-gray-900 dark:text-gray-200"
              aria-describedby={undefined}
            >
              <SheetTitle className="sr-only">
                {t("menu.classic.navigation")}
              </SheetTitle>
              <div className="flex h-14 shrink-0 items-center border-b border-secondary-highlight">
                <Wordmark onNavigate={() => setOpen(false)} />
              </div>
              <ClassicNavigation onNavigate={() => setOpen(false)} />
            </SheetContent>
          </Sheet>
          <Wordmark />
        </div>
        <div className="flex items-center gap-2">
          <GeneralSettings />
          <AccountSettings />
        </div>
      </header>
    </>
  );
}
