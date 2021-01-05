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
import constants

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

MAX_SCORE = 2

teamMappings = team.TeamMappings()

@client.event
async def on_message(msg):
    if msg.author == client.user:
            return

    if msg.attachments:
        if msg.attachments[0].url.endswith("aoe2record"):
            r = requests.get(msg.attachments[0].url)
            open("currentDLGame.aoe2record", "wb").write(r.content)
            summary = {}
            with open("currentDLGame.aoe2record", "rb") as data:
                summary = Summary(data)
            await asyncio.gather(asyncio.ensure_future(format_and_send_summary(msg, summary)), asyncio.ensure_future(upload_to_sheets(msg, summary)))
        else:
            await msg.delete()
            await msg.channel.send("Only Age of Empires 2 replay files allowed in this channel!")

async def upload_to_sheets(msg, summary):
    #Hacky way of differentiating between 1v1 and teamgames without changing much of team and util libs
    if(len(summary.get_players()) > 2):
        sh = g_client.open_by_key(constants.League2v2SheetLink)
        HTH_sheet = sh.worksheet(msg.channel.category.name.lower())
        winningTeam = teamMappings.findTeamNameByPlayer(util.get_winner_names(summary)[0])
        losingTeam = teamMappings.findTeamNameByPlayer(util.get_loser_names(summary)[0])
    else:
        sh = g_client.open_by_key(constants.League1v1SheetLink)
        #gSheets tab names are named after discord categories they're in
        HTH_sheet = sh.worksheet(msg.channel.category.name.lower())
        #if first player isn't the winner, obviously the second one is
        if(summary.get_players()[0]["winner"]):
            winningTeam = summary.get_players()[0]["name"]
            losingTeam = summary.get_players()[1]["name"]
        else:
            winningTeam = summary.get_players()[1]["name"]
            losingTeam = summary.get_players()[0]["name"]

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
        print("Error updating sheets for players ```{}``` Please make sure teams have the correct players/player names.".format(util.get_player_names(summary)))
    except ValueError:
        print("Error updating sheets for players ```{}``` Could not parse their score. Please make sure that their current scores have no values errors (should look like 1-0).".format(util.get_player_names(summary)))

async def format_and_send_summary(msg, summary):
    allPlayers = summary.get_players()
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
            winnerCiv.append(constants.civilizations[x["civilization"]-1])
            if(len(allPlayers) > 2):
                if wTeamName == "":
                    wTeamName = teamMappings.findTeamNameByPlayer(x["name"])
            else:
                wTeamName = "Team 1"
        else:
            loserNames.append(x["name"])
            loserCiv.append(constants.civilizations[x["civilization"]-1])
            if(len(allPlayers) > 2):
                if lTeamName == "":
                    lTeamName = teamMappings.findTeamNameByPlayer(x["name"])
            else:
                lTeamName = "Team 2"
    for w in range(len(winnerNames)):
        wTeam += winnerNames[w] + " - " + winnerCiv[w] + "\n"
        lTeam += loserNames[w] + " - " + loserCiv[w] + "\n"

    embed = discord.Embed(title = "Map: ||" + str(summary.get_map()["name"]) + "||")
    embed.add_field(name = "Winner:", value = "||**{}**||".format(wTeamName), inline= False)
    embed.add_field(name = wTeamName, value = wTeam, inline = True)
    embed.add_field(name = "VS", value = "   -   \n"*len(winnerNames), inline = True)
    embed.add_field(name = lTeamName, value = lTeam, inline = True)

    await msg.channel.send(embed = embed)

client.run(TOKEN)