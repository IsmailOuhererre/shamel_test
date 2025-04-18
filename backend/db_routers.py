class MongoDBRouter:
    """
    Routes models to PostgreSQL or MongoDB based on their app_label.
    Explicitly prevents authentication from using MongoDB.
    """
    
    # Apps that should use MongoDB
    mongo_apps = ['classrooms', 'courses', 'leaderboard', 'contracts', 'chat']
    
    # Apps that must NEVER use MongoDB
    postgres_only_apps = ['authentication', 'admin', 'auth', 'sessions', 'contenttypes']
    
    def db_for_read(self, model, **hints):
        """Send reads to MongoDB only for allowed apps"""
        if model._meta.app_label in self.postgres_only_apps:
            return 'default'
        if model._meta.app_label in self.mongo_apps:
            return 'mongodb'
        return 'default'

    def db_for_write(self, model, **hints):
        """Send writes to MongoDB only for allowed apps"""
        if model._meta.app_label in self.postgres_only_apps:
            return 'default'
        if model._meta.app_label in self.mongo_apps:
            return 'mongodb'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations only if:
        1. Both models are in the same database
        2. Special case for User model relations
        """
        db1 = 'mongodb' if obj1._meta.app_label in self.mongo_apps else 'default'
        db2 = 'mongodb' if obj2._meta.app_label in self.mongo_apps else 'default'
        
        if db1 == db2:
            return True
            
        # Special case: Allow relations between User and MongoDB models
        user_model = 'user'  # Match your AUTH_USER_MODEL's model_name
        if (obj1._meta.model_name == user_model and db2 == 'mongodb') or \
           (obj2._meta.model_name == user_model and db1 == 'mongodb'):
            return True
            
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Migration rules:
        - Never allow migrations to MongoDB
        - Only allow migrations to default DB for non-MongoDB apps
        """
        if app_label in self.postgres_only_apps:
            return db == 'default'
            
        if app_label in self.mongo_apps:
            return False
            
        return db == 'default'