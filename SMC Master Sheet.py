import discord, gspread
from discord.ext import commands
from datetime import datetime
from discord.ext.commands.core import has_permissions


sa = gspread.service_account(filename="creds.json")
sheet = sa.open("SMC master sheet")

Banned_players = sheet.worksheet("Banned Players")
SD_Payments = sheet.worksheet("SD Payments")
Discipline = sheet.worksheet("Discipline")



class BanList(commands.Cog):

    def __init__(self, client):
        self.client = client

    @has_permissions(administrator=True)
    @commands.command()
    async def banlist(self, ctx):
        embed = discord.Embed(title="Banned Players List", color=0x83e2e6)

        for list in Banned_players.get_all_values():
            embed.add_field(name= list[1], value = list[2], inline= False)

        await ctx.send(embed=embed)

    @has_permissions(administrator=True)
    @commands.command()
    async def ban(self, ctx, username, *, reason):
        Banned_players.insert_row([str(datetime.now())[:-7], username, reason],index=2)
        print(f'{username} was added to the ban list for {reason} at {str(datetime.now())[:-7]}')
        await ctx.send(f'{username} banned successfully for {reason} :white_check_mark:')

    @has_permissions(administrator=True)
    @commands.command()
    async def discipline(self, ctx, username, amount):
        try:
            amount = int(amount)
        except:
            await ctx.send('Amount needs to be an integer.')
            return
        Discipline.insert_row([str(datetime.now())[:-7], username, amount], index=2)
        print(f"{username} has recieved {amount} discipline point(s)")
        await ctx.send(f"{username}'s {amount} points have been added to the sheet successfully :white_check_mark:")

    @has_permissions(administrator=True)
    @commands.command()
    async def sdpayment(self, ctx, username, amount):        
        try:
            amount = int(amount)
        except:
            await ctx.send('Amount needs to be an integer.')
            return
        SD_Payments.insert_row([username, amount], index=2)
        print(f"{username}'s {amount} diamond block payment was added to the sheet")
        await ctx.send(f"{username}'s {amount} diamond block payment was added to the sheet successfully :white_check_mark:")
    

def setup(client):
    client.add_cog(BanList(client))
