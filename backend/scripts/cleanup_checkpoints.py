#!/usr/bin/env python3
"""Cleanup script for DeerFlow checkpoints database.

This script removes old and redundant checkpoints to control database size:
- Removes checkpoints older than specified days (default: 30)
- Keeps only the most recent N checkpoints per thread (default: 100)

Usage:
    python cleanup_checkpoints.py --size          # Show current database size
    python cleanup_checkpoints.py --days 30      # Remove checkpoints older than 30 days
    python cleanup_checkpoints.py --max 100      # Keep only 100 most recent per thread
    python cleanup_checkpoints.py --dry-run       # Show what would be deleted without deleting
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_checkpoints_db_path() -> Path | None:
    """Get the path to the checkpoints database."""
    from deerflow.config.app_config import get_app_config
    from deerflow.config.checkpointer_config import get_checkpointer_config
    from deerflow.config.paths import resolve_path

    config = get_checkpointer_config()
    if config is None:
        # Try to get from app config
        try:
            app_config = get_app_config()
            if app_config.checkpointer is not None:
                config = app_config.checkpointer
        except FileNotFoundError:
            pass

    if config is None:
        return None

    if config.type == "sqlite" and config.connection_string:
        return Path(resolve_path(config.connection_string))

    # Default path
    return Path(resolve_path(".deer-flow/checkpoints.db"))


def get_db_size(db_path: Path) -> str:
    """Get human-readable database size."""
    if db_path.exists():
        size = db_path.stat().st_size
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} MB"
        else:
            return f"{size / (1024 * 1024 * 1024):.1f} GB"
    return "N/A"


def show_size(db_path: Path) -> None:
    """Show current database size and checkpoint counts."""
    if not db_path.exists():
        print(f"Checkpoints database not found at {db_path}")
        return

    print(f"Database: {db_path}")
    print(f"Size: {get_db_size(db_path)}")

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Get checkpoint count
        cursor.execute("SELECT COUNT(*) FROM checkpoints")
        total = cursor.fetchone()[0]

        # Get thread count
        cursor.execute("SELECT COUNT(DISTINCT thread_id) FROM checkpoints")
        threads = cursor.fetchone()[0]

        print(f"Total checkpoints: {total}")
        print(f"Unique threads: {threads}")

        # Get oldest and newest
        cursor.execute("SELECT MIN(created_at), MAX(created_at) FROM checkpoints")
        oldest, newest = cursor.fetchone()
        if oldest:
            print(f"Oldest checkpoint: {oldest}")
        if newest:
            print(f"Newest checkpoint: {newest}")

        conn.close()
    except sqlite3.Error as e:
        print(f"Error reading database: {e}")


def cleanup_by_days(db_path: Path, days: int, dry_run: bool = False) -> int:
    """Remove checkpoints older than specified days.

    Returns the number of checkpoints removed.
    """
    if not db_path.exists():
        print(f"Checkpoints database not found at {db_path}")
        return 0

    cutoff_date = datetime.now() - timedelta(days=days)

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Find checkpoints to delete
        cursor.execute(
            """
            SELECT checkpoint_id, thread_id, created_at
            FROM checkpoints
            WHERE created_at < ?
            ORDER BY created_at
            """,
            (cutoff_date.isoformat(),),
        )
        to_delete = cursor.fetchall()

        if not to_delete:
            print(f"No checkpoints older than {days} days")
            return 0

        print(f"Found {len(to_delete)} checkpoints older than {days} days")

        if dry_run:
            print("Dry run - not deleting:")
            for checkpoint_id, thread_id, created_at in to_delete[:10]:
                print(f"  - {checkpoint_id[:8]}... (thread: {thread_id}, created: {created_at})")
            if len(to_delete) > 10:
                print(f"  ... and {len(to_delete) - 10} more")
            return 0

        # Delete checkpoints
        cursor.execute(
            "DELETE FROM checkpoints WHERE created_at < ?",
            (cutoff_date.isoformat(),),
        )
        deleted = cursor.rowcount

        # Vacuum to reclaim space
        conn.commit()
        conn.execute("VACUUM")
        conn.close()

        print(f"Deleted {deleted} checkpoints")
        print(f"New database size: {get_db_size(db_path)}")
        return deleted

    except sqlite3.Error as e:
        print(f"Error cleaning database: {e}")
        return 0


def cleanup_by_max_per_thread(db_path: Path, max_per_thread: int, dry_run: bool = False) -> int:
    """Keep only the most recent N checkpoints per thread.

    Returns the number of checkpoints removed.
    """
    if not db_path.exists():
        print(f"Checkpoints database not found at {db_path}")
        return 0

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Find threads with more than max_per_thread checkpoints
        cursor.execute(
            """
            SELECT thread_id, COUNT(*) as cnt
            FROM checkpoints
            GROUP BY thread_id
            HAVING cnt > ?
            """,
            (max_per_thread,),
        )
        threads_with_excess = cursor.fetchall()

        if not threads_with_excess:
            print(f"No threads with more than {max_per_thread} checkpoints")
            return 0

        print(f"Found {len(threads_with_excess)} threads with more than {max_per_thread} checkpoints")

        total_to_delete = 0
        threads_info = []

        for thread_id, count in threads_with_excess:
            # Get IDs of checkpoints to delete (keep the most recent max_per_thread)
            cursor.execute(
                """
                SELECT checkpoint_id
                FROM checkpoints
                WHERE thread_id = ?
                ORDER BY created_at DESC
                LIMIT -1 OFFSET ?
                """,
                (thread_id, max_per_thread),
            )
            ids_to_delete = [row[0] for row in cursor.fetchall()]
            total_to_delete += len(ids_to_delete)
            threads_info.append((thread_id, count, len(ids_to_delete)))

        if dry_run:
            print(f"Would delete {total_to_delete} checkpoints from {len(threads_info)} threads:")
            for thread_id, total, to_delete in threads_info[:10]:
                print(f"  - Thread {thread_id[:8]}...: {to_delete}/{total}")
            if len(threads_info) > 10:
                print(f"  ... and {len(threads_info) - 10} more threads")
            return 0

        # Delete excess checkpoints
        deleted = 0
        for thread_id, _, _ in threads_info:
            cursor.execute(
                """
                DELETE FROM checkpoints
                WHERE thread_id = ?
                AND checkpoint_id NOT IN (
                    SELECT checkpoint_id
                    FROM checkpoints
                    WHERE thread_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                )
                """,
                (thread_id, thread_id, max_per_thread),
            )
            deleted += cursor.rowcount

        # Vacuum to reclaim space
        conn.commit()
        conn.execute("VACUUM")
        conn.close()

        print(f"Deleted {deleted} checkpoints")
        print(f"New database size: {get_db_size(db_path)}")
        return deleted

    except sqlite3.Error as e:
        print(f"Error cleaning database: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Cleanup DeerFlow checkpoints database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --size              Show current database size and counts
  %(prog)s --days 30           Remove checkpoints older than 30 days
  %(prog)s --max 100           Keep only 100 most recent per thread
  %(prog)s --days 30 --dry-run Show what would be deleted without deleting
        """,
    )
    parser.add_argument(
        "--size",
        action="store_true",
        help="Show current database size and checkpoint counts",
    )
    parser.add_argument(
        "--days",
        type=int,
        metavar="N",
        help="Remove checkpoints older than N days",
    )
    parser.add_argument(
        "--max",
        type=int,
        metavar="N",
        help="Keep only N most recent checkpoints per thread",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    db_path = get_checkpoints_db_path()
    if db_path is None:
        print("Could not determine checkpoints database path")
        sys.exit(1)

    if args.size:
        show_size(db_path)
        return

    if args.days is not None:
        cleanup_by_days(db_path, args.days, args.dry_run)
        return

    if args.max is not None:
        cleanup_by_max_per_thread(db_path, args.max, args.dry_run)
        return

    # No action specified, show size
    show_size(db_path)
    print("\nUse --help for usage information")


if __name__ == "__main__":
    main()
