"use client";

import { useState } from "react";
import { runQuery, type QueryResult } from "@/lib/duck";
import { search, type Hit } from "@/lib/rag";

type Mode = "data" | "documents";

const EXAMPLES: Record<Mode, string[]> = {
  data: [
    "Which 10 tracts have the most Flock cameras per road-mile in King County?",
    "Compare average camera density between tracts above and below 50% Hispanic in LA County",
    "Which cities have the most cameras per 10,000 residents?",
    "How many tracts have cameras but no crime data?",
  ],
  documents: [
    "Can federal immigration agencies access Washington state Flock data?",
    "What does California SB 34 prohibit?",
    "How long may Washington agencies keep license plate data?",
    "Where is ALPR collection banned in Washington?",
  ],
};

export default function AskPanel() {
  const [mode, setMode] = useState<Mode>("data");
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sql, setSql] = useState<string | null>(null);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);

  const [answer, setAnswer] = useState<string | null>(null);
  const [hits, setHits] = useState<Hit[] | null>(null);

  const busy = status !== null;

  function reset() {
    setError(null);
    setSql(null);
    setResult(null);
    setExplanation(null);
    setAnswer(null);
    setHits(null);
  }

  async function askData(q: string) {
    setStatus("Asking Claude to write the SQL…");
    const res = await fetch("/api/sql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q }),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error ?? "Could not generate SQL");
    setSql(payload.sql);

    const queryResult = await runQuery(payload.sql, setStatus);
    setResult(queryResult);

    setStatus("Explaining the result…");
    const explainRes = await fetch("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, sql: payload.sql, rows: queryResult.rows }),
    });
    if (explainRes.ok) setExplanation((await explainRes.json()).explanation);
  }

  async function askDocuments(q: string) {
    const found = await search(q, 6, setStatus);
    setHits(found);
    if (found.length === 0) {
      setAnswer(
        "Nothing in the 42-document corpus is close enough to this question to answer it. Try rephrasing, or ask about ALPR law, federal data access, or a specific agency's policy.",
      );
      return;
    }
    setStatus("Writing an answer from the retrieved passages…");
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: q, passages: found }),
    });
    const payload = await res.json();
    if (!res.ok) throw new Error(payload.error ?? "Could not answer");
    setAnswer(payload.answer);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    reset();
    try {
      if (mode === "data") await askData(q);
      else await askDocuments(q);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStatus(null);
    }
  }

  return (
    <div className="space-y-6">
      <div className="inline-flex rounded-lg border border-slate-300 bg-white p-1">
        {(["data", "documents"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => {
              setMode(m);
              reset();
            }}
            className={`rounded-md px-4 py-2 text-sm ${
              mode === m ? "bg-ink text-white" : "text-slate-600 hover:text-ink"
            }`}
          >
            {m === "data" ? "Data questions" : "Document questions"}
          </button>
        ))}
      </div>

      <p className="max-w-3xl text-sm leading-6 text-slate-600">
        {mode === "data" ? (
          <>
            Claude converts your question into a read-only DuckDB query, shows you
            the SQL, and runs it <strong>in your browser</strong> against the
            11,129-row analysis table. Numbers always come from the query, never
            from the model.
          </>
        ) : (
          <>
            Your question is embedded locally, matched against 1,125 passages from
            42 policy documents, and answered from the winning passages only. If
            the corpus does not cover it, the answer says so.
          </>
        )}
      </p>

      <form onSubmit={submit} className="flex flex-wrap gap-3">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={
            mode === "data"
              ? "e.g. Which cities have the most cameras per resident?"
              : "e.g. Who can search Washington Flock data?"
          }
          className="min-w-[280px] flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-ink focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? "Working…" : "Ask"}
        </button>
      </form>

      <div className="flex flex-wrap gap-2">
        {EXAMPLES[mode].map((example) => (
          <button
            key={example}
            onClick={() => setQuestion(example)}
            className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-ink hover:text-ink"
          >
            {example}
          </button>
        ))}
      </div>

      {status && (
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
          {status}
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-flag/30 bg-flag/5 px-4 py-3 text-sm text-flag">
          {error}
        </div>
      )}

      {sql && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            SQL that ran
          </h2>
          <pre className="overflow-x-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100">
            {sql}
          </pre>
        </section>
      )}

      {result && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            {result.rows.length} row{result.rows.length === 1 ? "" : "s"}
          </h2>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  {result.columns.map((col) => (
                    <th key={col} className="px-3 py-2 text-left font-medium text-slate-600">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.slice(0, 100).map((row, i) => (
                  <tr key={i} className="border-t border-slate-100">
                    {result.columns.map((col) => (
                      <td key={col} className="px-3 py-1.5 text-slate-700">
                        {row[col] === null || row[col] === undefined
                          ? "—"
                          : typeof row[col] === "number"
                            ? Number(row[col]).toLocaleString(undefined, {
                                maximumFractionDigits: 4,
                              })
                            : String(row[col])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {explanation && (
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            What it means
          </h2>
          <p className="leading-7 text-slate-700">{explanation}</p>
        </section>
      )}

      {answer && (
        <section className="rounded-lg border border-slate-200 bg-white p-5">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Answer
          </h2>
          <div className="whitespace-pre-wrap leading-7 text-slate-700">{answer}</div>
        </section>
      )}

      {hits && hits.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Passages used
          </h2>
          {hits.map((hit, i) => (
            <article key={hit.id} className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-medium text-ink">
                  [{i + 1}] {hit.title}
                </h3>
                <span className="text-xs text-slate-500">
                  relevance {hit.score.toFixed(2)}
                </span>
              </div>
              <div className="mt-0.5 text-xs text-slate-500">
                {hit.publisher}
                {hit.date ? ` · ${hit.date}` : ""} · {hit.file}
                {hit.url && (
                  <>
                    {" · "}
                    <a href={hit.url} className="underline hover:text-ink" target="_blank" rel="noreferrer">
                      source
                    </a>
                  </>
                )}
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-600">{hit.text}</p>
            </article>
          ))}
        </section>
      )}
    </div>
  );
}
