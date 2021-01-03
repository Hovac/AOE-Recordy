import os
import sys
import requests
import random
import discord
import asyncio
import gspread
import util
import pickledb
import team
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
    'google-credentials.json',
    scopes=scopes
) 
g_client = gspread.authorize(credentials)
googleSheetLink="1p04CIWAJHLUA3wSj9Q80mp8MONzqHhlePPqnF7UdizI"

civCode = ["Britons", "Franks", "Goths", "Teutons", "Japanese", "Chinese", "Byzantines", "Persian", "Saracens", "Turks", "Vikings", "Mongols", "Celts", "Spanish", "Aztecs", "Mayans", "Huns", "Koreans", "Italians", "Indians", "Incas", "Magyars", "Slav", "Portuguese", "Ethiopians", "Malians", "Berbers", "Khmer", "Malay", "Burmese", "Vietnamese", "Bulgarians", "Tatars", "Cumans", "Lithuanians", "burgundians", "sicilians"]

""" rndLine = [
    "Who said mangoes grow on trees? I saw them coming from siege workshops, let me check if you grew some", 
    "Match didn't start in post-imp, so give me time to watch you get there and I’ll tell you how bad you did soon",
    "Wait for me, I’m an old bot, it takes me a bit of time to watch your long game", 
    "It takes a few seconds for me to watch your game, I have to stop and re-watch every miss-click you make",
    "Dude, give me a minute to process your game, it made me fall asleep a few times",
    "error 404: EPIC MANGO SHOT not found. Deleting your account...", 
    "are you sure you want others to watch this game?! I'll edit it as much as I can before FARM-MAN casts it", 
    "so many bad plays, and I still keep counting them", 
    "yo, got an error, can't move past this awful push you made, wait until I fix myself", 
    "I am actually kidnapped, forced to watch replays and report score, please send help befo-"
] """
rndColor = ["yaml", "fix", "css"] #many more to come

MAX_SCORE = 2

teamMappings = team.TeamMappings()

@client.event
async def on_message(msg):
    if msg.author == client.user:
            return

    if msg.attachments:
        if msg.attachments[0].url.endswith("aoe2record"):
            #await respond_message(msg)
            r = requests.get(msg.attachments[0].url)
            open("currentDLGame.aoe2record", "wb").write(r.content)
            summary = {}
            with open("currentDLGame.aoe2record", "rb") as data:
                summary = Summary(data)
            
            await asyncio.gather(asyncio.ensure_future(format_and_send_summary(msg, summary)), asyncio.ensure_future(upload_to_sheets(msg, summary)))
        else:
            await msg.delete()
            await msg.channel.send("Only Age of Empires 2 replay files allowed in this channel!")

#async def respond_message(msg):
#    random.seed()
#    replyMsg = "```" + rndColor[random.randint(0,len(rndColor)-1)] + "\n" + rndLine[random.randint(0, len(rndLine)-1)] + "\n```"
#    await msg.channel.send(replyMsg)

async def upload_to_sheets(msg, summary):
    sh = g_client.open_by_key(googleSheetLink)
    HTH_sheet = sh.worksheet("Results")

    winningTeam = teamMappings.findTeamNameByPlayer(util.get_winner_names(summary)[0])
    losingTeam = teamMappings.findTeamNameByPlayer(util.get_loser_names(summary)[0])

    winningTeamCell = HTH_sheet.findall(winningTeam)
    losingTeamCell = HTH_sheet.findall(losingTeam)
    
    try:
        winningScoreCell = [winningTeamCell[1].row, losingTeamCell[0].col]
        winningUpdatedVal = util.get_cell_updated_string(True, HTH_sheet.cell(winningScoreCell[0], winningScoreCell[1]).value, MAX_SCORE)

        losingScoreCell = [losingTeamCell[1].row, winningTeamCell[0].col]
        losingUpdatedVal = util.get_cell_updated_string(False, HTH_sheet.cell(losingScoreCell[0], losingScoreCell[1]).value, MAX_SCORE)
        
        # don't update scores until we know there are no format issue to avoid cases where some updates are made, others fail, and the scores are left out of whack
        util.update_cell(HTH_sheet, winningScoreCell, winningUpdatedVal)
        util.update_cell(HTH_sheet, losingScoreCell, losingUpdatedVal)
    except IndexError:
        #await msg.channel.send("Error updating sheets for players ```{}``` Please make sure those players names are the exact same in both the row and col.".format(player_names))
        print("Error updating sheets for players ```{}``` Please make sure teams have the correct players/player names.".format(util.get_player_names(summary)))
    except ValueError:
        #await msg.channel.send("Error updating sheets for players ```{}``` Could not parse their score. Please make sure that their current scores have no values errors (should look like 1-0).".format(player_names))
        print("Error updating sheets for players ```{}``` Could not parse their score. Please make sure that their current scores have no values errors (should look like 1-0).".format(util.get_player_names(summary)))

async def format_and_send_summary(msg, summary):
    allPlayers = summary.get_players()
    pMap = summary.get_map()
    winnerNames = []
    winnerCiv = []
    loserNames = []
    loserCiv = []
    wTeam = ""
    lTeam = ""
    wTeamName = ""
    lTeamName = ""

    for x in allPlayers:
        if x["winner"]:
            winnerNames.append(x["name"])
            winnerCiv.append(civCode[x["civilization"]-1])
            if wTeamName == "":
                wTeamName = teamMappings.findTeamNameByPlayer(x["name"])
        else:
            loserNames.append(x["name"])
            loserCiv.append(civCode[x["civilization"]-1])
            if lTeamName == "":
                lTeamName = teamMappings.findTeamNameByPlayer(x["name"])
    for w in range(len(winnerNames)):
        wTeam += winnerNames[w] + " - " + winnerCiv[w] + "\n"
        lTeam += loserNames[w] + " - " + loserCiv[w] + "\n"

    embed = discord.Embed(title = "Map: ||" + str(pMap["name"]) + "||")
    embed.add_field(name = "Winner:", value = "||**{}**||".format(wTeamName), inline= False)
    embed.add_field(name = wTeamName, value = wTeam, inline = True)
    embed.add_field(name = "VS", value = "   -   \n"*len(winnerNames), inline = True)
    embed.add_field(name = lTeamName, value = lTeam, inline = True)

    await msg.channel.send(embed = embed)

client.run(TOKEN)