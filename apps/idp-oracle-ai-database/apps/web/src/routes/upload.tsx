import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useCallback, type DragEvent, type ChangeEvent } from "react";
import { api, type DocumentDetail } from "../lib/api";
import { Button, Card, Badge, PageHeader } from "../components/ui";
import { MAX_UPLOAD_BYTES } from "@idp/shared";

export const Route = createFileRoute("/upload")({
  component: UploadPage,
});

interface UploadEntry {
  clientId: string;
  filename: string;
  documentId?: string;
  error?: string;
}

function UploadPage() {
  const [entries, setEntries] = useState<UploadEntry[]>([]);
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: api.uploadDocument,
    onSuccess: (data, file) => {
      setEntries((prev) =>
        prev.map((e) =>
          e.filename === file.name && !e.documentId ? { ...e, documentId: data.id } : e
        )
      );
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (err, file) => {
      setEntries((prev) =>
        prev.map((e) =>
          e.filename === file.name && !e.documentId ? { ...e, error: String(err) } : e
        )
      );
    },
  });

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      Array.from(fileList).forEach((file) => {
        if (file.size > MAX_UPLOAD_BYTES) {
          setEntries((prev) => [
            ...prev,
            {
              clientId: crypto.randomUUID(),
              filename: file.name,
              error: `File exceeds ${MAX_UPLOAD_BYTES / 1024 / 1024} MB upload cap`,
            },
          ]);
          return;
        }
        setEntries((prev) => [...prev, { clientId: crypto.randomUUID(), filename: file.name }]);
        uploadMutation.mutate(file);
      });
    },
    [uploadMutation]
  );

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    handleFiles(e.dataTransfer.files);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
    e.target.value = "";
  };

  return (
    <>
      <PageHeader title="Upload" />
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        className="mb-6 rounded-lg border-2 border-dashed border-slate-300 bg-white py-12 text-center"
      >
        <p className="mb-4 text-slate-600">Drop a PDF here, or</p>
        <label className="inline-block cursor-pointer">
          <input
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={onPick}
          />
          <Button
            type="button"
            onClick={() => document.querySelector<HTMLInputElement>("input[type=file]")?.click()}
          >
            Choose files
          </Button>
        </label>
        <p className="mt-4 text-xs text-slate-500">
          PDF only, up to {MAX_UPLOAD_BYTES / 1024 / 1024} MB.
        </p>
      </div>

      {entries.length > 0 && (
        <div className="space-y-3">
          {entries.map((entry) => (
            <UploadRow key={entry.clientId} entry={entry} />
          ))}
        </div>
      )}
    </>
  );
}

function UploadRow({ entry }: { entry: UploadEntry }) {
  if (entry.error) {
    return (
      <Card className="border-red-200 bg-red-50">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium">{entry.filename}</div>
            <div className="text-xs text-red-700">{entry.error}</div>
          </div>
          <Badge tone="status">failed</Badge>
        </div>
      </Card>
    );
  }
  if (!entry.documentId) {
    return (
      <Card>
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">{entry.filename}</div>
          <Badge tone="status">pending</Badge>
        </div>
      </Card>
    );
  }
  return <UploadRowPolling documentId={entry.documentId} filename={entry.filename} />;
}

function UploadRowPolling({ documentId, filename }: { documentId: string; filename: string }) {
  const { data } = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => api.getDocument(documentId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "done" || s === "failed" ? false : 2000;
    },
    initialData: undefined as DocumentDetail | undefined,
  });
  const status = data?.status ?? "pending";
  const docType = data?.docType ?? "unknown";
  return (
    <Card>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-medium">{filename}</div>
          {data?.failedReason && <div className="text-xs text-red-700">{data.failedReason}</div>}
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="type">{docType}</Badge>
          <Badge tone="status">{status}</Badge>
          {status === "done" && (
            <Link
              to="/documents/$id"
              params={{ id: documentId }}
              className="text-sm font-medium text-slate-900 underline"
            >
              View →
            </Link>
          )}
        </div>
      </div>
    </Card>
  );
}
