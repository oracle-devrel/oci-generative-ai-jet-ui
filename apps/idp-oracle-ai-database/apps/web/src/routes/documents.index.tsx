import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { z } from "zod";
import { api } from "../lib/api";
import { Card, Badge, PageHeader } from "../components/ui";

const searchSchema = z.object({
  docType: z.enum(["invoice", "purchase_order", "delivery_note", "unknown"]).optional(),
  status: z
    .enum([
      "pending",
      "text_extracted",
      "classified",
      "fields_extracted",
      "embedded",
      "done",
      "failed",
    ])
    .optional(),
});

export const Route = createFileRoute("/documents/")({
  validateSearch: searchSchema,
  component: DocumentsListPage,
});

function DocumentsListPage() {
  const search = Route.useSearch();
  const navigate = Route.useNavigate();
  const { data, isLoading } = useQuery({
    queryKey: ["documents", search],
    queryFn: () => api.listDocuments({ docType: search.docType, status: search.status, limit: 50 }),
  });

  const items = data?.items ?? [];

  return (
    <>
      <PageHeader title="Documents" />
      <div className="mb-4 flex gap-2">
        <select
          value={search.docType ?? ""}
          onChange={(e) =>
            navigate({ search: { ...search, docType: (e.target.value || undefined) as never } })
          }
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All types</option>
          <option value="invoice">Invoices</option>
          <option value="purchase_order">Purchase orders</option>
          <option value="delivery_note">Delivery notes</option>
          <option value="unknown">Unknown</option>
        </select>
        <select
          value={search.status ?? ""}
          onChange={(e) =>
            navigate({ search: { ...search, status: (e.target.value || undefined) as never } })
          }
          className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="done">Done</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {isLoading ? (
        <Card>Loading…</Card>
      ) : items.length === 0 ? (
        <Card>
          <p className="text-sm text-slate-600">
            No documents yet.{" "}
            <Link to="/upload" className="font-medium text-slate-900 underline">
              Upload one
            </Link>{" "}
            to get started.
          </p>
        </Card>
      ) : (
        <Card className="p-0">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Filename</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((doc) => (
                <tr key={doc.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to="/documents/$id"
                      params={{ id: doc.id }}
                      className="font-medium underline-offset-2 hover:underline"
                    >
                      {doc.originalFilename}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone="type">{doc.docType}</Badge>
                  </td>
                  <td className="px-4 py-3">
                    <Badge tone="status">{doc.status}</Badge>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {(doc.byteSize / 1024).toFixed(1)} KB
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {new Date(doc.createdAt).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </>
  );
}
