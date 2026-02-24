def score_bracket(user_bracket, true_bracket):
    """
    Very simple scoring:
    +1 for every correct game pick
    Replace with your real system later.
    """

    score = 0

    for round_name in true_bracket:
        for game_index in range(len(true_bracket[round_name])):
            if user_bracket[round_name][game_index] == true_bracket[round_name][game_index]:
                score += 1

    return score