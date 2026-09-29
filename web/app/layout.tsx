import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Flock ALPR Cameras and Neighbourhood Demographics",
  description:
    "A spatial and statistical analysis of Flock license plate readers against census demographics in Los Angeles County and King County, with document search over the policy record.",
};

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/maps", label: "Maps" },
  { href: "/report", label: "Report" },
  { href: "/ask", label: "Explore" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-2 px-5 py-4">
            <Link href="/" className="font-semibold text-ink">
              Flock ALPR × Demographics
            </Link>
            <nav className="flex gap-5 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="text-slate-600 transition-colors hover:text-flag"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
            <a
              href="https://github.com/Savowai/flock-demographics-analysis"
              className="ml-auto text-sm text-slate-500 hover:text-ink"
              target="_blank"
              rel="noreferrer"
            >
              Source
            </a>
          </div>
        </header>

        <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>

        <footer className="mt-16 border-t border-slate-200 bg-white">
          <div className="mx-auto max-w-6xl px-5 py-8 text-sm text-slate-500">
            <p>
              Camera locations come from OpenStreetMap, contributed largely by the
              DeFlock project, queried 23 September 2026. The data is crowdsourced
              and certainly incomplete; gaps are probably not random. Demographics
              are ACS 2020–2024 5-year estimates.
            </p>
            <p className="mt-3">
              Placement disparity does not establish intent. See the report&apos;s
              limitations section before citing any figure here.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
