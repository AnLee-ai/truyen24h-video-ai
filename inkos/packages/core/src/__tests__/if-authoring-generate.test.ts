import { describe, expect, it } from "vitest";
import { buildFillNodeDeltaFromLLMText, buildStructureDeltaFromLLMText } from "../interactive-film/authoring-generate.js";

const nodeJson = JSON.stringify({ id: "WILL_OVERRIDE", type: "branch", title: "抉择", sceneDesc: "宫门前", dialogue: [{ speaker: "阿梅", text: "账不能错", emotion: "坚定" }], choices: [{ id: "a", text: "公开", targetNodeId: "n2" }] });
const structJson = JSON.stringify({ nodes: [
  { id: "s", type: "start", choices: [{ id: "c", text: "go", targetNodeId: "e" }] },
  { id: "e", type: "ending", choices: [] },
] });

describe("authoring-generate builders", () => {
  it("fill_node: parses a node and forces its id", () => {
    const d = buildFillNodeDeltaFromLLMText("```json\n" + nodeJson + "\n```", "real-node");
    expect(d.nodes?.upsert?.[0].id).toBe("real-node");
    expect(d.nodes?.upsert?.[0].dialogue?.[0].speaker).toBe("阿梅");
  });
  it("draft_structure: parses a nodes array", () => {
    const d = buildStructureDeltaFromLLMText(structJson);
    expect(d.nodes?.upsert?.map(n => n.id)).toEqual(["s", "e"]);
  });
  it("draft_structure: throws on empty nodes", () => {
    expect(() => buildStructureDeltaFromLLMText(JSON.stringify({ nodes: [] }))).toThrow();
  });
});
