import { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage";
import ToolCallBubble from "./ToolCallBubble";
import ChatInput from "./ChatInput";
import WelcomeMat from "./WelcomeMat";

export default function ChatPane({ chat, identity }) {
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [chat.messages, chat.trace]);

  return (
    <main className="flex-1 flex flex-col overflow-hidden">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-5">
        {chat.messages.length === 0 && !chat.isThinking && (
          <WelcomeMat identity={identity} onStart={chat.sendMessage} />
        )}

        <div className="max-w-3xl mx-auto space-y-3">
          {chat.messages.map((m, i) => (
            <ChatMessage key={i} message={m} />
          ))}

          {chat.isThinking && (
            <div className="space-y-2">
              {chat.trace.filter((t) => t.type === "tool_started" || t.type === "tool_finished").map((t, i) => (
                <ToolCallBubble key={i} event={t} />
              ))}
              <div className="text-xs text-text-secondary italic">agent is thinking…</div>
            </div>
          )}
        </div>
      </div>

      <ChatInput onSend={chat.sendMessage} disabled={chat.isThinking} />
    </main>
  );
}
