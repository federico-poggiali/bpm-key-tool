import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api, type LibraryQuery, type Page, type RecordSummary, type Status, type TrackHit } from "../api/api";
import { FilterBar } from "../components/FilterBar";
import { RecordGrid, RecordTable, TrackResults } from "../components/LibraryResults";
import { Pagination } from "../components/Pagination";
import { Skeleton, SkeletonGrid } from "../components/Skeleton";
import { useKeyFormat, useTags } from "../hooks";
import { isFiltered, pageSize, parseFilters, serializeFilters, type Filters } from "../libraryParams";
import styles from "./LibraryPage.module.css";

export default function LibraryPage({ defaultStatus }: { defaultStatus: Status }) {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => parseFilters(params, defaultStatus), [params, defaultStatus]);
  const [keyFormat, setKeyFormat] = useKeyFormat();
  const tags = useTags();

  // Every change is a new history entry, so the back button restores the previous filters.
  const change = (patch: Partial<Filters>) => {
    const next = { ...filters, ...patch };
    if (!("page" in patch)) next.page = 1;
    setParams(serializeFilters(next, defaultStatus));
  };

  const limit = pageSize(filters.view);
  const query: LibraryQuery = {
    q: filters.q || undefined,
    bpm_min: filters.bpmMin,
    bpm_max: filters.bpmMax,
    key: filters.key,
    tag: filters.tags,
    status: filters.status === "all" ? undefined : filters.status,
    limit,
    offset: (filters.page - 1) * limit,
  };
  const tracksView = filters.view === "tracks";
  const result = useQuery<Page<RecordSummary> | Page<TrackHit>>({
    queryKey: ["records", tracksView ? "tracks" : "records", query],
    queryFn: ({ signal }) => (tracksView ? api.listTracks(query, signal) : api.listRecords(query, signal)),
    placeholderData: keepPreviousData,
  });

  const title = defaultStatus === "owned" ? "Library" : "Wantlist";
  const data = result.data;
  const empty = data && data.total === 0;
  const filtered = isFiltered(filters, defaultStatus);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div>
          <span className="micro">{tracksView ? "tracks" : "records"}</span>
          <h1>{title}</h1>
        </div>
        {data && <span className={styles.count} data-testid="count">{data.total} {tracksView ? "tracks" : "records"}</span>}
      </header>

      <FilterBar
        filters={filters} defaultStatus={defaultStatus} tags={tags.data ?? []}
        keyFormat={keyFormat} onKeyFormat={setKeyFormat}
        onChange={change} onClear={() => setParams(serializeFilters({ ...filters, q: "", bpmMin: undefined, bpmMax: undefined, key: undefined, tags: [], status: defaultStatus, page: 1 }, defaultStatus))}
      />

      <section aria-live="polite" aria-busy={result.isFetching} className={result.isPlaceholderData ? styles.stale : undefined}>
        {!data && result.isPending && (filters.view === "grid" ? <SkeletonGrid /> : <Skeleton rows={8} height={52} />)}
        {result.isError && !data && <p className={styles.empty}>Couldn't load the library. Check that the backend is running.</p>}
        {empty && (
          <div className={styles.empty}>
            {filtered ? (
              <>
                <h2>Nothing matches these filters.</h2>
                <p>Loosen the tempo range, drop a tag, or clear everything.</p>
                <button className="ghost" onClick={() => setParams(new URLSearchParams())}>Clear filters</button>
              </>
            ) : (
              <>
                <h2>{defaultStatus === "owned" ? "Your library is empty." : "Your wantlist is empty."}</h2>
                <p>Paste a Discogs link and the tempo and key come with it.</p>
                <Link className="primary" style={{ display: "inline-flex", alignItems: "center", textDecoration: "none" }} to="/add">Add a record</Link>
              </>
            )}
          </div>
        )}
        {data && data.total > 0 && (
          tracksView ? <TrackResults items={(data as Page<TrackHit>).items} keyFormat={keyFormat} />
          : filters.view === "table" ? <RecordTable items={(data as Page<RecordSummary>).items} keyFormat={keyFormat} />
          : <RecordGrid items={(data as Page<RecordSummary>).items} keyFormat={keyFormat} />
        )}
        {data && <Pagination page={filters.page} limit={limit} total={data.total} onPage={(page) => change({ page })} />}
      </section>
    </div>
  );
}
