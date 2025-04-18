# leaderboard/urls.py
from django.urls import path
from .views import  LeaderboardView, UserLeaderboardStatusView

urlpatterns = [
    path('', LeaderboardView.as_view(), name='leaderboard'),
    path('my-status/', UserLeaderboardStatusView.as_view(), name='user-leaderboard-status'),
    
]