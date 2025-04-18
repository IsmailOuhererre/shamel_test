# In a new migration file (e.g., 0002_create_geospatial_index.py)
from django.db import migrations

def create_geospatial_index(apps, schema_editor):
    # Using raw MongoDB command
    from djongo import connection
    db = connection.get_db()
    db.classrooms_classroom.create_index(
        [("location", "2dsphere")],
        name="location_2dsphere"
    )

class Migration(migrations.Migration):
    dependencies = [
        ('classrooms', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_geospatial_index),
    ]