# ----- Summary utils ----- #

def get_winner_names(summary):
    return [ player["name"] for player in list(filter(lambda player: player["winner"], summary.get_players())) ]

def get_player_names(summary):
    return [ player["name"] for player in summary.get_players() ]

# ----- Sheets utils ----- #

def get_cell_updated_string(winner, current_val):
    current_val_split = current_val.split("-")
    if winner:
        return str(int(current_val_split[0]) + 1) + "-" + current_val_split[1]
    else:
        return current_val_split[0] + "-" + str(int(current_val_split[1]) + 1)

def update_cell(sheet, cell, value):
    sheet.update_cell(cell[0], cell[1], value)