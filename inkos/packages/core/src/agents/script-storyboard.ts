import { BaseAgent } from "./base.js";

export type ScriptTargetFormat =
  | "vertical_short_drama"
  | "screenplay"
  | "audio_drama"
  | "interactive_script"
  | "general_script";

export interface ScriptCreationInput {
  readonly title: string;
  readonly sourceKind?: string;
  readonly targetFormat?: ScriptTargetFormat;
  readonly sourceText?: string;
  readonly requirements?: string;
  readonly episodeCount?: number;
  readonly episodeDuration?: string;
  readonly language?: "zh" | "en";
}

export interface StoryboardCreationInput {
  readonly title: string;
  readonly sourceKind?: string;
  readonly sourceText?: string;
  readonly requirements?: string;
  readonly visualStyle?: string;
  readonly aspectRatio?: string;
  readonly granularity?: string;
  readonly maxShots?: number;
  readonly language?: "zh" | "en";
}

export interface InteractiveFilmCreationInput {
  readonly title: string;
  readonly sourceKind?: string;
  readonly sourceText?: string;
  readonly requirements?: string;
  readonly targetAudience?: string;
  readonly episodeCount?: number;
  readonly episodeDuration?: string;
  readonly budget?: string;
  readonly referenceMode?: string;
  readonly language?: "zh" | "en";
}

export class ScriptCreationAgent extends BaseAgent {
  get name(): string {
    return "script-creation-writer";
  }

  async writeScript(input: ScriptCreationInput): Promise<string> {
    const language = input.language ?? "zh";
    const response = await this.chat([
      { role: "system", content: buildScriptCreationSystemPrompt(language) },
      { role: "user", content: buildScriptCreationUserPrompt(input, language) },
    ], {
      temperature: 0.55,
      maxTokens: estimateScriptMaxTokens(input),
    });
    return response.content.trim();
  }
}

export class StoryboardCreationAgent extends BaseAgent {
  get name(): string {
    return "storyboard-creation-writer";
  }

  async writeStoryboard(input: StoryboardCreationInput): Promise<string> {
    const language = input.language ?? "zh";
    const response = await this.chat([
      { role: "system", content: buildStoryboardCreationSystemPrompt(language) },
      { role: "user", content: buildStoryboardCreationUserPrompt(input, language) },
    ], {
      temperature: 0.45,
      maxTokens: estimateStoryboardMaxTokens(input),
    });
    return response.content.trim();
  }
}

export class InteractiveFilmCreationAgent extends BaseAgent {
  get name(): string {
    return "interactive-film-creation-writer";
  }

  async writeInteractiveFilm(input: InteractiveFilmCreationInput): Promise<string> {
    const language = input.language ?? "zh";
    const response = await this.chat([
      { role: "system", content: buildInteractiveFilmCreationSystemPrompt(language) },
      { role: "user", content: buildInteractiveFilmCreationUserPrompt(input, language) },
    ], {
      temperature: 0.5,
      maxTokens: estimateInteractiveFilmMaxTokens(input),
    });
    return response.content.trim();
  }
}

export function renderScriptSpec(input: ScriptCreationInput): string {
  if ((input.language ?? "zh") === "en") {
    return [
      `# ${input.title} Script Creation Spec`,
      "",
      "## Goal",
      `- Deliverable: ${formatScriptTarget(input.targetFormat, "en")}`,
      input.episodeCount
        ? `- Episode/segment count: ${input.episodeCount}`
        : "- Episode/segment count: unspecified; judge from the source material and user requirements",
      input.episodeDuration
        ? `- Per-episode/segment duration: ${input.episodeDuration}`
        : "- Per-episode/segment duration: unspecified",
      input.sourceKind
        ? `- Source material: ${input.sourceKind}`
        : "- Source material: user input / conversation brief",
      "",
      "## User Requirements",
      input.requirements?.trim() || "Not separately specified; follow the instruction the user confirmed.",
      "",
      "## Adaptation Boundaries",
      "- Preserve the characters, relationships, conflicts, key events, and taboos the user explicitly specified.",
      "- Never decide adaptation intensity (\"faithful adaptation / commercial punch-up / low-budget shoot\") on the user's behalf; execute only the spec the user has confirmed.",
      "- If the source material is a novel, convert interiority into playable action, dialogue, evidence, objects, or on-screen consequences.",
      "- If the target is a short drama, every episode needs visible conflict and an end-of-episode reason to keep watching.",
      "",
      "## Source Material Summary",
      summarizeSourceForSpec(input.sourceText, "en"),
    ].join("\n");
  }
  return [
    `# ${input.title} 剧本创作规格`,
    "",
    "## 目标",
    `- 交付类型：${formatScriptTarget(input.targetFormat)}`,
    input.episodeCount ? `- 集数/段落数：${input.episodeCount}` : "- 集数/段落数：未指定，按素材和用户要求判断",
    input.episodeDuration ? `- 单集/单段时长：${input.episodeDuration}` : "- 单集/单段时长：未指定",
    input.sourceKind ? `- 原素材：${input.sourceKind}` : "- 原素材：用户输入/对话需求",
    "",
    "## 用户要求",
    input.requirements?.trim() || "未单独指定；以用户确认时的 instruction 为准。",
    "",
    "## 改编边界",
    "- 优先保留用户明确指定的人物、关系、冲突、关键事件和禁忌。",
    "- 不替用户擅自决定“忠实改编 / 商业强化 / 低成本拍摄”等强度；只执行用户已确认的规格。",
    "- 如果原素材是小说，内心戏要转成可演的动作、对白、证据、物件或场面后果。",
    "- 如果目标是短剧，每集必须有可见冲突和集尾继续看的理由。",
    "",
    "## 源素材摘要",
    summarizeSourceForSpec(input.sourceText),
  ].join("\n");
}

export function renderStoryboardSpec(input: StoryboardCreationInput): string {
  if ((input.language ?? "zh") === "en") {
    return [
      `# ${input.title} Storyboard Creation Spec`,
      "",
      "## Goal",
      `- Shot granularity: ${input.granularity?.trim() || "split by scene and key shots"}`,
      `- Aspect ratio: ${input.aspectRatio?.trim() || "unspecified; default to what the user's material and target imply"}`,
      `- Visual style: ${input.visualStyle?.trim() || "unspecified; judge from the user's material and target platform"}`,
      input.maxShots ? `- Shot cap: ${input.maxShots}` : "- Shot cap: unspecified",
      input.sourceKind
        ? `- Source material: ${input.sourceKind}`
        : "- Source material: user input / conversation brief",
      "",
      "## User Requirements",
      input.requirements?.trim() || "Not separately specified; follow the instruction the user confirmed.",
      "",
      "## Storyboard Boundaries",
      "- A storyboard is a creative tool, not a locked-in shooting plan; the output must stay easy to discuss, extend, trim, and re-shoot.",
      "- Each shot carries only what the frame can show, an actor can play, and a camera can express.",
      "- Image prompts serve image generation: subject, action, shot size, setting, lighting, mood, and key props must be explicit.",
      "- Follow only the art style, format, composition, and visual constraints the user has confirmed; never turn unstated preferences into default hard constraints.",
      "",
      "## Source Material Summary",
      summarizeSourceForSpec(input.sourceText, "en"),
    ].join("\n");
  }
  return [
    `# ${input.title} 分镜创作规格`,
    "",
    "## 目标",
    `- 分镜粒度：${input.granularity?.trim() || "按场景和关键镜头拆分"}`,
    `- 画幅：${input.aspectRatio?.trim() || "未指定，默认按用户素材目标判断"}`,
    `- 视觉风格：${input.visualStyle?.trim() || "未指定，按用户素材和目标平台判断"}`,
    input.maxShots ? `- 镜头上限：${input.maxShots}` : "- 镜头上限：未指定",
    input.sourceKind ? `- 原素材：${input.sourceKind}` : "- 原素材：用户输入/对话需求",
    "",
    "## 用户要求",
    input.requirements?.trim() || "未单独指定；以用户确认时的 instruction 为准。",
    "",
    "## 分镜边界",
    "- 分镜是创作工具，不替用户锁死最终拍法；输出要便于继续讨论、增删、改镜头。",
    "- 每个镜头只写画面能看见、角色能演、镜头能表达的信息。",
    "- 分镜图提示词服务图像生成：角色、动作、景别、场景、光线、情绪和关键道具要清楚。",
    "- 只遵循用户已确认的画风、格式、构图和视觉限制；用户没说的，不写成默认硬限制。",
    "",
    "## 源素材摘要",
    summarizeSourceForSpec(input.sourceText),
  ].join("\n");
}

export function renderInteractiveFilmSpec(input: InteractiveFilmCreationInput): string {
  if ((input.language ?? "zh") === "en") {
    return [
      `# ${input.title} Interactive Film Creation Spec`,
      "",
      "## Goal",
      "- Deliverable: interactive film / interactive narrative game / film-game script",
      input.episodeCount
        ? `- Story segments/episodes: ${input.episodeCount}`
        : "- Story segments/episodes: unspecified; judge from the source material and user requirements",
      input.episodeDuration
        ? `- Per-segment/episode duration: ${input.episodeDuration}`
        : "- Per-segment/episode duration: unspecified",
      input.budget ? `- Budget constraint: ${input.budget}` : "- Budget constraint: unspecified",
      input.targetAudience ? `- Target audience: ${input.targetAudience}` : "- Target audience: unspecified",
      input.referenceMode
        ? `- Reference mode: ${input.referenceMode}`
        : "- Reference mode: unspecified by the user; do not impose a fixed game template",
      input.sourceKind
        ? `- Source material: ${input.sourceKind}`
        : "- Source material: user input / conversation brief",
      "",
      "## User Requirements",
      input.requirements?.trim() || "Not separately specified; follow the instruction the user confirmed.",
      "",
      "## Interactive Film Boundaries",
      "- This is a creative deliverable, not a hard-numbers RPG engine design; variables, flags, relationships, and ending conditions must serve story branching.",
      "- It must include branching storylines, key player choices, how variables/flags change later plot, and the conditions for reaching each of the multiple endings.",
      "- Describe the variable system in natural language: states, relationships, secret/public status, evidence, items, identities, affinity/trust, and the like; never force fixed numeric stats or equipment tiers.",
      "- The deliverable must fit interactive film/drama production: a clear story tree, shootable nodes, playable dialogue, drawable storyboards, and image prompts usable for asset generation.",
      "- Never decide subject matter, budget, art style, or commercial punch-up intensity on the user's behalf; mark anything unspecified as adjustable.",
      "",
      "## Source Material Summary",
      summarizeSourceForSpec(input.sourceText, "en"),
    ].join("\n");
  }
  return [
    `# ${input.title} 互动影游创作规格`,
    "",
    "## 目标",
    "- 交付类型：互动影游 / 互动叙事类游戏 / 影游剧本",
    input.episodeCount ? `- 剧情段落/集数：${input.episodeCount}` : "- 剧情段落/集数：未指定，按素材和用户要求判断",
    input.episodeDuration ? `- 单段/单集时长：${input.episodeDuration}` : "- 单段/单集时长：未指定",
    input.budget ? `- 预算约束：${input.budget}` : "- 预算约束：未指定",
    input.targetAudience ? `- 目标受众：${input.targetAudience}` : "- 目标受众：未指定",
    input.referenceMode ? `- 参考模式：${input.referenceMode}` : "- 参考模式：用户未指定，不擅自套固定游戏模板",
    input.sourceKind ? `- 原素材：${input.sourceKind}` : "- 原素材：用户输入/对话需求",
    "",
    "## 用户要求",
    input.requirements?.trim() || "未单独指定；以用户确认时的 instruction 为准。",
    "",
    "## 互动影游边界",
    "- 这是创作交付稿，不是硬数值 RPG 引擎设计；变量、旗标、关系和结局条件必须服务剧情分支。",
    "- 必须包含多分支剧情、玩家关键选择、变量/旗标如何改变后续剧情，以及多结局达成条件。",
    "- 变量系统用自然语言说明即可：状态、关系、隐瞒/公开、证据、物品、身份、好感/信任等；不要强行套固定数值或装备等级。",
    "- 交付要适配影游/互动剧制作：剧情树清晰、节点可拍、对白可演、分镜可画、图片提示词可用于资产生成。",
    "- 不替用户擅自决定题材、预算、画风和商业强化强度；未指定处写为可调整。",
    "",
    "## 源素材摘要",
    summarizeSourceForSpec(input.sourceText),
  ].join("\n");
}

export function extractStoryboardImagePrompts(raw: string): string {
  const section = extractMarkdownSection(raw, [
    "图像提示词",
    "分镜图提示词",
    "Image Prompts",
    "Shot Image Prompts",
  ]);
  const source = section?.trim() || raw.trim();
  const prompts = extractPromptLines(source);
  return prompts.length > 0 ? prompts.map((prompt, index) => `${index + 1}. ${prompt}`).join("\n") : "";
}

export function extractMarkdownSection(raw: string, headings: readonly string[]): string | undefined {
  const lines = raw.split(/\r?\n/);
  let start = -1;
  let level = 0;
  const normalizedHeadings = headings.map(normalizeHeadingText);
  for (let index = 0; index < lines.length; index += 1) {
    const match = /^(#{1,6})\s*(.+?)\s*$/u.exec(lines[index] ?? "");
    if (!match) continue;
    const text = normalizeHeadingText(match[2]!);
    if (normalizedHeadings.some((heading) => headingMatches(text, heading))) {
      start = index + 1;
      level = match[1]!.length;
      break;
    }
  }
  if (start < 0) return undefined;
  let end = lines.length;
  for (let index = start; index < lines.length; index += 1) {
    const match = /^(#{1,6})\s+/u.exec(lines[index] ?? "");
    if (match && match[1]!.length <= level) {
      end = index;
      break;
    }
  }
  return lines.slice(start, end).join("\n");
}

function normalizeHeadingText(text: string): string {
  return text
    .trim()
    .replace(/^\*\*(.+)\*\*$/u, "$1")
    .replace(/[`*_]+/gu, "")
    .replace(/\s+/gu, " ")
    .toLowerCase();
}

function headingMatches(text: string, heading: string): boolean {
  if (text === heading) return true;
  if (!text.startsWith(heading)) return false;
  const rest = text.slice(heading.length).trim();
  return rest === "" || /^[（(【\[\s:：\-—]/u.test(rest);
}

export function normalizeScriptEpisodeEndLabels(script: string): string {
  const lines = script.split(/\r?\n/);
  let currentEpisode: string | null = null;
  return lines.map((line) => {
    const heading = /^#{1,6}\s*第\s*([一二三四五六七八九十百千万\d]+)\s*集(?:\s|$)/u.exec(line.trim());
    if (heading) currentEpisode = heading[1]!;
    if (!currentEpisode) return line;
    return line.replace(
      /(字幕\s*[：:]\s*)第\s*[一二三四五六七八九十百千万\d]+\s*集完/gu,
      `$1第${currentEpisode}集完`,
    );
  }).join("\n");
}

function buildScriptCreationSystemPrompt(language: "zh" | "en" = "zh"): string {
  if (language === "en") {
    return [
      "You are a script-creation tool, not a novel-continuation engine.",
      "Your job is to adapt a novel, concept, outline, or existing text into a script that production can keep working from, following the spec the user has confirmed.",
      "Never decide adaptation intensity on the user's behalf; execute only the goals, format, boundaries, and constraints already confirmed in the spec.",
      "Action lines carry only what the audience can see, an actor can play, and a camera can shoot; convert interiority into behavior, dialogue, objects, evidence, or on-screen consequences.",
      "Dialogue must serve conflict, relationships, information flow, or emotional shifts; no hollow exposition.",
      "Output Markdown. No process notes, no model self-narration, no \"Here is\" preamble.",
    ].join("\n");
  }
  return [
    "你是剧本创作工具，不是小说续写器。",
    "你的任务是根据用户确认过的规格，把小说、创意、大纲或已有文本改成可继续制作的剧本。",
    "不要替用户擅自决定改编强度；只执行规格里已经确认的目标、格式、边界和限制。",
    "动作行只写观众能看见、演员能演、镜头能拍的信息；内心戏要转成行为、对白、物件、证据或场面后果。",
    "对白要服务冲突、关系、信息推进或情绪变化，不写空泛解释。",
    "输出 Markdown。不要写流程说明、模型自述或“以下是”。",
  ].join("\n");
}

function buildScriptCreationUserPrompt(input: ScriptCreationInput, language: "zh" | "en" = "zh"): string {
  if (language === "en") {
    return [
      "## Creation Spec",
      renderScriptSpec(input),
      "",
      "## Full Source Material",
      input.sourceText?.trim()
        || "The user did not provide full source material; write an extensible script draft strictly from the creation spec and user requirements.",
      "",
      "## Output Format",
      `# ${input.title}`,
      "",
      "## Script",
      "",
      "Follow the target format. Vertical short drama: \"Episode N / scene slug / characters / action / dialogue / end-of-episode hook\". Standard screenplay: \"scene heading / action / character / dialogue\".",
    ].join("\n");
  }
  return [
    "## 创作规格",
    renderScriptSpec(input),
    "",
    "## 完整源素材",
    input.sourceText?.trim() || "用户没有提供完整源素材；请严格根据创作规格和用户要求写一个可继续扩展的剧本稿。",
    "",
    "## 输出格式",
    `# ${input.title}`,
    "",
    "## 剧本正文",
    "",
    "按目标格式输出。竖屏短剧使用“第N集 / 场次 / 人物 / 动作 / 对白 / 集尾钩子”；标准剧本使用“场景标题 / 动作 / 角色 / 对白”。",
  ].join("\n");
}

function buildStoryboardCreationSystemPrompt(language: "zh" | "en" = "zh"): string {
  if (language === "en") {
    return [
      "You are a storyboard-creation tool: you break a script, novel excerpt, or concept into shots that can be filmed, drawn, and fed to image generation.",
      "A storyboard is not a plot summary; every shot needs a visual, character placement, action, shot size, or a visual focus.",
      "Keep the visual spec the user has confirmed; never promote visual constraints the user did not confirm into default requirements.",
      "Image prompts must be generation-ready: subject, action, setting, lighting, composition, mood, and key props all explicit.",
      "Output Markdown. No model self-narration or process explanation.",
    ].join("\n");
  }
  return [
    "你是分镜创作工具，负责把剧本、小说片段或创意拆成可拍、可画、可生图的分镜。",
    "分镜不是剧情摘要；每个镜头都要有画面、角色位置、动作、景别或视觉重点。",
    "保留用户确认的视觉规格；不要把用户没有确认的视觉限制写成默认要求。",
    "图像提示词要便于生图：主体、动作、场景、光线、构图、情绪、关键道具明确。",
    "输出 Markdown。不要写模型自述或流程解释。",
  ].join("\n");
}

function buildStoryboardCreationUserPrompt(input: StoryboardCreationInput, language: "zh" | "en" = "zh"): string {
  const maxShots = input.maxShots ?? 24;
  if (language === "en") {
    return [
      "## Storyboard Spec",
      renderStoryboardSpec(input),
      "",
      "## Full Source Material",
      input.sourceText?.trim()
        || "The user did not provide full source material; write an extensible storyboard draft strictly from the storyboard spec and user requirements.",
      "",
      "## Output Format",
      `# ${input.title} Storyboard`,
      "",
      "## Storyboard",
      "",
      `Output at most ${maxShots} shots. Each shot includes: shot number, visual, characters/objects, action, shot size/camera, dialogue/captions, suggested duration, notes.`,
      "",
      "## Image Prompts",
      "",
      "Write one generation-ready image prompt per shot. Each prompt MUST be its own `Prompt: ...` line; never merge it into the storyboard body, table headers, or explanations. Include only the visual constraints the user has confirmed.",
    ].join("\n");
  }
  return [
    "## 分镜规格",
    renderStoryboardSpec(input),
    "",
    "## 完整源素材",
    input.sourceText?.trim() || "用户没有提供完整源素材；请严格根据分镜规格和用户要求写一个可继续扩展的分镜稿。",
    "",
    "## 输出格式",
    `# ${input.title} 分镜`,
    "",
    "## 分镜表",
    "",
    `输出不超过 ${maxShots} 个镜头。每个镜头包含：镜号、画面、人物/物件、动作、景别/机位、对白/字幕、时长建议、备注。`,
    "",
    "## 图像提示词",
    "",
    "为每个镜头写一条可用于生图的提示词。每条必须单独写成 `Prompt: ...`，不要混入分镜正文、表头或解释；只写用户确认过的视觉限制。",
  ].join("\n");
}

function buildInteractiveFilmCreationSystemPrompt(language: "zh" | "en" = "zh"): string {
  if (language === "en") {
    return [
      "You are an interactive-film creation tool: you turn a concept, novel, script, or user brief into an interactive-film deliverable that production can build from.",
      "An interactive film is not an ordinary script: it must have a story tree, key player choices, variables/flags, relationship/evidence/item states, and the conditions for reaching each of the multiple endings.",
      "The variable system exists only to drive plot progression and branch unlocking; no default RPG stats, combat formulas, or equipment tiers. Write such rules only when the user explicitly asks for them.",
      "Output must be Markdown with the specified sections. No model self-narration, process notes, or \"Here is\" preamble.",
      "Every storyboard image prompt must be its own standalone `Prompt: ...` line so downstream asset management can pick it up; include only the visual constraints the user has confirmed.",
    ].join("\n");
  }
  return [
    "你是互动影游创作工具，负责把创意、小说、剧本或用户需求整理成可制作的互动影游交付稿。",
    "互动影游不是普通剧本：必须有剧情树、关键选择、变量/旗标、关系/证据/物品状态、多结局达成条件。",
    "变量系统只服务剧情推进和分支解锁，不要默认 RPG 数值、战斗公式或装备等级；只有用户明确要求时才写对应规则。",
    "输出必须是 Markdown，包含指定小节。不要写模型自述、流程说明或“以下是”。",
    "分镜图提示词必须写成单独的 `Prompt: ...` 行，便于后续资产管理；只写用户确认过的视觉限制。",
  ].join("\n");
}

function buildInteractiveFilmCreationUserPrompt(input: InteractiveFilmCreationInput, language: "zh" | "en" = "zh"): string {
  if (language === "en") {
    return [
      "## Interactive Film Spec",
      renderInteractiveFilmSpec(input),
      "",
      "## Full Source Material",
      input.sourceText?.trim()
        || "The user did not provide full source material; write an extensible interactive-film deliverable strictly from the creation spec and user requirements.",
      "",
      "## Output Format",
      `# ${input.title} Interactive Film Package`,
      "",
      "## Story Tree",
      "Lay out main-line nodes, branch nodes, key choices, and merge/no-return relationships as Markdown. The multi-ending structure must be visible at a glance.",
      "",
      "## Variables and Flags",
      "List each variable/flag: name, meaning, trigger, scope of impact, and related nodes. Variables may be relationships, states, evidence, items, identities, secret/public status, ending gates, and so on.",
      "",
      "## Ending Paths",
      "For every ending: its unlock conditions, the key choice chain, the required variables/flags, plus any failure or hidden-ending conditions.",
      "",
      "## Interactive Script",
      "Write a playable script per node: scene, characters, action, dialogue, player choices, variable changes, and branch destinations. Never write summaries only.",
      "",
      "## Storyboard and Image Prompts",
      "List the key shots. Each shot includes visual, characters/objects, action, shot size, and suggested duration. After each shot, add exactly one standalone `Prompt: ...` line.",
    ].join("\n");
  }
  return [
    "## 互动影游规格",
    renderInteractiveFilmSpec(input),
    "",
    "## 完整源素材",
    input.sourceText?.trim() || "用户没有提供完整源素材；请严格根据创作规格和用户要求写一个可继续扩展的互动影游交付稿。",
    "",
    "## 输出格式",
    `# ${input.title} 互动影游方案`,
    "",
    "## 剧情树",
    "用 Markdown 列出主线节点、分支节点、关键选择、回流/不可回流关系。必须能看出多结局结构。",
    "",
    "## 变量与旗标表",
    "列出变量/旗标名、含义、触发方式、影响范围、对应节点。变量可以是关系、状态、证据、物品、身份、公开/隐瞒、结局门槛等。",
    "",
    "## 多结局路径",
    "列出每个结局的达成条件、关键选择链、必需变量/旗标，以及失败或隐藏结局条件。",
    "",
    "## 互动剧本",
    "按节点写可演剧本：场景、人物、动作、对白、玩家选择、变量变化和分支去向。不要只写摘要。",
    "",
    "## 分镜与图像提示词",
    "列出关键镜头。每个镜头包含画面、人物/物件、动作、景别、时长建议。每个镜头后必须单独写一行 `Prompt: ...`。",
  ].join("\n");
}

function formatScriptTarget(value: ScriptTargetFormat | undefined, language: "zh" | "en" = "zh"): string {
  if (language === "en") {
    switch (value) {
      case "vertical_short_drama":
        return "vertical short drama";
      case "screenplay":
        return "standard screenplay";
      case "audio_drama":
        return "audio drama";
      case "interactive_script":
        return "interactive script";
      case "general_script":
      default:
        return "general script";
    }
  }
  switch (value) {
    case "vertical_short_drama":
      return "竖屏短剧";
    case "screenplay":
      return "标准剧本";
    case "audio_drama":
      return "广播剧/有声剧";
    case "interactive_script":
      return "互动剧本";
    case "general_script":
    default:
      return "通用剧本";
  }
}

function summarizeSourceForSpec(sourceText: string | undefined, language: "zh" | "en" = "zh"): string {
  const text = sourceText?.replace(/\s+/g, " ").trim();
  if (language === "en") {
    if (!text) return "No full source material provided.";
    return `Full source material provided, about ${text.length} characters; the full content will be read during generation.`;
  }
  if (!text) return "未提供完整源素材。";
  return `已提供完整源素材，约 ${text.length} 字符；生成时会读取完整内容。`;
}

function estimateScriptMaxTokens(input: ScriptCreationInput): number {
  const episodes = input.episodeCount ?? 6;
  return Math.min(32000, Math.max(12000, episodes * 2200));
}

function estimateStoryboardMaxTokens(input: StoryboardCreationInput): number {
  const shots = input.maxShots ?? 24;
  return Math.min(24000, Math.max(10000, shots * 700));
}

function estimateInteractiveFilmMaxTokens(input: InteractiveFilmCreationInput): number {
  const episodes = input.episodeCount ?? 6;
  return Math.min(36000, Math.max(16000, episodes * 3000));
}

function extractPromptLines(markdown: string): string[] {
  const prompts: string[] = [];
  let promptColumnIndex = -1;
  for (const rawLine of markdown.split(/\r?\n/)) {
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
    if (!promptMatch) continue;
    const prompt = cleanPromptText(promptMatch[1]!);
    if (prompt) prompts.push(prompt);
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
