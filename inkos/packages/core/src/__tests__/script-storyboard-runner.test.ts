import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  runInteractiveFilmCreation,
  runStoryboardCreation,
  type StoryboardAssetsManifest,
} from "../pipeline/script-storyboard-runner.js";
import type { AgentContext } from "../agents/base.js";
import { loadStoryGraph } from "../interactive-film/graph-store.js";

const chatCompletionMock = vi.hoisted(() => vi.fn());

vi.mock("../llm/provider.js", () => ({
  chatCompletion: chatCompletionMock,
}));

describe("storyboard creation runner", () => {
  let root: string;

  beforeEach(async () => {
    root = await mkdtemp(join(tmpdir(), "inkos-storyboard-assets-"));
    chatCompletionMock.mockReset();
    chatCompletionMock.mockResolvedValue({
      content: [
        "# 冷库账页 分镜",
        "",
        "## 分镜表",
        "镜头 1：女出纳推开冷库门。",
        "镜头 2：手电光扫过旧账页。",
        "",
        "## 图像提示词",
        "1. Prompt: 冷库门口，女出纳推门，冷色写实，9:16",
        "2. Prompt: 旧账页特写，手电光扫过红章",
      ].join("\n"),
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });
  });

  afterEach(async () => {
    await rm(root, { recursive: true, force: true });
  });

  it("writes a first-class image asset manifest and asset directories", async () => {
    const result = await runStoryboardCreation({
      projectRoot: root,
      runtime: makeRuntime(root),
      title: "冷库账页",
      instruction: "把小说片段拆成分镜。",
      projectId: "cold-ledger",
      visualStyle: "写实冷色",
      aspectRatio: "9:16",
    });

    expect(result.assetsManifestPath).toBe("storyboards/cold-ledger/assets.json");
    expect(result.assetsDir).toBe("storyboards/cold-ledger/assets");
    expect((await stat(join(root, "storyboards/cold-ledger/assets/source"))).isDirectory()).toBe(true);
    expect((await stat(join(root, "storyboards/cold-ledger/assets/generated"))).isDirectory()).toBe(true);
    expect((await stat(join(root, "storyboards/cold-ledger/assets/selected"))).isDirectory()).toBe(true);

    const manifest = JSON.parse(
      await readFile(join(root, result.assetsManifestPath), "utf-8"),
    ) as StoryboardAssetsManifest;
    expect(manifest.kind).toBe("storyboard_assets");
    expect(manifest.storyboardPath).toBe(result.storyboardPath);
    expect(manifest.imagePromptsPath).toBe(result.imagePromptsPath);
    expect(manifest.assets.map((asset) => [asset.shotId, asset.prompt])).toEqual([
      ["shot-001", "冷库门口，女出纳推门，冷色写实，9:16"],
      ["shot-002", "旧账页特写，手电光扫过红章"],
    ]);
  });

  it("writes interactive-film story tree, flags, script, storyboard, prompts, and image assets", async () => {
    chatCompletionMock.mockResolvedValueOnce({
      content: [
        "# 盛世账页 互动影游方案",
        "",
        "## 剧情树（主干+分支）",
        "- N1 入宫查账 -> 选择 A 公开账页 / 选择 B 暗藏账页",
        "",
        "## 旗标与变量系统说明",
        "| 变量 | 含义 | 触发 |",
        "| --- | --- | --- |",
        "| trust_guard | 侍卫信任 | 选择交出证据 |",
        "",
        "## 多结局路径",
        "- 真相公开结局：trust_guard + ledger_public",
        "",
        "## 互动剧本（第1幕示例）",
        "### 节点 N1",
        "玩家选择：公开账页 / 暗藏账页",
        "",
        "## 分镜与图像提示词（关键镜头列表）",
        "镜头 1：女官在烛光下展开账页。",
        "**Prompt for C01**: 古装宫廷账页特写，女官手持账册，烛光，写实，16:9",
        "镜头 2：侍卫拦在宫门前。",
        "Prompt: 宫门雨夜，侍卫回头，压迫感，电影感，16:9",
      ].join("\n"),
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });
    chatCompletionMock.mockResolvedValueOnce({
      content: JSON.stringify({
        schemaVersion: 1,
        projectId: "shengshi-ledger",
        title: "盛世账页",
        variables: [
          { name: "trust_guard", type: "relationship", default: 0, desc: "侍卫信任" },
        ],
        nodes: [
          {
            id: "start",
            title: "入宫查账",
            type: "start",
            sceneDesc: "女官在烛光下展开账页。",
            dialogue: [],
            choices: [{ id: "c1", text: "公开账页", targetNodeId: "branch-1", effects: [] }],
          },
          {
            id: "branch-1",
            title: "宫门选择",
            type: "branch",
            sceneDesc: "侍卫拦在宫门前。",
            dialogue: [],
            choices: [
              { id: "c2", text: "交出证据", targetNodeId: "ending-good", effects: [{ var: "trust_guard", op: "add", value: 1 }] },
              { id: "c3", text: "暗藏账页", targetNodeId: "ending-secret", effects: [] },
            ],
          },
          {
            id: "branch-2",
            title: "账页去向",
            type: "branch",
            sceneDesc: "玩家决定账页的最终去向。",
            dialogue: [],
            choices: [{ id: "c4", text: "留给御史", targetNodeId: "ending-good", effects: [] }],
          },
          { id: "ending-good", title: "真相公开", type: "ending", sceneDesc: "真相公开。", dialogue: [], choices: [] },
          { id: "ending-secret", title: "暗线潜行", type: "ending", sceneDesc: "暗线潜行。", dialogue: [], choices: [] },
        ],
        endings: [
          { id: "good", nodeId: "ending-good", title: "真相公开", type: "good", description: "账页公开。" },
          { id: "secret", nodeId: "ending-secret", title: "暗线潜行", type: "secret", description: "账页被藏起。" },
        ],
      }),
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });

    const result = await runInteractiveFilmCreation({
      projectRoot: root,
      runtime: makeRuntime(root),
      title: "盛世账页",
      instruction: "做一个盛世天下式多结局互动影游。",
      projectId: "shengshi-ledger",
      outDir: "interactive-films/shengshi-ledger",
      budget: "5000元",
      referenceMode: "盛世天下式多走向",
    });

    expect(result.baseDir).toBe("interactive-films/shengshi-ledger");
    expect(result).toMatchObject({
      storyGraphPath: "interactive-films/shengshi-ledger/story-graph.json",
    });
    await expect(readFile(join(root, result.specPath), "utf-8")).resolves.toContain("互动影游创作规格");
    await expect(readFile(join(root, result.storyTreePath), "utf-8")).resolves.toContain("N1 入宫查账");
    await expect(readFile(join(root, result.flagsPath), "utf-8")).resolves.toContain("trust_guard");
    await expect(readFile(join(root, result.scriptPath), "utf-8")).resolves.toContain("节点 N1");
    await expect(readFile(join(root, result.storyboardPath), "utf-8")).resolves.toContain("镜头 1");
    await expect(readFile(join(root, result.imagePromptsPath), "utf-8")).resolves.toContain("古装宫廷账页特写");

    const manifest = JSON.parse(
      await readFile(join(root, result.assetsManifestPath), "utf-8"),
    ) as StoryboardAssetsManifest;
    expect(manifest.assets.map((asset) => asset.prompt)).toEqual([
      "古装宫廷账页特写，女官手持账册，烛光，写实，16:9",
      "宫门雨夜，侍卫回头，压迫感，电影感，16:9",
    ]);

    const graph = await loadStoryGraph(root, "shengshi-ledger");
    expect(graph).not.toBeNull();
    if (!graph) throw new Error("Expected generated story graph");
    expect(graph.title).toBe("盛世账页");
    expect(graph.nodes.some((node) => node.type === "start")).toBe(true);
  });

  it("runs storyboard creation in English with English prompts and parses English section headings", async () => {
    chatCompletionMock.mockResolvedValueOnce({
      content: [
        "# Cold Ledger Storyboard",
        "",
        "## Storyboard",
        "Shot 1: The cashier pushes open the cold-storage door.",
        "Shot 2: A flashlight beam sweeps across the old ledger pages.",
        "",
        "## Image Prompts",
        "1. Prompt: cold-storage doorway, female cashier pushing the door, desaturated realism, 9:16",
        "2. Prompt: close-up of an old ledger page, flashlight beam, oppressive mood",
      ].join("\n"),
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });

    const result = await runStoryboardCreation({
      projectRoot: root,
      runtime: makeRuntime(root),
      title: "Cold Ledger",
      instruction: "Break the novel excerpt into a storyboard.",
      projectId: "cold-ledger-en",
      visualStyle: "desaturated realism",
      aspectRatio: "9:16",
      language: "en",
    });

    const [, , messages] = chatCompletionMock.mock.calls[0]!;
    const system = messages[0].content as string;
    const user = messages[1].content as string;
    expect(system).toContain("storyboard-creation tool");
    expect(system).not.toMatch(/[一-鿿]/);
    expect(user).toContain("## Storyboard Spec");
    expect(user).toContain("## Image Prompts");
    expect(user).not.toMatch(/[一-鿿]/);

    await expect(readFile(join(root, result.specPath), "utf-8")).resolves.toContain(
      "# Cold Ledger Storyboard Creation Spec",
    );
    const manifest = JSON.parse(
      await readFile(join(root, result.assetsManifestPath), "utf-8"),
    ) as StoryboardAssetsManifest;
    expect(manifest.assets.map((asset) => [asset.shotId, asset.prompt])).toEqual([
      ["shot-001", "cold-storage doorway, female cashier pushing the door, desaturated realism, 9:16"],
      ["shot-002", "close-up of an old ledger page, flashlight beam, oppressive mood"],
    ]);
  });

  it("runs interactive-film creation in English and splits the package by English headings", async () => {
    chatCompletionMock.mockResolvedValueOnce({
      content: [
        "# Crown Feast Interactive Film Package",
        "",
        "## Story Tree",
        "- N1 The banquet hall -> choice A reveal the letter / choice B hide the letter",
        "",
        "## Variables and Flags",
        "| Variable | Meaning | Trigger |",
        "| --- | --- | --- |",
        "| trust_guard | Guard's trust | Hand over the evidence |",
        "",
        "## Ending Paths",
        "- Truth ending: trust_guard + letter_public",
        "",
        "## Interactive Script",
        "### Node N1",
        "Player choice: reveal the letter / hide the letter",
        "",
        "## Storyboard and Image Prompts",
        "Shot 1: The envoy unfolds the letter by candlelight.",
        "Prompt: medieval banquet hall, envoy holding a letter, candlelight, cinematic, 16:9",
      ].join("\n"),
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });
    chatCompletionMock.mockResolvedValueOnce({
      content: "I cannot produce JSON, but I can summarize the plot.",
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });

    const result = await runInteractiveFilmCreation({
      projectRoot: root,
      runtime: makeRuntime(root),
      title: "Crown Feast",
      instruction: "Build a multi-ending interactive film.",
      projectId: "crown-feast",
      language: "en",
    });

    const [, , messages] = chatCompletionMock.mock.calls[0]!;
    const system = messages[0].content as string;
    const user = messages[1].content as string;
    expect(system).toContain("interactive-film creation tool");
    expect(system).not.toMatch(/[一-鿿]/);
    expect(user).toContain("## Story Tree");
    expect(user).toContain("## Variables and Flags");
    expect(user).toContain("## Interactive Script");
    expect(user).toContain("## Storyboard and Image Prompts");
    expect(user).not.toMatch(/[一-鿿]/);

    await expect(readFile(join(root, result.specPath), "utf-8")).resolves.toContain(
      "Interactive Film Creation Spec",
    );
    const storyTree = await readFile(join(root, result.storyTreePath), "utf-8");
    expect(storyTree).toContain("N1 The banquet hall");
    expect(storyTree).not.toContain("trust_guard");
    await expect(readFile(join(root, result.flagsPath), "utf-8")).resolves.toContain("trust_guard");
    await expect(readFile(join(root, result.scriptPath), "utf-8")).resolves.toContain("Node N1");
    await expect(readFile(join(root, result.storyboardPath), "utf-8")).resolves.toContain("Shot 1");
    await expect(readFile(join(root, result.imagePromptsPath), "utf-8")).resolves.toContain(
      "medieval banquet hall",
    );

    const graph = await loadStoryGraph(root, "crown-feast");
    expect(graph).not.toBeNull();
    if (!graph) throw new Error("Expected fallback story graph");
    expect(graph.title).toBe("Crown Feast");
    expect(JSON.stringify(graph)).not.toMatch(/[一-鿿]/);
    expect(graph.nodes.find((node) => node.id === "start")?.title).toBe("Opening");
  });

  it("falls back to a loadable story graph when graph JSON generation fails", async () => {
    chatCompletionMock.mockResolvedValueOnce({
      content: [
        "# 回声剧场 互动影游方案",
        "",
        "## 剧情树",
        "- 开场：主角进入废弃剧场。",
        "- 分支：追逐回声 / 检查后台。",
        "",
        "## 变量与旗标表",
        "- echo_trust：回声可信度",
        "",
        "## 互动剧本",
        "### 开场",
        "玩家选择：追逐回声 / 检查后台",
        "",
        "## 分镜与图像提示词",
        "Prompt: 废弃剧场，红色帷幕，悬疑，16:9",
      ].join("\n"),
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });
    chatCompletionMock.mockResolvedValueOnce({
      content: "我无法输出 JSON，但可以概括剧情。",
      usage: { promptTokens: 1, completionTokens: 1, totalTokens: 2 },
    });

    const result = await runInteractiveFilmCreation({
      projectRoot: root,
      runtime: makeRuntime(root),
      title: "回声剧场",
      instruction: "做一个悬疑互动影游。",
      projectId: "echo-theater",
      episodeCount: 3,
    });

    expect(result.storyGraphPath).toBe("interactive-films/echo-theater/story-graph.json");
    const graph = await loadStoryGraph(root, "echo-theater");
    expect(graph).not.toBeNull();
    if (!graph) throw new Error("Expected fallback story graph");
    expect(graph.title).toBe("回声剧场");
    expect(graph.nodes.some((node) => node.type === "start")).toBe(true);
    expect(graph.endings.length).toBeGreaterThanOrEqual(2);
  });
});

function makeRuntime(root: string): AgentContext {
  return {
    projectRoot: root,
    model: "test-model",
    client: {
      provider: "openai",
      apiFormat: "chat",
      stream: false,
      defaults: {
        temperature: 0.5,
        maxTokens: 4096,
        thinkingBudget: 0,
        extra: {},
      },
    },
  };
}
