import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import {
  loadTranslationChapter,
  loadTranslationGlossary,
  loadTranslationManifest,
  mergeGlossaryTerms,
  saveTranslationChapter,
  saveTranslationGlossary,
  saveTranslationManifest,
  translationProjectDir,
} from "./run-store.js";
import type {
  RunTranslationProjectResult,
  TranslationChapterFile,
  TranslationModelPort,
  TranslationProjectManifest,
  TranslationSegment,
} from "./types.js";

export async function runTranslationProject(
  projectRoot: string,
  projectId: string,
  options: {
    readonly model: TranslationModelPort;
    readonly batchSize?: number;
  },
): Promise<RunTranslationProjectResult> {
  let manifest = await loadTranslationManifest(projectRoot, projectId);
  let glossary = [...await loadTranslationGlossary(projectRoot, projectId)];
  const reportLines = [`# Translation Review`, ""];
  let translatedSegments = 0;
  let reviewedChapters = 0;
  const batchSize = Math.max(1, Math.min(options.batchSize ?? 8, 32));

  for (const chapterInfo of manifest.chapters) {
    const source = await loadTranslationChapter(projectRoot, chapterInfo.sourcePath);
    const translated = await loadTranslationChapter(projectRoot, chapterInfo.translatedPath).catch(() => ({
      ...source,
      segments: [],
    } satisfies TranslationChapterFile));
    const translatedByIndex = new Map(translated.segments.map((segment) => [segment.index, segment]));
    const pending = source.segments.filter((segment) => !translatedByIndex.get(segment.index)?.target?.trim());

    for (let offset = 0; offset < pending.length; offset += batchSize) {
      const batch = pending.slice(offset, offset + batchSize);
      const result = await options.model.translateSegments({
        sourceLanguage: manifest.sourceLanguage,
        targetLanguage: manifest.targetLanguage,
        chapterTitle: source.title,
        segments: batch,
        glossary,
      });
      for (const item of result.segments) {
        const original = source.segments.find((segment) => segment.index === item.index);
        if (!original) continue;
        translatedByIndex.set(item.index, {
          ...original,
          target: item.target,
          ...(item.notes?.trim() ? { notes: item.notes.trim() } : {}),
        });
        translatedSegments++;
      }
      if (result.glossary?.length) {
        glossary = [...mergeGlossaryTerms([...glossary, ...result.glossary])];
      }
      await saveTranslationGlossary(projectRoot, projectId, glossary);
      await saveTranslationChapter(projectRoot, chapterInfo.translatedPath, {
        ...source,
        segments: orderedTranslatedSegments(source.segments, translatedByIndex),
      });
    }

    const completedChapter = await loadTranslationChapter(projectRoot, chapterInfo.translatedPath);
    let status: "translated" | "reviewed" = "translated";
    if (options.model.reviewChapter && completedChapter.segments.some((segment) => segment.target?.trim())) {
      const review = await options.model.reviewChapter({
        sourceLanguage: manifest.sourceLanguage,
        targetLanguage: manifest.targetLanguage,
        chapterTitle: source.title,
        segments: completedChapter.segments,
        glossary,
      });
      reviewedChapters++;
      status = review.passed ? "reviewed" : "translated";
      reportLines.push(`## ${source.title}`, "", `- passed: ${review.passed ? "yes" : "no"}`, `- summary: ${review.summary}`, "");
      for (const issue of review.issues) {
        reportLines.push(`- issue: ${issue}`);
      }
      reportLines.push("");
    }
    manifest = updateChapterStatus(manifest, chapterInfo.number, status);
    await saveTranslationManifest(projectRoot, manifest);
  }

  const reportPathAbs = join(translationProjectDir(projectRoot, projectId), "review-report.md");
  await writeFile(reportPathAbs, reportLines.join("\n").trimEnd() + "\n", "utf-8");
  return {
    projectId,
    translatedSegments,
    reviewedChapters,
    reportPath: `translations/${projectId}/review-report.md`,
  };
}

function orderedTranslatedSegments(
  sourceSegments: ReadonlyArray<TranslationSegment>,
  translatedByIndex: ReadonlyMap<number, TranslationSegment>,
): ReadonlyArray<TranslationSegment> {
  return sourceSegments.map((segment) => translatedByIndex.get(segment.index) ?? segment);
}

function updateChapterStatus(
  manifest: TranslationProjectManifest,
  chapterNumber: number,
  status: "translated" | "reviewed",
): TranslationProjectManifest {
  return {
    ...manifest,
    updatedAt: new Date().toISOString(),
    chapters: manifest.chapters.map((chapter) =>
      chapter.number === chapterNumber ? { ...chapter, status } : chapter,
    ),
  };
}
