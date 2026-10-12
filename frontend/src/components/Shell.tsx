import { useEffect, useRef, useState } from "react";
import { useIsFetching, useQuery } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import { Toasts } from "./Toasts";
import styles from "./Shell.module.css";

const NAV = [
  { to: "/add", label: "Add record" },
  { to: "/labels", label: "Make a label" },
  { to: "/tags", label: "Tag Manager" },
  { to: "/settings", label: "Settings" },
];

const LIBRARY = [
  { to: "/", label: "Records" },
  { to: "/wantlist", label: "Wishlist" },
  { to: "/crate", label: "Crate" },
];

/** Top-right menu holding the library, the wishlist and the crate (the physical shelf). */
function LibraryMenu() {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const { pathname } = useLocation();
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return;
    const away = (e: MouseEvent) => box.current && !box.current.contains(e.target as Node) && setOpen(false);
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => { document.removeEventListener("mousedown", away); document.removeEventListener("keydown", esc); };
  }, [open]);
  const inLibrary = LIBRARY.some((item) => item.to === pathname);
  return (
    <div className={styles.menu} ref={box}>
      <button type="button" className={`${styles.menuBtn} ${inLibrary ? styles.active : ""}`} aria-expanded={open} aria-haspopup="true" onClick={() => setOpen(!open)}>
        Library <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul className={styles.menuList} aria-label="Library">
          {LIBRARY.map((item) => {
            const on = pathname === item.to;
            return (
              <li key={item.to}>
                <Link to={item.to} className={on ? styles.active : ""} aria-current={on ? "page" : undefined}>{item.label}</Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

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
                <NavLink to={item.to} className={({ isActive }) => (isActive ? styles.active : "")}>
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
      <div className={styles.content}>
        <div className={styles.topbar}><LibraryMenu /></div>
        <main id="main" className={styles.main} tabIndex={-1}>
          <Outlet />
        </main>
      </div>
      <Toasts />
    </div>
  );
}
