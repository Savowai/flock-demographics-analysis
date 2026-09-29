import AskPanel from "@/components/AskPanel";

export const metadata = { title: "Explore · Flock ALPR × Demographics" };

export default function AskPage() {
  return (
    <div className="space-y-6">
      <header className="border-b border-rule pb-8">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">Tools</p>
        <h1 className="mt-4 font-serif text-4xl font-semibold leading-tight tracking-[-0.015em] text-ink">Explore the evidence</h1>
        <p className="mt-4 max-w-measure font-serif text-lg leading-8 text-slate-600">
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
