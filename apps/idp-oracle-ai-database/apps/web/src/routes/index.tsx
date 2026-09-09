import { createFileRoute, Link } from "@tanstack/react-router";
import { Card, PageHeader } from "../components/ui";

export const Route = createFileRoute("/")({
  component: HomePage,
});

function HomePage() {
  return (
    <>
      <PageHeader title="Intelligent Document Processor" />
      <div className="grid gap-4 sm:grid-cols-2">
        <Card>
          <h2 className="mb-2 text-lg font-medium">Upload</h2>
          <p className="mb-4 text-sm text-slate-600">
            Drop a PDF and watch it move through text extraction, classification, structured
            extraction, and embedding — all stored in a single Oracle AI Database.
          </p>
          <Link to="/upload" className="text-sm font-medium text-slate-900 underline">
            Go to upload →
          </Link>
        </Card>
        <Card>
          <h2 className="mb-2 text-lg font-medium">Documents</h2>
          <p className="mb-4 text-sm text-slate-600">
            Browse processed purchase orders, delivery notes, and invoices. Open any document to see
            the extracted fields and similar documents found via vector search.
          </p>
          <Link to="/documents" className="text-sm font-medium text-slate-900 underline">
            See documents →
          </Link>
        </Card>
      </div>
    </>
  );
}
