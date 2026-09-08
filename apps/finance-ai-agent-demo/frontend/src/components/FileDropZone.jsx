export default function FileDropZone() {
  return (
    <div className="absolute inset-0 z-50 bg-primary/80 backdrop-blur-sm flex items-center justify-center">
      <div className="border-2 border-dashed border-text-accent/30 rounded-2xl p-12 text-center">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          className="mx-auto mb-4 text-text-accent/50"
        >
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p className="text-text-accent/60 text-sm font-medium">Drop files here</p>
        <p className="text-text-secondary/40 text-xs mt-1">to add to knowledge base</p>
      </div>
    </div>
  );
}
