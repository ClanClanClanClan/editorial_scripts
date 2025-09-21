#!/usr/bin/env python3
"""
CACHE MANAGEMENT CLI
====================

Command-line tool for managing the editorial extractor cache.
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from src.core.cache_manager import CacheManager


def stats_command(args):
    """Show cache statistics with v1.0 spec compliance."""
    from .multi_layer_cache import MultiLayerCache

    # Initialize multi-layer cache for complete stats
    multi_cache = MultiLayerCache()
    cache_stats = multi_cache.get_cache_stats()

    print("\n📊 EDITORIAL CACHE STATISTICS (V1.0 COMPLIANT)")
    print("=" * 70)

    # Layer 1: Memory Cache
    memory_stats = cache_stats["layer_1_memory"]
    print("\n📱 LAYER 1 - IN-MEMORY CACHE:")
    print(f"   Items: {memory_stats['count']:,} / {memory_stats['max_items']:,}")
    print(f"   Size: {memory_stats['size_bytes'] / 1024:.1f} KB")

    # Layer 2: SQLite Cache
    sqlite_stats = cache_stats["layer_2_sqlite"]
    print("\n💿 LAYER 2 - SQLITE CACHE:")
    print(f"   👥 Referees: {sqlite_stats['total_referees']:,}")
    print(f"   🏢 Institutions: {sqlite_stats['unique_institutions']:,}")
    print(f"   🌍 Countries: {sqlite_stats['unique_countries']:,}")
    print(f"   📄 Manuscripts: {sqlite_stats['total_manuscripts']:,}")

    if sqlite_stats.get("manuscripts_by_journal"):
        for journal, count in sorted(sqlite_stats["manuscripts_by_journal"].items()):
            print(f"      {journal}: {count:,}")

    # Layer 3: File System Cache
    fs_stats = cache_stats["layer_3_filesystem"]
    print("\n📁 LAYER 3 - FILE SYSTEM CACHE:")
    print(f"   Files: {fs_stats['count']:,}")
    print(f"   Size: {fs_stats['size_bytes'] / (1024*1024):.1f} MB")
    print(f"   Location: {fs_stats['directory']}")

    # Layer 4: Redis Cache
    redis_stats = cache_stats["layer_4_redis"]
    print("\n🌐 LAYER 4 - REDIS CACHE:")
    print(f"   Status: {redis_stats['status']}")

    # V1.0 Spec Tables
    cache = multi_cache.sqlite_cache
    print("\n📋 V1.0 SPECIFICATION COMPLIANCE:")

    # Check referee performance cache
    with cache.lock:
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM referee_performance_cache")
            perf_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM journal_statistics")
            stats_count = cursor.fetchone()[0]

    print(f"   ✅ referee_performance_cache: {perf_count:,} entries")
    print(f"   ✅ journal_statistics: {stats_count:,} entries")

    # Recent extractions
    print("\n📈 RECENT EXTRACTIONS:")
    for extraction in sqlite_stats.get("recent_extractions", [])[:10]:
        date = extraction["date"][:10]
        time = extraction["date"][11:19]
        print(f"   {extraction['journal']:8} {date} {time} - {extraction['count']:3} manuscripts")

    # Total cache size
    total_size_mb = (
        memory_stats["size_bytes"] / (1024 * 1024)
        + sqlite_stats["cache_size_mb"]
        + fs_stats["size_bytes"] / (1024 * 1024)
    )

    print(f"\n💾 TOTAL CACHE SIZE: {total_size_mb:.1f} MB")
    print(f"📍 Cache Directory: {multi_cache.sqlite_cache.cache_dir}")


def referee_command(args):
    """Search for referee by email."""
    cache = CacheManager()
    referee = cache.get_referee(args.email.lower().strip())

    if referee:
        print("\n👤 REFEREE PROFILE")
        print("=" * 60)
        print(f"Name:        {referee.name}")
        print(f"Email:       {referee.email}")
        print(f"Institution: {referee.institution}")
        print(f"Department:  {referee.department}")
        print(f"Country:     {referee.country}")
        print(f"ORCID:       {referee.orcid or 'Not available'}")
        print(f"Journals:    {', '.join(referee.journals_seen)}")
        print(f"Last seen:   {referee.last_seen[:10] if referee.last_seen else 'Unknown'}")
        print(f"Last update: {referee.last_updated[:10] if referee.last_updated else 'Unknown'}")

        if referee.affiliations_history:
            print("\n📜 AFFILIATION HISTORY:")
            for aff in referee.affiliations_history:
                print(f"   {aff['date'][:10]}: {aff['institution']}")
                if aff.get("department"):
                    print(f"                  {aff['department']}")
                print(f"                  (via {aff['journal']})")
    else:
        print(f"\n❌ No referee found with email: {args.email}")

        # Suggest similar emails
        with cache.lock:
            import sqlite3

            with sqlite3.connect(cache.db_path) as conn:
                cursor = conn.cursor()
                domain = args.email.split("@")[-1] if "@" in args.email else ""
                if domain:
                    cursor.execute(
                        "SELECT email, name FROM referees WHERE email LIKE ?", (f"%@{domain}",)
                    )
                    similar = cursor.fetchall()
                    if similar:
                        print(f"\n💡 Similar emails from {domain}:")
                        for email, name in similar[:5]:
                            print(f"   {email} ({name})")


def manuscript_command(args):
    """Search for manuscript."""
    cache = CacheManager()
    manuscript = cache.get_manuscript(args.id, args.journal)

    if manuscript:
        print(f"\n📄 MANUSCRIPT: {manuscript.manuscript_id}")
        print("=" * 60)
        print(f"Journal:     {manuscript.journal}")
        print(f"Title:       {manuscript.title[:80]}...")
        print(f"Status:      {manuscript.status}")
        print(f"Authors:     {', '.join(manuscript.authors[:3])}")
        if len(manuscript.authors) > 3:
            print(f"             and {len(manuscript.authors) - 3} more")
        print(f"Submitted:   {manuscript.submission_date}")
        print(f"Updated:     {manuscript.last_updated}")
        print(f"Cached:      {manuscript.extraction_date[:10]}")
        print(f"Referees:    {manuscript.referee_count}")
        print(f"Version History: {'Yes' if manuscript.has_version_history else 'No'}")

        if args.full:
            print("\n📋 FULL DATA:")
            print(json.dumps(manuscript.full_data, indent=2))
    else:
        print(f"\n❌ No manuscript found: {args.id} in {args.journal}")


def clear_command(args):
    """Clear old cache entries."""
    cache = CacheManager()

    if args.journal:
        # Clear specific journal
        import sqlite3

        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM manuscripts WHERE journal = ?", (args.journal,))
            deleted = cursor.rowcount
            conn.commit()
        print(f"🧹 Cleared {deleted} manuscripts for {args.journal}")
    else:
        # Clear old entries
        deleted_manuscripts, deleted_runs = cache.clear_old_cache(args.days)
        print(
            f"🧹 Cleared {deleted_manuscripts} manuscripts and {deleted_runs} runs older than {args.days} days"
        )


def export_command(args):
    """Export referee data."""
    cache = CacheManager()

    import sqlite3

    with sqlite3.connect(cache.db_path) as conn:
        cursor = conn.cursor()

        if args.journal:
            # Export referees for specific journal
            cursor.execute(
                """
                SELECT DISTINCT r.* FROM referees r
                WHERE r.journals_seen LIKE ?
            """,
                (f'%"{args.journal}"%',),
            )
        else:
            # Export all referees
            cursor.execute("SELECT * FROM referees")

        referees = []
        for row in cursor.fetchall():
            referees.append(
                {
                    "email": row[0],
                    "name": row[1],
                    "institution": row[2],
                    "department": row[3],
                    "country": row[4],
                    "orcid": row[5],
                    "last_seen": row[6],
                    "last_updated": row[7],
                    "journals": json.loads(row[8] or "[]"),
                }
            )

    # Save to file
    output_file = args.output or f"referees_export_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_file, "w") as f:
        json.dump(referees, f, indent=2)

    print(f"📤 Exported {len(referees)} referees to {output_file}")


def populate_stats_command(args):
    """Populate journal statistics for v1.0 spec compliance."""
    cache = CacheManager()

    print("📊 Populating journal statistics from extraction data...")

    # Get all manuscripts by journal
    with cache.lock:
        with sqlite3.connect(cache.db_path) as conn:
            cursor = conn.cursor()

            # Get journals and their manuscript counts
            cursor.execute(
                """
                SELECT journal, COUNT(*) as count,
                       MIN(submission_date) as earliest,
                       MAX(submission_date) as latest
                FROM manuscripts
                GROUP BY journal
            """
            )
            journal_data = cursor.fetchall()

            stats_added = 0

            for journal, count, earliest, latest in journal_data:
                if earliest and latest:
                    # Create monthly statistics
                    from datetime import datetime

                    try:
                        start_date = datetime.fromisoformat(earliest).strftime("%Y-%m-01")
                        end_date = datetime.fromisoformat(latest).strftime("%Y-%m-28")

                        # Calculate basic statistics
                        cursor.execute(
                            """
                            SELECT
                                COUNT(*) as submissions,
                                AVG(CASE WHEN status LIKE '%Accept%' THEN 1.0 ELSE 0.0 END) * 100 as acceptance_rate,
                                AVG(CASE WHEN status LIKE '%Reject%' THEN 1.0 ELSE 0.0 END) * 100 as rejection_rate
                            FROM manuscripts
                            WHERE journal = ?
                        """,
                            (journal,),
                        )

                        stats = cursor.fetchone()

                        if stats:
                            # Parse dates properly
                            start = datetime.strptime(start_date, "%Y-%m-%d").date()
                            end = datetime.strptime(end_date, "%Y-%m-%d").date()

                            cache.update_journal_statistics(
                                journal_id=journal,
                                period_start=start,
                                period_end=end,
                                total_submissions=stats[0],
                                average_review_time=45.0,  # Default estimate
                                acceptance_rate=(stats[1] or 0.0) / 100.0,  # Convert to 0-1 scale
                                desk_rejection_rate=(stats[2] or 0.0)
                                / 100.0,  # Convert to 0-1 scale
                            )
                            stats_added += 1
                            print(
                                f"   ✅ {journal}: {stats[0]} submissions, {stats[1]:.1f}% acceptance"
                            )

                    except Exception as e:
                        print(f"   ⚠️ Error processing {journal}: {e}")

            print(f"\n✅ Added {stats_added} journal statistics entries")


def main():
    parser = argparse.ArgumentParser(
        description="Editorial Cache Management Tool (V1.0 Compliant)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show cache statistics
  python cache_cli.py stats

  # Search for a referee
  python cache_cli.py referee john.doe@university.edu

  # Look up a manuscript
  python cache_cli.py manuscript MOR-2023-0376 --journal MOR

  # Clear old cache entries
  python cache_cli.py clear --days 30

  # Export referee data
  python cache_cli.py export --journal MF -o mf_referees.json

  # Populate v1.0 compliance tables
  python cache_cli.py populate-stats
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show cache statistics")

    # Referee command
    referee_parser = subparsers.add_parser("referee", help="Search for referee by email")
    referee_parser.add_argument("email", help="Referee email address")

    # Manuscript command
    manuscript_parser = subparsers.add_parser("manuscript", help="Search for manuscript")
    manuscript_parser.add_argument("id", help="Manuscript ID")
    manuscript_parser.add_argument("--journal", required=True, help="Journal name (e.g., MOR, MF)")
    manuscript_parser.add_argument("--full", action="store_true", help="Show full data")

    # Clear command
    clear_parser = subparsers.add_parser("clear", help="Clear old cache entries")
    clear_parser.add_argument(
        "--days", type=int, default=90, help="Clear entries older than N days"
    )
    clear_parser.add_argument("--journal", help="Clear only specific journal")

    # Export command
    export_parser = subparsers.add_parser("export", help="Export referee data")
    export_parser.add_argument("--journal", help="Export only referees from specific journal")
    export_parser.add_argument("-o", "--output", help="Output file name")

    # Populate stats command
    populate_parser = subparsers.add_parser(
        "populate-stats", help="Populate v1.0 compliance statistics"
    )

    args = parser.parse_args()

    if args.command == "stats":
        stats_command(args)
    elif args.command == "referee":
        referee_command(args)
    elif args.command == "manuscript":
        manuscript_command(args)
    elif args.command == "clear":
        clear_command(args)
    elif args.command == "export":
        export_command(args)
    elif args.command == "populate-stats":
        populate_stats_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
