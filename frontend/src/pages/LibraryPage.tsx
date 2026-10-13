import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api, type LibraryQuery, type Page, type RecordSummary, type Status, type TrackHit } from "../api/api";
import { SearchPopup } from "../components/SearchPopup";
import { FilterBar } from "../components/FilterBar";
import { RecordGrid, RecordTable, TrackResults } from "../components/LibraryResults";
import { Icon } from "../components/Icon";
import { Pagination } from "../components/Pagination";
import { Skeleton, SkeletonGrid } from "../components/Skeleton";
import { useKeyFormat, useKeysEnabled, useStyles, useTags } from "../hooks";
import { isFiltered, pageSize, parseFilters, serializeFilters, type Filters } from "../libraryParams";
import styles from "./LibraryPage.module.css";

export default function LibraryPage({ defaultStatus }: { defaultStatus: Status }) {
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => parseFilters(params, defaultStatus), [params, defaultStatus]);
  const [keyFormat, setKeyFormat] = useKeyFormat();
  const [keysOn] = useKeysEnabled();
  const [searchOpen, setSearchOpen] = useState(false);
  const tags = useTags();
  const styleCounts = useStyles();

  // Every change is a new history entry, so the back button restores the previous filters.
  const change = (patch: Partial<Filters>) => {
    const next = { ...filters, ...patch };
    if (!("page" in patch)) next.page = 1;
    setParams(serializeFilters(next, defaultStatus));
  };

  const limit = pageSize(filters.view);
  const query: LibraryQuery = {
    q: filters.q || undefined,
    bpm_min: filters.view === "tracks" ? filters.bpmMin : undefined,
    bpm_max: filters.view === "tracks" ? filters.bpmMax : undefined,
    key: filters.view === "tracks" && keysOn ? filters.key : undefined,
    tag: filters.tags,
    style: filters.styles,
    status: filters.status === "all" ? undefined : filters.status,
    limit,
    offset: (filters.page - 1) * limit,
  };
  const tracksView = filters.view === "tracks";
  const result = useQuery<Page<RecordSummary> | Page<TrackHit>>({
    queryKey: ["records", tracksView ? "tracks" : "records", query],
    queryFn: ({ signal }) => (tracksView ? api.listTracks(query, signal) : api.listRecords(query, signal)),
    // Keep the old page while filtering, but never show records in the tracks table or the reverse.
    placeholderData: (prev, prevQuery) => (prevQuery?.queryKey[1] === (tracksView ? "tracks" : "records") ? prev : undefined),
  });

  const title = defaultStatus === "owned" ? "Library" : "Wishlist";
  const data = result.data;
  const empty = data && data.total === 0;
  const filtered = isFiltered(filters, defaultStatus);

  return (
    <div className={styles.page}>
      <header className={styles.head}>
        <div className={styles.title}>
          <h1>{title}</h1>
          {data && <span className={styles.count} data-testid="count">{data.total} {tracksView ? "tracks" : "records"}</span>}
        </div>
        <Link className="primary" to="/add"><Icon name="add" />Add record</Link>
      </header>
      <FilterBar
        filters={filters} defaultStatus={defaultStatus} tags={tags.data ?? []} styleCounts={styleCounts.data ?? []}
        keyFormat={keyFormat} onKeyFormat={setKeyFormat} showKeys={keysOn}
        onOpenSearch={() => setSearchOpen(true)}
        onChange={change} onClear={() => setParams(serializeFilters({ ...filters, q: "", bpmMin: undefined, bpmMax: undefined, key: undefined, tags: [], styles: [], status: defaultStatus, page: 1 }, defaultStatus))}
      />

      {searchOpen && <SearchPopup onClose={() => setSearchOpen(false)} />}

      <section aria-live="polite" aria-busy={result.isFetching} className={result.isPlaceholderData ? styles.stale : undefined}>
        {!data && result.isPending && (filters.view === "grid" ? <SkeletonGrid /> : <Skeleton rows={10} height={44} />)}
        {result.isError && !data && <p className={styles.empty}>Couldn't load the library. Check that the backend is running.</p>}
        {empty && (
          <div className={styles.empty}>
            {filtered ? (
              <>
                <h2>Nothing matches these filters.</h2>
                <p>Loosen the tempo range, drop a tag or style, or clear everything.</p>
                <button className="ghost" onClick={() => setParams(new URLSearchParams())}>Clear filters</button>
              </>
            ) : (
              <>
                <h2>{defaultStatus === "owned" ? "Your library is empty." : "Your wishlist is empty."}</h2>
                <p>Paste a Discogs link to add your first record.</p>
                <Link className="primary" to="/add">Add a record</Link>
              </>
            )}
          </div>
        )}
        {data && data.total > 0 && (
          tracksView ? <TrackResults items={(data as Page<TrackHit>).items} keyFormat={keyFormat} showKeys={keysOn} />
          : filters.view === "table" ? <RecordTable items={(data as Page<RecordSummary>).items} />
          : <RecordGrid items={(data as Page<RecordSummary>).items} />
        )}
        {data && <Pagination page={filters.page} limit={limit} total={data.total} onPage={(page) => change({ page })} />}
      </section>
    </div>
  );
}
