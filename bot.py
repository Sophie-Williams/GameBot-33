from discord.ext import commands

from GameBot import resistance


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_cog(resistance.Resistance(self))

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

prp = Bot(command_prefix="!", description="Fun bot is fun", pm_help=True)
prp.run("MzE5MjkwOTQzOTI2Njk3OTk0.DIC6pw.Qc5xLVSthGLWM5oDZ5Y_Gw1blNc")
