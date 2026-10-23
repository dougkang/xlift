import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { WindowInput } from "../src/components/Controls";

describe("WindowInput", () => {
  afterEach(cleanup);

  it("allows clearing and retyping; commits only valid values", async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<WindowInput value={15} onCommit={onCommit} />);
    const input = screen.getByLabelText("Games in window") as HTMLInputElement;
    await user.click(input);
    await user.keyboard("{Backspace}{Backspace}");
    expect(input.value).toBe("");
    // "1" was a valid intermediate value; the empty field is never committed.
    expect(onCommit.mock.calls).toEqual([[1]]);
    await user.keyboard("8");
    expect(onCommit).toHaveBeenLastCalledWith(8);
    await user.keyboard("{Backspace}");
    await user.tab();
    expect(input.value).toBe("15"); // invalid draft restores the committed value
  });

  it("rejects out-of-range and non-numeric input", async () => {
    const user = userEvent.setup();
    const onCommit = vi.fn();
    render(<WindowInput value={15} onCommit={onCommit} />);
    const input = screen.getByLabelText("Games in window") as HTMLInputElement;
    await user.clear(input);
    await user.type(input, "9a9");
    expect(input.value).toBe("99");
    expect(onCommit).toHaveBeenLastCalledWith(9);
  });
});
