class MongoDBRouter:
    """
    Routes models to PostgreSQL or MongoDB based on their app_label.
    """
    
    mongo_apps = ['classrooms', 'courses', 'leaderboard', 'contracts',]
    
    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.mongo_apps:
            return 'mongodb'
        return 'default'

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.mongo_apps:
            return 'mongodb'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between User and MongoDB models"""
        # Allow relations if one model is User and the other is a MongoDB model
        if (obj1._meta.model_name == 'user' and obj2._meta.app_label in self.mongo_apps) or \
           (obj2._meta.model_name == 'user' and obj1._meta.app_label in self.mongo_apps):
            return True
        # Allow relations between models in the same database
        if obj1._meta.app_label in self.mongo_apps and obj2._meta.app_label in self.mongo_apps:
            return True
        if obj1._meta.app_label not in self.mongo_apps and obj2._meta.app_label not in self.mongo_apps:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Don't attempt to run Django migrations on MongoDB"""
        if app_label in self.mongo_apps:
            return False  # Disable Django migrations for MongoDB apps
        return db == 'default'