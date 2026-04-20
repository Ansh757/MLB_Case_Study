from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path("standings/", views.standings_page, name="standings"),
    path("teams/<int:team_id>/", views.team_page, name="team_page"),
    path("players/<int:player_id>/", views.player_page, name="player_page"),
    path("leaders/", views.leaders_page, name="leaders_page"),
]
