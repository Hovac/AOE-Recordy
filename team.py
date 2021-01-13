# Operations around syncing the player/team mapping in google sheets to the local db files as well as retrieving those mappings
# If the sheet has not changed since the last sync has ran, retrieval of team names will be faster and we wont use up google sheet api call quotas
# Note: The db structure is not optimized for the main retrieval of team name from player name (mapping is currently team name -> player names)

from enum import Enum
import pickledb
import gspread
import json
from google.oauth2.service_account import Credentials
import constants

TEAM_DICT_KEY = "Teams"
UNKNOWN_TEAM = "Unknown Team"

# players -> a list of player, len = 3 if there is a sub
# group -> 'A' through 'F'
class Team(object):
    def __init__(self, players, group):
        self.players = players
        self.group = group

# Cols:
# Pos,Player(team name), Points, Wins, Losses, No-Shows, Played, Remaining, Group
class TeamStats(object):
    def __init__(self, position, name, points, wins, losses, noShows, played, remaining, group):
        self.position = position
        self.name = name
        self.points = points
        self.wins = wins
        self.losses = losses
        self.noShows = noShows
        self.played = played
        self.remaining = remaining
        self.group = group
    
    def __str__(self):
        return "position: {}, name: {}, points: {}, wins: {}, lossses: {}, noShows: {}, played: {}, remaining: {}, group: {}".format(self.position, self.name, self.points, self.wins, self.losses, self.noShows, self.played, self.remaining, self.group)

class TeamMappings(object): 

    scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
    ]
    credentials = Credentials.from_service_account_file(
        'google-credentials.json',
        scopes=scopes
    )
    
    def __init__(self):
        self.teamsDB = pickledb.load('teams.db', True)
        self.g_client = gspread.authorize(self.credentials)
        self.teamSheet = self.g_client.open_by_key(constants.teamNamesSheetLink).worksheet("Player_Team_Mapping")
        self.teamStandings = self.g_client.open_by_key(constants.League2v2SheetLink).worksheet(constants.League2v2SheetsName)
        self._syncWithSheets()
    
    def findTeamNameByPlayer(self, playerName):
        name = self._interalFindTeamNameByPlayer(playerName)
        return name if name != None else UNKNOWN_TEAM  

    def findTeamNameByPlayerAndSync(self, playerName):
        name = self._interalFindTeamNameByPlayer(playerName)
        if name == None:
            # sync and try again
            self._syncWithSheets()
            name = self._interalFindTeamNameByPlayer(playerName)            
            return name if name != None else UNKNOWN_TEAM    
        else:
            return name

    def findTeamStatsByPlayerName(self, playerName):
        teamName = self.findTeamNameByPlayer(playerName)
        
        if teamName != UNKNOWN_TEAM:
            teamNameCell = self.teamStandings.find(teamName)
            teamStatsRow = self.teamStandings.row_values(teamNameCell.row)            
            return TeamStats(teamStatsRow[0], teamStatsRow[1], teamStatsRow[2], teamStatsRow[3], teamStatsRow[4], teamStatsRow[5], teamStatsRow[6], teamStatsRow[7], teamStatsRow[8]) 

    # Due to the mapping in the db of team -> player (not the other way around) this is not optimized
    def _interalFindTeamNameByPlayer(self, playerName):
        for teamName in self.teamsDB.dgetall(TEAM_DICT_KEY):
            for player in json.loads(self.teamsDB.dget(TEAM_DICT_KEY, teamName))['players']:
                if playerName.upper() == player.upper():
                    return teamName

    # To be called during init as well as before any queries that need to be 100% up to date with sheets
    def _syncWithSheets(self):
        currentVals = self.teamSheet.get_all_values()
        if self._syncRequired(currentVals):
            self._performSync(currentVals)

    def _syncRequired(self, currentVals):
        if self.teamsDB.totalkeys() == 0:
            return True # brand new
        elif not self.teamsDB.exists(TEAM_DICT_KEY):
            return True # haven't added a team dict yet

        # team[0] - team name
        # team[1-3] - player names
        # team[4] - group
        for team in currentVals:
            # Filter out header
            if team[0].upper() != "teamName".upper():
                if not self.teamsDB.dexists(TEAM_DICT_KEY, team[0]):
                    return True # new team added or team name changed

                oldTeam = json.loads(self.teamsDB.dget(TEAM_DICT_KEY, team[0]))

                if oldTeam['group'] != team[4]:
                    return True # team group has changed
                
                index = 1
                for player in oldTeam['players']:
                    if player != team[index]:
                        return True # player name has changed or player order has changed
                    index += 1

                if team[3] != '' and len(oldTeam['players']) != 3:
                    return True # sub has been added

                if team[3] == '' and len(oldTeam['players']) == 3:
                    return True # sub has been removed

        return False # we have saved a synced yay!

    def _performSync(self, currentVals):
        # To avoid complication and due to small team sizes, just clear and sync all the teams if out of date
        if self.teamsDB.exists(TEAM_DICT_KEY):
            self.teamsDB.drem(TEAM_DICT_KEY)
        
        self.teamsDB.dcreate(TEAM_DICT_KEY)

        for team in currentVals:
            # Filter out header
            if team[0].upper() != "teamName".upper():
                # team[0] - team name
                # team[1-3] - player names
                # team[4] - group

                players = [team[1], team[2]]
                if team[3] != '':
                    players.append(team[3])
                    
                newTeam = json.dumps(Team(players, team[4]).__dict__)
                self.teamsDB.dadd(TEAM_DICT_KEY, [team[0], newTeam])