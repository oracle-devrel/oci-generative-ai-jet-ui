import { useState, useRef } from "react";
import { uploadFile } from "../utils/uploadFile";

export default function ChatInput({ onSend, isLoading, threadId, dispatch }) {
  const [value, setValue] = useState("");
  const [files, setFiles] = useState([]);
  const fileInputRef = useRef(null);
  const textareaRef = useRef(null);

  const handleSubmit = async () => {
    if (isLoading) return;

    // Upload files first
    for (const file of files) {
      await uploadFile(file, threadId, dispatch);
    }
    setFiles([]);

    if (value.trim()) {
      onSend(value.trim());
      setValue("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = (e) => {
    const newFiles = Array.from(e.target.files);
    setFiles((prev) => [...prev, ...newFiles]);
    e.target.value = "";
  };

  const removeFile = (index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="px-4 pb-4 pt-2">
      {/* File chips */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {files.map((f, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 bg-tertiary text-text-secondary text-xs rounded-full px-2.5 py-1 border border-white/5"
            >
              <span className="text-[10px]">&#128196;</span>
              {f.name}
              <button
                onClick={() => removeFile(i)}
                className="text-text-secondary/60 hover:text-text-primary ml-1"
              >
                &#215;
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2">
        {/* Attach button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className="p-2 text-text-secondary hover:text-text-primary transition shrink-0"
          title="Attach file"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
          </svg>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md,.csv,.json,.docx"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Textarea */}
        <div className="flex-1 bg-tertiary rounded-xl glow-input focus-within:glow-border-active transition">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about portfolio risk, compliance, accounts..."
            rows={1}
            className="w-full bg-transparent text-text-primary text-sm px-4 py-3 resize-none outline-none placeholder:text-text-secondary/40"
            style={{ maxHeight: "120px" }}
            onInput={(e) => {
              e.target.style.height = "auto";
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
            }}
          />
        </div>

        {/* Send button */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || (!value.trim() && files.length === 0)}
          className={`p-2.5 rounded-xl transition shrink-0 ${
            isLoading || (!value.trim() && files.length === 0)
              ? "bg-tertiary text-text-secondary/30"
              : "bg-text-accent/10 text-text-accent hover:bg-text-accent/20 glow-border-hover"
          }`}
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
