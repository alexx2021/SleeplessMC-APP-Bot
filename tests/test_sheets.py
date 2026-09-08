from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from cogs.sheet_commands import SheetCommands, ban_pages
from tests.common import config


class SheetTests(unittest.IsolatedAsyncioTestCase):
    def test_ban_pages_respect_embed_field_limit(self):
        pages = ban_pages(
            [["date", f"Player {index}", "reason"] for index in range(45)]
        )
        self.assertEqual([len(page) for page in pages], [20, 20, 5])
        long_pages = ban_pages(
            [["date", f"Player {index}", "x" * 1_024] for index in range(10)]
        )
        self.assertTrue(
            all(
                sum(len(name) + len(reason) for name, reason in page) <= 5_000
                for page in long_pages
            )
        )

    def test_uses_every_configured_spreadsheet_target(self):
        bot = SimpleNamespace(config=config())
        cog = SheetCommands(bot)
        spreadsheet = MagicMock()
        client = MagicMock()
        client.open.return_value = spreadsheet

        with patch("cogs.sheet_commands.gspread.service_account", return_value=client) as service:
            cog._open_worksheets()

        service.assert_called_once_with(filename="service-account.json")
        client.open.assert_called_once_with("Community Book")
        self.assertEqual(
            [call.args[0] for call in spreadsheet.worksheet.call_args_list],
            ["Bans", "Payments", "Discipline", "Finances"],
        )

    async def test_donation_batches_four_cells_into_one_update(self):
        finances = MagicMock()
        finances.col_values.return_value = ["Date", "existing"]
        cog = SheetCommands(SimpleNamespace(config=config()))
        cog.worksheets = {"finances": finances}
        ctx = SimpleNamespace(defer=AsyncMock(), send=AsyncMock())

        await SheetCommands.donation.callback(cog, ctx, "Donor", 10.0, 1.5)

        ctx.defer.assert_awaited_once_with()
        finances.update.assert_called_once()
        values, cell_range = finances.update.call_args.args
        self.assertEqual(cell_range, "A4:D4")
        self.assertEqual(values[0][1:], ["Donation (Donor)", 10.0, 1.5])
        self.assertIn("€10", ctx.send.await_args.args[0])

    async def test_payment_uses_configured_unit(self):
        payments = MagicMock()
        cog = SheetCommands(SimpleNamespace(config=config(PAYMENT_UNIT="credit")))
        cog.worksheets = {"payments": payments}
        ctx = SimpleNamespace(defer=AsyncMock(), send=AsyncMock())

        await SheetCommands.payment.callback(cog, ctx, "Player", 3)

        ctx.defer.assert_awaited_once_with()
        payments.insert_row.assert_called_once_with(["Player", 3], 2)
        self.assertIn("3 credit", ctx.send.await_args.args[0])

    async def test_sheet_connection_failure_is_reported(self):
        cog = SheetCommands(SimpleNamespace(config=config()))
        cog._open_worksheets = MagicMock(side_effect=RuntimeError("offline"))
        ctx = SimpleNamespace(send=AsyncMock())

        with self.assertLogs("cogs.sheet_commands", level="ERROR"):
            self.assertIsNone(await cog._sheets(ctx))

        self.assertIn("unavailable", ctx.send.await_args.args[0])


if __name__ == "__main__":
    unittest.main()
