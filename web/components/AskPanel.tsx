"use client";

import { useState } from "react";
import { runQuery, type QueryResult } from "@/lib/duck";
import { search, type Hit } from "@/lib/rag";
import { PRESETS, SCHEMA_SUMMARY, type Preset } from "@/lib/presets";

type Mode = "data" | "documents";

const DOC_EXAMPLES = [
  "Can federal immigration agencies access Washington state Flock data?",
  "What does California SB 34 prohibit?",
  "How long may Washington agencies keep license plate data?",
  "Where is ALPR collection banned in Washington?",
  "Has an audit found misuse of a Flock system?",
];

// Everything runs in the visitor's browser, but a typo that drops a table is
// still worth preventing.
const READ_ONLY = /^\s*(select|with)\b/i;
const FORBIDDEN =
  /\b(insert|update|delete|drop|create|alter|attach|detach|copy|install|load|pragma)\b/i;

export default function AskPanel() {
  const [mode, setMode] = useState<Mode>("data");
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sql, setSql] = useState<string>(PRESETS[0].sql);
  const [activeNote, setActiveNote] = useState<string>(PRESETS[0].note);
  const [result, setResult] = useState<QueryResult | null>(null);

  const [question, setQuestion] = useState("");
  const [hits, setHits] = useState<Hit[] | null>(null);
  const [searched, setSearched] = useState(false);

  const busy = status !== null;

  function choosePreset(preset: Preset) {
    setSql(preset.sql);
    setActiveNote(preset.note);
    setResult(null);
    setError(null);
  }

  async function execute() {
    setError(null);
    if (!READ_ONLY.test(sql) || FORBIDDEN.test(sql)) {
      setError("Only SELECT and WITH queries are allowed.");
      return;
    }
    try {
      const queryResult = await runQuery(sql, setStatus);
      setResult(queryResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStatus(null);
    }
  }

  async function runSearch(q: string) {
    const trimmed = q.trim();
    if (!trimmed || busy) return;
    setError(null);
    setHits(null);
    try {
      const found = await search(trimmed, 8, setStatus);
      setHits(found);
      setSearched(true);
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
              setError(null);
            }}
            className={`rounded-md px-4 py-2 text-sm ${
              mode === m ? "bg-ink text-white" : "text-slate-600 hover:text-ink"
            }`}
          >
            {m === "data" ? "Query the data" : "Search the documents"}
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

      {mode === "data" ? (
        <>
          <p className="max-w-3xl text-sm leading-6 text-slate-600">
            The full 11,129-row analysis table runs in your browser through
            DuckDB — nothing is sent to a server. Pick a question or write your
            own SQL.
          </p>

          <div className="flex flex-wrap gap-2">
            {PRESETS.map((preset) => (
              <button
                key={preset.question}
                onClick={() => choosePreset(preset)}
                className={`rounded-full border px-3 py-1.5 text-xs ${
                  sql === preset.sql
                    ? "border-ink bg-ink text-white"
                    : "border-slate-300 bg-white text-slate-600 hover:border-ink hover:text-ink"
                }`}
              >
                {preset.question}
              </button>
            ))}
          </div>

          {activeNote && (
            <p className="max-w-3xl rounded-lg border border-sand/50 bg-sand/10 px-4 py-3 text-sm leading-6 text-slate-700">
              {activeNote}
            </p>
          )}

          <div className="space-y-3">
            <textarea
              value={sql}
              onChange={(e) => {
                setSql(e.target.value);
                setActiveNote("");
              }}
              spellCheck={false}
              rows={12}
              className="w-full rounded-lg border border-slate-300 bg-slate-900 p-4 font-mono text-xs text-slate-100 focus:border-ink focus:outline-none"
            />
            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={execute}
                disabled={busy}
                className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
              >
                {busy ? "Running…" : "Run query"}
              </button>
              <details className="text-sm text-slate-600">
                <summary className="cursor-pointer hover:text-ink">
                  Table columns
                </summary>
                <pre className="mt-2 overflow-x-auto rounded-lg border border-slate-200 bg-white p-4 text-xs leading-5">
                  {SCHEMA_SUMMARY}
                </pre>
              </details>
            </div>
          </div>

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
                        <th
                          key={col}
                          className="px-3 py-2 text-left font-medium text-slate-600"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.slice(0, 200).map((row, i) => (
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
              {result.rows.length > 200 && (
                <p className="text-xs text-slate-500">
                  Showing the first 200 of {result.rows.length} rows.
                </p>
              )}
            </section>
          )}
        </>
      ) : (
        <>
          <p className="max-w-3xl text-sm leading-6 text-slate-600">
            Your question is turned into a vector in your own browser and matched
            against 1,125 passages from 42 policy documents. You get the source
            text itself, with citations — nothing is summarised or paraphrased,
            so nothing can be invented.
          </p>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              runSearch(question);
            }}
            className="flex flex-wrap gap-3"
          >
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. Who can search Washington Flock data?"
              className="min-w-[280px] flex-1 rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:border-ink focus:outline-none"
            />
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white disabled:opacity-50"
            >
              {busy ? "Searching…" : "Search"}
            </button>
          </form>

          <div className="flex flex-wrap gap-2">
            {DOC_EXAMPLES.map((example) => (
              <button
                key={example}
                onClick={() => {
                  setQuestion(example);
                  runSearch(example);
                }}
                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-600 hover:border-ink hover:text-ink"
              >
                {example}
              </button>
            ))}
          </div>

          <p className="text-xs text-slate-500">
            The embedding model (~25 MB) downloads once on your first search, then
            stays cached.
          </p>

          {searched && hits && hits.length === 0 && (
            <div className="rounded-lg border border-slate-200 bg-white p-5 text-slate-700">
              Nothing in the corpus is close enough to answer that. The documents
              cover ALPR law in California and Washington, federal access to
              Flock data, and agency policies in both regions.
            </div>
          )}

          {hits && hits.length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
                {hits.length} matching passages
              </h2>
              {hits.map((hit, i) => (
                <article
                  key={hit.id}
                  className="rounded-lg border border-slate-200 bg-white p-4"
                >
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
                    {hit.date ? ` · ${hit.date}` : ""} · {hit.bucket}
                    {hit.url && (
                      <>
                        {" · "}
                        <a
                          href={hit.url}
                          className="underline hover:text-ink"
                          target="_blank"
                          rel="noreferrer"
                        >
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
        </>
      )}
    </div>
  );
}
