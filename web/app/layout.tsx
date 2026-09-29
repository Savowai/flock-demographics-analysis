import type { Metadata } from "next";
import { Newsreader, Public_Sans, JetBrains_Mono } from "next/font/google";
import SiteHeader from "@/components/SiteHeader";
import "./globals.css";

/**
 * Editorial pairing: Newsreader for long-form reading, Public Sans for UI
 * chrome, JetBrains Mono for figures and labels. Loaded through next/font so
 * they are self-hosted and cause no layout shift.
 */
const newsreader = Newsreader({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-serif",
  display: "swap",
});

const publicSans = Public_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Flock ALPR Cameras and Neighbourhood Demographics",
    template: "%s · Flock ALPR Analysis",
  },
  description:
    "A spatial and statistical analysis of 3,025 Flock license plate readers against census demographics in Los Angeles County and King County, with document search over the policy record.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${newsreader.variable} ${publicSans.variable} ${jetbrainsMono.variable}`}
    >
      <body className="flex min-h-screen flex-col">
        <SiteHeader />

        <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-12">{children}</main>

        <footer className="mt-20 border-t border-rule bg-white">
          <div className="mx-auto max-w-6xl px-6 py-10">
            <div className="grid gap-8 md:grid-cols-[1.5fr_1fr]">
              <div>
                <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted">
                  About the data
                </h2>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">
                  Camera locations come from OpenStreetMap, contributed largely by
                  the DeFlock project and queried 23 September 2026. The data is
                  crowdsourced and certainly incomplete, and the gaps are probably
                  not random. Demographics are ACS 2020–2024 five-year estimates.
                </p>
                <p className="mt-3 max-w-xl text-sm leading-6 text-slate-600">
                  Placement disparity does not establish intent. Read the
                  report&apos;s limitations before citing any figure here.
                </p>
              </div>
              <div className="md:justify-self-end">
                <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted">
                  Source
                </h2>
                <a
                  href="https://github.com/Savowai/flock-demographics-analysis"
                  target="_blank"
                  rel="noreferrer"
                  className="mt-3 inline-flex items-center gap-2 text-sm text-ink underline decoration-rule underline-offset-4 transition-colors hover:decoration-accent"
                >
                  Code and data on GitHub
                </a>
                <p className="mt-3 text-xs leading-5 text-muted">
                  Python · GeoPandas · DuckDB · statsmodels · ChromaDB · Next.js
                </p>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
