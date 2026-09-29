import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * The report is authored as a file in docs/ and copied into public/data by
 * src/analysis/export_web.py, so the site and the repository never drift.
 * Figure paths in the markdown are relative to docs/, and are rewritten here.
 */
export default function ReportMarkdown({ markdown }: { markdown: string }) {
  const withWebPaths = markdown.replaceAll("../outputs/figures/", "/figures/");
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        table: ({ children }) => (
          <div className="overflow-x-auto">
            <table>{children}</table>
          </div>
        ),
      }}
    >
      {withWebPaths}
    </Markdown>
  );
}
