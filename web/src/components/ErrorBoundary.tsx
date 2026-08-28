import { Component, type ReactNode } from "react";

/** A view that throws must not leave a blank page. This console is meant to be
 *  opened cold by someone evaluating the project, and a white screen is the
 *  one failure mode that tells them nothing at all. */
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { error: Error | null }
> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className="empty" style={{ padding: "var(--s-8)" }}>
        <h3>This view stopped rendering</h3>
        <p>
          {error.message}. The console reads static JSON from <code>public/data</code>. If that data
          was regenerated while the page was open, reloading usually clears it.
        </p>
        <button className="control" onClick={() => location.reload()}>
          Reload the console
        </button>
      </div>
    );
  }
}
