import { useCallback, useEffect, useRef, useState } from "react";

/** Element width in CSS pixels, tracked without a scroll or resize listener.
 *
 *  A callback ref, not useRef plus useEffect. The measured element mounts only
 *  after the channel payload arrives, so an effect with an empty dependency
 *  list runs once against a null ref, never observes anything, and the plot
 *  renders at zero width forever.
 */
export function useWidth<T extends HTMLElement>() {
  const [w, setW] = useState(0);
  const observer = useRef<ResizeObserver | null>(null);

  const ref = useCallback((node: T | null) => {
    observer.current?.disconnect();
    if (!node) return;
    const ro = new ResizeObserver(([entry]) => setW(Math.round(entry.contentRect.width)));
    ro.observe(node);
    observer.current = ro;
    setW(Math.round(node.getBoundingClientRect().width));
  }, []);

  useEffect(() => () => observer.current?.disconnect(), []);

  return [ref, w] as const;
}

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  useEffect(() => {
    const mq = matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

/**
 * Eases the visible x-domain toward a target.
 *
 * This is the one authored motion in the console, and it earns its place: when
 * an operator opens a detection the plot travels from the whole pass down to
 * the flagged window, so the window's position in the channel stays legible
 * instead of being replaced by a new picture with no memory of the old one.
 * A cut would lose that; a slower travel would waste the operator's time.
 */
export function useAnimatedDomain(target: [number, number]): [number, number] {
  const reduced = useReducedMotion();
  const [domain, setDomain] = useState<[number, number]>(target);
  const from = useRef<[number, number]>(target);
  const raf = useRef(0);

  useEffect(() => {
    if (reduced) {
      setDomain(target);
      from.current = target;
      return;
    }
    const a = from.current;
    const b = target;
    if (a[0] === b[0] && a[1] === b[1]) return;

    const t0 = performance.now();
    const dur = 420;
    cancelAnimationFrame(raf.current);

    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur);
      // Exponential ease-out: fastest at the start, so the move reads as
      // responsive to the click rather than as a scheduled animation.
      const e = 1 - Math.pow(2, -10 * p);
      const cur: [number, number] = [a[0] + (b[0] - a[0]) * e, a[1] + (b[1] - a[1]) * e];
      setDomain(p >= 1 ? b : cur);
      from.current = p >= 1 ? b : cur;
      if (p < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [target[0], target[1], reduced]);

  return domain;
}
