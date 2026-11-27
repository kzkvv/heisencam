export const DOCS_URL = "https://docs.heisen.cam/";

export function documentationUrl(path: string) {
  return new URL(path.replace(/^\//, ""), DOCS_URL).href;
}

export function useDocDomain() {
  return { getLocaleDocUrl: documentationUrl };
}
