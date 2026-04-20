from django.shortcuts import render

from .services.api import (
    get_home_leaders,
    get_leaderboard_sections,
    get_mlb_news,
    get_player_gamelog,
    get_player_with_stats,
    get_standings_grouped,
    get_team,
    get_roster,
    get_team_leaders_from_roster,
    get_team_news,
    get_teams_grouped_for_dropdown,
)


def home(request):
    """Render the home page with standings, news, and top league leader cards."""
    context = {
        "standings": get_standings_grouped(),
        "news": get_mlb_news(),
        "leaders": get_home_leaders(),
        "teams": get_teams_grouped_for_dropdown(),
    }
    return render(request, "home.html", context)


def standings_page(request):
    """Render the standalone standings page."""
    context = {
        "standings": get_standings_grouped(),
        "teams": get_teams_grouped_for_dropdown(),
    }
    return render(request, "standings.html", context)


def team_page(request, team_id):
    """
    Render one team page.

    The roster API already includes season stats in the hydrated person object,
    so we split players into hitters vs pitchers here and shape the rows for the
    two tables used in the template.
    """
    team = get_team(team_id)
    roster = get_roster(team_id)
    news = get_team_news(team_id)
    leaders = get_team_leaders_from_roster(roster)

    hitters = []
    pitchers = []

    for player in roster:
        person = player.get("person", {})
        stats = person.get("stats", [])
        stat_block = {}

        if stats and stats[0].get("splits"):
            stat_block = stats[0]["splits"][0].get("stat", {})

        pos = player.get("position", {}).get("abbreviation", "")
        player_id = person.get("id")

        row = {
            "id": player_id,
            "name": person.get("fullName"),
            "position": pos,
            "jersey": player.get("jerseyNumber", ""),
            "headshot": f"https://content.mlb.com/images/headshots/current/60x60/{player_id}@2x.png",
            "age": person.get("currentAge", ""),
        }

        if pos in ["SP", "RP", "P"]:
            bf = stat_block.get("battersFaced", "")
            so = stat_block.get("strikeOuts", "")
            bb = stat_block.get("baseOnBalls", "")

            so_pct = ""
            bb_pct = ""
            if bf:
                try:
                    so_pct = f"{round((float(so) / float(bf)) * 100, 1)}%"
                    bb_pct = f"{round((float(bb) / float(bf)) * 100, 1)}%"
                except Exception:
                    pass

            row.update({
                "g": stat_block.get("gamesPlayed", ""),
                "ip": stat_block.get("inningsPitched", ""),
                "bf": bf,
                "era": stat_block.get("era", ""),
                "so": so,
                "bb": bb,
                "so_pct": so_pct,
                "bb_pct": bb_pct,
                "ops_allowed": stat_block.get("ops", ""),
            })
            pitchers.append(row)
        else:
            pa = stat_block.get("plateAppearances", "")
            so = stat_block.get("strikeOuts", "")
            bb = stat_block.get("baseOnBalls", "")

            so_pct = ""
            bb_pct = ""
            if pa:
                try:
                    so_pct = f"{round((float(so) / float(pa)) * 100, 1)}%"
                    bb_pct = f"{round((float(bb) / float(pa)) * 100, 1)}%"
                except Exception:
                    pass

            row.update({
                "bats": person.get("batSide", {}).get("code", ""),
                "throws": person.get("pitchHand", {}).get("code", ""),
                "pa": pa,
                "h": stat_block.get("hits", ""),
                "doubles": stat_block.get("doubles", ""),
                "triples": stat_block.get("triples", ""),
                "hr": stat_block.get("homeRuns", ""),
                "sb": stat_block.get("stolenBases", ""),
                "so_pct": so_pct,
                "bb_pct": bb_pct,
                "avg": stat_block.get("avg", ""),
                "obp": stat_block.get("obp", ""),
                "ops": stat_block.get("ops", ""),
            })
            hitters.append(row)

    context = {
        "team": team,
        "team_logo": f"https://www.mlbstatic.com/team-logos/{team_id}.svg",
        "hitters": hitters,
        "pitchers": pitchers,
        "news": news,
        "leaders": leaders,
        "teams": get_teams_grouped_for_dropdown(),
    }
    return render(request, "team.html", context)


def player_page(request, player_id):
    """
    Render one player page.

    The player stats payload contains multiple stat blocks, so this view reshapes
    those splits into rows that the yearly stats table can render directly.
    """
    player = get_player_with_stats(player_id)
    if not player:
        return render(
            request,
            "player.html",
            {"player": None, "teams": get_teams_grouped_for_dropdown()},
        )

    primary_position = player.get("primaryPosition", {}).get("abbreviation", "")
    is_pitcher = primary_position in ["P", "SP", "RP"]

    gamelog_group = "pitching" if is_pitcher else "hitting"
    recent_games_raw = get_player_gamelog(player_id, gamelog_group)

    stat_rows = []

    for block in player.get("stats", []):
        group = block.get("group", {}).get("displayName", "").lower()
        stat_type = block.get("type", {}).get("displayName", "").lower()

        if is_pitcher and group != "pitching":
            continue
        if not is_pitcher and group != "hitting":
            continue

        for split in block.get("splits", []):
            stat = split.get("stat", {})
            team = split.get("team", {})
            season = split.get("season", "")
            season_label = season

            row_type = "normal"
            if "projected" in stat_type:
                row_type = "projected"
                season_label = f"{season} Projected"
            elif "career" in stat_type:
                row_type = "career"
                season_label = "Career"

            if is_pitcher:
                bf = stat.get("battersFaced", "")
                so = stat.get("strikeOuts", "")
                bb = stat.get("baseOnBalls", "")

                so_pct = ""
                bb_pct = ""
                if bf:
                    try:
                        so_pct = f"{round((float(so) / float(bf)) * 100, 1)}%"
                        bb_pct = f"{round((float(bb) / float(bf)) * 100, 1)}%"
                    except Exception:
                        pass

                stat_rows.append({
                    "row_type": row_type,
                    "season_label": season_label,
                    "team_name": team.get("name", ""),
                    "team_id": team.get("id"),
                    "team_logo": f"https://www.mlbstatic.com/team-logos/{team.get('id')}.svg" if team.get("id") else "",
                    "g": stat.get("gamesPlayed", ""),
                    "gs": stat.get("gamesStarted", ""),
                    "bf": bf,
                    "ip": stat.get("inningsPitched", ""),
                    "era": stat.get("era", ""),
                    "whip": stat.get("whip", ""),
                    "so": so,
                    "bb": bb,
                    "so_pct": so_pct,
                    "bb_pct": bb_pct,
                    "so9": stat.get("strikeoutsPer9Inn", ""),
                    "bb9": stat.get("walksPer9Inn", ""),
                    "sobb": stat.get("strikeoutWalkRatio", ""),
                    "hr": stat.get("homeRuns", ""),
                    "hr9": stat.get("homeRunsPer9", ""),
                })
            else:
                pa = stat.get("plateAppearances", "")
                so = stat.get("strikeOuts", "")
                bb = stat.get("baseOnBalls", "")

                so_pct = ""
                bb_pct = ""
                if pa:
                    try:
                        so_pct = f"{round((float(so) / float(pa)) * 100, 1)}%"
                        bb_pct = f"{round((float(bb) / float(pa)) * 100, 1)}%"
                    except Exception:
                        pass

                stat_rows.append({
                    "row_type": row_type,
                    "season_label": season_label,
                    "team_name": team.get("name", ""),
                    "team_id": team.get("id"),
                    "team_logo": f"https://www.mlbstatic.com/team-logos/{team.get('id')}.svg" if team.get("id") else "",
                    "g": stat.get("gamesPlayed", ""),
                    "pa": pa,
                    "h": stat.get("hits", ""),
                    "r": stat.get("runs", ""),
                    "doubles": stat.get("doubles", ""),
                    "triples": stat.get("triples", ""),
                    "hr": stat.get("homeRuns", ""),
                    "avg": stat.get("avg", ""),
                    "obp": stat.get("obp", ""),
                    "slg": stat.get("slg", ""),
                    "ops": stat.get("ops", ""),
                    "babip": stat.get("babip", ""),
                    "so": so,
                    "bb": bb,
                    "so_pct": so_pct,
                    "bb_pct": bb_pct,
                    "sb": stat.get("stolenBases", ""),
                    "cs": stat.get("caughtStealing", ""),
                })

    recent_games = []
    for game in recent_games_raw[:7]:
        stat = game.get("stat", {})
        recent_games.append({
            "date": game.get("date", ""),
            "opponent": game.get("opponent", {}),
            "summary": game.get("game", {}).get("gameNumber", ""),
            "ip": stat.get("inningsPitched", ""),
            "so": stat.get("strikeOuts", ""),
            "bb": stat.get("baseOnBalls", ""),
            "era": stat.get("era", ""),
            "ab": stat.get("atBats", ""),
            "h": stat.get("hits", ""),
            "hr": stat.get("homeRuns", ""),
            "rbi": stat.get("rbi", ""),
        })

    context = {
        "player": player,
        "headshot": f"https://content.mlb.com/images/headshots/current/60x60/{player_id}@2x.png",
        "recent_games": recent_games,
        "is_pitcher": is_pitcher,
        "stat_rows": stat_rows,
        "teams": get_teams_grouped_for_dropdown(),
    }
    return render(request, "player.html", context)


def leaders_page(request):
    """Render the leaderboard page."""
    context = {
        "leader_sections": get_leaderboard_sections(),
        "teams": get_teams_grouped_for_dropdown(),
    }
    return render(request, "leaders.html", context)
