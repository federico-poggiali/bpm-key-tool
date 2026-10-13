import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type NoteCreate, type NotePatch, type RecordDetail, type RecordPatch, type TrackPatch } from "./api/api";
import { keyByCamelot, type KeyFormat } from "./lib";

export function useDebounced<T>(value: T, ms = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(timer);
  }, [value, ms]);
  return debounced;
}

export const recordKey = (id: number) => ["record", id] as const;

export function useRecord(id: number, refetchWhileBusy = false) {
  return useQuery({
    queryKey: recordKey(id),
    queryFn: () => api.getRecord(id),
    enabled: id > 0,
    refetchInterval: refetchWhileBusy ? 2500 : false,
  });
}

export function useTags() {
  return useQuery({ queryKey: ["tags"], queryFn: () => api.listTags().then((r) => r.items) });
}

export function useStyles() {
  return useQuery({ queryKey: ["styles"], queryFn: () => api.listStyles().then((r) => r.items) });
}

/** A mutation that patches the cached record immediately and rolls back if the server refuses. */
function useRecordMutation<V, R = unknown>(
  id: number,
  mutationFn: (v: V) => Promise<R>,
  optimistic: (record: RecordDetail, v: V) => RecordDetail,
  alsoInvalidate: string[] = [],
) {
  const client = useQueryClient();
  return useMutation({
    mutationFn,
    onMutate: async (v: V) => {
      await client.cancelQueries({ queryKey: recordKey(id) });
      const previous = client.getQueryData<RecordDetail>(recordKey(id));
      if (previous) client.setQueryData(recordKey(id), optimistic(previous, v));
      return { previous };
    },
    onError: (_error, _v, context) => {
      if (context?.previous) client.setQueryData(recordKey(id), context.previous);
    },
    onSettled: () => {
      client.invalidateQueries({ queryKey: recordKey(id) });
      alsoInvalidate.forEach((key) => client.invalidateQueries({ queryKey: [key] }));
    },
  });
}

const mapTrack = (record: RecordDetail, trackId: number, fn: (t: RecordDetail["tracks"][number]) => RecordDetail["tracks"][number]) => ({
  ...record,
  tracks: record.tracks.map((t) => (t.id === trackId ? fn(t) : t)),
});

export function usePatchTrack(recordId: number) {
  return useRecordMutation(
    recordId,
    ({ trackId, patch }: { trackId: number; patch: TrackPatch }) => api.patchTrack(trackId, patch),
    (record, { trackId, patch }) =>
      mapTrack(record, trackId, (t) => {
        const key = patch.key ? keyByCamelot(patch.key.toUpperCase()) : undefined;
        return {
          ...t,
          ...(patch.bpm != null ? { bpm: patch.bpm, bpm_manual: true } : {}),
          ...(patch.key ? { key: key?.name ?? patch.key, camelot_key: key?.camelot ?? t.camelot_key, key_manual: true } : {}),
          ...(patch.unlock?.includes("bpm") ? { bpm_manual: false } : {}),
          ...(patch.unlock?.includes("key") ? { key_manual: false } : {}),
        };
      }),
  );
}

export function usePatchRecord(recordId: number) {
  return useRecordMutation(
    recordId,
    (patch: RecordPatch) => api.patchRecord(recordId, patch),
    (record, patch) => ({ ...record, ...(patch as Partial<RecordDetail>) }),
    ["records"],
  );
}

/** Edit a record's styles (locks them against Discogs) or reset them to Discogs' own list. */
export function useStyleMutations(recordId: number) {
  const set = useRecordMutation(
    recordId,
    (styles: string[]) => api.patchRecord(recordId, { styles }),
    (record, styles) => ({ ...record, styles, styles_manual: true, tracks: record.tracks.map((t) => ({ ...t, styles })) }),
    ["records", "styles"],
  );
  const reset = useRecordMutation(recordId, () => api.patchRecord(recordId, { reset_styles: true }), (record) => record, ["records", "styles"]);
  return { set, reset };
}

export function useNoteMutations(recordId: number) {
  const create = useRecordMutation(recordId, (body: NoteCreate) => api.createNote(body), (r) => r, ["records"]);
  const patch = useRecordMutation(
    recordId,
    ({ id, body }: { id: number; body: NotePatch }) => api.patchNote(id, body),
    (record, { id, body }) => {
      const update = (n: RecordDetail["notes"][number]) => (n.id === id ? { ...n, ...(body as object) } : n);
      return { ...record, notes: record.notes.map(update), tracks: record.tracks.map((t) => ({ ...t, notes: t.notes.map(update) })) };
    },
  );
  const remove = useRecordMutation(
    recordId,
    (id: number) => api.deleteNote(id),
    (record, id) => ({
      ...record,
      notes: record.notes.filter((n) => n.id !== id),
      tracks: record.tracks.map((t) => ({ ...t, notes: t.notes.filter((n) => n.id !== id) })),
    }),
    ["records"],
  );
  return { create, patch, remove };
}

export function useTagGroups() {
  return useQuery({ queryKey: ["tag-groups"], queryFn: api.listTagGroups });
}

export function useTagMutations(recordId: number) {
  const add = useRecordMutation(
    recordId,
    ({ kind, id, name }: { kind: "record" | "track"; id: number; name: string }) => api.addTag(kind, id, name),
    (record, { kind, id, name }) => {
      const tag = name.trim().toLowerCase();
      const withTag = (tags: string[]) => (tags.includes(tag) ? tags : [...tags, tag].sort());
      return kind === "record"
        ? { ...record, tags: withTag(record.tags ?? []) }
        : mapTrack(record, id, (t) => ({ ...t, tags: withTag(t.tags ?? []) }));
    },
    ["tags"],
  );
  const remove = useRecordMutation(
    recordId,
    ({ kind, id, name }: { kind: "record" | "track"; id: number; name: string }) => api.removeTag(kind, id, name),
    (record, { kind, id, name }) => {
      const without = (tags: string[]) => tags.filter((t) => t !== name);
      return kind === "record"
        ? { ...record, tags: without(record.tags ?? []) }
        : mapTrack(record, id, (t) => ({ ...t, tags: without(t.tags ?? []) }));
    },
    ["tags"],
  );
  return { add, remove };
}

const FORMAT_STORAGE = "spincount.keyformat";

/** Camelot or musical key labels, remembered per browser. */
export function useKeyFormat(): [KeyFormat, (f: KeyFormat) => void] {
  const [format, setFormat] = useState<KeyFormat>(() => {
    try {
      return localStorage.getItem(FORMAT_STORAGE) === "musical" ? "musical" : "camelot";
    } catch {
      return "camelot";
    }
  });
  const set = (f: KeyFormat) => {
    setFormat(f);
    try {
      localStorage.setItem(FORMAT_STORAGE, f);
    } catch {
      /* private mode: the choice just is not remembered */
    }
  };
  return [format, set];
}

const KEYS_STORAGE = "spincount.keys";
const KEYS_EVENT = "spincount-keys";

/** Whether musical keys are analysed and shown anywhere. Off unless switched on in Settings;
 *  remembered per browser. BPM is always shown regardless. */
export function useKeysEnabled(): [boolean, (on: boolean) => void] {
  const read = () => {
    try {
      return localStorage.getItem(KEYS_STORAGE) === "on";
    } catch {
      return false;
    }
  };
  const [on, setOn] = useState(read);
  useEffect(() => {
    const sync = () => setOn(read());
    window.addEventListener(KEYS_EVENT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(KEYS_EVENT, sync); window.removeEventListener("storage", sync); };
  }, []);
  const set = (next: boolean) => {
    setOn(next);
    try {
      localStorage.setItem(KEYS_STORAGE, next ? "on" : "off");
    } catch {
      /* private mode: the choice just is not remembered */
    }
    window.dispatchEvent(new Event(KEYS_EVENT));
  };
  return [on, set];
}
