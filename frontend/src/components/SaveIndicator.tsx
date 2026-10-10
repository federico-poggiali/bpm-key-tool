import { useIsMutating } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

/** "Saving…" while any edit is in flight, then a brief "Saved". */
export function SaveIndicator() {
  const pending = useIsMutating();
  const [saved, setSaved] = useState(false);
  const was = useRef(0);

  useEffect(() => {
    if (was.current > 0 && pending === 0) {
      setSaved(true);
      const timer = setTimeout(() => setSaved(false), 2500);
      was.current = pending;
      return () => clearTimeout(timer);
    }
    was.current = pending;
  }, [pending]);

  return (
    <span className="micro" role="status" aria-live="polite" data-testid="save-indicator">
      {pending > 0 ? "Saving…" : saved ? "Saved" : ""}
    </span>
  );
}
