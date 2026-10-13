import { useState, type FormEvent } from "react";
import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { api, type LabelData } from "../api/api";
import { LabelEditor } from "../components/LabelEditor";
import { fileStem, LabelPreview } from "../components/LabelPreview";
import { useDebounced } from "../hooks";
import shared from "../styles/intake.module.css";
import styles from "./LabelPage.module.css";

const BLANK: LabelData = { artist: "", title: "", styles: [], hidden: [], tracks: [] };

/** Make a label for a record you do not have: start blank, or paste a Discogs link to fill it in. Nothing is saved. */
export default function LabelMakerPage() {
  const [url, setUrl] = useState("");
  const [start, setStart] = useState<LabelData | null>(null);
  const [edited, setEdited] = useState<LabelData | null>(null);
  const fetchLabel = useMutation({
    mutationFn: () => api.labelFromDiscogs(url.trim()),
    onSuccess: (data) => { setStart(data); setEdited(null); },
  });
  const label = edited ?? start;
  const settled = useDebounced(label, 250);
  const preview = useQuery({
    queryKey: ["label-render", "loose", settled],
    queryFn: () => api.renderLooseLabel(settled!),
    enabled: settled != null && (settled.artist !== "" || settled.title !== ""),
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (url.trim()) fetchLabel.mutate();
  };

  return (
    <div className={styles.page}>
      <header className={shared.hero}>
        <span className="micro">label maker</span>
        <h1>Make a label. <span>Any record.</span></h1>
        <form onSubmit={submit} className={shared.form}>
          <label className={shared.field}>
            <span className="sr">Discogs link</span>
            <input type="url" inputMode="url" required autoComplete="off" placeholder="discogs.com/release/…" value={url} onChange={(e) => setUrl(e.target.value)} />
          </label>
          <button className="primary" type="submit" disabled={fetchLabel.isPending}>{fetchLabel.isPending ? "Fetching…" : "Fetch details"}</button>
          <button className="ghost" type="button" onClick={() => { setStart({ ...BLANK }); setEdited(null); }}>Start blank</button>
        </form>
        <p className={shared.hint}>For records you do not own yet. The record is not added to your library.</p>
        {fetchLabel.isError && <p className={shared.error} role="alert">{fetchLabel.error.message}</p>}
      </header>

      {label && (
        <div className={styles.layout}>
          <LabelEditor value={label} onChange={setEdited} loose />
          <LabelPreview
            images={preview.data?.images ?? []} warnings={preview.data?.warnings ?? []} stem={fileStem(label)}
            onReset={() => setEdited(null)} canReset={edited != null}
            hint="Nothing here is saved. Black and white, 696 px wide: ready for a Brother QL with 62 mm tape."
          />
        </div>
      )}
    </div>
  );
}
