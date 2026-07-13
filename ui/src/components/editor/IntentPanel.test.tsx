import { describe, expect, test } from "vitest";
import { DEFAULT_INTENT, composeBrief, intentModifiers } from "./IntentPanel";

describe("intent", () => {
  test("intentModifiers describes each slider position", () => {
    expect(intentModifiers(DEFAULT_INTENT)).toBe(
      "Power scale: average. Variety: mixed. Complexity: moderate. Theme adherence: balanced",
    );
    expect(intentModifiers({ ...DEFAULT_INTENT, power: 2, variety: 0 })).toContain("Power scale: strong");
  });

  test("composeBrief joins the theme text and the modifiers", () => {
    const brief = composeBrief({ ...DEFAULT_INTENT, brief: "cyberpunk hackers" });
    expect(brief).toContain("cyberpunk hackers");
    expect(brief).toContain("Complexity: moderate");
  });
});
