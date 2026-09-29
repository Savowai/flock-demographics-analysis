import fs from "node:fs/promises";
import path from "node:path";
import ReportMarkdown from "@/components/ReportMarkdown";

export const metadata = { title: "Report · Flock ALPR × Demographics" };

export default async function ReportPage() {
  const file = path.join(process.cwd(), "public", "data", "report.md");
  const markdown = await fs.readFile(file, "utf8");
  return (
    <article className="prose-report mx-auto max-w-measure">
      <ReportMarkdown markdown={markdown} />
    </article>
  );
}
