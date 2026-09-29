import Link from "next/link";

const HEADLINE_STATS = [
  { value: "3,025", label: "Flock cameras mapped", sub: "2,586 LA · 439 King" },
  { value: "2,993", label: "census tracts analysed", sub: "plus 8,136 block groups" },
  { value: "42", label: "policy documents indexed", sub: "1,125 searchable passages" },
  { value: "481k", label: "crime records joined", sub: "LAPD + Seattle PD, 2025→" },
];

const FINDINGS = [
  {
    title: "The two counties disagree",
    body: "In King County a tract 10 points more Hispanic has about 30% more cameras per road-mile, and the effect survives comparing neighbourhoods inside the same city. In LA County the same analysis finds 6% fewer. There is no single pattern across both.",
    figure: "/figures/fig4_quartiles.png",
    alt: "Bar chart of camera density by Hispanic quartile in both counties",
  },
  {
    title: "Home improvement stores stand out",
    body: "Home Depot and Lowe's are about five times more likely than matched big-box retailers — Target, Walmart, Costco, Best Buy, Kohl's — to have a Flock camera they do not own within 150 metres. The effect replicates almost exactly in both counties.",
    figure: "/figures/fig7_retailer_test.png",
    alt: "Bar chart comparing camera presence at home improvement versus control stores",
  },
  {
    title: "Nearly every city bought in",
    body: "81 of 88 LA cities and 25 of 31 King County cities have mapped cameras, and adopting cities are demographically indistinguishable from the rest. Beverly Hills and Medina are as saturated as San Fernando. The sharper question becomes who can query the network.",
    figure: "/figures/fig6_model_effects.png",
    alt: "Coefficient plot of model effects with confidence intervals",
  },
];

export default function Home() {
  return (
    <div className="space-y-14">
      <section className="space-y-5">
        <p className="text-sm font-medium uppercase tracking-wide text-flag">
          Los Angeles County, CA · King County, WA
        </p>
        <h1 className="max-w-3xl text-4xl font-semibold leading-tight text-ink">
          Are Flock license plate readers placed disproportionately in Hispanic
          neighbourhoods?
        </h1>
        <p className="max-w-3xl text-lg leading-8 text-slate-600">
          3,025 mapped Flock ALPR cameras tested against census demographics,
          arterial road density, population, income and reported crime — then set
          against the documentary record of who can search the resulting data.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <Link
            href="/report"
            className="rounded-lg bg-ink px-5 py-2.5 text-sm font-medium text-white hover:bg-ink/90"
          >
            Read the full report
          </Link>
          <Link
            href="/maps"
            className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 hover:border-ink hover:text-ink"
          >
            Explore the maps
          </Link>
          <Link
            href="/ask"
            className="rounded-lg border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 hover:border-ink hover:text-ink"
          >
            Ask a question
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {HEADLINE_STATS.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-slate-200 bg-white p-5"
          >
            <div className="text-3xl font-semibold text-ink">{stat.value}</div>
            <div className="mt-1 text-sm font-medium text-slate-700">
              {stat.label}
            </div>
            <div className="mt-0.5 text-xs text-slate-500">{stat.sub}</div>
          </div>
        ))}
      </section>

      <section className="space-y-10">
        <h2 className="text-2xl font-semibold text-ink">What the analysis found</h2>
        {FINDINGS.map((finding, i) => (
          <article
            key={finding.title}
            className="grid gap-6 border-t border-slate-200 pt-8 md:grid-cols-2 md:items-center"
          >
            <div className={i % 2 === 1 ? "md:order-2" : undefined}>
              <h3 className="text-xl font-semibold text-slate-900">
                {finding.title}
              </h3>
              <p className="mt-3 leading-7 text-slate-600">{finding.body}</p>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={finding.figure}
              alt={finding.alt}
              className="rounded-lg border border-slate-200 bg-white"
            />
          </article>
        ))}
      </section>

      <section className="rounded-xl border border-sand/60 bg-sand/10 p-6">
        <h2 className="text-lg font-semibold text-ink">
          Where the statistics and the documents meet
        </h2>
        <p className="mt-3 leading-7 text-slate-700">
          King County&apos;s densest camera deployments are Renton (63 cameras) and
          Auburn (42) — both well above the county&apos;s 11% Hispanic average.
          Working from public records, the University of Washington Center for
          Human Rights found that during 2025 Auburn enabled direct sharing of its
          Flock network with Border Patrol, and Renton&apos;s network had apparent
          &quot;back door&quot; access by Border Patrol that it had not
          authorised. Two independent methods, the same two cities.
        </p>
        <p className="mt-3 text-sm text-slate-600">
          California has prohibited sharing ALPR data with federal agencies since
          SB 34 took effect in 2016. Washington had no ALPR statute at all until
          SB 6002 was signed in March 2026 — after the sharing described above.
        </p>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-ink">How to read all this</h2>
        <ul className="mt-3 space-y-2 leading-7 text-slate-600">
          <li>
            Camera data is crowdsourced through DeFlock and OpenStreetMap. It is
            incomplete, and the gaps are probably not random — that is the binding
            limitation on every number here.
          </li>
          <li>
            Placement disparity is not intent. Cameras follow arterial roads,
            commercial corridors and municipal budgets, all of which correlate
            with demographics for reasons that predate ALPR by decades.
          </li>
          <li>
            Crime data covers the cities of Los Angeles and Seattle only, not the
            full counties. Tracts outside are recorded as missing, never zero.
          </li>
        </ul>
      </section>
    </div>
  );
}
