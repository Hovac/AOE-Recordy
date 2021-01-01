import os
import sys
import requests
import random
import discord
import asyncio
import gspread
import util
from dotenv import load_dotenv
from mgz.summary import Summary
from google.oauth2.service_account import Credentials

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = discord.Client()

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
credentials = Credentials.from_service_account_file(
    'credentials.json',
    scopes=scopes
)
g_client = gspread.authorize(credentials)
stats_sheet_key="1xgwnOon91pglyU8E0Wu_NOVM4Dwr3yOy3zBjB_YFJ_8"

civCode = ["Britons", "Franks", "Goths", "Teutons", "Japanese", "Chinese", "Byzantines", "Persian", "Saracens", "Turks", "Vikings", "Mongols", "Celts", "Spanish", "Aztecs", "Mayans", "Huns", "Koreans", "Italians", "Indians", "Incas", "Magyars", "Slav", "Portuguese", "Ethiopians", "Malians", "Berbers", "Khmer", "Malay", "Burmese", "Vietnamese", "Bulgarians", "Tatars", "Cumans", "Lithuanians", "burgundians", "sicilians"]

rndLine = [
    "Who said mangoes grow on trees? I saw them coming from siege workshops, let me check if you grew some", 
    "Match didn't start in post-imp, so give me time to watch you get there and I’ll tell you how bad you did soon",
    "Wait for me, I’m an old bot, it takes me a bit of time to watch your long game", 
    "It takes a few seconds for me to watch your game, I have to stop and re-watch every miss-click you make",
    "Dude, give me a minute to process your game, it made me fall asleep a few times",
    "error 404: EPIC MANGO SHOT not found. Deleting your account...", 
    "are you sure you want others to watch this game?! I'll edit it as much as I can before FARM-MAN casts it", 
    "so many bad plays, and I still keep counting them", 
    "yo, got an error, can't move past this awful push you made, wait until I fix myself", 
    "I am actually kidnapped, forced to watch replays and report score, please send help befo-",
    ""
]
rndColor = ["yaml", "fix", "css"] #many more to come

@client.event
async def on_message(msg):
    if msg.author == client.user:
        return

    if msg.attachments:
        if msg.attachments[0].url.endswith("aoe2record"):
            random.seed()
            replyMsg = "```" + rndColor[random.randint(0,len(rndColor)-1)] + "\n" + rndLine[random.randint(0, len(rndLine)-1)] + "\n```"
            await msg.channel.send(replyMsg)

            r = requests.get(msg.attachments[0].url)
            open("currentDLGame.aoe2record", "wb").write(r.content)

            summary = {}
            with open("currentDLGame.aoe2record", "rb") as data:
                summary = Summary(data)
            
            await asyncio.gather(asyncio.ensure_future(upload_to_sheets(msg, summary)), asyncio.ensure_future(format_and_send_summary(msg, summary)))
        else:
            await msg.delete()
            await msg.channel.send("Only Age of Empires 2 replay files allowed in this channel!")
    

async def upload_to_sheets(msg, summary):
    sh = g_client.open_by_key(stats_sheet_key)
    HTH_sheet = sh.worksheet("Head-to-Head")

    winners_names = util.get_winner_names(summary)
    player_names = util.get_player_names(summary)

    player_1_cells = HTH_sheet.findall(player_names[0])
    player_2_cells = HTH_sheet.findall(player_names[1])
    
    try:
        player_1_score_cell = [player_1_cells[1].row, player_2_cells[0].col]
        p1_updated_value = util.get_cell_updated_string(player_names[0] in winners_names, HTH_sheet.cell(player_1_score_cell[0], player_1_score_cell[1]).value)

        player_2_score_cell = [player_2_cells[1].row, player_1_cells[0].col]
        p2_updated_value = util.get_cell_updated_string(player_names[1] in winners_names, HTH_sheet.cell(player_2_score_cell[0], player_2_score_cell[1]).value)
        
        # don't update scores until we know there are no format issue to avoid cases where some updates are made, others fail, and the scores are left out of whack
        util.update_cell(HTH_sheet, player_1_score_cell, p1_updated_value)
        util.update_cell(HTH_sheet, player_2_score_cell, p2_updated_value)
    except IndexError:
        await msg.channel.send("Error updating sheets for players ```{}``` Please make sure those players names are the exact same in both the row and col.".format(player_names))
    except ValueError:
        await msg.channel.send("Error updating sheets for players ```{}``` Could not parse their score. Please make sure that their current scores have no values errors (should look like 1-0).".format(player_names))

async def format_and_send_summary(msg, summary):
    allPlayers = summary.get_players()
    pMap = summary.get_map()
    winnerNames = []
    winnerCiv = []
    loserNames = []
    loserCiv = []
    wTeam = ""
    lTeam = ""

    for x in allPlayers:
        if x["winner"]:
            winnerNames.append(x["name"])
            winnerCiv.append(civCode[x["civilization"]-1])
        else:
            loserNames.append(x["name"])
            loserCiv.append(civCode[x["civilization"]-1])
    for w in range(len(winnerNames)):
        wTeam += winnerNames[w] + " - " + winnerCiv[w] + "\n"
        lTeam += loserNames[w] + " - " + loserCiv[w] + "\n"

    embed = discord.Embed(title = "Map: ||" + str(pMap["name"]) + "||")
    if random.randint(0,1) == 1:
        embed.add_field(name = "Winner:", value = "||**Team 1**||", inline= False)
        embed.add_field(name = "Team 1", value = wTeam, inline = True)
        embed.add_field(name = "VS", value = "   -   \n"*len(winnerNames), inline = True)
        embed.add_field(name = "Team 2", value = lTeam, inline = True)
    else:
        embed.add_field(name = "Winner:", value = "||**Team 2**||", inline= False)
        embed.add_field(name = "Team 1", value = lTeam, inline = True)
        embed.add_field(name = "VS", value = "   -   \n"*len(winnerNames), inline = True)
        embed.add_field(name = "Team 2", value = wTeam, inline = True)
    await msg.channel.send(embed = embed)



client.run(TOKEN)