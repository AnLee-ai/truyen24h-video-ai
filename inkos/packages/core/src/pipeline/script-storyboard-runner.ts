import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, join } from "node:path";
import type { AgentContext } from "../agents/base.js";
import { generateStoryGraph } from "../interactive-film/generate.js";
import { saveStoryGraph } from "../interactive-film/graph-store.js";
import type { StoryGraph } from "../interactive-film/graph-schema.js";
import {
  InteractiveFilmCreationAgent,
  ScriptCreationAgent,
  StoryboardCreationAgent,
  extractStoryboardImagePrompts,
  extractMarkdownSection,
  normalizeScriptEpisodeEndLabels,
  renderInteractiveFilmSpec,
  renderScriptSpec,
  renderStoryboardSpec,
  type InteractiveFilmCreationInput,
  type ScriptCreationInput,
  type ScriptTargetFormat,
  type StoryboardCreationInput,
} from "../agents/script-storyboard.js";
import { safeChildPath } from "../utils/path-safety.js";
import { toPosixPath } from "../utils/posix-path.js";

export interface ScriptCreationRunOptions {
  readonly projectRoot: string;
  readonly runtime: AgentContext;
  readonly title: string;
  readonly instruction: string;
  readonly sourceKind?: string;
  readonly targetFormat?: ScriptTargetFormat;
  readonly sourceText?: string;
  readonly sourcePath?: string;
  readonly requirements?: string;
  readonly episodeCount?: number;
  readonly episodeDuration?: string;
  readonly language?: "zh" | "en";
  readonly projectId?: string;
  readonly outDir?: string;
  readonly onProgress?: (message: string) => void;
}

export interface StoryboardCreationRunOptions {
  readonly projectRoot: string;
  readonly runtime: AgentContext;
  readonly title: string;
  readonly instruction: string;
  readonly sourceKind?: string;
  readonly sourceText?: string;
  readonly sourcePath?: string;
  readonly requirements?: string;
  readonly visualStyle?: string;
  readonly aspectRatio?: string;
  readonly granularity?: string;
  readonly maxShots?: number;
  readonly language?: "zh" | "en";
  readonly projectId?: string;
  readonly outDir?: string;
  readonly onProgress?: (message: string) => void;
}

export interface InteractiveFilmCreationRunOptions {
  readonly projectRoot: string;
  readonly runtime: AgentContext;
  readonly title: string;
  readonly instruction: string;
  readonly sourceKind?: string;
  readonly sourceText?: string;
  readonly sourcePath?: string;
  readonly requirements?: string;
  readonly targetAudience?: string;
  readonly episodeCount?: number;
  readonly episodeDuration?: string;
  readonly budget?: string;
  readonly referenceMode?: string;
  readonly language?: "zh" | "en";
  readonly projectId?: string;
  readonly outDir?: string;
  readonly onProgress?: (message: string) => void;
}

export interface ScriptCreationRunResult {
  readonly projectId: string;
  readonly baseDir: string;
  readonly specPath: string;
  readonly scriptPath: string;
}

export interface InteractiveFilmCreationRunResult {
  readonly projectId: string;
  readonly baseDir: string;
  readonly storyGraphPath: string;
  readonly specPath: string;
  readonly storyTreePath: string;
  readonly flagsPath: string;
  readonly scriptPath: string;
  readonly storyboardPath: string;
  readonly imagePromptsPath: string;
  readonly assetsManifestPath: string;
  readonly assetsDir: string;
}

export interface StoryboardCreationRunResult {
  readonly projectId: string;
  readonly baseDir: string;
  readonly specPath: string;
  readonly storyboardPath: string;
  readonly imagePromptsPath: string;
  readonly assetsManifestPath: string;
  readonly assetsDir: string;
}

export interface StoryboardImageAssetVariant {
  readonly id: string;
  readonly path: string;
  readonly status: "pending" | "generated" | "selected" | "failed";
  readonly model?: string;
  readonly provider?: string;
  readonly createdAt?: string;
  readonly error?: string;
}

export interface StoryboardImageAsset {
  readonly shotId: string;
  readonly prompt: string;
  readonly sourceRefs: readonly string[];
  readonly variants: readonly StoryboardImageAssetVariant[];
  readonly selectedPath?: string;
  readonly status: "prompt_ready" | "generated" | "selected" | "failed";
}

export interface StoryboardAssetsManifest {
  readonly version: 1;
  readonly kind: "storyboard_assets";
  readonly title: string;
  readonly projectId: string;
  readonly baseDir: string;
  readonly storyboardPath: string;
  readonly imagePromptsPath: string;
  readonly assetsDir: string;
  readonly sourceDir: string;
  readonly generatedDir: string;
  readonly selectedDir: string;
  readonly createdAt: string;
  readonly assets: readonly StoryboardImageAsset[];
}

export async function runScriptCreation(
  options: ScriptCreationRunOptions,
): Promise<ScriptCreationRunResult> {
  const projectId = safeSegment(options.projectId ?? slugify(options.title));
  const baseDir = resolveProjectBaseDir(options.outDir ?? "dramas", projectId);
  const sourceText = await resolveSourceText(options.projectRoot, options.sourceText, options.sourcePath);
  const input: ScriptCreationInput = {
    title: options.title,
    sourceKind: options.sourceKind,
    targetFormat: options.targetFormat,
    sourceText,
    requirements: mergeRequirements(options.instruction, options.requirements, options.language),
    episodeCount: options.episodeCount,
    episodeDuration: options.episodeDuration,
    language: options.language,
  };

  options.onProgress?.("Writing script creation spec...");
  const spec = renderScriptSpec(input);
  await writeProjectText(options.projectRoot, join(baseDir, "script-spec.md"), spec);

  options.onProgress?.("Writing script draft...");
  const agent = new ScriptCreationAgent(options.runtime);
  const script = normalizeScriptEpisodeEndLabels(await agent.writeScript(input));
  await writeProjectText(options.projectRoot, join(baseDir, "script.md"), script);
  await writeProjectText(options.projectRoot, join(baseDir, "status.json"), JSON.stringify({
    status: "completed",
    kind: "script",
    title: options.title,
    completedAt: new Date().toISOString(),
  }, null, 2));

  return {
    projectId,
    baseDir,
    specPath: relPath(baseDir, "script-spec.md"),
    scriptPath: relPath(baseDir, "script.md"),
  };
}

export async function runInteractiveFilmCreation(
  options: InteractiveFilmCreationRunOptions,
): Promise<InteractiveFilmCreationRunResult> {
  const projectId = safeSegment(options.projectId ?? slugify(options.title));
  const baseDir = resolveProjectBaseDir(options.outDir ?? "interactive-films", projectId);
  const sourceText = await resolveSourceText(options.projectRoot, options.sourceText, options.sourcePath);
  const input: InteractiveFilmCreationInput = {
    title: options.title,
    sourceKind: options.sourceKind,
    sourceText,
    requirements: mergeRequirements(options.instruction, options.requirements, options.language),
    targetAudience: options.targetAudience,
    episodeCount: options.episodeCount,
    episodeDuration: options.episodeDuration,
    budget: options.budget,
    referenceMode: options.referenceMode,
    language: options.language,
  };

  options.onProgress?.("Writing interactive-film creation spec...");
  const spec = renderInteractiveFilmSpec(input);
  await writeProjectText(options.projectRoot, join(baseDir, "interactive-spec.md"), spec);

  options.onProgress?.("Writing story tree, flags, script, storyboard, and image prompts...");
  const agent = new InteractiveFilmCreationAgent(options.runtime);
  const packageMarkdown = await agent.writeInteractiveFilm(input);
  const storyTree = requiredSection(packageMarkdown, [
    "剧情树",
    "Story Tree",
    "Branching Story Tree",
  ], packageMarkdown);
  const flags = requiredSection(packageMarkdown, [
    "旗标与变量系统说明",
    "变量与旗标表",
    "变量和旗标表",
    "变量表",
    "旗标表",
    "Variables and Flags",
    "Flag Table",
  ], packageMarkdown);
  const script = requiredSection(packageMarkdown, [
    "互动剧本",
    "Interactive Script",
    "Script",
  ], packageMarkdown);
  const storyboard = requiredSection(packageMarkdown, [
    "分镜与图像提示词",
    "分镜表",
    "Storyboard and Image Prompts",
    "Storyboard",
  ], packageMarkdown);
  const imagePrompts = extractStoryboardImagePrompts(storyboard);
  const storyGraphPath = relPath("interactive-films", projectId, "story-graph.json");

  await writeProjectText(options.projectRoot, join(baseDir, "story-tree.md"), storyTree);
  await writeProjectText(options.projectRoot, join(baseDir, "flags.md"), flags);
  await writeProjectText(options.projectRoot, join(baseDir, "script.md"), normalizeScriptEpisodeEndLabels(script));
  await writeProjectText(options.projectRoot, join(baseDir, "storyboard.md"), storyboard);
  await writeProjectText(options.projectRoot, join(baseDir, "image-prompts.md"), imagePrompts);
  await ensureProjectDir(options.projectRoot, join(baseDir, "assets", "source"));
  await ensureProjectDir(options.projectRoot, join(baseDir, "assets", "generated"));
  await ensureProjectDir(options.projectRoot, join(baseDir, "assets", "selected"));
  await writeProjectText(options.projectRoot, join(baseDir, "assets.json"), JSON.stringify(
    createStoryboardAssetsManifest({
      title: options.title,
      projectId,
      baseDir,
      storyboardPath: join(baseDir, "storyboard.md"),
      imagePromptsPath: join(baseDir, "image-prompts.md"),
      imagePrompts,
      createdAt: new Date().toISOString(),
    }),
    null,
    2,
  ));

  options.onProgress?.("Writing interactive-film story graph...");
  const graph = await createInteractiveFilmStoryGraph(options.runtime, {
    projectId,
    title: options.title,
    input,
    storyTree,
    flags,
    script,
    imagePrompts,
    onProgress: options.onProgress,
  });
  await saveStoryGraph(options.projectRoot, projectId, graph);

  await writeProjectText(options.projectRoot, join(baseDir, "status.json"), JSON.stringify({
    status: "completed",
    kind: "interactive_film",
    title: options.title,
    completedAt: new Date().toISOString(),
  }, null, 2));

  return {
    projectId,
    baseDir,
    storyGraphPath,
    specPath: relPath(baseDir, "interactive-spec.md"),
    storyTreePath: relPath(baseDir, "story-tree.md"),
    flagsPath: relPath(baseDir, "flags.md"),
    scriptPath: relPath(baseDir, "script.md"),
    storyboardPath: relPath(baseDir, "storyboard.md"),
    imagePromptsPath: relPath(baseDir, "image-prompts.md"),
    assetsManifestPath: relPath(baseDir, "assets.json"),
    assetsDir: relPath(baseDir, "assets"),
  };
}

export async function runStoryboardCreation(
  options: StoryboardCreationRunOptions,
): Promise<StoryboardCreationRunResult> {
  const projectId = safeSegment(options.projectId ?? slugify(options.title));
  const baseDir = resolveProjectBaseDir(options.outDir ?? "storyboards", projectId);
  const sourceText = await resolveSourceText(options.projectRoot, options.sourceText, options.sourcePath);
  const input: StoryboardCreationInput = {
    title: options.title,
    sourceKind: options.sourceKind,
    sourceText,
    requirements: mergeRequirements(options.instruction, options.requirements, options.language),
    visualStyle: options.visualStyle,
    aspectRatio: options.aspectRatio,
    granularity: options.granularity,
    maxShots: options.maxShots,
    language: options.language,
  };

  options.onProgress?.("Writing storyboard creation spec...");
  const spec = renderStoryboardSpec(input);
  await writeProjectText(options.projectRoot, join(baseDir, "storyboard-spec.md"), spec);

  options.onProgress?.("Writing storyboard and image prompts...");
  const agent = new StoryboardCreationAgent(options.runtime);
  const storyboard = await agent.writeStoryboard(input);
  await writeProjectText(options.projectRoot, join(baseDir, "storyboard.md"), storyboard);
  const imagePrompts = extractStoryboardImagePrompts(storyboard);
  await writeProjectText(options.projectRoot, join(baseDir, "image-prompts.md"), imagePrompts);
  await ensureProjectDir(options.projectRoot, join(baseDir, "assets", "source"));
  await ensureProjectDir(options.projectRoot, join(baseDir, "assets", "generated"));
  await ensureProjectDir(options.projectRoot, join(baseDir, "assets", "selected"));
  await writeProjectText(options.projectRoot, join(baseDir, "assets.json"), JSON.stringify(
    createStoryboardAssetsManifest({
      title: options.title,
      projectId,
      baseDir,
      storyboardPath: join(baseDir, "storyboard.md"),
      imagePromptsPath: join(baseDir, "image-prompts.md"),
      imagePrompts,
      createdAt: new Date().toISOString(),
    }),
    null,
    2,
  ));
  await writeProjectText(options.projectRoot, join(baseDir, "status.json"), JSON.stringify({
    status: "completed",
    kind: "storyboard",
    title: options.title,
    completedAt: new Date().toISOString(),
  }, null, 2));

  return {
    projectId,
    baseDir,
    specPath: relPath(baseDir, "storyboard-spec.md"),
    storyboardPath: relPath(baseDir, "storyboard.md"),
    imagePromptsPath: relPath(baseDir, "image-prompts.md"),
    assetsManifestPath: relPath(baseDir, "assets.json"),
    assetsDir: relPath(baseDir, "assets"),
  };
}

async function createInteractiveFilmStoryGraph(
  runtime: AgentContext,
  args: {
    readonly projectId: string;
    readonly title: string;
    readonly input: InteractiveFilmCreationInput;
    readonly storyTree: string;
    readonly flags: string;
    readonly script: string;
    readonly imagePrompts: string;
    readonly onProgress?: (message: string) => void;
  },
): Promise<StoryGraph> {
  try {
    return await generateStoryGraph(runtime.client, runtime.model, {
      projectId: args.projectId,
      title: args.title,
      premise: buildInteractiveFilmGraphPremise(args.input, args.storyTree, args.flags, args.script, args.imagePrompts),
    });
  } catch (error) {
    args.onProgress?.(`Story graph JSON generation failed; writing a minimal playable graph. ${formatError(error)}`);
    return buildFallbackStoryGraph(args.projectId, args.title, args.input, args.imagePrompts);
  }
}

function buildInteractiveFilmGraphPremise(
  input: InteractiveFilmCreationInput,
  storyTree: string,
  flags: string,
  script: string,
  imagePrompts: string,
): string {
  if ((input.language ?? "zh") === "en") {
    return [
      `Creation brief: ${input.requirements}`,
      input.targetAudience ? `Target audience: ${input.targetAudience}` : "",
      input.episodeCount ? `Segments/episodes: ${input.episodeCount}` : "",
      input.episodeDuration ? `Per-segment duration: ${input.episodeDuration}` : "",
      input.budget ? `Budget: ${input.budget}` : "",
      input.referenceMode ? `Reference mode: ${input.referenceMode}` : "",
      `Story tree:\n${storyTree}`,
      `Variables and flags:\n${flags}`,
      `Interactive script:\n${script}`,
      `Image prompts:\n${imagePrompts}`,
    ].filter(Boolean).join("\n\n");
  }
  return [
    `创作需求：${input.requirements}`,
    input.targetAudience ? `目标受众：${input.targetAudience}` : "",
    input.episodeCount ? `段落/集数：${input.episodeCount}` : "",
    input.episodeDuration ? `单段时长：${input.episodeDuration}` : "",
    input.budget ? `预算：${input.budget}` : "",
    input.referenceMode ? `参考模式：${input.referenceMode}` : "",
    `剧情树：\n${storyTree}`,
    `变量旗标：\n${flags}`,
    `互动剧本：\n${script}`,
    `图像提示词：\n${imagePrompts}`,
  ].filter(Boolean).join("\n\n");
}

function buildFallbackStoryGraph(
  projectId: string,
  title: string,
  input: InteractiveFilmCreationInput,
  imagePrompts: string,
): StoryGraph {
  const en = (input.language ?? "zh") === "en";
  const prompts = parseStoryboardPromptLines(imagePrompts);
  const actCount = Math.max(2, Math.min(8, (input.episodeCount ?? prompts.length) || 3));
  const nodes: StoryGraph["nodes"] = [
    {
      id: "start",
      title: en ? "Opening" : "开场",
      type: "start",
      sceneDesc: input.requirements || title,
      dialogue: [],
      choices: [{ id: "start-act-1", text: en ? "Enter Act 1" : "进入第一幕", targetNodeId: "act-1", effects: [] }],
      imageSlot: { prompt: prompts[0] ?? input.requirements ?? title },
      act: "start",
      position: { x: 0, y: 0 },
    },
  ];

  for (let index = 1; index <= actCount; index += 1) {
    const isLast = index === actCount;
    nodes.push({
      id: `act-${index}`,
      title: en ? `Act ${index}` : `第 ${index} 幕`,
      type: isLast ? "branch" : "normal",
      sceneDesc: en ? `Act ${index} of the interactive film "${title}".` : `互动影游《${title}》第 ${index} 幕。`,
      dialogue: [],
      choices: isLast
        ? [
          { id: "to-ending-a", text: en ? "Complete the main objective" : "完成主线目标", targetNodeId: "ending-a", effects: [{ var: "story_progress", op: "add", value: 1 }] },
          { id: "to-ending-b", text: en ? "Take the other aftermath" : "进入另一条余波", targetNodeId: "ending-b", effects: [{ var: "story_progress", op: "add", value: 1 }] },
        ]
        : [{ id: `act-${index}-next`, text: en ? "Keep going" : "继续推进", targetNodeId: `act-${index + 1}`, effects: [{ var: "story_progress", op: "add", value: 1 }] }],
      imageSlot: { prompt: prompts[index - 1] ?? prompts[0] ?? input.requirements ?? title },
      act: `act-${index}`,
      position: { x: index * 260, y: index % 2 === 0 ? 120 : 0 },
    });
  }

  nodes.push(
    {
      id: "ending-a",
      title: en ? "Ending One" : "结局一",
      type: "ending",
      sceneDesc: en ? "The main objective is completed and the story converges." : "主线目标被完成，故事进入收束。",
      dialogue: [],
      choices: [],
      act: "ending",
      position: { x: (actCount + 1) * 260, y: -80 },
    },
    {
      id: "ending-b",
      title: en ? "Ending Two" : "结局二",
      type: "ending",
      sceneDesc: en
        ? "The player keeps the other aftermath and the story closes on the forked path."
        : "玩家选择保留另一条余波，故事进入分岔收束。",
      dialogue: [],
      choices: [],
      act: "ending",
      position: { x: (actCount + 1) * 260, y: 120 },
    },
  );

  return {
    schemaVersion: 1,
    projectId,
    title,
    worldAnchor: {
      storyCore: input.requirements || title,
      theme: "",
      genre: "interactive-film",
      worldRules: input.referenceMode ?? "",
      durationMinutes: 0,
    },
    characters: [],
    variables: [{
      name: "story_progress",
      type: "counter",
      default: 0,
      desc: en ? "Story progression" : "剧情推进进度",
    }],
    nodes,
    endings: [
      {
        id: "ending-a",
        nodeId: "ending-a",
        title: en ? "Ending One" : "结局一",
        type: "neutral",
        description: en ? "The main objective is completed." : "主线目标被完成。",
      },
      {
        id: "ending-b",
        nodeId: "ending-b",
        title: en ? "Ending Two" : "结局二",
        type: "secret",
        description: en ? "The player keeps the other aftermath." : "玩家选择保留另一条余波。",
      },
    ],
  };
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function createStoryboardAssetsManifest(args: {
  readonly title: string;
  readonly projectId: string;
  readonly baseDir: string;
  readonly storyboardPath: string;
  readonly imagePromptsPath: string;
  readonly imagePrompts: string;
  readonly createdAt: string;
}): StoryboardAssetsManifest {
  const assetsDir = relPath(args.baseDir, "assets");
  const prompts = parseStoryboardPromptLines(args.imagePrompts);
  return {
    version: 1,
    kind: "storyboard_assets",
    title: args.title,
    projectId: args.projectId,
    baseDir: toPosixPath(args.baseDir),
    storyboardPath: toPosixPath(args.storyboardPath),
    imagePromptsPath: toPosixPath(args.imagePromptsPath),
    assetsDir,
    sourceDir: relPath(assetsDir, "source"),
    generatedDir: relPath(assetsDir, "generated"),
    selectedDir: relPath(assetsDir, "selected"),
    createdAt: args.createdAt,
    assets: prompts.map((prompt, index) => {
      const shotId = `shot-${String(index + 1).padStart(3, "0")}`;
      return {
        shotId,
        prompt,
        sourceRefs: [],
        variants: [],
        status: "prompt_ready",
      };
    }),
  };
}

async function resolveSourceText(
  projectRoot: string,
  sourceText: string | undefined,
  sourcePath: string | undefined,
): Promise<string | undefined> {
  const direct = sourceText?.trim();
  if (direct) return direct;
  const path = sourcePath?.trim();
  if (!path) return undefined;
  return readFile(safeChildPath(projectRoot, path), "utf-8");
}

async function writeProjectText(projectRoot: string, relativePath: string, content: string): Promise<void> {
  const fullPath = safeChildPath(projectRoot, relativePath);
  await mkdir(dirname(fullPath), { recursive: true });
  await writeFile(fullPath, content.endsWith("\n") ? content : `${content}\n`, "utf-8");
}

async function ensureProjectDir(projectRoot: string, relativePath: string): Promise<void> {
  await mkdir(safeChildPath(projectRoot, relativePath), { recursive: true });
}

function mergeRequirements(
  instruction: string,
  requirements: string | undefined,
  language: "zh" | "en" = "zh",
): string {
  const extraLabel = language === "en" ? "Additional requirements:" : "补充要求：";
  return [
    instruction.trim(),
    requirements?.trim() ? `\n${extraLabel}\n${requirements.trim()}` : "",
  ].filter(Boolean).join("\n");
}

function normalizeOutputDir(value: string): string {
  const text = value.trim().replace(/^\/+|\/+$/g, "");
  if (!text || text.includes("..") || text.includes("\0")) {
    throw new Error(`Invalid output directory: ${JSON.stringify(value)}`);
  }
  return text;
}

function resolveProjectBaseDir(outDir: string, projectId: string): string {
  const outputDir = normalizeOutputDir(outDir);
  return basename(outputDir) === projectId ? outputDir : relPath(outputDir, projectId);
}

// Project-relative path for results and manifests: always "/" separators.
function relPath(...segments: string[]): string {
  return toPosixPath(join(...segments));
}

function safeSegment(value: string): string {
  const text = value.trim();
  if (!text || text === "." || text === ".." || text.includes("/") || text.includes("\\") || text.includes("\0")) {
    throw new Error(`Invalid project id: ${JSON.stringify(value)}`);
  }
  return text.slice(0, 80);
}

function slugify(value: string): string {
  const text = value
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-+|-+$/g, "");
  return text || `script-${Date.now()}`;
}

function parseStoryboardPromptLines(markdown: string): string[] {
  const lines = markdown.split(/\r?\n/);
  const prompts: string[] = [];
  let promptColumnIndex = -1;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      promptColumnIndex = -1;
      continue;
    }
    const tableCells = parseMarkdownTableRow(line);
    if (tableCells) {
      if (isMarkdownTableSeparator(tableCells)) continue;
      const headerIndex = tableCells.findIndex(isPromptColumnHeader);
      if (headerIndex >= 0) {
        promptColumnIndex = headerIndex;
        continue;
      }
      if (promptColumnIndex >= 0) {
        const prompt = cleanPromptText(tableCells[promptColumnIndex] ?? "");
        if (prompt) prompts.push(prompt);
      }
      continue;
    }
    promptColumnIndex = -1;
    const promptMatch = /(?:^|[|>\-\d.)、\s])(?:\*\*)?\s*(?:Prompt(?:\s+for\s+[^:*：]+)?|提示词(?:\s*[^:*：]+)?|图像提示词|分镜图提示词)\s*(?:\*\*)?\s*[：:]\s*(.+?)\s*$/iu.exec(line);
    if (promptMatch) {
      const prompt = cleanPromptText(promptMatch[1]!);
      if (prompt) prompts.push(prompt);
      continue;
    }
    const numberedPrompt = /^(?:[-*]\s*)?(?:\d+|[０-９]+)[.)、：:\s-]+(.+)$/u.exec(line);
    if (numberedPrompt) {
      const prompt = numberedPrompt[1]!
        .replace(/\s+/g, " ")
        .trim();
      if (prompt) prompts.push(prompt);
    }
  }

  return prompts;
}

function parseMarkdownTableRow(line: string): string[] | undefined {
  if (!line.startsWith("|") || !line.endsWith("|")) return undefined;
  const cells = line.slice(1, -1).split("|").map((cell) => cell.trim());
  return cells.length >= 2 ? cells : undefined;
}

function isMarkdownTableSeparator(cells: readonly string[]): boolean {
  return cells.every((cell) => /^:?-{3,}:?$/u.test(cell));
}

function isPromptColumnHeader(cell: string): boolean {
  return /^(?:prompt|image\s*prompt|shot\s*prompt|提示词|图像提示词|分镜图提示词)$/iu.test(
    cell.replace(/[`*_]+/gu, "").trim(),
  );
}

function cleanPromptText(text: string): string {
  return text
    .replace(/\s*\|\s*$/u, "")
    .replace(/\*\*$/u, "")
    .replace(/^(?:Prompt(?:\s+for\s+[^:*：]+)?|提示词(?:\s*[^:*：]+)?|图像提示词|分镜图提示词)\s*[：:]\s*/iu, "")
    .replace(/\s+/g, " ")
    .trim();
}

function requiredSection(raw: string, headings: readonly string[], fallback: string): string {
  return extractMarkdownSection(raw, headings)?.trim() || fallback.trim();
}

export async function projectFileExists(projectRoot: string, relativePath: string): Promise<boolean> {
  try {
    await access(safeChildPath(projectRoot, relativePath));
    return true;
  } catch {
    return false;
  }
}
