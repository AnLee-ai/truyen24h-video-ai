import { lstat, readFile } from "node:fs/promises";
import { join, relative, sep } from "node:path";
import { Type, type Static } from "@mariozechner/pi-ai";
import type { AgentMessage, AgentTool, AgentToolResult } from "@mariozechner/pi-agent-core";
import type { SkillRegistry } from "../skills/index.js";
import { safeChildPath } from "../utils/path-safety.js";

const MAX_SKILL_RESOURCE_BYTES = 512 * 1024;
const EXPIRED_SKILL_GUIDANCE = "This skill was used for its original turn only. Its instructions are not active for later turns.";

const UseSkillParams = Type.Object({
  skillId: Type.String({
    description: "Exact skill id from the available skill catalog.",
  }),
  resourcePath: Type.Optional(Type.String({
    description: "Optional relative text resource inside the skill folder, after the main skill has been activated.",
  })),
});

type UseSkillParamsType = Static<typeof UseSkillParams>;

export interface CreateUseSkillToolOptions {
  readonly registry: SkillRegistry;
  readonly disabledSkillIds?: ReadonlyArray<string>;
  readonly onActivate?: (skillId: string) => void;
}

export function createUseSkillTool(
  options: CreateUseSkillToolOptions,
): AgentTool<typeof UseSkillParams> {
  const disabled = new Set((options.disabledSkillIds ?? []).map(normalizeSkillId));
  return {
    name: "use_skill",
    label: "Use Skill",
    description: "Load one available professional skill because the current user intent needs it. This only loads instructions and static references; it grants no tools or execution permissions.",
    parameters: UseSkillParams,
    async execute(_toolCallId: string, params: UseSkillParamsType): Promise<AgentToolResult<unknown>> {
      const skillId = normalizeSkillId(params.skillId);
      if (disabled.has(skillId)) {
        throw new Error(`Skill is disabled: ${skillId}`);
      }
      const skill = options.registry.getSkill(skillId);
      if (!skill) {
        throw new Error(`Skill is not available: ${skillId}`);
      }
      let resource: { readonly path: string; readonly body: string } | undefined;
      if (params.resourcePath?.trim()) {
        if (!skill.baseDir) {
          throw new Error(`Skill has no readable resource directory: ${skill.id}`);
        }
        const resourcePath = params.resourcePath.trim();
        const fullPath = safeChildPath(skill.baseDir, resourcePath);
        const info = await lstatWithoutSymlinks(skill.baseDir, fullPath);
        if (!info.isFile()) throw new Error(`Skill resource is not a file: ${resourcePath}`);
        if (info.size > MAX_SKILL_RESOURCE_BYTES) {
          throw new Error(`Skill resource is too large to load: ${resourcePath}`);
        }
        const body = await readFile(fullPath, "utf-8");
        if (body.includes("\0")) {
          throw new Error(`Skill resource is not UTF-8 text: ${resourcePath}`);
        }
        resource = { path: resourcePath, body };
      }

      options.onActivate?.(skill.id);
      return textResult(
        [
          `Skill activated: ${skill.id}`,
          `Purpose: ${skill.description}`,
          "",
          skill.body.trim() || skill.description,
          ...(resource
            ? [
                "",
                `Static resource (${resource.path}):`,
                resource.body,
              ]
            : []),
          "",
          "This skill provides instructions only. Continue using the current session's existing tools and confirmation rules.",
        ].filter(Boolean).join("\n"),
        {
          kind: "skill_activated",
          skillId: skill.id,
          ...(resource ? { resourcePath: resource.path } : {}),
        },
      );
    },
  };
}

function textResult<T>(text: string, details: T): AgentToolResult<T> {
  return { content: [{ type: "text", text }], details };
}

function normalizeSkillId(value: string): string {
  return value.trim().toLowerCase();
}

async function lstatWithoutSymlinks(root: string, fullPath: string) {
  const rel = relative(root, fullPath);
  let current = root;
  let info = await lstat(root);
  if (info.isSymbolicLink()) {
    throw new Error(`Skill resource symbolic link is not allowed: ${root}`);
  }
  for (const part of rel.split(sep).filter(Boolean)) {
    current = join(current, part);
    info = await lstat(current);
    if (info.isSymbolicLink()) {
      throw new Error(`Skill resource symbolic link is not allowed: ${rel}`);
    }
  }
  return info;
}

function expireSkillToolResult(message: AgentMessage): AgentMessage {
  if (
    !message
    || typeof message !== "object"
    || (message as { role?: unknown }).role !== "toolResult"
    || (message as { toolName?: unknown }).toolName !== "use_skill"
  ) {
    return message;
  }
  return {
    ...message,
    content: [{ type: "text", text: EXPIRED_SKILL_GUIDANCE }],
    details: { kind: "skill_expired" },
  } as AgentMessage;
}

export function assistantInvokesSkill(message: AgentMessage): boolean {
  if (
    !message
    || typeof message !== "object"
    || (message as { role?: unknown }).role !== "assistant"
  ) {
    return false;
  }
  const content = (message as { content?: unknown }).content;
  return Array.isArray(content) && content.some((part) => (
    part
    && typeof part === "object"
    && (part as { type?: unknown }).type === "toolCall"
    && (part as { name?: unknown }).name === "use_skill"
  ));
}

export function sanitizeSkillTurnMessage(
  message: AgentMessage,
  stripThinking: boolean,
): AgentMessage {
  const expired = expireSkillToolResult(message);
  if (
    !stripThinking
    || !expired
    || typeof expired !== "object"
    || (expired as { role?: unknown }).role !== "assistant"
  ) {
    return expired;
  }
  const content = (expired as { content?: unknown }).content;
  if (!Array.isArray(content)) return expired;
  const visibleContent = content.filter((part) => (
    !part
    || typeof part !== "object"
    || (part as { type?: unknown }).type !== "thinking"
  ));
  if (visibleContent.length === content.length) return expired;
  return {
    ...expired,
    content: visibleContent,
  } as AgentMessage;
}
