import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 30;

/**
 * Explains a result set that has ALREADY been computed in the browser.
 * The model never produces numbers of its own: it receives the executed SQL
 * and the actual rows, and describes them.
 */
export async function POST(req: NextRequest) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: "ANTHROPIC_API_KEY is not configured." }, { status: 503 });
  }

  const { question, sql, rows } = await req.json();
  if (!Array.isArray(rows)) {
    return NextResponse.json({ error: "rows must be an array" }, { status: 400 });
  }

  const sample = rows.slice(0, 40);
  const client = new Anthropic({ apiKey });
  const message = await client.messages.create({
    model: "claude-sonnet-5",
    max_tokens: 600,
    system:
      "You explain query results from a study of Flock ALPR camera placement versus census demographics in LA County and King County, WA. " +
      "Describe ONLY the rows provided; never invent or recall figures. Two sentences to a short paragraph, plain English, no preamble. " +
      "Where relevant, remind the reader that camera data is crowdsourced and incomplete, that crime data covers only the cities of LA and Seattle, " +
      "and that a placement difference is not evidence of intent. If the rows are empty, say the query returned nothing and suggest why.",
    messages: [
      {
        role: "user",
        content: `Question: ${question}\n\nSQL executed:\n${sql}\n\nRows returned (${rows.length} total, first ${sample.length} shown):\n${JSON.stringify(sample, null, 1)}`,
      },
    ],
  });

  const block = message.content[0];
  return NextResponse.json({ explanation: block.type === "text" ? block.text : "" });
}
