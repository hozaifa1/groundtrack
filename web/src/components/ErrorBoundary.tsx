import { Component, type ReactNode } from "react";

/** A view that throws must not leave a blank page. Someone may well open this
 *  page cold with a few minutes to spend, and a white screen tells them
 *  nothing at all. */
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
      <main className="shell">
        <div className="panel note" style={{ marginTop: 64 }}>
          <h3>This part of the page stopped working</h3>
          <p>{error.message}. Reloading usually clears it.</p>
          <button className="tbtn primary" style={{ marginTop: 14 }} onClick={() => location.reload()}>
            Reload
          </button>
        </div>
      </main>
    );
  }
}
