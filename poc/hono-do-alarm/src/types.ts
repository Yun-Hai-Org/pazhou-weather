export type Slot = "am" | "pm";

export interface AppConfig {
  appEnv: string;
  apiKey: string;
  apiHost: string;
  cityName: string;
  location: string;
  coords: string;
  prodWebhooks: string[];
  devWebhooks: string[];
  pagesBaseUrl: string;
  pagesProject: string;
  accountId: string;
  apiToken: string;
  skipSend: boolean;
}

export interface WeatherSnapshot {
  now: Record<string, string>;
  hourly: Array<Record<string, string>>;
  daily7: Array<Record<string, string>>;
  warnings: Record<string, unknown>[];
  indices: Record<string, string>[];
  air: Record<string, unknown> | null;
  sun: Record<string, unknown> | null;
  moon: Record<string, unknown> | null;
}

export interface Holiday {
  label: "法定工作日" | "休息日";
  source: "holiday-cn" | "weekend-fallback";
}

export interface Poetry {
  content: string;
  author: string;
  origin: string;
}

export interface SolarTermMeta {
  name: string;
  poem: string;
  author: string;
  origin: string;
}

export interface SolarTerm extends SolarTermMeta {
  termIndex: number;
  imageUrl: string;
}

export interface ReportContext {
  slot: Slot;
  requestId: string;
  date: string;
  time: string;
  weekday: string;
  holiday: Holiday;
  city: string;
  weather: WeatherSnapshot;
  solarTerm: SolarTerm | null;
  poetry: Poetry;
  imageUrl: string;
  jumpUrl: string;
}

export interface KVNamespace {
  get(key: string, type?: string): Promise<string | null>;
  get(key: string, type: "arrayBuffer"): Promise<ArrayBuffer | null>;
  put(key: string, value: string): Promise<void>;
  delete(key: string): Promise<void>;
}

export interface Env extends Record<string, unknown> {
  SLOT_DO: DurableObjectNamespace;
  ASSETS: KVNamespace;
  PUBLIC_PAGE_TOKEN?: string;
}
