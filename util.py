# ----- Summary utils ----- #

def get_winner_names(summary):
    return [ player["name"] for player in list(filter(lambda player: player["winner"], summary.get_players())) ]

def get_player_names(summary):
    return [ player["name"] for player in summary.get_players() ]

# ----- Sheets utils ----- #

def get_cell_updated_string(winner, current_val, max_score):
    if current_val == "":
        return "1-0" if winner else "0-1"     

    current_val_split = current_val.split("-")
    p1Score = int(current_val_split[0])
    p2Score = int(current_val_split[1])

    if winner:
        return (str(p1Score + 1) if p1Score < max_score else p1Score) + "-" + current_val_split[1]
    else:
        return current_val_split[0] + "-" + str((p2Score + 1) if p2Score < max_score else p2Score)

def update_cell(sheet, cell, value):
    sheet.update_cell(cell[0], cell[1], value)