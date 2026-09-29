import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 30;

type Passage = {
  text: string;
  title: string;
  publisher: string;
  date: string;
  url: string;
  file: string;
  score: number;
};

/**
 * Answers a document question from passages retrieved IN THE BROWSER. The
 * client embeds the question locally, scores it against precomputed vectors,
 * and sends only the winning passages here. The model is told to use nothing
 * else, and to say so when the passages do not answer the question.
 */
export async function POST(req: NextRequest) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: "ANTHROPIC_API_KEY is not configured." }, { status: 503 });
  }

  const { question, passages } = (await req.json()) as {
    question: string;
    passages: Passage[];
  };

  if (!question || !Array.isArray(passages) || passages.length === 0) {
    return NextResponse.json(
      { answer: "No relevant passages were retrieved, so the documents cannot answer this." },
      { status: 200 },
    );
  }

  const context = passages
    .map(
      (p, i) =>
        `[${i + 1}] ${p.title} — ${p.publisher}${p.date ? `, ${p.date}` : ""} (${p.file})\n${p.text}`,
    )
    .join("\n\n");

  const client = new Anthropic({ apiKey });
  const message = await client.messages.create({
    model: "claude-sonnet-5",
    max_tokens: 900,
    system:
      "Answer using ONLY the numbered sources supplied. Cite every claim with its bracket number. " +
      "If the sources do not contain the answer, say exactly that and stop — never fall back on outside knowledge, " +
      "and never soften a gap by guessing. Quote sparingly and briefly. Be direct and concise.",
    messages: [
      { role: "user", content: `SOURCES:\n${context}\n\nQUESTION: ${question}` },
    ],
  });

  const block = message.content[0];
  return NextResponse.json({
    answer: block.type === "text" ? block.text : "",
    sources: passages.map((p, i) => ({
      n: i + 1,
      title: p.title,
      publisher: p.publisher,
      date: p.date,
      url: p.url,
      file: p.file,
      score: p.score,
    })),
  });
}
