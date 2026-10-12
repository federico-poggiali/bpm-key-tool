import { useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, ApiError, type LabelData } from "../api/api";
import { LabelEditor } from "../components/LabelEditor";
import { fileStem, LabelPreview } from "../components/LabelPreview";
import { Skeleton } from "../components/Skeleton";
import { useDebounced } from "../hooks";
import styles from "./LabelPage.module.css";

export default function LabelPage() {
  const id = Number(useParams().id);
  const base = useQuery({
    queryKey: ["label", id], queryFn: () => api.getLabel(id), refetchOnWindowFocus: false,
  });
  const [edited, setEdited] = useState<LabelData | null>(null);
  const label = edited ?? base.data ?? null;
  const settled = useDebounced(label, 250);
  const preview = useQuery({
    queryKey: ["label-render", id, settled],
    queryFn: () => api.renderLabel(id, settled!),
    enabled: settled != null,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });

  if (base.isError) {
    const missing = base.error instanceof ApiError && base.error.status === 404;
    return (
      <div className={styles.missing}>
        <span className="micro">{missing ? "404" : "error"}</span>
        <h1>{missing ? "That record isn't in your library, so there is no label to make." : "Couldn't load this label."}</h1>
        <Link className="ghost" to="/">Back to the library</Link>
      </div>
    );
  }
  if (!label) return <Skeleton rows={6} />;

  const images = preview.data?.images ?? [];
  const warnings = preview.data?.warnings ?? [];

  return (
    <article className={styles.page}>
      <header className={styles.head}>
        <div>
          <span className="micro">label</span>
          <h1>{label.title}</h1>
          <p className={styles.sub}>{label.artist}</p>
        </div>
        <Link className="ghost" to={`/records/${id}`}>Back to the record</Link>
      </header>

      <div className={styles.layout}>
        <LabelEditor value={label} onChange={setEdited} />

        <LabelPreview images={images} warnings={warnings} stem={fileStem(label)} onReset={() => setEdited(null)} canReset={edited != null}
          hint="Edits are for this print only; the record is not changed. Black and white, 696 px wide: ready for a Brother QL with 62 mm tape." />
      </div>
    </article>
  );
}
