"use client";

import * as duckdb from "@duckdb/duckdb-wasm";

/**
 * DuckDB running in the browser over units.parquet (0.8 MB). Queries never
 * reach a server, so the dataset can be explored freely and a bad query costs
 * nothing but the user's own tab.
 */

let db: duckdb.AsyncDuckDB | null = null;
let connection: duckdb.AsyncDuckDBConnection | null = null;

export async function getConnection(onProgress?: (msg: string) => void) {
  if (connection) return connection;

  onProgress?.("Starting DuckDB in your browser…");
  const bundles = duckdb.getJsDelivrBundles();
  const bundle = await duckdb.selectBundle(bundles);

  const workerUrl = URL.createObjectURL(
    new Blob([`importScripts("${bundle.mainWorker!}");`], {
      type: "text/javascript",
    }),
  );
  const worker = new Worker(workerUrl);
  const logger = new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING);
  db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule, bundle.pthreadWorker);
  URL.revokeObjectURL(workerUrl);

  onProgress?.("Loading the analysis table…");
  const res = await fetch("/data/units.parquet");
  const buffer = new Uint8Array(await res.arrayBuffer());
  await db.registerFileBuffer("units.parquet", buffer);

  connection = await db.connect();
  await connection.query(
    `CREATE OR REPLACE VIEW units AS SELECT * FROM read_parquet('units.parquet')`,
  );
  return connection;
}

export type QueryResult = {
  columns: string[];
  rows: Record<string, unknown>[];
};

export async function runQuery(
  sql: string,
  onProgress?: (msg: string) => void,
): Promise<QueryResult> {
  const conn = await getConnection(onProgress);
  onProgress?.("Running the query…");
  const table = await conn.query(sql);
  const rows = table.toArray().map((row) => {
    const obj = row.toJSON() as Record<string, unknown>;
    // Arrow returns BigInt for integer columns; JSON cannot serialise those.
    for (const [key, value] of Object.entries(obj)) {
      if (typeof value === "bigint") obj[key] = Number(value);
    }
    return obj;
  });
  return { columns: table.schema.fields.map((f) => f.name), rows };
}
