/**
 * Route transition: a single calm fade + 6px lift, ~220ms, exponential ease-out.
 * App.tsx remounts this on pathname change (via key), so the enter animation
 * runs on every navigation. Collapses to an instant render under reduced motion.
 */
import { motion, useReducedMotion } from "framer-motion";

interface PageTransitionProps {
  children: React.ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const reduce = useReducedMotion();

  return (
    <motion.div
      initial={reduce ? { opacity: 0 } : { opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reduce ? 0.001 : 0.22, ease: [0.16, 1, 0.3, 1] }}
    >
      {children}
    </motion.div>
  );
}
