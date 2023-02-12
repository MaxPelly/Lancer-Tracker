# A discord bot for managing Manna in a Lancer game
#     Copyright (C) 2021  Max Pelly

#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.

#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see https://www.gnu.org/licenses/.

import discord
from discord.ext import commands
import logging
import typing
from threading import Lock
from Player import Player


import requests
from lxml import etree as ET
import configparser
from os.path import exists

def update_config(config, config_file):
    with open(config_file, "w+") as cfg_file:
                config.write(cfg_file)

config = configparser.ConfigParser()
CONFIG_FILE = "bot_config.ini"
config.read(CONFIG_FILE)
config.lock = Lock()

if not exists(CONFIG_FILE):
    config.add_section("bot")
    update_config(config, CONFIG_FILE)


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)


bot.config = config
bot.CONFIG_FILE = CONFIG_FILE
bot.main_channel = config.getint("bot", "main_channel", fallback=None)
bot.gm_manna = config.getint("bot", "gm_manna", fallback=100)
bot.err = bot.on_command_error
handler = logging.FileHandler(filename="botlog.log", encoding="utf-8", mode='w')


bot.no_mech_error = f"You do not seem to have a mech. Run \"{bot.command_prefix}init <callsign>\" to create one."
bot.incorect_args_error = "This function rerquires input: "
bot.not_implemented_error = "Opps, im not here yet!"


async def check_channel_set(ctx):
    """
    Check if the bot channel has been set. If not reply with a relevant error message
    """
    if not bot.main_channel:
        names = [channel.name for channel in ctx.guild.channels if type(channel) == discord.channel.TextChannel]
        name_text = "\n- ".join(names)
        await ctx.reply(f"Using this function requires setting the bot channel. Please reply \"{bot.command_prefix}set_channel <channel name>\".\nAvaliable channels:\n- {name_text}", delete_after=10)
        return False
    return True


async def check_channel_or_dm(ctx):
    """
    Check if the bot has been called in its designated channel or a DM
    """
    if (ctx.channel.id == bot.main_channel) or (type(ctx.channel) == discord.channel.DMChannel):
        return True

    await check_channel_set(ctx)
    return False


@bot.command(alias=['r'])
async def relay(
    ctx
):
    """
    Mystery Biscuits
    """
    message = await ctx.send("Fetching show lists.")
    version_one = set(requests.get("https://www.relay.fm/robots.txt").text.split("\n"))
    version_two = set(requests.get("https://www.relay.fm/robots.txt").text.split("\n"))

    repeats = version_one.intersection(version_two)
    urls = ["https://www.relay.fm" + i.split(" ")[1] + ".rss" for i in repeats if "feed" in i]
    await message.edit(content=f"{len(urls)} shows found. Processing.")

    out = ""
    for url in urls:
        feed = ET.fromstring(requests.get(url).text)
        title = feed.find("channel").find("title").text
        out += f"{title}: {url}"
        await message.edit(content=out)
        out += "\n"

@bot.command(aliases=['sc'])
async def set_channel(
    ctx,
    *,
    channel: str = commands.parameter(
        description="The desired channel."
    )
):
    """
    Set the channel to bot will listen in and share information in.
    """

    await ctx.reply(channel)
    if len(channel) == 0:
        await ctx.reply(f"{bot.incorect_args_error} please provide the name of the channel")
        return
    names = {channel.name: channel.id for channel in ctx.guild.channels if type(channel) == discord.channel.TextChannel}
    if channel_id := names.get(channel, False):
        await ctx.reply(f"Setting Channel to {channel}")
        bot.main_channel = channel_id
        channel = bot.get_channel(channel_id)
        with bot.config.lock:
            bot.config.set("bot", "main_channel", str(channel_id))
            update_config(bot.config, bot.CONFIG_FILE)
        await channel.send('This is the new bot channel', delete_after=10)
    else:
        channel_names = "\n- ".join(names.keys())
        await ctx.reply(f"\"{channel}\" does not appear to be a valid channel.\nAvaliable channels are:\n- {channel_names}")


@bot.command(aliases=['i'])
@commands.check(check_channel_or_dm)
async def init(
    ctx,
    manna: typing.Optional[int] = commands.parameter(
        default=0,
        description="Starting Manna"
    ),
    *,
    callsign: str = commands.parameter(
        description="Your desired callsign."
    )
):
    """
    Create a record.
    Yes the order is mad but otherwise callsigns can't have spaces.
    Callsigns can not start with a number followed by a space.
    If you really want this use a dummy here then run update_callsign
    """

    if mech := Player.get_player_by_name(ctx.author.id):
        await ctx.reply(f"You already have a mech: {mech}. Run \"{bot.command_prefix}delete\" to remove it.")
        return

    new_player = Player(name=ctx.author.id, callsign=callsign, manna=manna)
    await ctx.reply(f"Created new mech.\n{new_player}")


@bot.command()
@commands.check(check_channel_or_dm)
async def delete(ctx):
    """
    Delete your record. WARNING IREVERSIBLE.
    """

    if mech := Player.get_player_by_name(ctx.author.id):
        callsign = mech.get("callsign")
        mech.delete(confirm=True)
        await ctx.reply(f"{callsign} deleted.")
    else:
        await ctx.reply(bot.no_mech_error)


@bot.command(aliases=['c'])
@commands.check(check_channel_or_dm)
async def check(ctx):
    """
    Check your balance and purchases
    """
    if mech := Player.get_player_by_name(ctx.author.id):
        await ctx.reply(f"{mech}")
    else:
        await ctx.reply(bot.no_mech_error)


@bot.command(aliases=['uc'])
@commands.check(check_channel_or_dm)
async def update_callsign(
    ctx,
    *,
    callsign: str = commands.parameter(
        description="The new callsign"
    ),
):
    """
    Update your callsign.
    Can now include any mix of numbers and letters.
    """
    if mech := Player.get_player_by_name(ctx.author.id):
        mech.update_callsign(callsign)
        await ctx.reply(f"{mech}")
    else:
        await ctx.reply(bot.no_mech_error)


@bot.command(aliases=['b'])
@commands.dm_only()
async def buy(
    ctx,
    *,
    items: str = commands.parameter(
        description="list of what you want to buy."
    )
):
    """
    Spend some Manna.
    Options are l[icence], ta[lent] or tr[aining].
    """

    if mech := Player.get_player_by_name(ctx.author.id):
        reply = []
        for request in items.split(" "):
            if request[0] == "l":
                sucess, res = mech.buy_licence()
                if sucess:
                    reply.append("Sucesfully bought a licence.")
                else:
                    reply.append("Unable to buy a licence. {res}")

            elif len(request) > 1 and request[:2] == "ta":
                sucess, res = mech.buy_talent()
                if sucess:
                    reply.append("Sucesfully bought a talent.")
                else:
                    reply.append(f"Unable to buy a talent. {res}")

            elif len(request) > 1 and request[:2] == "tr":
                sucess, res = mech.buy_training()
                if sucess:
                    reply.append("Sucesfully bought training.")
                else:
                    reply.append(f"Unable to buy training. {res}")
            else:
                reply.append(f"I dont know what to do with {request}. Options are: l[icence], ta[lent] or tr[aining]")
        reply.append("")
        reply.append(str(mech))
        await ctx.reply("\n".join(reply))
    else:
        await ctx.reply(bot.no_mech_error)


@bot.command(aliases=['cm'])
@commands.dm_only()
@commands.check(check_channel_set)
async def complete_mission(
    ctx,
    manna: int = commands.parameter(
        description="Amount of Manna to award"
    ),
    players: commands.Greedy[discord.Member] = commands.parameter(
        description="List of @<player>"
    )
):
    """
    Awards Manna for a mission where you were the GM.
    Includes GM Manna.
    """
    if gm_mech := Player.get_player_by_name(ctx.author.id):
        await ctx.send(f"giving {bot.gm_manna} Manna to {ctx.author.name}")
        gm_mech.give_manna(bot.gm_manna)
    else:
        await ctx.send(f"Unable to award GM Manna. {bot.no_mech_error}")

    for player in players:
        if mech := Player.get_player_by_name(player.id):
            await ctx.send(f"giving {manna} Manna to {player.name}")
            mech.give_manna(manna)
        else:
            # await player.send(f"You completed a Lancer mission that should have awarded {manna} Manna! {bot.no_mech_error} Add ;{manna} after your callsign to include this missed manna.")
            await ctx.send(f"Unable to award {player.name} Manna.")

    players = ", ".join(player.mention for player in players)
    channel = bot.get_channel(bot.main_channel)
    await channel.send(f"A game run by {ctx.author.mention} completed attended by {players}. {manna} Manna is awarded.")


@bot.command(aliases=['pcm'])
@commands.dm_only()
@commands.check(check_channel_set)
async def player_complete_mission(
    ctx,
    manna: int = commands.parameter(
        description="Amount of Manna to award"
    ),
    gm: discord.Member = commands.parameter(
        description="@<the GM>"
    ),
    players: commands.Greedy[discord.Member] = commands.parameter(
        description="List of @<player>"
    )
):
    """
    Awards Manna for a mission where you were a player.
    Includes GM manna.
    No need to @ yourself.
    """
    if gm_mech := Player.get_player_by_name(gm.id):
        await ctx.send(f"giving 100 Manna to {gm.name}")
        gm_mech.give_manna(100)
    else:
        await ctx.send(f"Unable to award GM Manna to {gm.name}.")

    for player in players:
        if mech := Player.get_player_by_name(player.id):
            await ctx.send(f"giving {manna} Manna to {player.name}")
            mech.give_manna(manna)
        else:
            # await player.send(f"You completed a Lancer mission that should have awarded {manna} Manna! {bot.no_mech_error} Add ;{manna} after your callsign to include this missed manna.")
            await ctx.send(f"Unable to award {player.name} Manna. {bot.no_mech_error}")

    player_names = ", ".join(player.mention for player in players)
    if ctx.author not in players:
        if your_mech := Player.get_player_by_name(ctx.author.id):
            await ctx.send(f"giving {manna} Manna to {ctx.author.name}")
            your_mech.give_manna(manna)
        else:
            await ctx.send(f"Unable to award you Manna. {bot.no_mech_error}")

        player_names += f", {ctx.author.mention}"

    channel = bot.get_channel(bot.main_channel)
    await channel.send(f"A mission by {gm.mention} was sucesfully completed by {player_names}. {manna} Manna is awarded.")


@bot.command(aliases=['p'])
@commands.check(check_channel_or_dm)
async def ping(ctx):
    """
    pong

    :param args: some args
    """
    await ctx.reply('pong')


@bot.event
async def on_command_error(ctx, error):
    """
    Custom error messaging
    """
    if isinstance(error, commands.BadArgument):
        await ctx.reply(f"Incorect Arguments. Please check the \"{bot.command_prefix}help\" command for more information.", delete_after=10)
    elif isinstance(error, commands.CommandNotFound):
        await ctx.reply(f"Command not found. Please check the \"{bot.command_prefix}help\" command for a list a commands.", delete_after=10)
    elif isinstance(error, commands.PrivateMessageOnly):
        await ctx.reply("This command is only avaliable in DMs to keep things clean.", delete_after=10)
    else:
        await ctx.reply(f"{error}", delete_after=30)

    # THERE HAS GOT TO BE A BETTER WAY TO DO THIS!!!!
    await bot.err(ctx, error)

bot.run(config.get("bot", "token"), log_handler=handler)
