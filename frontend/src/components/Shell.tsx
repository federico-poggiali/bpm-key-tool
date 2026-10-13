import { useEffect } from "react";
import { useIsFetching, useQuery } from "@tanstack/react-query";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api/api";
import { Icon, type IconName } from "./Icon";
import { Toasts } from "./Toasts";
import styles from "./Shell.module.css";

const VIEWS: { to: string; label: string; icon: IconName }[] = [
  { to: "/", label: "Library", icon: "library" },
  { to: "/wantlist", label: "Wishlist", icon: "wishlist" },
  { to: "/crate", label: "Crate", icon: "crate" },
];

const TOOLS: { to: string; label: string; icon: IconName }[] = [
  { to: "/add", label: "Add record", icon: "add" },
  { to: "/labels", label: "Make a label", icon: "label" },
  { to: "/tags", label: "Tag Manager", icon: "tag" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

/** One sidebar group: a quiet caption over a list of links, the current one lifted with a red tick. */
function Group({ title, label, items }: { title: string; label: string; items: typeof VIEWS }) {
  return (
    <nav aria-label={label} className={styles.group}>
      <span className={styles.caption}>{title}</span>
      <ul className={styles.nav}>
        {items.map((item) => (
          <li key={item.to}>
            <NavLink to={item.to} end className={({ isActive }) => (isActive ? styles.active : "")}>
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
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
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        navigate("/search?focus=1");
        return;
      }
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
          <span className={styles.mark} aria-hidden="true" />
          Spin Count
          <span className={`${styles.led} ${busy ? styles.busy : state === "ok" ? styles.ok : ""}`} aria-hidden="true" />
        </div>
        <Link to="/search?focus=1" className={styles.search}>
          <Icon name="search" />
          <span>Search</span>
          <kbd>⌘K</kbd>
        </Link>
        <Group title="Views" label="Library" items={VIEWS} />
        <Group title="Tools" label="Main" items={TOOLS} />
        <div className={styles.foot}>
          <span className={styles.status} role="status" data-testid="health">
            <i data-state={state} aria-hidden="true" />api {state}
          </span>
          <span className={styles.keys}><kbd>/</kbd> search <kbd>n</kbd> add</span>
        </div>
      </aside>
      <main id="main" className={styles.main} tabIndex={-1}>
        <Outlet />
      </main>
      <Toasts />
    </div>
  );
}
