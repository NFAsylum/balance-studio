"use client";
import * as React from "react";

/** Generic error boundary: a crashing subtree shows a recoverable message instead of taking
 * down the whole app. Wrap panels that render server/LLM data. */

interface Props {
  children: React.ReactNode;
  label?: string;
}
interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }
  componentDidCatch(error: unknown): void {
    console.error("UI error boundary caught:", error);
  }
  reset = () => this.setState({ error: null });

  render(): React.ReactNode {
    if (this.state.error) {
      return (
        <div
          data-testid="error-boundary"
          className="flex flex-col items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-center"
        >
          <span className="text-2xl">💥</span>
          <p className="text-sm font-medium">{this.props.label ?? "Something went wrong."}</p>
          <p className="max-w-md text-xs text-muted-foreground">{this.state.error.message}</p>
          <button onClick={this.reset} className="rounded-md border border-border px-3 py-1 text-sm hover:bg-accent">
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
