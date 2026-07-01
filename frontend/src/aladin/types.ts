/** Minimal Aladin Lite v3 globals (https://aladin.cds.unistra.fr/AladinLite/doc/API/) */

export type AladinSource = {
  ra?: number;
  dec?: number;
  lon?: number;
  lat?: number;
  name?: string;
  [key: string]: unknown;
};

export type AladinCatalog = {
  addSources: (sources: AladinSource[]) => void;
  remove: () => void;
};

export type AladinInstance = {
  setProjection: (proj: string) => void;
  setImageSurvey: (surveyId: string) => void;
  setBaseImageLayer: (layer: unknown) => void;
  setOverlayImageLayer: (layer: unknown, name?: string) => void;
  createImageSurvey: (
    name: string,
    id: string,
    url: string,
    frame: string,
    options?: Record<string, unknown>,
  ) => unknown;
  newImageSurvey: (hipsId: string) => unknown;
  addCatalog: (catalog: AladinCatalog) => void;
  removeCatalog: (catalog: AladinCatalog) => void;
  setFoV: (fov: number) => void;
  gotoRaDec: (ra: number, dec: number) => void;
  getFov: () => number;
};

export type AladinFactory = {
  init: Promise<void>;
  aladin: (target: string | HTMLElement, options?: Record<string, unknown>) => AladinInstance;
  catalog: (options?: Record<string, unknown>) => AladinCatalog;
};

declare global {
  interface Window {
    A?: AladinFactory;
  }
}

export const ALADIN_SCRIPT =
  "https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js";

export function loadAladin(): Promise<AladinFactory> {
  if (window.A) return window.A.init.then(() => window.A as AladinFactory);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = ALADIN_SCRIPT;
    script.charset = "utf-8";
    script.async = true;
    script.onload = () => {
      if (!window.A) {
        reject(new Error("Aladin Lite failed to load"));
        return;
      }
      window.A.init.then(() => resolve(window.A as AladinFactory));
    };
    script.onerror = () => reject(new Error("Could not load Aladin Lite from CDS"));
    document.head.appendChild(script);
  });
}
