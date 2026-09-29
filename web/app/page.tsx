import Link from "next/link";

const HEADLINE_STATS = [
  { value: "3,025", label: "Flock cameras mapped", sub: "2,586 LA · 439 King" },
  { value: "2,993", label: "Census tracts analysed", sub: "plus 8,136 block groups" },
  { value: "42", label: "Policy documents indexed", sub: "1,125 searchable passages" },
  { value: "481k", label: "Crime records joined", sub: "LAPD + Seattle PD, 2025→" },
];

const FINDINGS = [
  {
    number: "01",
    title: "The two counties disagree",
    body: "In King County a tract 10 points more Hispanic has about 30% more cameras per road-mile, and the effect survives comparing neighbourhoods inside the same city. In Los Angeles County the same analysis finds 6% fewer. There is no single pattern across both.",
    figure: "/figures/fig4_quartiles.png",
    alt: "Bar chart of camera density by Hispanic quartile, showing opposite directions in the two counties",
  },
  {
    number: "02",
    title: "Home improvement stores stand out",
    body: "Home Depot and Lowe's are about five times more likely than matched big-box retailers — Target, Walmart, Costco, Best Buy, Kohl's — to have a Flock camera they do not own within 150 metres. The effect replicates almost exactly in both counties, which is what makes it the most solid result here.",
    figure: "/figures/fig7_retailer_test.png",
    alt: "Bar chart comparing camera presence at home improvement stores versus control big-box stores",
  },
  {
    number: "03",
    title: "Nearly every city bought in",
    body: "81 of 88 LA cities and 25 of 31 King County cities have mapped cameras, and adopting cities are demographically indistinguishable from the rest. Beverly Hills and Medina are as saturated as San Fernando. The sharper question becomes who can query the network.",
    figure: "/figures/fig6_model_effects.png",
    alt: "Coefficient plot of model effects with 95% confidence intervals",
  },
];

export default function Home() {
  return (
    <div className="space-y-20">
      {/* Hero */}
      <section className="border-b border-rule pb-12">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
          Los Angeles County, CA · King County, WA
        </p>
        <h1 className="mt-5 max-w-4xl font-serif text-[2.6rem] font-semibold leading-[1.1] tracking-[-0.015em] text-ink sm:text-5xl">
          Does Flock camera placement track neighbourhood demographics?
        </h1>
        <p className="mt-6 max-w-measure font-serif text-lg leading-8 text-slate-600">
          3,025 mapped ALPR cameras in two counties, tested against census
          demographics, arterial road density, population, income and reported
          crime — then set against the documentary record of who can search the
          data they collect.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            href="/report"
            className="inline-flex min-h-[44px] items-center rounded-md bg-ink px-5 text-sm font-medium text-paper transition-colors duration-200 hover:bg-accent"
          >
            Read the full report
          </Link>
          <Link
            href="/maps"
            className="inline-flex min-h-[44px] items-center rounded-md border border-rule bg-white px-5 text-sm font-medium text-slate-700 transition-colors duration-200 hover:border-ink hover:text-ink"
          >
            Explore the maps
          </Link>
          <Link
            href="/ask"
            className="inline-flex min-h-[44px] items-center rounded-md border border-rule bg-white px-5 text-sm font-medium text-slate-700 transition-colors duration-200 hover:border-ink hover:text-ink"
          >
            Query the data
          </Link>
        </div>
      </section>

      {/* Key figures */}
      <section>
        <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted">
          The dataset
        </h2>
        <dl className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-rule bg-rule lg:grid-cols-4">
          {HEADLINE_STATS.map((stat) => (
            <div key={stat.label} className="bg-white p-5">
              <dt className="sr-only">{stat.label}</dt>
              <dd>
                <span className="block font-mono text-3xl font-medium text-ink">
                  {stat.value}
                </span>
                <span className="mt-2 block text-sm font-medium text-slate-700">
                  {stat.label}
                </span>
                <span className="mt-0.5 block text-xs text-muted">{stat.sub}</span>
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {/* Findings */}
      <section className="space-y-14">
        <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted">
          What the analysis found
        </h2>
        {FINDINGS.map((finding, i) => (
          <article
            key={finding.title}
            className="grid gap-8 border-t border-rule pt-10 md:grid-cols-2 md:items-center"
          >
            <div className={i % 2 === 1 ? "md:order-2" : undefined}>
              <span className="font-mono text-xs tracking-[0.18em] text-accent">
                {finding.number}
              </span>
              <h3 className="mt-3 font-serif text-2xl font-semibold leading-snug text-ink">
                {finding.title}
              </h3>
              <p className="mt-4 max-w-measure font-serif text-[1.0625rem] leading-[1.75] text-slate-600">
                {finding.body}
              </p>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={finding.figure}
              alt={finding.alt}
              loading="lazy"
              className="rounded-lg border border-rule bg-white"
            />
          </article>
        ))}
      </section>

      {/* Convergence */}
      <section className="rounded-lg border-l-2 border-accent bg-white p-7 ring-1 ring-rule">
        <h2 className="font-serif text-2xl font-semibold text-ink">
          Where the statistics and the documents meet
        </h2>
        <p className="mt-4 max-w-measure font-serif text-[1.0625rem] leading-[1.75] text-slate-700">
          King County&apos;s densest camera deployments are Renton (63 cameras) and
          Auburn (42) — both well above the county&apos;s 11% Hispanic average.
          Working from public records, the University of Washington Center for
          Human Rights found that during 2025 Auburn enabled direct sharing of its
          Flock network with Border Patrol, and Renton&apos;s network had apparent
          &quot;back door&quot; access by Border Patrol it had not authorised. Two
          independent methods, the same two cities.
        </p>
        <p className="mt-4 max-w-measure text-sm leading-6 text-slate-600">
          California has prohibited sharing ALPR data with federal agencies since
          SB 34 took effect in 2016. Washington had no ALPR statute at all until
          SB 6002 was signed in March 2026 — after the sharing described above.
        </p>
      </section>

      {/* Caveats */}
      <section>
        <h2 className="font-mono text-xs uppercase tracking-[0.18em] text-muted">
          How to read all this
        </h2>
        <ul className="mt-5 grid gap-px overflow-hidden rounded-lg border border-rule bg-rule md:grid-cols-3">
          {[
            {
              head: "The camera data is incomplete",
              body: "Locations are crowdsourced through DeFlock and OpenStreetMap. Volunteers map what they notice, and the gaps are probably not random — the binding limitation on every number here.",
            },
            {
              head: "Disparity is not intent",
              body: "Cameras follow arterial roads, commercial corridors and municipal budgets, all of which correlate with demographics for reasons that predate ALPR by decades.",
            },
            {
              head: "Crime data covers cities only",
              body: "LAPD polices 3.8M of LA County's 9.8M residents, Seattle PD 750k of King County's 2.3M. Tracts outside are recorded as missing, never as zero.",
            },
          ].map((item) => (
            <div key={item.head} className="bg-white p-6">
              <h3 className="font-serif text-lg font-semibold text-ink">
                {item.head}
              </h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">{item.body}</p>
            </div>
          ))}
        </ul>
      </section>
    </div>
  );
}
