import { useRef } from "react";
import { HELP, type TopicId } from "./content";
import { HelpPopover } from "./HelpPopover";
import { useHelp } from "./HelpProvider";

/** A quiet "?" placed inline after a section heading. */
export function HelpButton({ topic }: { topic: TopicId }) {
  const { openId, open, close, ctx } = useHelp();
  const ref = useRef<HTMLButtonElement>(null);
  const isOpen = openId === topic;
  const content = HELP[topic](ctx);
  return (
    <>
      <button
        ref={ref}
        type="button"
        className="help-button"
        aria-label={`Help: ${content.title}`}
        aria-haspopup="dialog"
        aria-expanded={isOpen}
        onClick={() => (isOpen ? close() : open(topic))}
      >
        ?
      </button>
      {isOpen && <HelpPopover topic={content} anchor={ref} onClose={close} />}
    </>
  );
}
