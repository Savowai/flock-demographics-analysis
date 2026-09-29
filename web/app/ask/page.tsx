import AskPanel from "@/components/AskPanel";

export const metadata = { title: "Ask · Flock ALPR × Demographics" };

export default function AskPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-ink">Ask the data</h1>
        <p className="max-w-3xl leading-7 text-slate-600">
          Two ways in: query the analysis table in plain English, or search the
          policy documents. Both show their working — the SQL that ran, or the
          passages an answer came from.
        </p>
      </header>
      <AskPanel />
    </div>
  );
}
