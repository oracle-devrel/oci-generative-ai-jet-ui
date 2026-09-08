import { useState } from "react";
import { Send } from "lucide-react";

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  const submit = () => {
    if (!value.trim() || disabled) return;
    onSend(value);
    setValue("");
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-white/5 bg-bg-panel px-4 py-3">
      <div className="max-w-3xl mx-auto flex gap-2 items-end">
        <textarea
          rows={2}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKey}
          placeholder={disabled ? "Agent is working…" : "Ask about your data… (Enter to send, Shift+Enter for newline)"}
          disabled={disabled}
          className="flex-1 bg-bg-elev border border-white/5 rounded px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent-skill resize-none"
        />
        <button
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="bg-accent-skill/80 hover:bg-accent-skill text-white px-3 py-2 rounded disabled:opacity-30"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}
