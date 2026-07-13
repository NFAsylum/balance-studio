import { describe, expect, test } from "vitest";
import { DEFAULT_VIEW, allViews, getViewById, getViewsForDomain, registerView } from "./registry";
import type { EntityView } from "./types";

const cardView: EntityView = {
  id: "card_game.test",
  name: "Test Card",
  domain: "card_game",
  component: () => null,
  defaultMapping: {},
};

describe("view registry", () => {
  test("get by id; unknown -> null", () => {
    expect(getViewById("default")).toBe(DEFAULT_VIEW);
    expect(getViewById("does-not-exist")).toBeNull();
  });

  test("DefaultListView is the always-available fallback (last) for any domain", () => {
    const list = getViewsForDomain("anything-goes");
    expect(list.at(-1)!.id).toBe("default");
  });

  test("a registered domain view surfaces for that domain only", () => {
    registerView(cardView);
    const card = getViewsForDomain("card_game").map((v) => v.id);
    const creature = getViewsForDomain("creature_rpg").map((v) => v.id);
    expect(card).toContain("card_game.test");
    expect(creature).not.toContain("card_game.test");
    expect(card).toContain("default"); // fallback everywhere
  });

  test("registerView ignores duplicate ids", () => {
    const before = allViews().length;
    const v: EntityView = { ...cardView, id: "creature_rpg.dupe" };
    registerView(v);
    registerView(v);
    expect(allViews().length).toBe(before + 1);
  });
});
