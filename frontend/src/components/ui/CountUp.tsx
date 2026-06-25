/**
 * Counts a number up to its value on mount. Reads as "expensive software" for
 * almost no cost. Honors prefers-reduced-motion by showing the final value
 * immediately.
 */
import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";

interface CountUpProps {
  value: number;
  /** Formats the (interpolated) number for display. */
  format?: (n: number) => string;
  /** Animation length in ms. */
  duration?: number;
  className?: string;
}

const easeOutExpo = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

export function CountUp({ value, format, duration = 900, className }: CountUpProps) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? value : 0);
  const frame = useRef<number>();

  useEffect(() => {
    if (reduce) {
      setDisplay(value);
      return;
    }
    const start = performance.now();
    const from = 0;
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      setDisplay(from + (value - from) * easeOutExpo(t));
      if (t < 1) frame.current = requestAnimationFrame(tick);
      else setDisplay(value);
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
  }, [value, duration, reduce]);

  return (
    <span className={className}>{format ? format(display) : Math.round(display).toString()}</span>
  );
}
