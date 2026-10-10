import { Component, type ErrorInfo, type ReactNode } from "react";
import styles from "./ErrorBoundary.module.css";

type State = { error: Error | null };

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Unhandled UI error", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className={styles.wrap} role="alert">
        <span className="micro">something broke</span>
        <h1>That screen crashed.</h1>
        <p>{this.state.error.message}</p>
        <button className="primary" onClick={() => location.assign("/")}>
          Back to the library
        </button>
      </div>
    );
  }
}
