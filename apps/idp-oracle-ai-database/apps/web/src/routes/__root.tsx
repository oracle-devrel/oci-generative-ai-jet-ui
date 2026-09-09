import { createRootRouteWithContext, Link, Outlet } from "@tanstack/react-router";
import type { QueryClient } from "@tanstack/react-query";

export interface RouterContext {
  queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold tracking-tight">
            IDP <span className="text-slate-400">·</span>{" "}
            <span className="text-slate-500">Oracle AI Database</span>
          </Link>
          <nav className="flex gap-4 text-sm">
            <Link
              to="/upload"
              className="text-slate-600 hover:text-slate-900"
              activeProps={{ className: "text-slate-900 font-medium" }}
            >
              Upload
            </Link>
            <Link
              to="/documents"
              className="text-slate-600 hover:text-slate-900"
              activeProps={{ className: "text-slate-900 font-medium" }}
            >
              Documents
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  ),
});
