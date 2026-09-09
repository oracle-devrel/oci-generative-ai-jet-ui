import {
  forwardRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";

function classes(...parts: (string | false | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}

export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" }
>(({ variant = "primary", className, ...rest }, ref) => (
  <button
    ref={ref}
    className={classes(
      "inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium transition",
      variant === "primary"
        ? "bg-slate-900 text-white hover:bg-slate-700 disabled:bg-slate-300"
        : "border border-slate-300 bg-white text-slate-900 hover:bg-slate-100",
      className
    )}
    {...rest}
  />
));
Button.displayName = "Button";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...rest }, ref) => (
    <input
      ref={ref}
      className={classes(
        "rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500",
        className
      )}
      {...rest}
    />
  )
);
Input.displayName = "Input";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={classes("rounded-lg border border-slate-200 bg-white p-4 shadow-sm", className)}
    >
      {children}
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  pending: "bg-slate-100 text-slate-700",
  text_extracted: "bg-blue-50 text-blue-700",
  classified: "bg-blue-100 text-blue-800",
  fields_extracted: "bg-indigo-100 text-indigo-800",
  embedded: "bg-violet-100 text-violet-800",
  done: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

const TYPE_TONE: Record<string, string> = {
  invoice: "bg-amber-100 text-amber-800",
  purchase_order: "bg-purple-100 text-purple-800",
  delivery_note: "bg-emerald-100 text-emerald-800",
  unknown: "bg-slate-100 text-slate-700",
};

export function Badge({ children, tone }: { children: ReactNode; tone: "status" | "type" }) {
  const value = String(children);
  const tone_map = tone === "status" ? STATUS_TONE : TYPE_TONE;
  const label = tone === "type" ? value.replace(/_/g, " ") : value;
  return (
    <span
      className={classes(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        tone_map[value] ?? "bg-slate-100 text-slate-700"
      )}
    >
      {label}
    </span>
  );
}

export function PageHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="mb-6 flex items-end justify-between">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {action}
    </div>
  );
}
