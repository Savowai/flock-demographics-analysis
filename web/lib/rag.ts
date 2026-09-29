"use client";

import { pipeline, env, type FeatureExtractionPipeline } from "@huggingface/transformers";

/**
 * Browser-side retrieval.
 *
 * Passage vectors were computed offline with all-MiniLM-L6-v2, L2-normalised,
 * then quantised to int8 (see src/analysis/export_web.py) — 1,125 × 384 values
 * in 432 KB. The question is embedded here with the same model via
 * Transformers.js, so nothing is sent anywhere until the user asks for an
 * answer, and only the winning passages are sent then.
 */

export type Chunk = {
  id: string;
  text: string;
  file: string;
  title: string;
  publisher: string;
  date: string;
  url: string;
  bucket: string;
};

export type Hit = Chunk & { score: number };

type Meta = { count: number; dims: number; scale: number; model: string };

let chunks: Chunk[] | null = null;
let vectors: Int8Array | null = null;
let meta: Meta | null = null;
let extractor: FeatureExtractionPipeline | null = null;

// Cosine similarity below this means retrieval found nothing on topic.
export const SCORE_FLOOR = 0.15;

export async function loadIndex(onProgress?: (msg: string) => void) {
  if (chunks && vectors && meta) return;

  onProgress?.("Loading passages…");
  const [chunksRes, metaRes, vecRes] = await Promise.all([
    fetch("/data/chunks.json"),
    fetch("/data/embeddings_meta.json"),
    fetch("/data/embeddings.bin"),
  ]);
  chunks = (await chunksRes.json()) as Chunk[];
  meta = (await metaRes.json()) as Meta;
  vectors = new Int8Array(await vecRes.arrayBuffer());
}

export async function loadModel(onProgress?: (msg: string) => void) {
  if (extractor) return extractor;
  onProgress?.("Loading the embedding model (first time only, ~25 MB)…");
  env.allowLocalModels = false;
  // pipeline() is overloaded per task; TypeScript cannot represent the union,
  // so narrow it to the one signature this file uses.
  const loadPipeline = pipeline as unknown as (
    task: "feature-extraction",
    model: string,
    options?: Record<string, unknown>,
  ) => Promise<FeatureExtractionPipeline>;

  extractor = await loadPipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2", {
    dtype: "q8",
  });
  return extractor;
}

export async function search(
  question: string,
  topK = 6,
  onProgress?: (msg: string) => void,
): Promise<Hit[]> {
  await loadIndex(onProgress);
  const model = await loadModel(onProgress);
  if (!chunks || !vectors || !meta) throw new Error("index not loaded");

  onProgress?.("Searching 1,125 passages…");
  const output = await model(question, { pooling: "mean", normalize: true });
  const query = Array.from(output.data as Float32Array);

  const { dims, scale, count } = meta;
  const scored: Hit[] = [];
  for (let i = 0; i < count; i++) {
    let dot = 0;
    const offset = i * dims;
    for (let d = 0; d < dims; d++) {
      // Undo int8 quantisation inline: value = stored / 127 * scale
      dot += query[d] * ((vectors[offset + d] / 127) * scale);
    }
    scored.push({ ...chunks[i], score: dot });
  }

  scored.sort((a, b) => b.score - a.score);

  // Keep at most two passages per document so one long PDF cannot crowd out
  // every other source.
  const perFile = new Map<string, number>();
  const kept: Hit[] = [];
  for (const hit of scored) {
    if (hit.score < SCORE_FLOOR) break;
    const seen = perFile.get(hit.file) ?? 0;
    if (seen >= 2) continue;
    perFile.set(hit.file, seen + 1);
    kept.push(hit);
    if (kept.length >= topK) break;
  }
  return kept;
}
