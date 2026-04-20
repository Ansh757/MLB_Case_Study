# Homebase MLB Case Study

A Django-based MLB stats website that pulls live data from the MLB StatsAPI and MLB news feeds, then renders it into a
clean multi-page web app.

## Overview

This project was built as an MLB case study focused on:

- fetching live baseball data from external APIs
- transforming raw API responses into template-friendly structures
- displaying standings, team stats, player stats, news, and leaderboards
- keeping the UI consistent across multiple pages

The app uses Django for server-side rendering, Bootstrap 5 for layout support, and custom CSS for styling.

## Features

### Home Page

- league standings by division
- MLB news cards
- season leader cards for:
    - Home Runs
    - OPS
    - Strikeouts
    - ERA

### Standings Page

- expanded standings tables
- division-by-division view
- includes win/loss record, last 10, run differential, home/away, one-run, and extra innings stats

### Team Page

- team header and logo
- hitter stats table
- pitcher stats table
- team-specific news
- team leaders based on the selected roster

### Player Page

- player header with basic metadata
- yearly stats table
- recent games table
- supports both hitters and pitchers

### Leaders Page

- top 5 leaderboard tables for:
    - Home Runs
    - Strikeouts
    - OPS
    - ERA

## Tech Stack

- Python
- Django
- SQLite
- Bootstrap 5
- Font Awesome
- MLB StatsAPI
- MLB RSS news feeds

## Project Structure

```text
config/
├── baseball/              # Django project settings
├── mlb/                   # Main app
│   ├── services/          # API + cache helpers
│   ├── templates/         # HTML templates
│   ├── static/            # CSS + images
│   ├── views.py           # Page views
│   └── models.py          # Cache model
├── manage.py
└── db.sqlite3

```

## API/Data Sources

### MLB StatsAPI

Used for:
- teams
- standings
- rosters 
- player stats 
- player game logs 
- stat leaders

## MLB RSS Feeds

Used for:
- league-wide MLB news 
- team-specific news

## Caching

The app includes a lightweight cache layer using SQLite.

Cached responses are stored in an `ApiCache model` with:
- a unique cache key 
- JSON response data 
- an updated_at timestamp

This helps reduce repeated API calls and improves page load speed for frequently accessed endpoints like:
- standings 
- teams 
- news 
- player stats 
- leaderboards

## Styling

The UI is built with:
- Bootstrap 5 for layout and responsiveness 
- a custom external stylesheet for project-specific styling 
- team logos and player headshots pulled from MLB asset URLs

## Setup Instructions

- Clone the repo
```commandline
git clone https://github.com/Ansh757/MLB_Case_Study.git
```

- Create and Activate Virtual Env
```commandline
python3 -m venv .venv
source .venv/bin/activate
```

- Install Dependencies 
```commandline
pip install -r requirements.txt
```
- Cd into Config
```commandline
cd config
```

- Run Migrations
```commandline
python manage.py makemigrations
python manage.py migrate
```

- Run server
```commandline
python manage.py runserver
```

- Open
```commandline
http://127.0.0.1:8000/
```


## Design Notes

A few implementation decisions I made:
- Used server-side rendering with Django templates instead of building a separate frontend 
- Kept the app API-first rather than fully normalizing all MLB data into relational tables 
- Used a cache model to reduce repeat API calls while keeping the architecture simple 
- Transformed API responses in service functions so templates stay cleaner and easier to read

## Future Improvements 
- Add stronger cache invalidation rules by endpoint 
- Improve responsive behaviour for wide stats tables on small screens 
- Add search/filtering for players and teams 
- Add loading/error states for external data fetches 
- Add automated tests for service-layer parsing and transformations

## Notes

This project is intended as a case study/demo app and focuses on clean data flow, readable Django structure, and
practical API integration rather than full production hardening.
