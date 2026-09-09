import { memo, useRef, type ReactNode, type PointerEvent } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { spring } from "../lib/motion";

interface Props {
  children: ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  type?: "button" | "submit";
  ariaLabel?: string;
  /** Magnet pull strength in px at the edge of the element. */
  strength?: number;
  className?: string;
}

/**
 * Button that physically pulls toward the cursor. Continuous motion is driven
 * entirely by Framer motion values (never React state) so it stays off the
 * render path — safe on mobile (taste-skill magnetic-physics rule).
 */
function MagneticButtonBase({
  children,
  onClick,
  disabled,
  type = "button",
  ariaLabel,
  strength = 6,
  className = "",
}: Props) {
  const ref = useRef<HTMLButtonElement>(null);
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const x = useSpring(mx, spring);
  const y = useSpring(my, spring);
  // Slight icon parallax for a tactile feel.
  const ix = useTransform(x, (v) => v * 0.4);
  const iy = useTransform(y, (v) => v * 0.4);

  function handleMove(e: PointerEvent<HTMLButtonElement>) {
    if (disabled) return;
    const el = ref.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
    const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
    mx.set(dx * strength);
    my.set(dy * strength);
  }

  function reset() {
    mx.set(0);
    my.set(0);
  }

  return (
    <motion.button
      ref={ref}
      type={type}
      aria-label={ariaLabel}
      disabled={disabled}
      onClick={onClick}
      onPointerMove={handleMove}
      onPointerLeave={reset}
      style={{ x, y }}
      whileTap={{ scale: 0.92 }}
      className={className}
    >
      <motion.span style={{ x: ix, y: iy }} className="inline-flex">
        {children}
      </motion.span>
    </motion.button>
  );
}

export const MagneticButton = memo(MagneticButtonBase);
