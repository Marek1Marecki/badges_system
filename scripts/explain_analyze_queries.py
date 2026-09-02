"""Skrypty EXPLAIN ANALYZE dla krytycznych ścieżek biznesowych.

AUDYT-074: Do uruchomienia na środowisku z produkcyjnymi danymi.

Wymagania:
  - Dostęp do bazy danych PostgreSQL z danymi produkcyjnymi
  - Uprawnienia SELECT na tabelach analizowanych

Usage:
  python scripts/explain_analyze_queries.py --db-url "postgresql://user:pass@localhost/db" --query badge_detail
"""

import argparse
import sys

QUERY_TEMPLATES = {
    "badge_detail": {
        "description": "Badge detail page — fetch version, pools, tiers, user progress",
        "sql": """
            -- Replikacja Django ORM query dla /odznaki/{badge_code}
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT
                bv.id, bv.badge_id, bv.version_number, bv.start_date,
                bp.id as pool_id, bp.peak_id,
                bt.id as tier_id, bt.name, bt.required_count, bt."order",
                up.progress, up.status
            FROM badges_badgeversionmodel bv
            JOIN badges_badgemodel b ON b.id = bv.badge_id
            LEFT JOIN badges_badgepool_peaks bp ON bp.badgeversionmodel_id = bv.id
            LEFT JOIN badges_badgetier bt ON bt.badgeversionmodel_id = bv.id
            LEFT JOIN badges_userbadgeprogress up
                ON up.badge_version_id = bv.id AND up.profile_id = %s
            WHERE b.code = %s
            ORDER BY bt."order";
        """,
        "params": ["profile_id", "badge_code"],
    },
    "object_detail": {
        "description": "Tourist object detail — scores, regions, ascents",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT
                to.id, to.name, to.altitude, to.geom,
                orc.region_level, orc.region_id,
                al.ascent_date
            FROM tourists_touristobject to
            LEFT JOIN badges_objectregioncache orc ON orc.tourist_object_id = to.id
            LEFT JOIN badges_ascentlog al
                ON al.peak_id = to.id AND al.profile_id = %s
            WHERE to.id = %s;
        """,
        "params": ["object_id", "profile_id"],
    },
    "region_detail": {
        "description": "Region detail — objects in region with N queries",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT
                to.id, to.name, to.altitude, to.type,
                orc.region_level, orc.region_id
            FROM tourists_touristobject to
            JOIN badges_objectregioncache orc ON orc.tourist_object_id = to.id
            WHERE orc.region_level = %s AND orc.region_id = %s
            ORDER BY to.name
            LIMIT 500;
        """,
        "params": ["region_level", "region_id"],
    },
    "progress_recalculate": {
        "description": "Bulk progress recalculation for a profile",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT
                al.peak_id, al.ascent_date,
                bv.badge_id, bv.version_number
            FROM badges_ascentlog al
            JOIN badges_badgeversionmodel bv ON bv.id = al.badge_version_id
            WHERE al.profile_id = %s
            ORDER BY al.ascent_date DESC
            LIMIT 1000;
        """,
        "params": ["profile_id"],
    },
    "st_dwithin_nearby": {
        "description": "Nearby objects query (ST_DWithin)",
        "sql": """
            EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
            SELECT id, name, ST_Distance(geom, ST_SetSRID(ST_Point(%s, %s), 4326)) as dist_m
            FROM tourists_touristobject
            WHERE geom IS NOT NULL
              AND ST_DWithin(
                  geom::geography,
                  ST_SetSRID(ST_Point(%s, %s), 4326)::geography,
                  %s
              )
              AND is_active = true
              AND status = 'READY'
            ORDER BY dist_m
            LIMIT 100;
        """,
        "params": ["lon", "lat", "lon", "lat", "radius_meters"],
    },
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXPLAIN ANALYZE queries for AUDYT-074")
    parser.add_argument(
        "--query",
        choices=list(QUERY_TEMPLATES.keys()) + ["all"],
        help="Which query to explain",
    )
    parser.add_argument("--db-url", required=True, help="PostgreSQL connection string")
    parser.add_argument("--profile-id", type=int, default=1, help="Test profile_id for queries")
    parser.add_argument("--badge-code", default="KGP", help="Test badge_code for queries")
    args = parser.parse_args()

    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 nie jest zainstalowany. Zainstaluj: pip install psycopg2-binary", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(args.db_url)
    conn.autocommit = True
    cur = conn.cursor()

    queries_to_run = QUERY_TEMPLATES.keys() if args.query == "all" else [args.query]

    for name in queries_to_run:
        template = QUERY_TEMPLATES[name]
        print(f"\n{'=' * 60}")
        print(f"Query: {name}")
        print(f"Description: {template['description']}")
        print(f"{'=' * 60}\n")

        param_values = []
        for param in template["params"]:
            if param in ("profile_id", "object_id"):
                param_values.append(args.profile_id)
            elif param == "badge_code":
                param_values.append(args.badge_code)
            elif param == "region_level":
                param_values.append("voivodeship")
            elif param == "region_id":
                param_values.append(1)
            elif param in ("lon", "lat"):
                param_values.append(20.0 if param == "lon" else 50.0)
            elif param == "radius_meters":
                param_values.append(2000)

        cur.execute(template["sql"], param_values)
        result = cur.fetchall()
        print(result[0][0])

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
