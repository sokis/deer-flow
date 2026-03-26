"use client";

import { type ReactNode } from "react";

import { ErrorBoundary, type ErrorBoundaryProps } from "./error-boundary";

export function withErrorBoundary<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  errorBoundaryProps?: Omit<ErrorBoundaryProps, "children">,
) {
  function WithErrorBoundaryWrapper(props: P) {
    return (
      <ErrorBoundary {...errorBoundaryProps}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  }

  WithErrorBoundaryWrapper.displayName = `withErrorBoundary(${WrappedComponent.displayName ?? WrappedComponent.name ?? "Component"})`;

  return WithErrorBoundaryWrapper;
}
