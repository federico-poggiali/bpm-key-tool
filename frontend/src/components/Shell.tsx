import { useEffect } from "react";
import { useIsFetching, useQuery } from "@tanstack/react-query";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import { Toasts } from "./Toasts";
import styles from "./Shell.module.css";

const NAV = [
  { to: "/", label: "Library", end: true },
  { to: "/wantlist", label: "Wantlist" },
  { to: "/search", label: "Search" },
  { to: "/add", label: "Add record" },
  { to: "/settings", label: "Settings" },
];

function typing(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  return !!el && (["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName) || el.isContentEditable);
}

export function Shell() {
  const navigate = useNavigate();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.health(signal),
    refetchInterval: 15_000,
    meta: { quiet: true },
  });
  const busy = useIsFetching() > 0;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || typing(e.target)) return;
      if (e.key === "/") {
        e.preventDefault();
        navigate("/search?focus=1");
      } else if (e.key === "n") {
        e.preventDefault();
        navigate("/add");
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navigate]);

  const state = health.isError ? "offline" : health.data ? "ok" : "checking";
  return (
    <div className={styles.shell}>
      <a className={styles.skip} href="#main">
        Skip to content
      </a>
      <aside className={styles.side}>
        <div className={styles.brand}>
          <span className={`${styles.led} ${busy ? styles.busy : state === "ok" ? styles.ok : ""}`} aria-hidden="true" />
          Spin Count
        </div>
        <nav aria-label="Main">
          <ul className={styles.nav}>
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.end} className={({ isActive }) => (isActive ? styles.active : "")}>
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className={styles.foot}>
          <span className="micro" role="status" data-testid="health">
            api {state}
          </span>
          <span className="micro">/ search · n add</span>
        </div>
      </aside>
      <main id="main" className={styles.main} tabIndex={-1}>
        <Outlet />
      </main>
      <Toasts />
    </div>
  );
}
