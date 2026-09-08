import sqlite3
import unittest

import aiosqlite

from utils import migrate_tickets


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = await aiosqlite.connect(":memory:")

    async def asyncTearDown(self):
        await self.db.close()

    async def test_migrates_legacy_rows_and_keeps_newest_unique_mappings(self):
        await self.db.execute("CREATE TABLE tickets(user_id INTERGER, channel_id INTERGER)")
        await self.db.executemany(
            "INSERT INTO tickets VALUES (?, ?)",
            [(1, 10), (1, 11), (2, 10), (0, 20), (3, 30)],
        )
        await self.db.commit()

        await migrate_tickets(self.db)
        rows = await self.db.execute_fetchall(
            "SELECT user_id, channel_id FROM tickets ORDER BY user_id"
        )

        self.assertEqual(rows, [(1, 11), (2, 10), (3, 30)])
        with self.assertRaises(sqlite3.IntegrityError):
            await self.db.execute("INSERT INTO tickets VALUES (1, 99)")
        await self.db.rollback()
        with self.assertRaises(sqlite3.IntegrityError):
            await self.db.execute("INSERT INTO tickets VALUES (99, 10)")

    async def test_migration_is_safe_to_run_again(self):
        await migrate_tickets(self.db)
        await self.db.execute("INSERT INTO tickets VALUES (1, 10)")
        await self.db.commit()
        await migrate_tickets(self.db)
        self.assertEqual(
            await self.db.execute_fetchall("SELECT user_id, channel_id FROM tickets"),
            [(1, 10)],
        )


if __name__ == "__main__":
    unittest.main()
