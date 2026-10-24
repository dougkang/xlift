import { useEffect, useId, useLayoutEffect, useRef, useState, type RefObject } from "react";
import { createPortal } from "react-dom";
import type { HelpTopic } from "./content";

const GUTTER = 16;
const GAP = 4;

interface Props {
  topic: HelpTopic;
  anchor: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
}

/**
 * Anchored help panel: below its button (above when there's no room), clamped inside the
 * viewport, scrolling when tall (FR-006). Esc or a click outside closes it, and focus goes
 * back to the button (FR-005).
 */
export function HelpPopover({ topic, anchor, onClose }: Props) {
  const panel = useRef<HTMLDivElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const titleId = useId();
  const [pos, setPos] = useState<{ top: number; left: number }>({ top: -9999, left: GUTTER });

  const dismiss = () => {
    onClose();
    anchor.current?.focus();
  };

  useLayoutEffect(() => {
    const place = () => {
      const a = anchor.current?.getBoundingClientRect();
      const p = panel.current;
      if (!a || !p) return;
      const w = p.offsetWidth;
      const h = p.offsetHeight;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const left = Math.max(GUTTER, Math.min(a.left, vw - w - GUTTER));
      const below = a.bottom + GAP;
      const top =
        below + h <= vh - GUTTER || a.top - GAP - h < GUTTER
          ? Math.max(GUTTER, Math.min(below, vh - h - GUTTER))
          : a.top - GAP - h;
      setPos({ top, left });
    };
    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [anchor, topic]);

  useEffect(() => {
    title.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") dismiss();
    };
    const onDown = (e: MouseEvent) => {
      const t = e.target as Node;
      if (panel.current?.contains(t) || anchor.current?.contains(t)) return;
      onClose();
      // Return focus once the click has settled, unless it landed on something focusable.
      setTimeout(() => {
        if (!document.activeElement || document.activeElement === document.body) anchor.current?.focus();
      });
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return createPortal(
    <div
      ref={panel}
      className="help-popover"
      role="dialog"
      aria-modal="false"
      aria-labelledby={titleId}
      style={{ top: pos.top, left: pos.left }}
    >
      <div className="help-title-row">
        <h4 id={titleId} ref={title} tabIndex={-1} className="help-title">
          {topic.title}
        </h4>
      </div>
      {topic.controls?.length ? (
        <section>
          <div className="col-header">Controls</div>
          <ul>
            {topic.controls.map(([name, effect]) => (
              <li key={name}>
                <b>{name}</b> — {effect}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <section>
        <div className="col-header">Reading it</div>
        <ul>
          {topic.reading.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>
      {topic.terms?.length ? (
        <section>
          <div className="col-header">Terms</div>
          <ul>
            {topic.terms.map(([term, def]) => (
              <li key={term}>
                <b>{term}</b> — {def}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>,
    document.body,
  );
}
