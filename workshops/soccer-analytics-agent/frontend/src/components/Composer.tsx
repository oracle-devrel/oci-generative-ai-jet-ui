import { useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowRightIcon } from "@phosphor-icons/react";
import { MagneticButton } from "./MagneticButton";

interface Props {
  onSend: (message: string) => void;
  busy: boolean;
}

/** Message composer with auto-growing textarea and a tactile magnetic send. */
export function Composer({ onSend, busy }: Props) {
  const [value, setValue] = useState("");
  const taRef = useRef<HTMLTextAreaElement>(null);

  function autosize() {
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 168)}px`;
  }

  function submit() {
    const msg = value.trim();
    if (!msg || busy) return;
    onSend(msg);
    setValue("");
    requestAnimationFrame(() => {
      if (taRef.current) taRef.current.style.height = "auto";
    });
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit();
  }

  function handleKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <form onSubmit={handleSubmit} autoComplete="off">
      <div className="flex items-end gap-2.5">
        <div className="flex flex-1 items-end rounded-[15px] border border-line bg-surface px-4 py-1 transition-[border-color,box-shadow] focus-within:border-accent-dim focus-within:shadow-[0_0_0_3px_rgba(47,181,115,0.14)]">
          <textarea
            ref={taRef}
            rows={1}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              autosize();
            }}
            onKeyDown={handleKey}
            placeholder="Ask about a team, a match, or a prediction…"
            className="max-h-[168px] w-full resize-none bg-transparent py-2.5 text-[14.5px] leading-relaxed text-fg outline-none placeholder:text-fg-faint"
          />
        </div>
        <MagneticButton
          type="submit"
          ariaLabel="Send message"
          disabled={busy || !value.trim()}
          strength={7}
          className="grid h-[46px] w-[46px] flex-none place-items-center rounded-[13px] bg-accent text-ink shadow-[inset_0_1px_0_rgba(255,255,255,0.3)] transition-[background,opacity] hover:bg-accent-bright disabled:cursor-not-allowed disabled:opacity-45"
        >
          <ArrowRightIcon size={18} weight="bold" />
        </MagneticButton>
      </div>
      <p className="mt-2.5 text-center font-mono text-[10.5px] text-fg-faint">
        Every probability is computed by the trained model — expand any tool to verify.
      </p>
    </form>
  );
}
