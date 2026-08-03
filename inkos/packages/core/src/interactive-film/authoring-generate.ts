import { extractJson } from "./generate.js";
import { StoryNodeSchema } from "./graph-schema.js";
import type { StoryGraphDelta } from "./delta.js";

export function buildFillNodeDeltaFromLLMText(text: string, nodeId: string): StoryGraphDelta {
  const parsed = extractJson(text) as Record<string, unknown>;
  const node = StoryNodeSchema.parse({ ...parsed, id: nodeId });
  return { nodes: { upsert: [node], remove: [] }, notes: [] };
}

export function buildStructureDeltaFromLLMText(text: string): StoryGraphDelta {
  const parsed = extractJson(text) as { nodes?: unknown[] };
  const rawNodes = Array.isArray(parsed.nodes) ? parsed.nodes : [];
  if (rawNodes.length === 0) throw new Error("draft_structure: LLM returned no nodes");
  const nodes = rawNodes.map((n) => StoryNodeSchema.parse(n));
  return { nodes: { upsert: nodes, remove: [] }, notes: [] };
}
