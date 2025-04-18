from rest_framework import serializers

class LeaderboardUserSerializer(serializers.Serializer):
    _id = serializers.CharField()
    user_id = serializers.CharField()
    user_name = serializers.CharField()
    points = serializers.IntegerField()
    rank = serializers.IntegerField()
    last_updated = serializers.DateTimeField()
    medal = serializers.CharField(required=False)

class LeaderboardSerializer(serializers.Serializer):
    students = LeaderboardUserSerializer(many=True)
    teachers = LeaderboardUserSerializer(many=True)
    schools = LeaderboardUserSerializer(many=True)

class UserLeaderboardStatusSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    user_name = serializers.CharField()
    points = serializers.IntegerField()
    rank = serializers.IntegerField()
    role = serializers.CharField()
    is_on_leaderboard = serializers.BooleanField()