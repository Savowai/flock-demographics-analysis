"""Phase 6.1: download the document corpus for the RAG layer.

Sources were found with web search but are downloaded here in full with
requests - search summaries are not document text and are not used.

Priority is primary sources: statutes, bill text, agency policies, audits,
public-records-based reports and city records, with investigative reporting
included where it is the only account of an event.

Anything that fails (paywall, login, blocked) is written to
docs/manual_downloads.md rather than silently skipped.

Careful: there is a Pasadena, California and a Pasadena, Texas, both with
Flock controversies in 2026. Only California sources belong in this corpus.

Run: .venv/bin/python src/collect/rag_documents.py
Writes: rag/documents/*.txt, rag/documents/sources.csv
"""

from __future__ import annotations

import csv
import re
import sys
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from common import PROJECT_ROOT, session, stamp

DOCS = PROJECT_ROOT / "rag" / "documents"
MIN_CHARS = 400  # shorter than this is a nav page or an error page, not a document


@dataclass(frozen=True)
class Source:
    slug: str
    title: str
    publisher: str
    date: str
    url: str
    bucket: str


SOURCES = [
    # --- Federal / immigration access to Flock data ---
    Source("uwchr_leaving_door_wide_open",
           "Leaving the Door Wide Open: Flock Surveillance Systems Expose Washington Data to Immigration Enforcement",
           "UW Center for Human Rights", "2025-10-21",
           "https://jsis.washington.edu/humanrights/2025/10/21/leaving-the-door-wide-open/",
           "federal access"),
    Source("flock_does_flock_share_data_with_ice",
           "Does Flock Share Data With ICE? Here's Flock's Answer",
           "Flock Safety", "2025",
           "https://www.flocksafety.com/blog/does-flock-share-data-with-ice",
           "vendor statement"),
    Source("immpolicy_ice_alpr_tracking",
           "Reported: ICE using ALPR cameras for immigration enforcement via state/local police",
           "Immigration Policy Tracking Project", "2025",
           "https://immpolicytracking.org/policies/reported-ice-accessing-flock-automated-license-plate-reader-cameras-via-local-law-enforcement/",
           "federal access"),
    Source("urbanist_wa_cities_question_lprs",
           "Washington Cities Question Use of License Plate Readers Citing Federal Overreach",
           "The Urbanist", "2025-11-13",
           "https://www.theurbanist.org/2025/11/13/washington-cities-question-use-of-license-plate-readers/",
           "reporting"),
    Source("kiro7_legal_concerns_federal_sharing",
           "Legal concerns raised as WA license plate data is shared with federal agencies",
           "KIRO 7 News Seattle", "2025",
           "https://www.kiro7.com/news/local/legal-concerns-raised-wa-license-plate-data-is-shared-with-federal-agencies/FS3TOCDRWFC2FHQSP3D7WE6CQE/",
           "reporting"),
    Source("mynorthwest_federal_immigration_access",
           "Federal immigration agencies access WA license plate data",
           "MyNorthwest", "2025",
           "https://mynorthwest.com/local/flock-safety-immigration-data/4145569",
           "reporting"),
    Source("opb_immigration_agencies_wa_plate_data",
           "Immigration agencies have access to license plate data in Washington state",
           "OPB", "2025-12-04",
           "https://www.opb.org/article/2025/12/04/think-out-loud-washington-immigration-agencies-license-plate/",
           "reporting"),
    Source("dailyuw_uwchr_report_coverage",
           "UWCHR releases report on surveillance data in Washington state, used by immigration enforcement",
           "The Daily (UW)", "2025-11-05",
           "https://www.dailyuw.com/article/uwchr-releases-report-on-surveillance-data-in-washington-state-used-by-immigration-enforcement-20251105",
           "reporting"),
    Source("stateofsurveillance_school_cameras_ice",
           "School Cameras Feeding Data to ICE: An Investigation",
           "State of Surveillance", "2026",
           "https://stateofsurveillance.org/news/school-cameras-ice-flock-safety-immigration-enforcement-2026/",
           "reporting"),

    # --- California law ---
    Source("ca_sb34_enrolled_text",
           "SB 34 (2015) Automated license plate recognition systems: use of data - enrolled text",
           "California Legislature", "2015-09-08",
           "https://leginfo.public.ca.gov/pub/15-16/bill/sen/sb_0001-0050/sb_34_bill_20150908_enrolled.pdf",
           "state law - CA"),
    Source("ca_civil_code_1798_90_5",
           "California Civil Code Section 1798.90.5 (ALPR definitions and duties)",
           "California Civil Code via onecle", "2025",
           "https://law.onecle.com/california/civil/1798.90.5.html",
           "state law - CA"),
    Source("ca_ag_bulletin_2023_dle_06",
           "Information Bulletin 2023-DLE-06: Guidance on SB 34 and ALPR data",
           "California Attorney General", "2023-10-27",
           "https://oag.ca.gov/system/files/media/2023-dle-06.pdf",
           "state law - CA"),
    Source("ca_ag_press_release_alpr_guidance",
           "Attorney General Bonta advises California law enforcement on legal uses of ALPR data",
           "California Attorney General", "2023-10-30",
           "https://oag.ca.gov/news/press-releases/attorney-general-bonta-advises-california-law-enforcement-legal-uses-and",
           "state law - CA"),
    Source("eff_ca_doj_out_of_state_sharing_unlawful",
           "California DOJ Declares Out-of-State Sharing of License Plate Data Unlawful",
           "Electronic Frontier Foundation", "2023-10",
           "https://www.eff.org/deeplinks/2023/10/victory-california-department-justice-declares-out-state-sharing-license-plate",
           "advocacy analysis"),
    Source("aclu_norcal_letter_ag_bonta_sb34",
           "Letter to Attorney General Bonta re: SB 34 compliance",
           "ACLU of Northern California", "2024-01-31",
           "https://www.aclunorcal.org/sites/default/files/2024-01-31_letter_to_ag_bonta_re_sb_34_final.pdf",
           "advocacy analysis"),
    Source("aclu_ca_agencies_sharing_anti_abortion_states",
           "Dozens of Police Agencies in California Are Still Sharing Driver Locations with Anti-Abortion States",
           "ACLU", "2024",
           "https://www.aclu.org/news/privacy-technology/dozens-of-police-agencies-in-california-are-still-sharing-driver-locations-with-anti-abortion-states-were-fighting-back",
           "advocacy analysis"),

    # --- Washington law ---
    Source("wa_sb6002_passed_legislature",
           "SB 6002 (Driver Privacy Act) - as passed legislature",
           "Washington State Legislature", "2026-03-30",
           "https://lawfilesext.leg.wa.gov/biennium/2025-26/Htm/Bills/Senate%20Passed%20Legislature/6002-S.PL.htm",
           "state law - WA"),
    Source("wa_hb2332_text",
           "HB 2332 - ALPR related legislation text",
           "Washington State Legislature", "2026",
           "https://lawfilesext.leg.wa.gov/biennium/2025-26/Htm/Bills/House%20Bills/2332.htm",
           "state law - WA"),
    Source("wa_rcw_10_130_030",
           "RCW 10.130.030",
           "Washington State Legislature", "2026",
           "https://app.leg.wa.gov/RCW/default.aspx?cite=10.130.030",
           "state law - WA"),
    Source("mrsc_restrictions_flock_cameras",
           "What to Know About the New Restrictions on Flock and Similar Camera Systems",
           "Municipal Research and Services Center (MRSC)", "2026-04",
           "https://mrsc.org/stay-informed/mrsc-insight/april-2026/restrictions-flock-cameras",
           "state law - WA"),
    Source("mrsc_closing_the_blinds_pra_exemption",
           "Closing the Blinds: New Public Records Act Exemption Limits Disclosure of ALPR Data",
           "Municipal Research and Services Center (MRSC)", "2026-04",
           "https://mrsc.org/stay-informed/mrsc-insight/april-2026/license-plate-reader-data",
           "state law - WA"),
    Source("aclu_wa_first_regulations_lpr",
           "Washington enacts first regulations on license plate readers",
           "ACLU of Washington", "2026",
           "https://www.aclu-wa.org/news/washington-enacts-first-regulations-on-license-plate-readers/",
           "advocacy analysis"),
    Source("cascadia_police_adjust_surveillance_law",
           "Local police adjust to Washington's new mass surveillance law",
           "Cascadia Daily News", "2026-04-26",
           "https://www.cascadiadaily.com/2026/apr/26/local-police-adjust-to-washingtons-new-mass-surveillance-law/",
           "reporting"),
    Source("axios_wa_alpr_retention_21_days",
           "Washington moves to limit license plate data retention",
           "Axios Seattle", "2026-02-19",
           "https://www.axios.com/local/seattle/2026/02/19/washington-alpr-bill-sb6002-license-plate-reader-data-retention-21-days-privacy",
           "reporting"),

    # --- Seattle / King County local policy ---
    Source("seattle_ord_127044_alpr_sir",
           "Seattle Ordinance 127044 - SPD Fleet-Wide ALPR Surveillance Impact Report",
           "Seattle City Clerk", "2024",
           "https://clerk.seattle.gov/~archives/Ordinances/Ord_127044.pdf",
           "local policy - King"),
    Source("seattle_2023_sir_fleetwide_alpr",
           "2023 Surveillance Impact Report: Fleet-Wide ALPR (with change markup)",
           "City of Seattle", "2023",
           "https://www.seattle.gov/documents/Departments/Tech/Surveillance/Material%20Update%20Docs/ALPR/2023%20SIR%20Fleet-Wide%20ALPR%20with%20Change%20Markup.pdf",
           "local policy - King"),
    Source("seattle_oig_alpr_usage_review",
           "Surveillance Technology Usage Review: Automated License Plate Reader, Patrol (2021 and 2022)",
           "Seattle Office of Inspector General", "2023",
           "https://www.seattle.gov/documents/departments/oig/audits/surveillancetechnologyusagereview-automatedlicenseplatereader-patrol(2021and2022).pdf",
           "audit"),
    Source("seattle_2024_equity_impact_assessment",
           "2024 Surveillance Technology Community Equity Impact Assessment and Policy Guidance Report",
           "Seattle Chief Technology Officer", "2024",
           "https://www.seattle.gov/documents/Departments/Tech/Surveillance/Equity%20Reports/2024%20CTO%20Surveillance%20Technology%20Community%20Equity%20Impact%20Assessment%20and%20Policy%20Guidance%20Report.pdf",
           "local policy - King"),
    Source("seattle_master_list_surveillance_tech",
           "City of Seattle Master List of Surveillance Technologies",
           "Seattle City Clerk", "2017-11-30",
           "https://clerk.seattle.gov/~CFS/CF_320558.pdf",
           "local policy - King"),

    # --- LA County local policy ---
    Source("lasd_alpr_transparency_page",
           "Automatic License Plate Recognition - transparency page",
           "Los Angeles County Sheriff's Department", "2026",
           "https://lasd.org/transparency/alpr/",
           "local policy - LA"),
    Source("lasd_alpr_privacy_policy",
           "LASD Automated License Plate Recognition (ALPR) Privacy Policy",
           "Los Angeles County Sheriff's Department", "2026-04-22",
           "http://shq.lasdnews.net/content/uoa/epc/alprprivacypolicy.pdf",
           "local policy - LA"),
    Source("lasd_alpr_coc_community_presentation",
           "LASD ALPR Civilian Oversight Commission community presentation",
           "Los Angeles County Sheriff's Department", "2026-05-06",
           "https://file.lacounty.gov/SDSInter/bos/supdocs/LASD-ALPRCOCCommunityPresentation_May6_2026.pdf",
           "local policy - LA"),
    Source("la_county_bos_motion_207511",
           "Revised motion by Supervisors (LA County Board of Supervisors) on ALPR",
           "Los Angeles County Board of Supervisors", "2026",
           "https://file.lacounty.gov/SDSInter/bos/supdocs/207511.pdf",
           "local policy - LA"),
    Source("lapd_special_order_31_alpr",
           "LAPD Special Order No. 31: ALPR Usage and Privacy Policy",
           "Los Angeles Police Department", "2020-12-10",
           "https://lapdonlinestrgeacc.blob.core.usgovcloudapi.net/lapdonlinemedia/2021/11/so31-12-10.pdf",
           "local policy - LA"),
    Source("eff_lapd_alpr_user_guide",
           "LAPD Automated License Plate Reader User Guide",
           "Electronic Frontier Foundation (records release)", "2015",
           "https://www.eff.org/document/lapd-automated-license-plate-reader-user-guide",
           "local policy - LA"),
    Source("lacity_cd12_alpr_program",
           "Automated License Plate Reader Program Launches (Council District 12)",
           "Los Angeles City Council District 12", "2025",
           "https://cd12.lacity.gov/articles/automated-license-plate-reader-program-launches",
           "local policy - LA"),
    Source("nbcla_lapd_renews_expands_alpr",
           "LAPD renews, expands some automatic license plate reader systems",
           "NBC Los Angeles", "2025",
           "https://www.nbclosangeles.com/investigations/lapd-renews-expands-some-automatic-license-plate-reader-systems/3945420/",
           "reporting"),

    # --- Pasadena, CALIFORNIA (not Pasadena, Texas) ---
    Source("pasadena_ca_audit_flock_compliance",
           "Independent Audit Finds Pasadena Police's Flock Camera Program Complies With State Law",
           "Pasadena Now (Pasadena, CA)", "2026",
           "https://pasadenanow.com/main/independent-audit-finds-pasadena-polices-flock-camera-program-complies-with-state-law-department-policy",
           "audit"),
    Source("pasadena_ca_rally_remove_flock",
           "Dozens Rally at Pasadena City Hall to Demand Removal of Flock Cameras",
           "Pasadena Now (Pasadena, CA)", "2026",
           "https://pasadenanow.com/main/dozens-rally-at-pasadena-city-hall-to-demand-removal-of-flock-license-plate-reader-cameras",
           "reporting"),
    Source("pasadena_ca_halt_flock_request",
           "Councilmember Hampton Asks City to Halt Flock Camera Use",
           "Pasadena Now (Pasadena, CA)", "2026",
           "https://pasadenanow.com/main/councilmember-hampton-asks-city-to-halt-flock-camera-use-as-review-committee-struggles-to-meet",
           "reporting"),
    Source("south_pasadena_flock_contract",
           "City Council OKs Contract for Flock Safety Cameras (South Pasadena, CA)",
           "Outlook Newspapers / South Pasadena Review", "2025",
           "https://outlooknewspapers.com/southpasadenareview/news/city-council-oks-contract-for-flock-safety-cameras/article_c997fa54-9069-58a7-a4e0-e07005371d26.html",
           "local policy - LA"),
    Source("deflock_pasadena_ca",
           "DeFlock Pasadena - camera mapping and local campaign",
           "Pasadena Privacy (Pasadena, CA)", "2026",
           "https://pasadenaprivacy.org/deflock-pasadena",
           "advocacy analysis"),

    # --- Background / national ---
    Source("brennan_center_alpr_legal_status",
           "Automatic License Plate Readers: Legal Status and Policy Recommendations for Law Enforcement Use",
           "Brennan Center for Justice", "2020",
           "https://www.brennancenter.org/our-work/research-reports/automatic-license-plate-readers-legal-status-and-policy-recommendations",
           "background"),
    Source("bja_lpr_policy_template",
           "License Plate Reader Policy Development Template for Use by Law Enforcement",
           "Bureau of Justice Assistance (US DOJ)", "2020",
           "https://bja.ojp.gov/doc/lpr-policy-development-template.pdf",
           "background"),
    Source("eff_sls_alpr_overview",
           "Street-Level Surveillance: Automated License Plate Readers",
           "Electronic Frontier Foundation", "2026",
           "https://sls.eff.org/technologies/automated-license-plate-readers-alprs",
           "background"),
]


def clean_html(html: bytes) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                     "form", "noscript", "iframe"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = main.get_text("\n")
    if len(text.strip()) < MIN_CHARS and main is not soup:
        # Some sites put the body in unlabelled divs; fall back to everything.
        text = soup.get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def clean_pdf(data: bytes) -> str:
    reader = PdfReader(BytesIO(data))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            continue
    return re.sub(r"\n{3,}", "\n\n", "\n\n".join(pages)).strip()


def fetch(src: Source) -> tuple[str | None, str]:
    """Returns (text, note). text is None on failure."""
    try:
        with session() as s:
            for attempt in range(3):
                resp = s.get(src.url, timeout=120)
                if resp.status_code not in (429, 503):
                    break
                # Rate limited or temporarily unavailable: back off and retry.
                time.sleep(15 * (attempt + 1))
        if resp.status_code != 200:
            return None, f"HTTP {resp.status_code}"

        ctype = resp.headers.get("content-type", "").lower()
        if "pdf" in ctype or src.url.lower().endswith(".pdf"):
            text = clean_pdf(resp.content)
            kind = "pdf"
        else:
            text = clean_html(resp.content)
            kind = "html"

        if len(text) < MIN_CHARS:
            return None, f"only {len(text)} chars extracted from {kind} (paywall or JS-rendered?)"
        return text, kind
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    today = stamp()
    rows, failures = [], []

    print(f"Downloading {len(SOURCES)} documents\n")
    for i, src in enumerate(SOURCES, 1):
        existing = DOCS / f"{src.slug}.txt"
        if existing.exists() and existing.stat().st_size > MIN_CHARS:
            body = existing.read_text(encoding="utf-8").split("-" * 70, 1)[-1]
            print(f"  [{i:>2}/{len(SOURCES)}] cached  {src.slug}")
            rows.append({
                "file": existing.name, "title": src.title,
                "publisher": src.publisher, "date": src.date, "url": src.url,
                "bucket": src.bucket, "date_retrieved": today,
                "words": len(body.split()),
            })
            continue

        text, note = fetch(src)
        if text is None:
            print(f"  [{i:>2}/{len(SOURCES)}] FAILED  {src.slug}: {note}")
            failures.append((src, note))
            continue

        path = DOCS / f"{src.slug}.txt"
        header = (
            f"TITLE: {src.title}\n"
            f"PUBLISHER: {src.publisher}\n"
            f"DATE: {src.date}\n"
            f"URL: {src.url}\n"
            f"RETRIEVED: {today}\n"
            f"{'-' * 70}\n\n"
        )
        path.write_text(header + text, encoding="utf-8")
        words = len(text.split())
        print(f"  [{i:>2}/{len(SOURCES)}] ok  {src.slug} ({words:,} words, {note})")
        rows.append(
            {
                "file": path.name,
                "title": src.title,
                "publisher": src.publisher,
                "date": src.date,
                "url": src.url,
                "bucket": src.bucket,
                "date_retrieved": today,
                "words": words,
            }
        )

    with open(DOCS / "sources.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["file", "title", "publisher", "date", "url", "bucket",
                        "date_retrieved", "words"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n{len(rows)} documents saved, {len(failures)} failed")
    if rows:
        total = sum(r["words"] for r in rows)
        print(f"Total corpus: {total:,} words")
        by_bucket: dict[str, int] = {}
        for r in rows:
            by_bucket[r["bucket"]] = by_bucket.get(r["bucket"], 0) + 1
        for bucket, n in sorted(by_bucket.items()):
            print(f"  {bucket}: {n}")

    if failures:
        print("\nFailures (add to docs/manual_downloads.md):")
        for src, note in failures:
            print(f"  {src.title[:60]} - {note}\n    {src.url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
