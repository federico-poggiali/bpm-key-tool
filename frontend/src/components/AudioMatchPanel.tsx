import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/api";
import { recordKey } from "../hooks";
import styles from "./AudioMatchPanel.module.css";

/** Shows how files in audio/<release_id>/ line up with the tracks, and lets you fix mismatches by hand. */
export function AudioMatchPanel({ recordId, onAssigned }: { recordId: number; onAssigned?: () => void }) {
  const client = useQueryClient();
  const report = useQuery({ queryKey: ["audio-match", recordId], queryFn: () => api.audioMatch(recordId), meta: { quiet: true } });
  const [choice, setChoice] = useState<Record<string, string>>({});

  const assign = useMutation({
    mutationFn: ({ trackId, file }: { trackId: number; file: string }) => api.assignAudio(trackId, file),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["audio-match", recordId] });
      client.invalidateQueries({ queryKey: recordKey(recordId) });
      onAssigned?.();
    },
  });

  const data = report.data;
  if (!data || (data.matched.length === 0 && data.unmatched_files.length === 0)) return null;

  return (
    <section className={styles.panel} aria-label="Audio files">
      <div className={styles.head}>
        <span className="micro">audio files</span>
        <span className={styles.count}>{data.matched.length} matched · {data.unmatched_files.length} unmatched</span>
      </div>
      {data.unmatched_files.length > 0 && (
        <ul className={styles.list}>
          {data.unmatched_files.map((f) => (
            <li key={f.file}>
              <div>
                <b>{f.file}</b>
                <small>{f.reason}</small>
              </div>
              <label className="sr" htmlFor={`assign-${f.file}`}>Track for {f.file}</label>
              <select
                id={`assign-${f.file}`} className="field-input"
                value={choice[f.file] ?? ""}
                onChange={(e) => setChoice({ ...choice, [f.file]: e.target.value })}
              >
                <option value="">Assign to track…</option>
                {data.unmatched_tracks.map((t) => (
                  <option key={t.track_id} value={t.track_id}>{t.position} {t.title}</option>
                ))}
              </select>
              <button
                className="ghost small"
                disabled={!choice[f.file] || assign.isPending}
                onClick={() => assign.mutate({ trackId: Number(choice[f.file]), file: f.file })}
              >
                Assign
              </button>
            </li>
          ))}
        </ul>
      )}
      {data.unmatched_files.length > 0 && data.unmatched_tracks.length === 0 && (
        <p className={styles.note}>Every track already has a file; unassign one to reuse a file.</p>
      )}
      {data.unmatched_tracks.length > 0 && data.matched.length + data.unmatched_files.length > 0 && (
        <p className={styles.note}>
          Tracks without audio: {data.unmatched_tracks.map((t) => t.position || t.title).join(", ")}
        </p>
      )}
    </section>
  );
}
