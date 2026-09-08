const PRESETS = [
  "How many products are in the catalogue?",
  "What do customers say about wireless headphones?",
  "Show average rating by category",
];

export function DemoPills({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 mb-3">
      {PRESETS.map((p) => (
        <button
          key={p}
          disabled={disabled}
          onClick={() => onPick(p)}
          className="text-left text-sm px-3 py-2 rounded-md border border-oracle-ink/15 hover:border-oracle-red disabled:opacity-40"
        >
          {p}
        </button>
      ))}
    </div>
  );
}
