import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, type Status } from "../api/api";
import type { Arrival } from "./RecordPage";
import shared from "../styles/intake.module.css";
import styles from "./AddRecordPage.module.css";

// Nothing picked means "considering": it only keeps it on a list. Owned and wantlist are opt-in toggles.
const ADD_AS: Status[] = ["wantlist", "owned"];

export default function AddRecordPage() {
  const client = useQueryClient();
  const navigate = useNavigate();
  const [url, setUrl] = useState("");
  const [status, setStatus] = useState<Status>("considering");

  // A pasted release goes straight to its record page, which shows the jobs it started.
  const intake = useMutation({
    mutationFn: () => api.intake({ discogs_url: url.trim(), status }),
    onSuccess: ({ data, status: http }) => {
      client.invalidateQueries({ queryKey: ["records"] });
      client.invalidateQueries({ queryKey: ["crate"] });
      const arrival: Arrival = { existed: http === 200, fromMaster: data.resolved_from_master != null, askShelf: data.status === "owned" };
      navigate(`/records/${data.id}`, { state: arrival });
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) intake.mutate();
  };

  return (
    <div className={styles.page}>
      <header className={shared.hero}>
        <span className="micro">add record</span>
        <h1>Paste a record. <span>We'll do the rest ;-)</span></h1>
        <form onSubmit={submit} className={shared.form}>
          <label className={shared.field}>
            <span className="sr">Discogs link</span>
            <input
              type="url" inputMode="url" required autoFocus autoComplete="off"
              placeholder="discogs.com/release/…" value={url} onChange={(e) => setUrl(e.target.value)}
            />
          </label>
          <button className="primary" type="submit" disabled={intake.isPending}>
            {intake.isPending ? "Adding…" : "Add record"}
          </button>
        </form>
        <fieldset className={styles.status}>
          <legend className="micro">add as</legend>
          {ADD_AS.map((s) => (
            <button key={s} type="button" aria-pressed={status === s} className={status === s ? styles.on : ""}
              onClick={() => setStatus(status === s ? "considering" : s)}>
              {s}
            </button>
          ))}
        </fieldset>
        <p className={shared.hint}>Release or master links both work. Pick nothing and it is only considered. Click a choice again to undo it.</p>
        {intake.isError && <p className={shared.error} role="alert">{intake.error.message}</p>}
      </header>
    </div>
  );
}
