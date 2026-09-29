"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/maps", label: "Maps" },
  { href: "/report", label: "Report" },
  { href: "/ask", label: "Explore" },
];

export default function SiteHeader() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <header className="sticky top-0 z-50 border-b border-rule bg-paper/90 backdrop-blur supports-[backdrop-filter]:bg-paper/75">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3.5">
        <Link
          href="/"
          className="group flex min-w-0 flex-col leading-tight focus-visible:outline-none"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted">
            Surveillance &amp; demographics
          </span>
          <span className="truncate font-serif text-lg font-semibold text-ink transition-colors group-hover:text-accent">
            Flock ALPR Analysis
          </span>
        </Link>

        <nav className="ml-auto hidden items-center gap-1 md:flex">
          {NAV.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`relative rounded-md px-3 py-2 text-sm transition-colors duration-200 ${
                  active ? "text-ink" : "text-slate-500 hover:text-ink"
                }`}
              >
                {item.label}
                <span
                  className={`absolute inset-x-3 -bottom-px h-0.5 rounded-full transition-all duration-200 ${
                    active ? "bg-accent opacity-100" : "bg-accent opacity-0"
                  }`}
                />
              </Link>
            );
          })}
          <a
            href="https://github.com/Savowai/flock-demographics-analysis"
            target="_blank"
            rel="noreferrer"
            className="ml-2 inline-flex items-center gap-1.5 rounded-md border border-rule px-3 py-2 text-sm text-slate-600 transition-colors duration-200 hover:border-ink hover:text-ink"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 fill-current">
              <path d="M12 .5a12 12 0 0 0-3.79 23.4c.6.1.82-.26.82-.58v-2.2c-3.34.72-4.04-1.6-4.04-1.6-.55-1.4-1.34-1.77-1.34-1.77-1.1-.75.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.84 2.81 1.31 3.5 1 .1-.78.42-1.31.76-1.61-2.67-.3-5.47-1.34-5.47-5.96 0-1.32.47-2.4 1.24-3.24-.13-.3-.54-1.53.12-3.18 0 0 1-.32 3.3 1.23a11.4 11.4 0 0 1 6 0c2.3-1.55 3.3-1.23 3.3-1.23.66 1.65.25 2.88.12 3.18.77.84 1.23 1.92 1.23 3.24 0 4.63-2.8 5.65-5.48 5.95.43.37.81 1.1.81 2.22v3.29c0 .32.21.7.82.58A12 12 0 0 0 12 .5Z" />
            </svg>
            GitHub
          </a>
        </nav>

        <button
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Toggle navigation"
          className="ml-auto flex h-11 w-11 items-center justify-center rounded-md border border-rule text-slate-600 transition-colors hover:border-ink hover:text-ink md:hidden"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" className="h-5 w-5 stroke-current" fill="none" strokeWidth="1.8" strokeLinecap="round">
            {open ? (
              <>
                <path d="M6 6l12 12" />
                <path d="M18 6L6 18" />
              </>
            ) : (
              <>
                <path d="M4 7h16" />
                <path d="M4 12h16" />
                <path d="M4 17h16" />
              </>
            )}
          </svg>
        </button>
      </div>

      {open && (
        <nav className="border-t border-rule bg-paper px-6 py-2 md:hidden">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setOpen(false)}
              aria-current={isActive(item.href) ? "page" : undefined}
              className={`flex min-h-[44px] items-center border-b border-rule/60 text-sm last:border-0 ${
                isActive(item.href) ? "text-ink" : "text-slate-500"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
