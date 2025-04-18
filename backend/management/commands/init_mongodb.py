from django.core.management.base import BaseCommand
from django.db import connections

class Command(BaseCommand):
    help = 'Initialize MongoDB collections and indexes'

    def handle(self, *args, **options):
        db = connections['mongodb'].connection
        
        collections = {
            'classrooms_classroom': [
                {'keys': [('location', '2dsphere')], 'name': 'location_2dsphere'}
            ],
            'leaderboard': [
                {'keys': [('user_id', 1)], 'name': 'user_id_index'}
            ]
        }

        for collection_name, indexes in collections.items():
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
                self.stdout.write(f'Created collection: {collection_name}')
            
            existing_indexes = {idx['name'] for idx in db[collection_name].list_indexes()}
            
            for index in indexes:
                if index['name'] not in existing_indexes:
                    db[collection_name].create_index(**index)
                    self.stdout.write(f'Created index {index["name"]} on {collection_name}')