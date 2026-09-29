import AskPanel from "@/components/AskPanel";

export const metadata = { title: "Explore · Flock ALPR × Demographics" };

export default function AskPage() {
  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold text-ink">Explore the evidence</h1>
        <p className="max-w-3xl leading-7 text-slate-600">
          Query the analysis table, or search the policy documents. Both run
          entirely in your browser: no server, no account, no API key. You see
          the SQL that produced every number and the source text behind every
          citation.
        </p>
      </header>
      <AskPanel />
    </div>
  );
}
