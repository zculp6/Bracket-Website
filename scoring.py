def score_bracket(user_bracket: dict, true_results: dict) -> int:
    """
    Standard March Madness point scoring:

      Round of 64   (r64)         →  1 pt per correct pick
      Round of 32   (r32)         →  2 pts
      Sweet 16      (s16)         →  4 pts
      Elite 8       (e8)          →  8 pts
      Final Four    (ff_left/right)→ 16 pts
      Championship                → 32 pts

    Both dicts share the same structure:
      { "west_r64": ["Florida", "Auburn", ...], "west_r32": [...], ..., "championship": [...] }

    Each list is ordered by slot: index 0 = game-1 winner, index 1 = game-2 winner, etc.
    A None in either list means no pick / result not yet entered.
    """

    ROUND_POINTS = {
        "r64":          1,
        "r32":          2,
        "s16":          4,
        "e8":           8,
        "ff_left":      16,
        "ff_right":     16,
        "championship": 32,
    }

    def _pts_for(round_id: str) -> int:
        for key, pts in ROUND_POINTS.items():
            if round_id == key or round_id.endswith("_" + key):
                return pts
        return 0

    score = 0

    for round_id, true_winners in true_results.items():
        if round_id == "champion":
            continue

        pts = _pts_for(round_id)
        if pts == 0:
            continue

        user_picks = user_bracket.get(round_id, [])

        for i, true_winner in enumerate(true_winners):
            if true_winner is None:
                continue
            if i < len(user_picks) and user_picks[i] == true_winner:
                score += pts

    return score