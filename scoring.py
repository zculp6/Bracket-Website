# Map each round to its "next" rounds (winners advance here)
_ROUND_TO_NEXT = {
    "west_r64": ["west_r32"], "west_r32": ["west_s16"], "west_s16": ["west_e8"], "west_e8": ["ff_left"],
    "south_r64": ["south_r32"], "south_r32": ["south_s16"], "south_s16": ["south_e8"], "south_e8": ["ff_left"],
    "east_r64": ["east_r32"], "east_r32": ["east_s16"], "east_s16": ["east_e8"], "east_e8": ["ff_right"],
    "midwest_r64": ["midwest_r32"], "midwest_r32": ["midwest_s16"], "midwest_s16": ["midwest_e8"], "midwest_e8": ["ff_right"],
    "ff_left": ["championship"], "ff_right": ["championship"],
    "championship": ["champion"],
}


def _extract_user_winners(user_bracket: dict, round_id: str) -> list:
    """
    Get list of winner names for a round.
    Handles both formats:
      - New: list of {seed, name} in pairs; winner = team that appears in next round
      - Old: list of winner name strings
    """
    picks = user_bracket.get(round_id, [])
    if not picks:
        return []

    # Old format: list of strings (winner names)
    if isinstance(picks[0], str):
        return [p for p in picks if p]

    # New format: list of {seed, name} in pairs
    next_ids = _ROUND_TO_NEXT.get(round_id, [])
    next_names = set()
    for nid in next_ids:
        if nid == "champion":
            champ = user_bracket.get("champion")
            if champ:
                next_names.add(champ)
        else:
            for t in user_bracket.get(nid, []) or []:
                name = t.get("name") if isinstance(t, dict) else t
                if name:
                    next_names.add(name)

    winners = []
    for i in range(0, len(picks), 2):
        if i + 1 >= len(picks):
            break
        t1, t2 = picks[i], picks[i + 1]
        n1 = t1.get("name", "") if isinstance(t1, dict) else str(t1)
        n2 = t2.get("name", "") if isinstance(t2, dict) else str(t2)
        winners.append(n1 if n1 in next_names else (n2 if n2 in next_names else None))
    return winners


def score_bracket(user_bracket: dict, true_results: dict) -> int:
    """
    Standard March Madness point scoring:

      Round of 64   (r64)         →  1 pt per correct pick
      Round of 32   (r32)         →  2 pts
      Sweet 16      (s16)         →  4 pts
      Elite 8       (e8)          →  8 pts
      Final Four    (ff_left/right)→ 16 pts
      Championship                → 32 pts

    user_bracket can be:
      - New format: { "west_r64": [{seed,name},{seed,name},...], ... } (pairs for display)
      - Old format: { "west_r64": ["Florida", "Auburn", ...], ... } (winner names)

    true_results: { "west_r64": ["Florida", "Auburn", ...], ... }
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

        user_picks = _extract_user_winners(user_bracket, round_id)

        for i, true_winner in enumerate(true_winners):
            if true_winner is None:
                continue
            if i < len(user_picks) and user_picks[i] == true_winner:
                score += pts

    return score