import { useEffect, useState } from "react";
import { fetchAssessment, type Assessment } from "../api/assess";

export function AssessmentCard({ refreshKey }: { refreshKey?: number | string }) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);

  useEffect(() => {
    fetchAssessment()
      .then(setAssessment)
      .catch(() => setAssessment(null));
  }, [refreshKey]);

  if (!assessment)
    return (
      <div className="w-full rounded-lg border border-oracle-ink/10 bg-white/60 p-3 text-xs opacity-60">
        Assessment loading...
      </div>
    );

  const rich = assessment.mode === "rich_product_reviews";
  return (
    <div className="w-full rounded-lg border border-oracle-ink/10 bg-white/70 p-3 text-xs">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-semibold uppercase tracking-wide text-oracle-ink/50">Assessment</span>
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] ${rich ? "bg-oracle-red text-white" : "bg-oracle-ink/10 text-oracle-ink/70"}`}
        >
          {rich ? "Duality path" : "Generic JSON path"}
        </span>
      </div>
      <div className="space-y-1 text-oracle-ink/70">
        <div>✓ {assessment.document_count.toLocaleString()} documents</div>
        <div>✓ {assessment.fields.length} field paths sampled</div>
        <div>
          {assessment.vectors.length
            ? `✓ ${assessment.vectors[0].dim}-dimensional vector field detected`
            : "⚠ no vector field detected"}
        </div>
        <div>
          {rich
            ? "✓ product-review shape detected"
            : "✓ arbitrary collection will land as Oracle JSON"}
        </div>
      </div>
      {assessment.warnings.length > 0 && (
        <div className="mt-2 space-y-1 text-[11px] text-oracle-ink/55">
          {assessment.warnings.slice(0, 2).map((w) => (
            <div key={w}>⚠ {w}</div>
          ))}
        </div>
      )}
    </div>
  );
}
