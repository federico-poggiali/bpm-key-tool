import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type JobOut } from "../api/api";
import styles from "./JobChip.module.css";

type Props = {
  label: string;
  jobId: number | null;
  idleText?: string;
  onSettled?: (job: JobOut) => void;
  onRetry: () => void;
  retrying?: boolean;
  canStart?: boolean;
};

export function JobChip({ label, jobId, idleText = "not started", onSettled, onRetry, retrying, canStart = true }: Props) {
  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: jobId != null,
    refetchInterval: (q) => (q.state.data && ["done", "failed"].includes(q.state.data.status) ? false : 1500),
    meta: { quiet: true },
  });
  const status = jobId == null ? "idle" : job.data?.status ?? "queued";
  const notified = useRef<number | null>(null);

  useEffect(() => {
    if (job.data && ["done", "failed"].includes(job.data.status) && notified.current !== job.data.id) {
      notified.current = job.data.id;
      onSettled?.(job.data);
    }
  }, [job.data, onSettled]);

  const skipped = job.data?.status === "done" && typeof (job.data.result as { skipped?: string } | null)?.skipped === "string";
  const text =
    status === "idle" ? idleText
    : status === "queued" ? "waiting"
    : status === "running" ? "working…"
    : status === "failed" ? "failed"
    : skipped ? "skipped"
    : "done";

  return (
    <div className={`${styles.chip} ${styles[status]}`} data-status={status} data-testid={`job-${label.toLowerCase().replace(/\s+/g, "-")}`}>
      <span className={styles.pad} aria-hidden="true" />
      <div className={styles.text}>
        <span className="micro">{label}</span>
        <b role="status">{text}</b>
        {status === "failed" && job.data?.error && <small>{job.data.error}</small>}
        {skipped && <small>{(job.data!.result as { skipped: string }).skipped}</small>}
      </div>
      {(status === "failed" || (status === "idle" && canStart)) && (
        <button className="ghost small" onClick={onRetry} disabled={retrying}>
          {status === "failed" ? "Retry" : "Start"}
        </button>
      )}
    </div>
  );
}
