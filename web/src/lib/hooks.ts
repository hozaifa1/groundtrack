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
