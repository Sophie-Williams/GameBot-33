from discord.ext import commands
import discord
from random import randint, choice, sample
import asyncio
from math import ceil

games_example = {
    "channel obj": {  # channel ids
        "state": 0,  # 0: lobby, 1: in progress, 2: cancelled
        "owner": "asdsadd",
        "members": {
            "member": 0,  # pids, 0 for inno
            "membe2r": 1,  # 1 for spy
        }
    }

}

mission_chart = {
    5: [2, 3, 2, 3, 3],
    6: [2, 3, 4, 3, 4],
    7: [2, 3, 3, 4, 4],
    8: [3, 4, 4, 5, 5],
    9: [3, 4, 4, 5, 5],
    10: [3, 4, 4, 5, 5],
}


class Resistance:
    def __init__(self, bot):
        self.bot = bot
        self.games = {}

    @staticmethod
    def waitlobby(command, channel):
        def inner(message):
            if message.channel == channel and message.content.startswith(command):
                return True
            return False

        return inner

    @commands.group(invoke_without_command=True, aliases=["r"])
    async def resistance(self, ctx):
        """Resistance subcommands. Use for information on the game."""
        await ctx.send("""
    ```markdown
    The Resistance is a social deduction game with secret identities. Players are either members of
    the Resistance attempting to overthrow a malignant government, or Spies trying to thwart the
    Resistance. The Resistance wins the game if three Missions are completed successfully; the Spies
    win if three Missions fail. The Spies can also win if the Resistance is unable to organize the Mission
    Team at any point in the game (5 failed votes on a single mission).
    
    A fundamental rule of the game is that players may say anything that they want, at anytime during
    the game. Discussion, deception, intuition, social interaction and logical deductions are all equally
    important to winning.
    
    To Start a Game:
        1. Create a lobby with !resistance lobby
        2. This lobby can be joined by up to 10 players using "!join resistance" in the channel the lobby was created
        3. Once a lobby has accumulated at least 5 players the game can be started with !resistance start
        
    At any time a lobby can be cancelled with "!resistance cancel"
    Games can only be cancelled and started by the lobby creator
    "!resistance players" can be used to see players in the current lobby or game
    ```""")

    @resistance.command()
    async def lobby(self, ctx):
        """Create a lobby in a channel for a new game of Resistance. Requires between 5 and 10 players to start"""
        game = dict(state=0, players={ctx.author: 0}, owner=ctx.author)
        if ctx.channel in self.games:
            await ctx.send("There is already a lobby or game going in this channel!")
            return
        await ctx.send("Starting a lobby!")
        self.games[ctx.channel] = game
        while self.games[ctx.channel]["state"] == 0:
            try:
                _msg = await ctx.bot.wait_for("message",
                                              check=self.waitlobby("!join resistance", ctx.channel),
                                              timeout=10)
            except asyncio.TimeoutError:
                continue
            game["players"][_msg.author] = 0
            await ctx.send(f"{_msg.author} has joined the game!")
            if len(game["players"]) >= 10:
                await ctx.send("This game has hit its max capacity! `!resistance start` in this channel to begin!")
            await asyncio.sleep(10)

        if self.games[ctx.channel]["state"] == 2:
            del self.games[ctx.channel]

    @resistance.command()
    async def cancel(self, ctx):
        """Cancel the lobby currently in the channel"""
        if ctx.channel not in self.games:
            await ctx.send("No game has been prepared!")
            return

        game = self.games[ctx.channel]
        if game["owner"] != ctx.author:
            await ctx.send("Only the lobby owner may cancel the game!")
            return

        self.games[ctx.channel]["state"] = 2
        await ctx.send("Game cancelled!")

    @resistance.command()
    async def players(self, ctx):
        """See which players are participating in the game or are in the lobby"""
        if ctx.channel not in self.games:
            await ctx.send("There is no game or lobby currently running to check players for!")
            return
        await ctx.send("Current players are {}".format(", ".join(self.games[ctx.channel]["players"])))

    @resistance.command()
    @commands.has_any_role("Bot Mod", "Bot Admin")
    async def start(self, ctx):
        """Start a game of Resistance with the players in the current lobby for the channel. Requires lobby to have 5-10 players"""
        if ctx.channel not in self.games:
            await ctx.send("No game has been prepared!")
            return

        game = self.games[ctx.channel]
        if game["owner"] != ctx.author:
            await ctx.send("Only the lobby owner may start the game!")
            return

        if len(game["players"]) < 5:
            await ctx.send("This game requires at least 5 people! Wait for more!")
            return

        if game["state"] != 0:
            await ctx.send("This game is already in progress or has been cancelled!")
            return

        game["state"] = 1

        np = {}
        nspies = ceil(len(game["players"]) / 3)
        spies = sample(list(game["players"]), nspies)
        for player in game["players"]:
            role = int(player in spies)
            np[player] = role
            if role == 0:
                await player.send("You are a rebel (good guy)!")
            else:
                await player.send(
                    "You are a spy! Your comrades are {}".format(", ".join(str(m) for m in spies if m != player)))

        waiting_on = []

        def waitdm(user, command):
            def inner(message):
                if message.author.id == user.id and isinstance(message.channel, discord.DMChannel):
                    return True
                return False

            return inner

        def waituser(user, command):
            def inner(message):
                if message.author.id == user.id and ctx.channel == message.channel and message.content.startswith(
                        command):
                    return True
                return False

            return inner

        def waitany(command):
            def inner(message):
                if message.author in waiting_on and ctx.channel == message.channel and message.content.startswith(
                        command):
                    return True
                return False

            return inner

        def waitanydm(command):
            def inner(message):
                if message.author in waiting_on and isinstance(message.channel,
                                                               discord.DMChannel) and message.content.startswith(
                    command):
                    return True
                return False

            return inner

        game["players"] = np
        await ctx.send("The game begins with 1 minute of discussion.")
        # await asyncio.sleep(60)

        failed_votes = 0
        results = []
        while True:
            waiting_on = list(game["players"].keys())
            leader = choice(list(game["players"]))

            await ctx.send(f"The current leader is {leader}! The leader will decide with `!choose"
                           " @Player1 @Player2 ... etc` who will be selected. After which voting will"
                           " take place until all players have decided whether they `!vote approve` or "
                           "`!vote reject` the proposed players. If not all players have decided anyone"
                           f" may change his vote. The leader may pick {mission_chart[len(game['players'])][len(results)]}")

            while True:
                _msg = await ctx.bot.wait_for("message", check=waituser(leader, "!choose"))
                mplayers = mission_chart[len(game["players"])][len(results)]
                players = _msg.content[8:].strip().split(" ")
                if len(players) != mplayers:
                    await ctx.send(f"You need to choose {mplayers}! You only chose {len(players)}")
                    continue
                splayers = []
                ct = False
                for player in players:
                    id = player.strip("<").strip("@").strip(">").strip("!")
                    if not id.isdigit():
                        print(id)
                        await ctx.send("Invalid syntax! Use mentions!")
                        ct = True

                    user = discord.utils.get(game["players"], id=int(id))
                    if user is None:
                        await ctx.send(f"{user} isn't playing!")
                        ct = True

                    splayers.append(user)

                if ct:
                    continue

                break

            await ctx.send("{} has chosen {}!".format(leader, ", ".join(str(x) for x in splayers)))

            votes = {}
            while len(game["players"]) > len(votes):
                _msg = await ctx.bot.wait_for("message", check=waitany("!vote "))
                if _msg.content[6:].strip() == "approve":
                    votes[_msg.author] = 1
                    await ctx.send(f"{_msg.author} has approved this mission!")
                elif _msg.content[6:].strip() == "reject":
                    votes[_msg.author] = 0
                    await ctx.send(f"{_msg.author} has rejected this mission!")
                else:
                    await ctx.send("That is not a valid vote!")

            await ctx.send("The vote has finished!")
            approvals = sum(votes.values())
            rejections = len(votes) - approvals

            if approvals > rejections:
                await ctx.send(f"The vote has passed ({approvals}/{len(votes)}! The team shall proceed!")
            else:
                failed_votes += 1
                await ctx.send(f"The vote has failed ({approvals}/{len(votes)}! The next leader shall be chosen!")
                await ctx.send(f"You have chosen not to pass the vote {failed_votes}/5 times!")
                if failed_votes >= 5:
                    await ctx.send("5 leadership votes have failed! The spies win!")
                    del self.games[ctx.channel]
                    return
                continue

            await ctx.send("All going on the mission cast your votes! DM the bot with either `!mission succeed` or "
                           "`!mission fail`!")

            votes = {}
            while len(game["players"]) > len(votes):
                _msg = await ctx.bot.wait_for("message", check=waitanydm("!mission "))
                if _msg.content[8:].strip() == "succeed":
                    votes[_msg.author] = 0
                    await _msg.author.send("You have voted to try to make this mission succeed")
                elif _msg.content[8:].strip() == "fail" and game["players"][_msg.author] == 0:
                    await ctx.send("You cannot vote for the mission to fail if you are a rebel! (Are you trying to "
                                   "throw the game?!)")
                elif _msg.content[8:].strip() == "fail":
                    votes[_msg.author] = 1
                    await _msg.author.send("You have voted to fail this mission!")
                else:
                    await _msg.author.send("That is not a valid vote!")

            res = sum(votes.values())
            if res:
                await ctx.send(f"The mission failed with {res} fail cards and {len(votes) - res} success cards!")
                results.append(1)
            else:
                await ctx.send(f"The mission was a success!")
                results.append(0)

            fails = sum(results)
            if fails >= 3:
                await ctx.send("The spies have sabotaged 3 missions successfully! The spies win!")
                return
            elif (5 - fails) >= 3:
                await ctx.send("The rebels have successfully launched 3 missions! The rebels win!")
                return

    @commands.command(hidden=True)
    @commands.is_owner()
    async def logout(self, ctx):
        await ctx.send("Logging out")
        await ctx.bot.logout()

    @commands.command()
    async def join(self, ctx, *, args):
        pass
