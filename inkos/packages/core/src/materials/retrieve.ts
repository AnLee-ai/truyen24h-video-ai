import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { safeChildPath } from "../utils/path-safety.js";
import { toPosixPath } from "../utils/posix-path.js";
import type { MaterialAsset, MaterialPurpose } from "./ingest.js";

export interface RetrieveMaterialsInput {
  readonly query: string;
  readonly purpose?: MaterialPurpose;
  readonly limit?: number;
}

export interface RetrievedMaterial {
  readonly id: string;
  readonly title: string;
  readonly kind: MaterialAsset["kind"];
  readonly purpose: MaterialPurpose;
  readonly source: string;
  readonly markdownPath: string;
  readonly score: number;
  readonly excerpt: string;
  readonly charStart: number;
  readonly charEnd: number;
}

const DEFAULT_LIMIT = 5;
const MAX_LIMIT = 12;
const SNIPPET_RADIUS = 700;

export async function retrieveMaterials(
  projectRoot: string,
  input: RetrieveMaterialsInput,
): Promise<RetrievedMaterial[]> {
  const queryTerms = extractTerms(input.query);
  const assets = await listMaterialAssets(projectRoot);
  const results: RetrievedMaterial[] = [];
  for (const asset of assets) {
    if (input.purpose && asset.purpose !== input.purpose) continue;
    const markdownPath = safeChildPath(projectRoot, asset.markdownPath);
    let markdown = "";
    try {
      markdown = await readFile(markdownPath, "utf-8");
    } catch {
      continue;
    }
    const score = scoreMaterial(asset, markdown, queryTerms);
    if (queryTerms.length > 0 && score <= 0) continue;
    const snippet = buildSnippet(markdown, queryTerms);
    results.push({
      id: asset.id,
      title: asset.title,
      kind: asset.kind,
      purpose: asset.purpose,
      source: asset.source,
      // Manifests written by older Windows builds may contain "\" separators.
      markdownPath: toPosixPath(asset.markdownPath),
      score,
      excerpt: snippet.excerpt,
      charStart: snippet.charStart,
      charEnd: snippet.charEnd,
    });
  }
  return results
    .sort((a, b) => b.score - a.score || a.title.localeCompare(b.title))
    .slice(0, normalizeLimit(input.limit));
}

async function listMaterialAssets(projectRoot: string): Promise<MaterialAsset[]> {
  const materialsDir = join(projectRoot, ".inkos", "materials");
  let entries: string[] = [];
  try {
    entries = await readdir(materialsDir);
  } catch {
    return [];
  }
  const assets: MaterialAsset[] = [];
  for (const entry of entries) {
    if (!entry.endsWith(".json")) continue;
    try {
      const raw = await readFile(join(materialsDir, entry), "utf-8");
      const asset = JSON.parse(raw) as MaterialAsset;
      if (asset.id && asset.markdownPath && asset.title) assets.push(asset);
    } catch {
      // Ignore corrupt stale manifests; retrieval should not break the chat turn.
    }
  }
  return assets;
}

function scoreMaterial(asset: MaterialAsset, markdown: string, terms: readonly string[]): number {
  if (terms.length === 0) return 1;
  const title = asset.title.toLowerCase();
  const source = asset.source.toLowerCase();
  const body = markdown.toLowerCase();
  let score = 0;
  for (const term of terms) {
    const normalized = term.toLowerCase();
    if (title.includes(normalized)) score += 8;
    if (source.includes(normalized)) score += 4;
    const first = body.indexOf(normalized);
    if (first >= 0) score += 2 + Math.max(0, 2 - first / 4000);
  }
  return score;
}

function buildSnippet(markdown: string, terms: readonly string[]): { excerpt: string; charStart: number; charEnd: number } {
  const lower = markdown.toLowerCase();
  let hit = -1;
  for (const term of terms) {
    const idx = lower.indexOf(term.toLowerCase());
    if (idx >= 0 && (hit < 0 || idx < hit)) hit = idx;
  }
  const center = hit >= 0 ? hit : Math.min(markdown.length, 500);
  const charStart = Math.max(0, center - SNIPPET_RADIUS);
  const charEnd = Math.min(markdown.length, center + SNIPPET_RADIUS);
  return {
    excerpt: markdown.slice(charStart, charEnd).trim(),
    charStart,
    charEnd,
  };
}

function normalizeLimit(limit: number | undefined): number {
  if (!Number.isFinite(limit ?? DEFAULT_LIMIT)) return DEFAULT_LIMIT;
  return Math.max(1, Math.min(MAX_LIMIT, Math.floor(limit ?? DEFAULT_LIMIT)));
}

function extractTerms(query: string): string[] {
  const raw = query.normalize("NFKC").trim().toLowerCase();
  if (!raw) return [];
  const terms = new Set<string>();
  for (const match of raw.matchAll(/[\p{L}\p{N}]{2,}/gu)) {
    terms.add(match[0]);
  }
  return [...terms].slice(0, 24);
}
