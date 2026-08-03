import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { mkdtemp, rm, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createFillNodeTool, createReviseNodeTool } from "../agent/film-authoring-tools.js";
import { loadStoryGraph } from "../interactive-film/graph-store.js";
import { saveStoryGraph } from "../interactive-film/graph-store.js";
import { StoryGraphSchema } from "../interactive-film/graph-schema.js";

const node = JSON.stringify({ type: "branch", title: "抉择", sceneDesc: "宫门前", dialogue: [{ speaker: "阿梅", text: "账不能错", emotion: "坚定" }], choices: [{ id: "a", text: "公开", targetNodeId: "e" }] });

describe("fill_node tool (stubbed LLM)", () => {
  let root: string;
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), "if-llm-"));
    await mkdir(join(root, "interactive-films", "p"), { recursive: true });
    await saveStoryGraph(root, "p", StoryGraphSchema.parse({ schemaVersion: 1, projectId: "p", title: "T", variables: [], nodes: [{ id: "n1", type: "branch", choices: [] }, { id: "e", type: "ending", choices: [] }], endings: [] }));
  });
  afterEach(async () => { await rm(root, { recursive: true, force: true }); });

  it("fills a node from stubbed LLM text and persists it", async () => {
    const tool = createFillNodeTool(root, "p", { chat: async () => "```json\n" + node + "\n```" });
    await tool.execute("call-1", { nodeId: "n1", instruction: "写抉择场景" } as never);
    const g = await loadStoryGraph(root, "p");
    expect(g?.nodes.find(n => n.id === "n1")?.dialogue?.[0].speaker).toBe("阿梅");
  });

  it("loads interactive-film script prompt-pack overrides and reports skill details", async () => {
    await mkdir(join(root, "prompt", "interactive-film"), { recursive: true });
    await writeFile(join(root, "prompt", "interactive-film", "script.md"), "PROJECT SCRIPT OVERRIDE: keep node dialogue short and playable.");
    let systemPrompt = "";
    const tool = createFillNodeTool(root, "p", {
      chat: async (system) => {
        systemPrompt = system;
        return "```json\n" + node + "\n```";
      },
    });

    const result = await tool.execute("call-1", { nodeId: "n1", instruction: "写抉择场景" } as never);

    expect(systemPrompt).toContain("Prompt Pack Guidance");
    expect(systemPrompt).toContain("PROJECT SCRIPT OVERRIDE");
    expect(result.details).not.toHaveProperty("usedSkills");
    expect((result.details as any).promptPacks).toContain("interactive-film.script");
  });
});

describe("revise_node tool (stubbed LLM)", () => {
  let root: string;
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), "if-llm-rv-"));
    await mkdir(join(root, "interactive-films", "p"), { recursive: true });
    await saveStoryGraph(root, "p", StoryGraphSchema.parse({
      schemaVersion: 1, projectId: "p", title: "T", variables: [],
      nodes: [
        { id: "n1", type: "branch", sceneDesc: "旧场景", dialogue: [{ speaker: "旧人", text: "旧台词", emotion: "平静" }], choices: [] },
        { id: "e", type: "ending", choices: [] },
      ],
      endings: [],
    }));
  });
  afterEach(async () => { await rm(root, { recursive: true, force: true }); });

  it("revises a node via stubbed LLM text and persists updated dialogue", async () => {
    const revised = JSON.stringify({ type: "branch", title: "修改后", sceneDesc: "新场景", dialogue: [{ speaker: "新人", text: "新台词", emotion: "激动" }], choices: [{ id: "c1", text: "继续", targetNodeId: "e" }] });
    const tool = createReviseNodeTool(root, "p", { chat: async () => "```json\n" + revised + "\n```" });
    await tool.execute("call-2", { nodeId: "n1", instruction: "改写" } as never);
    const g = await loadStoryGraph(root, "p");
    const updated = g?.nodes.find(n => n.id === "n1");
    expect(updated?.dialogue?.[0].speaker).toBe("新人");
    expect(updated?.sceneDesc).toBe("新场景");
  });
});
