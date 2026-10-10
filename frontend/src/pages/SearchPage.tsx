import { Fragment, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError, type NoteOut, type RecordSummary, type TrackOut } from "../api/api";
import { Cover } from "../components/Cover";
import { Skeleton } from "../components/Skeleton";
import { useDebounced } from "../hooks";
import styles from "./SearchPage.module.css";

type Mode = "meaning" | "exact";

/** Renders an FTS snippet whose matches are wrapped in \x02 ... \x03. */
function Snippet({ text }: { text: string }) {
  return (
    <>
      {text.split("\x02").map((part, i) => {
        const [hit, rest] = part.split("\x03");
        return i === 0 ? <Fragment key={i}>{part}</Fragment> : (
          <Fragment key={i}><mark>{hit}</mark>{rest}</Fragment>
        );
      })}
    </>
  );
}

type Hit = { note: NoteOut; record: { id: number; artist: string; title: string; cover_url: string | null }; track?: TrackOut | null };

function HitCard({ hit, children, score }: { hit: Hit; children: React.ReactNode; score?: number }) {
  return (
    <li>
      <Link to={`/records/${hit.record.id}#note-${hit.note.id}`} className={styles.hit}>
        <Cover url={hit.record.cover_url} size={56} />
        <div className={styles.hitBody}>
          <p className={styles.snippet}>{children}</p>
          <span className={styles.where}>
            <span className={styles.type}>{hit.note.type}</span>
            {hit.track ? `${hit.track.position} ${hit.track.title} · ` : ""}{hit.record.artist} – {hit.record.title}
          </span>
        </div>
        {score != null && (
          <div className={styles.score} title={`similarity ${Math.round(score * 100)}%`}>
            <div className={styles.meter}><i style={{ width: `${Math.round(score * 100)}%` }} /></div>
            <span className="micro">{Math.round(score * 100)}%</span>
          </div>
        )}
      </Link>
    </li>
  );
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const mode: Mode = params.get("mode") === "exact" ? "exact" : "meaning";
  const urlQ = params.get("q") ?? "";
  const [text, setText] = useState(urlQ);
  const q = useDebounced(text.trim(), 300);
  const input = useRef<HTMLInputElement>(null);

  // "/" lands here with ?focus=1, also when the page is already open.
  useEffect(() => { input.current?.focus(); }, [params.get("focus")]);
  useEffect(() => {
    const next = new URLSearchParams(params);
    q ? next.set("q", q) : next.delete("q");
    if (next.toString() !== params.toString()) setParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const setMode = (m: Mode) => {
    const next = new URLSearchParams(params);
    m === "exact" ? next.set("mode", "exact") : next.delete("mode");
    next.delete("focus");
    setParams(next);
  };

  const semantic = useQuery({
    queryKey: ["search", "semantic", q],
    queryFn: ({ signal }) => api.searchSemantic(q, signal),
    enabled: mode === "meaning" && q.length > 0,
    meta: { quiet: true },
  });
  const exact = useQuery({
    queryKey: ["search", "exact", q],
    queryFn: ({ signal }) => api.searchExact(q, signal),
    enabled: mode === "exact" && q.length > 0,
  });

  const unavailable = semantic.error instanceof ApiError && semantic.error.status === 503;
  const active = mode === "meaning" ? semantic : exact;

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <span className="micro">search</span>
        <h1>{mode === "meaning" ? "Search by meaning" : "Search exact words"}</h1>
      </header>
      <div className={styles.controls}>
        <label className={styles.field}>
          <span className="sr">Search your notes</span>
          <input ref={input} type="search" autoFocus autoComplete="off" value={text} onChange={(e) => setText(e.target.value)}
            placeholder={mode === "meaning" ? "crowd goes crazy, slow burner, warm bassline…" : "words in a note, an artist, a title"} />
        </label>
        <div className={styles.modes} role="group" aria-label="Search mode">
          <button type="button" aria-pressed={mode === "meaning"} onClick={() => setMode("meaning")}>By meaning</button>
          <button type="button" aria-pressed={mode === "exact"} onClick={() => setMode("exact")}>Exact</button>
        </div>
      </div>

      {q === "" && <p className={styles.hint}>{mode === "meaning" ? "Describe what you remember. Notes of type “prose” are searched by what they mean, not the words they use." : "Matches whole words and word starts in every note, plus record artist, title and label."}</p>}
      {q !== "" && active.isFetching && !active.data && <Skeleton rows={4} height={72} />}

      {mode === "meaning" && unavailable && (
        <div className={styles.notice} role="status">
          <b>Search by meaning isn't set up yet.</b>
          <p>No embedding model is configured, so notes are only searchable by their words for now.</p>
          <button className="ghost" onClick={() => setMode("exact")}>Use exact search</button>
        </div>
      )}
      {mode === "meaning" && semantic.data && (
        semantic.data.length === 0
          ? <p className={styles.hint}>No prose notes are close to that.</p>
          : <ul className={styles.results} aria-label="Results">
              {semantic.data.map((h) => <HitCard key={h.note.id} hit={h} score={h.score}>{h.note.body}</HitCard>)}
            </ul>
      )}
      {mode === "exact" && exact.data && (
        exact.data.notes.length === 0 && exact.data.records.length === 0
          ? <p className={styles.hint}>Nothing matches “{q}”.</p>
          : <>
              {exact.data.notes.length > 0 && (
                <ul className={styles.results} aria-label="Matching notes">
                  {exact.data.notes.map((h) => <HitCard key={h.note.id} hit={h}><Snippet text={h.snippet} /></HitCard>)}
                </ul>
              )}
              {exact.data.records.length > 0 && (
                <section aria-label="Matching records">
                  <h2 className="micro">records</h2>
                  <ul className={styles.recs}>
                    {exact.data.records.map((r: Pick<RecordSummary, "id" | "artist" | "title" | "cover_url">) => (
                      <li key={r.id}><Link to={`/records/${r.id}`}><Cover url={r.cover_url} size={40} /><span><b>{r.title}</b><small>{r.artist}</small></span></Link></li>
                    ))}
                  </ul>
                </section>
              )}
            </>
      )}
    </div>
  );
}
