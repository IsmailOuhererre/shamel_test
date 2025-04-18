# backend/apps/leaderboard/management/commands/test_leaderboard.py
from django.core.management.base import BaseCommand
from backend.apps.authentication.models import Student, Teacher, School
from backend.apps.leaderboard.utils import update_leaderboard

class Command(BaseCommand):
    help = 'Test leaderboard initialization'

    def handle(self, *args, **options):
        # Test student update
        student = Student.objects.first()
        if student:
            update_leaderboard(student.user, student.points, 'student')
            self.stdout.write(f"Updated student: {student.user.email}")
        
        # Verify MongoDB entry
        from pymongo import MongoClient
        from django.conf import settings
        client = MongoClient(settings.DATABASES['mongodb']['CLIENT']['host'])
        db = client[settings.DATABASES['mongodb']['NAME']]
        entry = db.leaderboard.find_one({"user_id": str(student.user.id)})
        self.stdout.write(f"MongoDB entry: {entry}")