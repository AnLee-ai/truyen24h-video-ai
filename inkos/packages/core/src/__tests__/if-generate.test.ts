import { describe, expect, it } from "vitest";
import { extractJson, buildStoryGraphFromLLMText } from "../interactive-film/generate.js";

const validGraphJson = JSON.stringify({
  schemaVersion: 1, projectId: "WILL_BE_OVERRIDDEN", title: "G", variables: [],
  nodes: [
    { id: "s", type: "start", choices: [{ id: "c", text: "go", targetNodeId: "e" }] },
    { id: "e", type: "ending", choices: [] },
  ],
  endings: [{ id: "x", nodeId: "e", title: "end", type: "good" }],
});

describe("extractJson", () => {
  it("extracts from a fenced ```json block", () => {
    const obj = extractJson("前言\n```json\n{\"a\":1}\n```\n后语") as { a: number };
    expect(obj.a).toBe(1);
  });
  it("extracts a bare JSON object", () => {
    const obj = extractJson("noise {\"a\":2} tail") as { a: number };
    expect(obj.a).toBe(2);
  });
  it("throws when no JSON object is present", () => {
    expect(() => extractJson("no json here")).toThrow();
  });
});

describe("buildStoryGraphFromLLMText", () => {
  it("parses and forces projectId from the argument", () => {
    const g = buildStoryGraphFromLLMText("```json\n" + validGraphJson + "\n```", "real-id");
    expect(g.projectId).toBe("real-id");
    expect(g.nodes).toHaveLength(2);
  });
  it("throws on schema-invalid graph", () => {
    const bad = JSON.stringify({ schemaVersion: 1, title: "x" }); // missing projectId/nodes shape
    expect(() => buildStoryGraphFromLLMText(bad, "real-id")).toThrow();
  });
});
