import type { Transition, Variants } from "framer-motion";

// Premium spring (taste-skill: stiffness ~100, damping ~20, no linear easing).
export const spring: Transition = {
  type: "spring",
  stiffness: 110,
  damping: 20,
  mass: 0.9,
};

export const springSoft: Transition = {
  type: "spring",
  stiffness: 90,
  damping: 22,
};

// Staggered waterfall reveal for lists / bento grids.
export const stagger: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.07, delayChildren: 0.04 },
  },
};

export const riseItem: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: spring },
};

export const fadeItem: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.3 } },
};
