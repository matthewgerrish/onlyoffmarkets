"""
Seed the local SQLite with realistic-looking off-market signals so the
frontend has something to render before the live scrapers are wired up.

Run:
    python seed_demo.py
"""
from __future__ import annotations

from datetime import datetime, timedelta

from scrapers.models import RawLead
from storage.off_market_db import upsert


DEMO_LEADS = [
    # Pierce County NOD
    dict(source="preforeclosure", source_id="pierce-NTS-2026-04122",
         raw_address="4127 S Asotin St", city="Tacoma", county="Pierce", state="WA", zip="98418",
         filing_date=datetime.utcnow() - timedelta(days=4),
         default_amount=14210,
         source_url="https://rd.co.pierce.wa.us/PIERCE/web/Search/DocumentSearch?DocNum=2026-04122"),
    # Maricopa AZ trustee sale
    dict(source="auction", source_id="maricopa-TS-1142",
         raw_address="8821 E Sells Dr", city="Scottsdale", county="Maricopa", state="AZ", zip="85260",
         sale_date=datetime.utcnow() + timedelta(days=38),
         opening_bid=412000,
         source_url="https://recorder.maricopa.gov/recdocdata/?docnum=1142"),
    # Fulton GA tax delinquent + code violation
    dict(source="tax-lien", source_id="fulton-tax-2026-001",
         raw_address="209 Magnolia Ave", city="Atlanta", county="Fulton", state="GA", zip="30315",
         lien_amount=9840, years_delinquent=3,
         source_url="https://taxcommissioner.fultoncountyga.gov/list"),
    dict(source="vacant", source_id="fulton-code-22871",
         raw_address="209 Magnolia Ave", city="Atlanta", county="Fulton", state="GA",
         vacancy_duration_months=14,
         source_url="https://atlantaga.gov/code-enforcement/case/22871"),
    # Chesapeake VA FSBO
    dict(source="fsbo", source_id="cl-norfolk-7748112",
         raw_address="14 Heritage Ln", city="Chesapeake", county="Chesapeake City", state="VA", zip="23320",
         asking_price=349000,
         source_url="https://norfolk.craigslist.org/reb/d/7748112.html"),
    # Lehigh PA probate
    dict(source="probate", source_id="lehigh-prob-2026-0214-aa",
         raw_address="1142 Linden St", city="Allentown", county="Lehigh", state="PA", zip="18102",
         filing_date=datetime.utcnow() - timedelta(days=72),
         source_url="https://www.lccpa.org/probate/case/2026-0214-AA"),
    # Miami-Dade FL absentee
    dict(source="vacant", source_id="miami-attom-503nw22",
         raw_address="503 NW 22nd Ter", city="Miami", county="Miami-Dade", state="FL", zip="33125",
         owner_state="NY",
         source_url="https://api.gateway.attomdata.com/property/expandedprofile?address=503+NW+22nd+Ter"),
    # King County WA NOD
    dict(source="preforeclosure", source_id="king-NOD-2026-1190",
         raw_address="9402 Rainier Ave S", city="Seattle", county="King", state="WA", zip="98118",
         filing_date=datetime.utcnow() - timedelta(days=2),
         default_amount=22480,
         source_url="https://recording.kingcounty.gov/search?DocNum=2026-1190"),
    # Thurston WA tax delinquent
    dict(source="tax-lien", source_id="thurston-tax-2026-0042",
         raw_address="412 Capitol Way N", city="Olympia", county="Thurston", state="WA", zip="98501",
         lien_amount=4120, years_delinquent=2,
         source_url="https://www.thurstoncountywa.gov/treasurer/delinquent"),
]


def main() -> None:
    n = 0
    for d in DEMO_LEADS:
        lead = RawLead(**d)
        key = upsert(lead)
        if key:
            n += 1
            print(f"  ✓ {lead.source:20s}  {lead.raw_address}")
    print(f"\nSeeded {n} demo leads into .data/off_market.sqlite")


if __name__ == "__main__":
    main()
