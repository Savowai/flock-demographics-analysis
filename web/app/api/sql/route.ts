import Anthropic from "@anthropic-ai/sdk";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 30;

/**
 * Turns a plain-English question into ONE read-only DuckDB query against the
 * `units` table. The query is executed in the browser by DuckDB-WASM, never
 * here, so this route only ever returns text.
 */
const SCHEMA = `
TABLE units  -- one row per census tract or block group per region (11,129 rows)
  GEOID                      VARCHAR  census identifier
  region                     VARCHAR  'la' (Los Angeles County) or 'king' (King County, WA)
  region_label               VARCHAR  human-readable region name
  geo_level                  VARCHAR  'tract' or 'bg' (block group)
  city                       VARCHAR  incorporated city, or '(unincorporated county)'
  pop_total                  DOUBLE   total population
  pop_hispanic               DOUBLE   Hispanic or Latino population
  pct_hispanic               DOUBLE   percent Hispanic/Latino, 0-100
  median_hh_income           DOUBLE   median household income, USD (NULL where suppressed)
  land_sqkm                  DOUBLE   land area
  pop_density_sqkm           DOUBLE   people per square km
  cameras_alpr_all           BIGINT   all ALPR cameras, any vendor
  cameras_flock              BIGINT   all Flock cameras
  cameras_flock_retail       BIGINT   Flock cameras operated by Home Depot/Lowe's (private)
  cameras_flock_nonretail    BIGINT   Flock cameras NOT operated by those chains
  road_miles                 DOUBLE   arterial road-miles (primary/secondary/tertiary)
  cameras_per_road_mile      DOUBLE   cameras_flock / road_miles
  cameras_per_10k_residents  DOUBLE
  crime_data_available       BOOLEAN  false outside the reporting city (LAPD / Seattle PD)
  crime_count                DOUBLE   reported offences since 2025-01-01, NULL where unavailable
  retailer_count             BIGINT   Home Depot + Lowe's stores in the unit
  day_labor_candidate_count  BIGINT   unverified day-labor site candidates
`;

const RULES = `
Rules:
- Return ONE SQL statement for DuckDB. No prose, no markdown fences, no semicolon-separated batches.
- SELECT or WITH only. Never INSERT, UPDATE, DELETE, CREATE, DROP, ATTACH, COPY or INSTALL.
- ALWAYS filter geo_level, defaulting to 'tract', since tracts and block groups both live in this table and would double-count.
- Filter region when the question names one county.
- Rates: prefer SUM(cameras)/SUM(road_miles) over AVG of per-row ratios, which tiny tracts distort.
- crime_count is NULL outside the reporting city. Never treat NULL as zero; filter crime_data_available when using it.
- Use cameras_flock_nonretail when the question is about government placement; store-operated cameras are private.
- Round rates to 3-4 decimals and alias columns readably.
- Cap open-ended row output with LIMIT 100.
`;

const FORBIDDEN =
  /\b(insert|update|delete|drop|create|alter|attach|detach|copy|install|load|pragma|export|import)\b/i;

export async function POST(req: NextRequest) {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return NextResponse.json(
      { error: "ANTHROPIC_API_KEY is not configured on the server." },
      { status: 503 },
    );
  }

  const { question } = await req.json();
  if (typeof question !== "string" || question.trim().length < 3) {
    return NextResponse.json({ error: "Ask a question." }, { status: 400 });
  }

  const client = new Anthropic({ apiKey });
  const message = await client.messages.create({
    model: "claude-sonnet-5",
    max_tokens: 700,
    system: `You write DuckDB SQL for a public dataset about ALPR camera placement.\n${SCHEMA}\n${RULES}`,
    messages: [{ role: "user", content: question }],
  });

  const block = message.content[0];
  let sql = block.type === "text" ? block.text.trim() : "";
  sql = sql.replace(/^```(?:sql)?/i, "").replace(/```$/, "").trim();

  if (FORBIDDEN.test(sql) || !/^\s*(select|with)\b/i.test(sql)) {
    return NextResponse.json(
      { error: "Generated query was not read-only; refusing to run it.", sql },
      { status: 422 },
    );
  }

  return NextResponse.json({ sql });
}
