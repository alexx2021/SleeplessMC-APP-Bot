import logging
from discord.ext import commands
import traceback
import sys
logger = logging.getLogger('discord')


class Errors(commands.Cog, command_attrs=dict(hidden=True)):
    def __init__(self, bot):
        self.bot = bot    


    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):

        error = getattr(error, "original", error)
        # if isinstance(error, commands.CommandError):
        #     error = error.original

        if isinstance(error, commands.CommandNotFound):
            #await ctx.send('Invalid command used.')
            return
        
        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f'Command is missing required arguments. Correct usage: `{ctx.command} {ctx.command.signature}`')
        
        elif isinstance(error, commands.CommandOnCooldown):
            return await ctx.send(f'{ctx.author.mention}, You must wait **{round(error.retry_after, 2)}** seconds before using this command again.')
        
        elif isinstance(error, commands.MissingPermissions):
            return await ctx.send(f"{ctx.author.mention}, {error}.")

        elif isinstance(error, commands.BotMissingPermissions):
            return await ctx.send(f"{error}.")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(f'Command was given bad/invalid arguments. `{error}`')
        
        elif isinstance(error, commands.NotOwner): 
            return
        
        elif isinstance(error, commands.errors.CheckFailure):
            return
        else:

            logger.warning(msg=f'COMMAND ERROR - {ctx.message.clean_content} - {error} - u.{ctx.author.id} g.{ctx.guild.id}')
            #All unhandled Errors will print their original traceback
            print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):

        logger.warning(msg=f'EVENT ERROR - {event} - {traceback.format_exc()}')
        
        print(f'{event}')
        print(f'{traceback.format_exc()}')

def setup(bot):
    bot.add_cog(Errors(bot))