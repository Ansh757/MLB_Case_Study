import re
from datetime import datetime

import feedparser
import requests

from .cache import get_cached, set_cached

BASE_URL = "https://statsapi.mlb.com/api/v1"
MLB_NEWS_RSS = "https://www.mlb.com/feeds/news/rss.xml"

TEAM_SLUGS = {
    141: "bluejays",
    109: "diamondbacks",
    144: "braves",
    110: "orioles",
    111: "redsox",
    112: "cubs",
    113: "reds",
    114: "guardians",
    115: "rockies",
    116: "tigers",
    117: "astros",
    118: "royals",
    108: "angels",
    119: "dodgers",
    146: "marlins",
    158: "brewers",
    142: "twins",
    121: "mets",
    147: "yankees",
    133: "athletics",
    143: "phillies",
    134: "pirates",
    135: "padres",
    137: "giants",
    136: "mariners",
    138: "cardinals",
    139: "rays",
    140: "rangers",
    145: "whitesox",
    120: "nationals",
}

DIVISION_MAP = {
    200: "AL West",
    201: "AL East",
    202: "AL Central",
    203: "NL West",
    204: "NL East",
    205: "NL Central",
}


def fetch_json(endpoint, params=None):
    """Send a GET request to the MLB StatsAPI and return the JSON body."""
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def fetch_with_cache(cache_key, max_age_minutes, fetch_fn):
    """
    Read from cache first, otherwise fetch fresh data and store it.

    This keeps the views fast without changing how the rest of the code calls
    the service functions.
    """
    cached = get_cached(cache_key, max_age_minutes=max_age_minutes)
    if cached is not None:
        return cached

    data = fetch_fn()
    set_cached(cache_key, data)
    return data


def team_logo_url(team_id):
    """Return the MLB SVG logo URL for a team."""
    return f"https://www.mlbstatic.com/team-logos/{team_id}.svg"


def player_headshot_url(player_id):
    """Return the MLB headshot URL for a player."""
    return f"https://content.mlb.com/images/headshots/current/60x60/{player_id}@2x.png"


def safe_num(value):
    """Convert a value to float, defaulting to 0.0 for blank/missing data."""
    try:
        return float(value)
    except Exception:
        return 0.0


def category_label(category):
    """Map StatsAPI category keys to the labels used in the UI."""
    labels = {
        "homeRuns": "Home Runs",
        "ops": "OPS",
        "strikeOuts": "Strikeouts",
        "era": "ERA",
        "avg": "AVG",
        "rbi": "RBI",
        "hits": "Hits",
        "whip": "WHIP",
    }
    return labels.get(category, category)


# ---------------------------
# Teams / standings
# ---------------------------

def get_teams():
    """Return all MLB teams."""
    return fetch_with_cache(
        "teams_all",
        24 * 60,
        lambda: fetch_json("/teams", {"sportId": 1}).get("teams", []),
    )


def get_team(team_id):
    """Return one team by ID."""
    return fetch_with_cache(
        f"team_{team_id}",
        6 * 60,
        lambda: fetch_json(f"/teams/{team_id}").get("teams", [None])[0],
    )


def get_team_abbrev_map():
    """Build a quick lookup table for team abbreviation/name by team ID."""
    teams = get_teams()
    return {
        team["id"]: {
            "abbrev": team.get("abbreviation", ""),
            "team_name": team.get("teamName", ""),
            "name": team.get("name", ""),
        }
        for team in teams
        if team.get("id")
    }


def get_standings_raw():
    """Return the raw league standings payload."""
    return fetch_with_cache(
        "standings_all",
        15,
        lambda: fetch_json("/standings", {"leagueId": "103,104"}),
    )


def get_standings_grouped():
    """
    Reshape the standings response into a template-friendly structure.

    The API returns nested split records for things like last 10, home/away,
    one-run games, etc. This function flattens that down into the exact fields
    the standings templates need.
    """
    data = get_standings_raw()
    records = data.get("records", [])
    team_map = get_team_abbrev_map()
    grouped = []

    for record in records:
        division_id = record.get("division", {}).get("id")
        division_name = DIVISION_MAP.get(division_id, "Unknown")
        teams = []

        for team_record in record.get("teamRecords", []):
            split_records = team_record.get("records", {}).get("splitRecords", [])
            split_map = {item.get("type"): item for item in split_records}

            last_ten = split_map.get("lastTen", {})
            one_run = split_map.get("oneRun", {})
            extra_inning = split_map.get("extraInning", {})
            home = split_map.get("home", {})
            away = split_map.get("away", {})

            team_obj = team_record.get("team", {})
            team_id = team_obj.get("id")
            team_info = team_map.get(team_id, {})

            teams.append({
                "team_id": team_id,
                "name": team_obj.get("name", ""),
                "abbrev": team_info.get("abbrev") or team_obj.get("name", ""),
                "team_name": team_info.get("team_name") or team_obj.get("name", ""),
                "logo": team_logo_url(team_id) if team_id else "",
                "wins": team_record.get("wins", ""),
                "losses": team_record.get("losses", ""),
                "pct": team_record.get("winningPercentage", ""),
                "gb": team_record.get("gamesBack", ""),
                "diff": team_record.get("runDifferential", ""),
                "l10": f"{last_ten.get('wins', 0)}-{last_ten.get('losses', 0)}",
                "home_pct": home.get("pct", ""),
                "away_pct": away.get("pct", ""),
                "one_run_pct": one_run.get("pct", ""),
                "extra_inning_pct": extra_inning.get("pct", ""),
            })

        grouped.append({
            "division_name": division_name,
            "teams": teams,
        })

    # This keeps divisions in the exact UI order used across the site.
    order = ["AL East", "NL East", "AL Central", "NL Central", "AL West", "NL West"]
    grouped.sort(key=lambda row: order.index(row["division_name"]) if row["division_name"] in order else 999)
    return grouped


def get_teams_grouped_for_dropdown():
    """
    Return teams ordered for the navbar dropdown.

    We keep the dropdown flat in HTML, so the ordering is handled here instead.
    """
    teams = get_teams()

    grouped = {}
    for team in teams:
        division_id = team.get("division", {}).get("id")
        grouped.setdefault(division_id, []).append(team)

    ordered = []
    for division_id in [201, 202, 200, 204, 205, 203]:
        division_teams = grouped.get(division_id, [])
        division_teams.sort(key=lambda team: team.get("abbreviation", ""))
        ordered.extend(division_teams)

    return ordered


# ---------------------------
# News
# ---------------------------

def extract_og_image(article_url):
    """
    Fallback image extractor for RSS items that do not expose an image directly.

    Many feeds do not consistently populate media_content/media_thumbnail, so
    this checks the article page itself for an og:image tag.
    """
    try:
        response = requests.get(article_url, timeout=10)
        response.raise_for_status()
        html = response.text

        match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if match:
            return match.group(1)

        match = re.search(r'<meta content="([^"]+)" property="og:image"', html)
        if match:
            return match.group(1)

    except Exception:
        return ""

    return ""


def parse_feed_entries(entries):
    """
    Convert raw RSS entries into a clean list used by the templates.

    Image extraction is intentionally layered because different RSS items expose
    images in different places.
    """
    results = []

    for entry in entries:
        image_url = ""

        media = entry.get("media_content", [])
        if media and isinstance(media, list):
            image_url = media[0].get("url", "")

        if not image_url:
            media_thumb = entry.get("media_thumbnail", [])
            if media_thumb and isinstance(media_thumb, list):
                image_url = media_thumb[0].get("url", "")

        if not image_url:
            for link in entry.get("links", []):
                if "image" in link.get("type", ""):
                    image_url = link.get("href", "")
                    break

        if not image_url:
            summary = entry.get("summary", "")
            match = re.search(r'<img[^>]+src="([^"]+)"', summary)
            if match:
                image_url = match.group(1)

        if not image_url:
            image_url = extract_og_image(entry.get("link", ""))

        results.append({
            "title": entry.get("title", ""),
            "author": entry.get("author", "MLB.com"),
            "link": entry.get("link", "#"),
            "published": entry.get("published", ""),
            "image_url": image_url,
        })

    return results


def get_mlb_news(limit=4):
    """Return MLB-wide news items for the home page."""
    return fetch_with_cache(
        f"mlb_news_{limit}",
        30,
        lambda: parse_feed_entries(feedparser.parse(MLB_NEWS_RSS).entries[:limit]),
    )


def get_team_news(team_id, limit=4):
    """Return RSS news for a specific team."""
    slug = TEAM_SLUGS.get(team_id)
    if not slug:
        return []

    rss_url = f"https://www.mlb.com/{slug}/feeds/news/rss.xml"
    return fetch_with_cache(
        f"team_news_{team_id}_{limit}",
        30,
        lambda: parse_feed_entries(feedparser.parse(rss_url).entries[:limit]),
    )


# ---------------------------
# Leaders
# ---------------------------

def get_stat_leaders(category, limit=5):
    """Return league leaders for one stat category."""

    def _fetch():
        data = fetch_json(
            "/stats/leaders",
            {
                "leaderCategories": category,
                "statGroup": "hitting" if category in ["homeRuns", "ops"] else "pitching",
                "limit": limit,
                "season": datetime.now().year,
            },
        )

        leaders = data.get("leagueLeaders", [])
        if not leaders:
            return {"label": category_label(category), "leaders": []}

        leaders_list = leaders[0].get("leaders", [])
        leader_rows = []

        for item in leaders_list:
            person = item.get("person", {})
            team = item.get("team", {})

            leader_rows.append({
                "player_id": person.get("id"),
                "player_name": person.get("fullName"),
                "team_name": team.get("name", ""),
                "team_abbrev": team.get("abbreviation", ""),
                "team_id": team.get("id"),
                "team_logo": team_logo_url(team.get("id")) if team.get("id") else "",
                "value": item.get("value"),
                "headshot": player_headshot_url(person.get("id")),
            })

        return {
            "label": category_label(category),
            "leaders": leader_rows,
        }

    return fetch_with_cache(f"leaders_{category}_{limit}", 15, _fetch)


def get_leaderboard_sections():
    """Return the four leaderboard sections shown on the leaders page."""
    categories = ["homeRuns", "strikeOuts", "ops", "era"]
    return [get_stat_leaders(category, limit=5) for category in categories]


def get_home_leaders():
    """Return one leader card per category for the home page."""
    cards = []

    for category in ["homeRuns", "ops", "strikeOuts", "era"]:
        section = get_stat_leaders(category, limit=1)
        if section and section.get("leaders"):
            top = section["leaders"][0]
            if not top.get("player_id"):
                continue

            cards.append({
                "label": section["label"],
                "player_id": top.get("player_id"),
                "player_name": top.get("player_name"),
                "team_abbrev": top.get("team_abbrev"),
                "value": top.get("value"),
                "headshot": top.get("headshot"),
            })

    return cards


def get_team_leaders_from_roster(roster):
    """
    Build team-specific leaders from the active roster stats.

    ERA is the only category here where lower is better, so it needs separate
    handling from the HR / OPS / strikeout leader lookups.
    """
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

        base_player = {
            "player_id": player_id,
            "player_name": person.get("fullName", ""),
            "team_abbrev": person.get("currentTeam", {}).get("abbreviation", ""),
            "headshot": player_headshot_url(player_id),
        }

        if pos in ["SP", "RP", "P"]:
            pitchers.append({
                **base_player,
                "era": safe_num(stat_block.get("era")),
                "strikeOuts": safe_num(stat_block.get("strikeOuts")),
            })
        else:
            hitters.append({
                **base_player,
                "homeRuns": safe_num(stat_block.get("homeRuns")),
                "ops": safe_num(stat_block.get("ops")),
            })

    hr_leader = max(hitters, key=lambda row: row["homeRuns"], default=None)
    ops_leader = max(hitters, key=lambda row: row["ops"], default=None)
    so_leader = max(pitchers, key=lambda row: row["strikeOuts"], default=None)

    valid_pitchers = [row for row in pitchers if row["era"] > 0]
    era_leader = min(valid_pitchers, key=lambda row: row["era"], default=None)

    leaders = []

    if hr_leader:
        leaders.append({
            "label": "Home Runs",
            "player_id": hr_leader["player_id"],
            "player_name": hr_leader["player_name"],
            "team_abbrev": hr_leader["team_abbrev"],
            "headshot": hr_leader["headshot"],
            "value": int(hr_leader["homeRuns"]),
        })

    if ops_leader:
        leaders.append({
            "label": "OPS",
            "player_id": ops_leader["player_id"],
            "player_name": ops_leader["player_name"],
            "team_abbrev": ops_leader["team_abbrev"],
            "headshot": ops_leader["headshot"],
            "value": f"{ops_leader['ops']:.3f}",
        })

    if so_leader:
        leaders.append({
            "label": "Strikeouts",
            "player_id": so_leader["player_id"],
            "player_name": so_leader["player_name"],
            "team_abbrev": so_leader["team_abbrev"],
            "headshot": so_leader["headshot"],
            "value": int(so_leader["strikeOuts"]),
        })

    if era_leader:
        leaders.append({
            "label": "ERA",
            "player_id": era_leader["player_id"],
            "player_name": era_leader["player_name"],
            "team_abbrev": era_leader["team_abbrev"],
            "headshot": era_leader["headshot"],
            "value": f"{era_leader['era']:.2f}",
        })

    return leaders


# ---------------------------
# Players
# ---------------------------

def get_roster(team_id):
    """
    Return the active roster for a team.

    The hydrate part is important here because it tells the MLB API to include
    each player's current season stats in the same response. That saves us from
    making extra API calls for every player on the roster.
    """
    return fetch_with_cache(
        f"roster_{team_id}",
        60,
        lambda: fetch_json(
            f"/teams/{team_id}/roster/Active",
            {"hydrate": "person(stats(type=season))"},
        ).get("roster", []),
    )

def get_player(player_id):
    """Return one player by ID."""
    data = fetch_json(f"/people/{player_id}")
    people = data.get("people", [])
    return people[0] if people else None


def get_player_with_stats(player_id):
    """Return one player with year-by-year and career stats."""
    return fetch_with_cache(
        f"player_stats_{player_id}",
        180,
        lambda: (
            fetch_json(
                f"/people/{player_id}",
                {
                    "hydrate": "stats(type=[yearByYear,career],group=[hitting,pitching],sportId=1)"
                },
            ).get("people", [None])[0]
        ),
    )


def get_player_gamelog(player_id, group="hitting"):
    """Return up to seven recent game log entries for a player."""

    def _fetch():
        data = fetch_json(
            f"/people/{player_id}",
            {"hydrate": f"stats(type=[gameLog],group=[{group}])"},
        )
        people = data.get("people", [])
        if not people:
            return []

        stats = people[0].get("stats", [])
        if not stats:
            return []

        return stats[0].get("splits", [])[:7]

    return fetch_with_cache(f"player_gamelog_{player_id}_{group}", 15, _fetch)
