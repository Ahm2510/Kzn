/**
 * Restrained motion primitives built on Framer Motion.
 *
 * One orchestrated reveal per view (staggered children), no scattered effects.
 * Every primitive collapses to an instant, transform-free render when the user
 * prefers reduced motion — the quality floor the design skill requires.
 */
import { motion, useReducedMotion, type Variants } from "framer-motion";
import type { ReactNode } from "react";

// Exponential ease-out (no bounce, no elastic) per the design laws.
const EASE = [0.16, 1, 0.3, 1] as const;

interface RevealProps {
  children: ReactNode;
  className?: string;
  /** seconds between each child's entrance */
  stagger?: number;
  /** seconds before the sequence begins */
  delay?: number;
}

/** Orchestrates a single staggered entrance for its RevealItem children. */
export function Reveal({ children, className, stagger = 0.06, delay = 0 }: RevealProps) {
  const reduce = useReducedMotion();

  const container: Variants = {
    hidden: {},
    show: {
      transition: reduce
        ? { staggerChildren: 0, delayChildren: 0 }
        : { staggerChildren: stagger, delayChildren: delay },
    },
  };

  return (
    <motion.div
      className={className}
      variants={container}
      initial="hidden"
      animate="show"
    >
      {children}
    </motion.div>
  );
}

interface RevealItemProps {
  children: ReactNode;
  className?: string;
}

/** A single element in a Reveal sequence: fades + lifts 8px, or appears instantly. */
export function RevealItem({ children, className }: RevealItemProps) {
  const reduce = useReducedMotion();

  const item: Variants = {
    hidden: reduce ? { opacity: 0 } : { opacity: 0, y: 8 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: reduce ? 0.001 : 0.4, ease: EASE },
    },
  };

  return (
    <motion.div className={className} variants={item}>
      {children}
    </motion.div>
  );
}

/** Hover/press elevation for interactive rows. Static when motion is reduced. */
export function HoverLift({ children, className }: { children: ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      whileHover={reduce ? undefined : { y: -1 }}
      transition={{ duration: 0.18, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}
