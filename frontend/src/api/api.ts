import type { components } from "./schema";

type S = components["schemas"];
export type RecordDetail = S["RecordDetail"];
export type RecordSummary = S["RecordSummary"];
export type RecordPatch = S["RecordPatch"];
export type TrackOut = S["TrackOut"];
export type TrackHit = S["TrackHit"];
export type TrackPatch = Partial<S["TrackPatch"]>;
export type NoteOut = S["NoteOut"];
export type NoteCreate = S["NoteCreate"];
export type NotePatch = S["NotePatch"];
export type IntakeResponse = S["IntakeResponse"];
export type JobOut = S["JobOut"];
export type AudioMatchReport = S["AudioMatchReport"];
export type ExactResults = S["ExactResults"];
export type SemanticHit = S["SemanticHit"];
export type TagCount = S["TagCount"];
export type VaultStatus = S["VaultStatus"];
export type VaultSyncOut = S["VaultSyncOut"];
export type Status = RecordSummary["status"];
export type Page<T> = { items: T[]; total: number; limit: number; offset: number };

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown,
  ) {
    super(message);
  }
}

type Query = Record<string, string | number | boolean | string[] | null | undefined>;

function toSearch(query?: Query): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => params.append(key, v));
    else params.append(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export async function request<T>(
  method: string,
  path: string,
  opts: { query?: Query; body?: unknown; signal?: AbortSignal } = {},
): Promise<{ data: T; status: number }> {
  let response: Response;
  try {
    response = await fetch(path + toSearch(opts.query), {
      method,
      headers: opts.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: opts.signal,
    });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Can't reach the server. Is the backend running?");
  }
  if (!response.ok) {
    let code = "error";
    let message = `Request failed (${response.status})`;
    let details: unknown;
    try {
      const body = await response.json();
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
      details = body.error?.details;
    } catch {
      /* not JSON */
    }
    throw new ApiError(response.status, code, message, details);
  }
  const data = response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  return { data, status: response.status };
}

const get = async <T>(path: string, query?: Query, signal?: AbortSignal) =>
  (await request<T>("GET", path, { query, signal })).data;
const send = async <T>(method: string, path: string, body?: unknown) =>
  (await request<T>(method, path, { body })).data;

export type LibraryQuery = {
  q?: string;
  bpm_min?: number;
  bpm_max?: number;
  key?: string;
  tag?: string[];
  status?: Status;
  limit?: number;
  offset?: number;
};

export const api = {
  health: (signal?: AbortSignal) => get<{ status: string }>("/health", undefined, signal),

  listRecords: (query: LibraryQuery, signal?: AbortSignal) =>
    get<Page<RecordSummary>>("/api/records", query, signal),
  listTracks: (query: LibraryQuery, signal?: AbortSignal) =>
    get<Page<TrackHit>>("/api/tracks", query, signal),
  getRecord: (id: number) => get<RecordDetail>(`/api/records/${id}`),
  patchRecord: (id: number, body: RecordPatch) => send<RecordDetail>("PATCH", `/api/records/${id}`, body),
  deleteRecord: (id: number) => send<void>("DELETE", `/api/records/${id}`),
  intake: (body: { discogs_url: string; status: Status }) =>
    request<IntakeResponse>("POST", "/api/records/intake", { body }),
  analyze: (id: number) => send<{ job_id: number }>("POST", `/api/records/${id}/analyze`),
  syncDiscogs: (id: number) => send<{ job_id: number }>("POST", `/api/records/${id}/sync-discogs`),
  audioMatch: (id: number) => get<AudioMatchReport>(`/api/records/${id}/audio-match`),
  getJob: (id: number) => get<JobOut>(`/api/jobs/${id}`),

  patchTrack: (id: number, body: TrackPatch) => send<TrackOut>("PATCH", `/api/tracks/${id}`, body),
  assignAudio: (id: number, file: string) => send<TrackOut>("POST", `/api/tracks/${id}/audio`, { file }),
  unassignAudio: (id: number) => send<TrackOut>("DELETE", `/api/tracks/${id}/audio`),

  createNote: (body: NoteCreate) => send<NoteOut>("POST", "/api/notes", body),
  patchNote: (id: number, body: NotePatch) => send<NoteOut>("PATCH", `/api/notes/${id}`, body),
  deleteNote: (id: number) => send<void>("DELETE", `/api/notes/${id}`),

  listTags: () => get<{ items: TagCount[] }>("/api/tags"),
  addTag: (kind: "record" | "track", id: number, name: string) =>
    send<string[]>("POST", `/api/${kind}s/${id}/tags`, { name }),
  removeTag: (kind: "record" | "track", id: number, name: string) =>
    send<string[]>("DELETE", `/api/${kind}s/${id}/tags/${encodeURIComponent(name)}`),

  searchExact: (q: string, signal?: AbortSignal) => get<ExactResults>("/api/search/exact", { q }, signal),
  searchSemantic: (q: string, signal?: AbortSignal) => get<SemanticHit[]>("/api/search/semantic", { q }, signal),

  vaultStatus: () => get<VaultStatus>("/api/admin/vault-status"),
  syncVault: () => send<VaultSyncOut>("POST", "/api/admin/sync-vault"),
  openVault: () => send<{ opened: boolean; path: string }>("POST", "/api/admin/open-vault"),
};
