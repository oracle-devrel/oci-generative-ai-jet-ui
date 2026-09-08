import { useState } from "react";

export function ChatInput({
  onSubmit,
  disabled,
  placeholder,
}: {
  onSubmit: (q: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [q, setQ] = useState("");

  function send() {
    const trimmed = q.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setQ("");
  }

  return (
    <div className="flex gap-2 mt-3 pt-3 border-t border-oracle-ink/10">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && !disabled && send()}
        placeholder={placeholder ?? "Ask a question..."}
        disabled={disabled}
        className="flex-1 px-3 py-2 text-sm rounded-md border border-oracle-ink/15 bg-white focus:outline-none focus:border-oracle-red disabled:opacity-40"
      />
      <button
        onClick={send}
        disabled={disabled || !q.trim()}
        className="px-4 py-2 text-sm rounded-md bg-oracle-red text-white font-medium disabled:opacity-40"
      >
        Send
      </button>
    </div>
  );
}
