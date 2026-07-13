"use client";
import * as React from "react";
import DefaultListView from "./DefaultListView";
import type { EntityView, EntityViewProps } from "./types";

/** Renders a view inside an error boundary. If the view (often a user-supplied custom one)
 * throws, we fall back to the always-works DefaultListView and show a small warning — a broken
 * layout never takes down the board. */

interface Props extends EntityViewProps {
  view: EntityView;
}
interface State {
  failed: boolean;
}

export class SafeView extends React.Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: unknown): void {
    console.error(`view "${this.props.view.id}" crashed — falling back to default:`, error);
  }

  render(): React.ReactNode {
    const { view, ...props } = this.props;
    if (this.state.failed) {
      return (
        <div className="flex flex-col gap-1" data-testid="view-fallback">
          <p className="text-xs text-destructive">
            ⚠ “{view.name}” failed to render — showing the default view.
          </p>
          <DefaultListView {...props} />
        </div>
      );
    }
    const Component = view.component;
    return <Component {...props} />;
  }
}
