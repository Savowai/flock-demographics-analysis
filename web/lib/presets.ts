/**
 * Preset queries for the data explorer.
 *
 * These replace plain-English question parsing: no model, no API key, no cost,
 * and every query is one somebody can read and check. The SQL editor below
 * them lets anyone write their own.
 *
 * Note the recurring guards: filter geo_level (tracts and block groups share
 * the table), prefer SUM/SUM over AVG of ratios, and never treat a NULL
 * crime_count as zero.
 */

export type Preset = {
  question: string;
  note: string;
  sql: string;
};

export const PRESETS: Preset[] = [
  {
    question: "How does camera density compare across Hispanic quartiles?",
    note: "The headline comparison. Rates use total cameras over total road-miles, not an average of per-tract ratios, which tiny tracts distort.",
    sql: `WITH q AS (
  SELECT region_label, pct_hispanic, cameras_flock, road_miles, pop_total,
         ntile(4) OVER (PARTITION BY region ORDER BY pct_hispanic) AS quartile
  FROM units
  WHERE geo_level = 'tract' AND pct_hispanic IS NOT NULL AND road_miles > 0
)
SELECT region_label,
       quartile,
       count(*)                                        AS tracts,
       round(min(pct_hispanic), 1) || '-' ||
         round(max(pct_hispanic), 1) || '%'            AS hispanic_range,
       sum(cameras_flock)                              AS flock_cameras,
       round(sum(cameras_flock) / sum(road_miles), 4)  AS cameras_per_road_mile,
       round(10000 * sum(cameras_flock) / sum(pop_total), 2) AS per_10k_residents
FROM q
GROUP BY region_label, quartile
ORDER BY region_label, quartile`,
  },
  {
    question: "Which tracts have the most cameras per road-mile?",
    note: "Excludes store-operated cameras, which are private placements rather than government ones.",
    sql: `SELECT region_label, city, GEOID,
       round(pct_hispanic, 1)                 AS pct_hispanic,
       cameras_flock_nonretail                AS cameras,
       round(road_miles, 2)                   AS road_miles,
       round(cameras_flock_nonretail / road_miles, 3) AS per_road_mile,
       pop_total
FROM units
WHERE geo_level = 'tract' AND road_miles > 0.5 AND cameras_flock_nonretail > 0
ORDER BY per_road_mile DESC
LIMIT 25`,
  },
  {
    question: "Which cities have the most cameras?",
    note: "One row per city. A camera inside a city was not necessarily bought by that city — sheriffs, transit agencies and businesses deploy them too.",
    sql: `SELECT region_label, city,
       count(*)                                          AS tracts,
       sum(pop_total)                                    AS population,
       round(100 * sum(pop_hispanic) / sum(pop_total), 1) AS pct_hispanic,
       sum(cameras_flock_nonretail)                      AS cameras,
       round(sum(road_miles), 1)                         AS road_miles,
       round(sum(cameras_flock_nonretail) / sum(road_miles), 4) AS per_road_mile
FROM units
WHERE geo_level = 'tract' AND city <> '(unincorporated county)'
GROUP BY region_label, city
HAVING sum(road_miles) > 0
ORDER BY cameras DESC
LIMIT 30`,
  },
  {
    question: "Do heavily Hispanic tracts have more cameras than the rest?",
    note: "A simple split at 50%. Unadjusted: no controls for roads, population or crime — the regressions in the report do that.",
    sql: `SELECT region_label,
       CASE WHEN pct_hispanic >= 50 THEN '50% or more Hispanic'
            ELSE 'under 50% Hispanic' END                AS group_name,
       count(*)                                          AS tracts,
       sum(cameras_flock_nonretail)                      AS cameras,
       round(sum(cameras_flock_nonretail) / sum(road_miles), 4) AS per_road_mile,
       round(10000 * sum(cameras_flock_nonretail) / sum(pop_total), 2) AS per_10k_residents
FROM units
WHERE geo_level = 'tract' AND pct_hispanic IS NOT NULL AND road_miles > 0
GROUP BY region_label, group_name
ORDER BY region_label, group_name`,
  },
  {
    question: "Where are cameras high but reported crime low?",
    note: "Only tracts inside the City of LA or City of Seattle have crime data at all; everything else is excluded here rather than counted as zero crime.",
    sql: `SELECT region_label, city, GEOID,
       round(pct_hispanic, 1)                        AS pct_hispanic,
       cameras_flock_nonretail                       AS cameras,
       round(cameras_flock_nonretail / road_miles, 3) AS per_road_mile,
       crime_count,
       round(1000 * crime_count / pop_total, 1)      AS crime_per_1k
FROM units
WHERE geo_level = 'tract'
  AND crime_data_available
  AND road_miles > 0.5
  AND pop_total > 500
  AND cameras_flock_nonretail >= 3
ORDER BY crime_per_1k ASC
LIMIT 25`,
  },
  {
    question: "How much of each county has no crime data?",
    note: "LAPD polices the City of LA, Seattle PD the City of Seattle. The rest of both counties is policed by agencies that publish separately or not at all.",
    sql: `SELECT region_label,
       crime_data_available,
       count(*)                       AS tracts,
       sum(pop_total)                 AS population,
       sum(cameras_flock_nonretail)   AS cameras
FROM units
WHERE geo_level = 'tract'
GROUP BY region_label, crime_data_available
ORDER BY region_label, crime_data_available DESC`,
  },
  {
    question: "How many cameras are operated by Home Depot and Lowe's?",
    note: "Store-operated cameras are private placements. The models exclude them; the retailer test asks whether OTHER people's cameras cluster near these stores.",
    sql: `SELECT region_label,
       sum(cameras_alpr_all)        AS all_alpr,
       sum(cameras_flock)           AS all_flock,
       sum(cameras_flock_retail)    AS store_operated,
       sum(cameras_flock_nonretail) AS not_store_operated,
       round(100.0 * sum(cameras_flock_retail) / sum(cameras_flock), 1) AS pct_store_operated
FROM units
WHERE geo_level = 'tract'
GROUP BY region_label`,
  },
  {
    question: "Does the pattern hold at block-group level?",
    note: "Block groups are smaller than tracts. If a finding only appears at one geography, it is fragile.",
    sql: `WITH q AS (
  SELECT region_label, geo_level, pct_hispanic, cameras_flock_nonretail, road_miles,
         ntile(4) OVER (PARTITION BY region, geo_level ORDER BY pct_hispanic) AS quartile
  FROM units
  WHERE pct_hispanic IS NOT NULL AND road_miles > 0
)
SELECT region_label, geo_level, quartile,
       count(*)                                                     AS units,
       round(sum(cameras_flock_nonretail) / sum(road_miles), 4)     AS per_road_mile
FROM q
WHERE quartile IN (1, 4)
GROUP BY region_label, geo_level, quartile
ORDER BY region_label, geo_level, quartile`,
  },
];

export const SCHEMA_SUMMARY = `units — one row per tract or block group, per region (11,129 rows)

  GEOID, region ('la' | 'king'), region_label, geo_level ('tract' | 'bg'), city
  pop_total, pop_hispanic, pct_hispanic (0-100), median_hh_income
  land_sqkm, pop_density_sqkm
  cameras_alpr_all, cameras_flock, cameras_flock_retail, cameras_flock_nonretail
  road_miles (arterial), cameras_per_road_mile, cameras_per_10k_residents
  crime_data_available (false = no data, NOT zero crime), crime_count
  retailer_count, day_labor_candidate_count`;
