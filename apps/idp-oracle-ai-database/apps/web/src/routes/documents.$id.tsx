import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Card, Badge, PageHeader } from "../components/ui";
import { InvoiceView } from "../features/detail/InvoiceView";
import { PurchaseOrderView } from "../features/detail/PurchaseOrderView";
import { DeliveryNoteView } from "../features/detail/DeliveryNoteView";
import type { InvoiceFields, PurchaseOrderFields, DeliveryNoteFields } from "@idp/schemas";

export const Route = createFileRoute("/documents/$id")({
  component: DocumentDetailPage,
});

function DocumentDetailPage() {
  const { id } = Route.useParams();
  const { data: doc, isLoading } = useQuery({
    queryKey: ["documents", id],
    queryFn: () => api.getDocument(id),
  });
  const { data: similar } = useQuery({
    queryKey: ["similar", id],
    queryFn: () => api.similarDocuments(id, 5),
    enabled: doc?.status === "done",
  });

  if (isLoading) return <Card>Loading…</Card>;
  if (!doc) return <Card>Not found.</Card>;

  return (
    <>
      <PageHeader
        title={doc.originalFilename}
        action={
          <div className="flex gap-2">
            <Badge tone="type">{doc.docType}</Badge>
            <Badge tone="status">{doc.status}</Badge>
          </div>
        }
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-0">
          <object
            data={`${api.fileUrl(doc.id)}#toolbar=0&navpanes=0&view=FitH`}
            type={doc.mimeType}
            className="h-[800px] w-full rounded-lg"
          >
            <p className="p-4 text-sm text-slate-600">
              Cannot render PDF.{" "}
              <a className="underline" href={api.fileUrl(doc.id)}>
                Download
              </a>
            </p>
          </object>
        </Card>

        <div className="space-y-4">
          {doc.summary && (
            <Card>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
                In-DB summary
                <span className="ml-2 font-normal text-slate-400 normal-case tracking-normal">
                  via <code>DBMS_VECTOR_CHAIN.UTL_TO_SUMMARY</code>
                </span>
              </h3>
              <p className="whitespace-pre-line text-sm text-slate-700">{doc.summary}</p>
            </Card>
          )}
          {doc.fields ? (
            doc.docType === "invoice" ? (
              <InvoiceView fields={doc.fields as InvoiceFields} />
            ) : doc.docType === "purchase_order" ? (
              <PurchaseOrderView fields={doc.fields as PurchaseOrderFields} />
            ) : doc.docType === "delivery_note" ? (
              <DeliveryNoteView fields={doc.fields as DeliveryNoteFields} />
            ) : (
              <Card>No structured fields for unknown type.</Card>
            )
          ) : (
            <Card>
              <p className="text-sm text-slate-600">
                {doc.status === "failed"
                  ? `Failed: ${doc.failedReason ?? "unknown"}`
                  : "Still processing…"}
              </p>
            </Card>
          )}

          {similar && similar.items.length > 0 && (
            <Card>
              <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
                Similar documents
              </h3>
              <ul className="space-y-2">
                {similar.items.map((item) => (
                  <li key={item.id} className="flex items-center justify-between text-sm">
                    <Link
                      to="/documents/$id"
                      params={{ id: item.id }}
                      className="font-medium underline-offset-2 hover:underline"
                    >
                      {item.originalFilename}
                    </Link>
                    <div className="flex items-center gap-2">
                      <Badge tone="type">{item.docType}</Badge>
                      <span className="text-xs text-slate-500">
                        {(1 - item.distance).toFixed(3)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </div>
    </>
  );
}
