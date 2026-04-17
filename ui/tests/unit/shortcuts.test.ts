import { isCommandShortcut, isTypingTarget } from "@/lib/shortcuts";

describe("shortcut helpers", () => {
  it("detects typing targets", () => {
    const input = document.createElement("input");
    const div = document.createElement("div");

    expect(isTypingTarget(input)).toBe(true);
    expect(isTypingTarget(div)).toBe(false);
  });

  it("detects command palette shortcut", () => {
    const event = new KeyboardEvent("keydown", { key: "k", metaKey: true });
    expect(isCommandShortcut(event)).toBe(true);
  });
});
