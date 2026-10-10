import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div style={{ display: "grid", gap: 12, justifyItems: "start", paddingTop: "10vh" }}>
      <span className="micro">404</span>
      <h1 style={{ font: "600 2.2rem/1 var(--sans)", letterSpacing: "-0.04em" }}>Nothing here.</h1>
      <Link className="ghost" style={{ display: "inline-flex", alignItems: "center", textDecoration: "none" }} to="/">
        Back to the library
      </Link>
    </div>
  );
}
