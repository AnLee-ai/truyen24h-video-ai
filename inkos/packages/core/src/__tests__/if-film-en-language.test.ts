import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { mkdtemp, rm, mkdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import * as llmProvider from "../llm/provider.js";
import type { LLMClient } from "../llm/provider.js";
import { generateStoryGraph } from "../interactive-film/generate.js";
import {
  createFillNodeTool,
  createReviseNodeTool,
  createDraftStructureTool,
} from "../agent/film-authoring-tools.js";
import { saveStoryGraph } from "../interactive-film/graph-store.js";
import { StoryGraphSchema } from "../interactive-film/graph-schema.js";

const STUB_CLIENT: LLMClient = {
  provider: "openai",
  apiFormat: "chat",
  stream: false,
  defaults: { temperature: 0.7, maxTokens: 2048, thinkingBudget: 0, maxTokensCap: null, extra: {} },
} as LLMClient;

const validGraphJson = JSON.stringify({
  schemaVersion: 1, projectId: "x", title: "G", variables: [],
  nodes: [
    { id: "s", type: "start", choices: [{ id: "c", text: "go", targetNodeId: "e" }] },
    { id: "e", type: "ending", choices: [] },
  ],
  endings: [{ id: "x", nodeId: "e", title: "end", type: "good" }],
});

const nodeJson = JSON.stringify({
  type: "branch", title: "Choice", sceneDesc: "At the gate",
  dialogue: [{ speaker: "Mei", text: "The ledger cannot lie", emotion: "resolute" }],
  choices: [{ id: "a", text: "Go public", targetNodeId: "e" }],
});

const structureJson = JSON.stringify({ nodes: [
  { id: "s", type: "start", choices: [{ id: "c", text: "go", targetNodeId: "e" }] },
  { id: "e", type: "ending", choices: [] },
] });

describe("generateStoryGraph language switch", () => {
  afterEach(() => { vi.restoreAllMocks(); });

  it("uses the English system prompt and English user prompt when language is en", async () => {
    const chatSpy = vi.spyOn(llmProvider, "chatCompletion").mockResolvedValue({
      content: "```json\n" + validGraphJson + "\n```",
      usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
    } as unknown as Awaited<ReturnType<typeof llmProvider.chatCompletion>>);

    await generateStoryGraph(STUB_CLIENT, "m", { projectId: "p", title: "T", premise: "A heist" }, { language: "en" });

    const messages = chatSpy.mock.calls[0][2];
    expect(messages[0].content).toContain("You are an interactive film scriptwriter");
    expect(messages[0].content).not.toContain("你是互动影游编剧");
    expect(messages[1].content).toContain("Title: T");
    expect(messages[1].content).toContain("Premise: A heist");
  });

  it("defaults to the Chinese system prompt when language is omitted", async () => {
    const chatSpy = vi.spyOn(llmProvider, "chatCompletion").mockResolvedValue({
      content: "```json\n" + validGraphJson + "\n```",
      usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 },
    } as unknown as Awaited<ReturnType<typeof llmProvider.chatCompletion>>);

    await generateStoryGraph(STUB_CLIENT, "m", { projectId: "p", title: "标题T", premise: "前提P" });

    const messages = chatSpy.mock.calls[0][2];
    expect(messages[0].content).toContain("你是互动影游编剧");
    expect(messages[1].content).toContain("标题：标题T");
  });
});

describe("film authoring LLM tools language switch", () => {
  let root: string;
  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), "if-en-"));
    await mkdir(join(root, "interactive-films", "p"), { recursive: true });
    await saveStoryGraph(root, "p", StoryGraphSchema.parse({
      schemaVersion: 1, projectId: "p", title: "T", variables: [],
      nodes: [{ id: "n1", type: "branch", choices: [] }, { id: "e", type: "ending", choices: [] }],
      endings: [],
    }));
  });
  afterEach(async () => { await rm(root, { recursive: true, force: true }); });

  it("fill_node with language en sends the English node system prompt and user prompt", async () => {
    let systemPrompt = "";
    let userPrompt = "";
    const tool = createFillNodeTool(root, "p", {
      chat: async (system, user) => {
        systemPrompt = system;
        userPrompt = user;
        return "```json\n" + nodeJson + "\n```";
      },
    }, "en");

    await tool.execute("call-1", { nodeId: "n1", instruction: "Write the decision scene" } as never);

    expect(systemPrompt).toContain("You are an interactive film scriptwriter");
    expect(systemPrompt).not.toContain("你是互动影游编剧");
    expect(userPrompt).toContain("Node id to fill: n1");
    expect(userPrompt).toContain("Instruction: Write the decision scene");
  });

  it("fill_node defaults to the Chinese system prompt when language is omitted", async () => {
    let systemPrompt = "";
    let userPrompt = "";
    const tool = createFillNodeTool(root, "p", {
      chat: async (system, user) => {
        systemPrompt = system;
        userPrompt = user;
        return "```json\n" + nodeJson + "\n```";
      },
    });

    await tool.execute("call-2", { nodeId: "n1", instruction: "写抉择场景" } as never);

    expect(systemPrompt).toContain("你是互动影游编剧");
    expect(userPrompt).toContain("要填的节点 id：n1");
  });

  it("revise_node with language en sends the English node system prompt and user prompt", async () => {
    let systemPrompt = "";
    let userPrompt = "";
    const tool = createReviseNodeTool(root, "p", {
      chat: async (system, user) => {
        systemPrompt = system;
        userPrompt = user;
        return "```json\n" + nodeJson + "\n```";
      },
    }, "en");

    await tool.execute("call-3", { nodeId: "n1", instruction: "Tighten the dialogue" } as never);

    expect(systemPrompt).toContain("You are an interactive film scriptwriter");
    expect(userPrompt).toContain("Node id to revise: n1");
    expect(userPrompt).toContain("Revision instruction: Tighten the dialogue");
  });

  it("draft_structure with language en sends the English structure system prompt and user prompt", async () => {
    let systemPrompt = "";
    let userPrompt = "";
    const tool = createDraftStructureTool(root, "p", {
      chat: async (system, user) => {
        systemPrompt = system;
        userPrompt = user;
        return structureJson;
      },
    }, "en");

    await tool.execute("call-4", { instruction: "Three acts" } as never);

    expect(systemPrompt).toContain("You are an interactive film scriptwriter");
    expect(systemPrompt).toContain("branching skeleton");
    expect(systemPrompt).not.toContain("你是互动影游编剧");
    expect(userPrompt).toContain("Skeleton instruction: Three acts");
  });

  it("draft_structure defaults to the Chinese structure system prompt when language is omitted", async () => {
    let systemPrompt = "";
    let userPrompt = "";
    const tool = createDraftStructureTool(root, "p", {
      chat: async (system, user) => {
        systemPrompt = system;
        userPrompt = user;
        return structureJson;
      },
    });

    await tool.execute("call-5", { instruction: "三幕" } as never);

    expect(systemPrompt).toContain("你是互动影游编剧");
    expect(userPrompt).toContain("骨架指令：三幕");
  });
});
