import { useSyncExternalStore } from "react";

export type Toast = { id: number; message: string; kind: "error" | "info" };

let toasts: Toast[] = [];
let nextId = 1;
const listeners = new Set<() => void>();
const emit = () => listeners.forEach((l) => l());

export function pushToast(message: string, kind: Toast["kind"] = "error", ms = 6000) {
  if (toasts.some((t) => t.message === message)) return; // one toast per distinct problem
  const toast = { id: nextId++, message, kind };
  toasts = [...toasts, toast];
  emit();
  setTimeout(() => dismissToast(toast.id), ms);
}

export function dismissToast(id: number) {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

export function useToasts(): Toast[] {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => toasts,
  );
}
