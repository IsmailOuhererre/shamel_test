from pymongo import MongoClient
from django.conf import settings
import logging
from datetime import datetime, timedelta
import pymongo
from pymongo import UpdateOne

from backend.apps.authentication import apps

logger = logging.getLogger(__name__)

def get_db_handle():
    """Get MongoDB database handle using settings configuration"""
    try:
        client = MongoClient(settings.DATABASES['mongodb']['CLIENT']['host'])
        return client[settings.DATABASES['mongodb']['NAME']]
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {str(e)}")
        raise

def update_leaderboard(user, points, role):
    """
    Update leaderboard entry for a user with verification
    """
    db = get_db_handle()
    collection = db['leaderboard']
    
    try:
        # First verify the points are different from current
        existing = collection.find_one({
            "user_id": str(user.id),
            "role": role
        })
        
        if existing and existing.get("points") == points:
            logger.info(f"No points change for {user.id}, skipping update")
            return True  # Consider no change as success
            
        user_data = {
            "user_id": str(user.id),
            "user_name": user.get_full_name() or user.username,
            "role": role,
            "points": points,
            "last_updated": datetime.utcnow()
        }
        
        result = collection.update_one(
            {"user_id": user_data["user_id"], "role": role},
            {"$set": user_data},
            upsert=True
        )
        
        logger.info(
            f"Leaderboard update for {user.id}: "
            f"Matched {result.matched_count}, "
            f"Modified {result.modified_count}, "
            f"Upserted {result.upserted_id}"
        )
        
        # Force immediate rank recalculation
        recalculate_ranks(role)
        
        return True
    except Exception as e:
        logger.error(f"Failed to update leaderboard: {str(e)}")
        return False
def recalculate_ranks(role):
    """Completely recalculate ranks for a specific role based on current points"""
    db = get_db_handle()
    collection = db['leaderboard']
    
    try:
        # Get all users of this role sorted properly
        users = list(collection.find({"role": role}).sort([
            ("points", pymongo.DESCENDING),
            ("last_updated", pymongo.ASCENDING)
        ]))
        
        # Update ranks in bulk
        bulk_operations = []
        for index, user in enumerate(users):
            bulk_operations.append(
                pymongo.UpdateOne(
                    {"_id": user["_id"]},
                    {"$set": {"rank": index + 1}}
                )
            )
        
        if bulk_operations:
            collection.bulk_write(bulk_operations)
            
    except Exception as e:
        logger.error(f"Failed to recalculate ranks: {str(e)}")
        raise

def check_and_assign_badges(user, points, role):
    """
    Check and assign badges based on points and achievements
    Args:
        user: User model instance
        points: Current user points
        role: User role
    """
    from .models import Badge
    
    try:
        # Get the profile based on role
        if role == 'student':
            profile = user.student_profile
        elif role == 'teacher':
            profile = user.teacher_profile
        elif role == 'school':
            profile = user.school_profile
        else:
            return
        
        # Initialize badges if not exists
        if not hasattr(profile, 'badges'):
            profile.badges = []
        
        # Check for point-based badges
        point_badges = Badge.objects.filter(
            points_required__lte=points,
            role_specific=role
        ).exclude(name__in=[b.get('name') for b in profile.badges])
        
        for badge in point_badges:
            profile.badges.append({
                'name': badge.name,
                'description': badge.description,
                'earned_at': datetime.now().isoformat()
            })
        
        # Check for registration badge if this is the first update
        if len(profile.badges) == 0:
            registration_badge = Badge.objects.filter(
                name__contains='Registration',
                role_specific=role
            ).first()
            if registration_badge:
                profile.badges.append({
                    'name': registration_badge.name,
                    'description': registration_badge.description,
                    'earned_at': datetime.now().isoformat()
                })
        
        profile.save()
    except Exception as e:
        logger.error(f"Failed to assign badges: {str(e)}")

def get_leaderboard_data():
    """
    Optimized leaderboard data fetching with smart verification
    """
    db = get_db_handle()
    collection = db['leaderboard']
    
    try:
        # Run fast verification in background
        from threading import Thread
        Thread(target=fast_verify_leaderboard, daemon=True).start()
        
        # Get current data immediately
        students = list(collection.find({"role": "student"}).sort([
            ("points", pymongo.DESCENDING),
            ("last_updated", pymongo.ASCENDING)
        ]).limit(100))  # Limit to top 100 for each category
        
        teachers = list(collection.find({"role": "teacher"}).sort([
            ("points", pymongo.DESCENDING),
            ("last_updated", pymongo.ASCENDING)
        ]).limit(100))
        
        schools = list(collection.find({"role": "school"}).sort([
            ("points", pymongo.DESCENDING),
            ("last_updated", pymongo.ASCENDING)
        ]).limit(100))
        
        # Process entries (same as before)
        def process_entries(entries):
            processed = []
            for index, entry in enumerate(entries):
                processed_entry = {
                    "_id": str(entry["_id"]),
                    "user_id": entry["user_id"],
                    "user_name": entry["user_name"],
                    "points": entry["points"],
                    "rank": index + 1,
                    "last_updated": entry["last_updated"].isoformat() 
                    if isinstance(entry["last_updated"], datetime) 
                    else entry["last_updated"]
                }
                if index < 3:  # Only calculate medals for top 3
                    medals = ["gold", "silver", "bronze"]
                    processed_entry["medal"] = medals[index]
                processed.append(processed_entry)
            return processed
        
        return {
            "students": process_entries(students),
            "teachers": process_entries(teachers),
            "schools": process_entries(schools)
        }
        
    except Exception as e:
        logger.error(f"Failed to get leaderboard data: {str(e)}")
        return {"students": [], "teachers": [], "schools": []}
def ensure_indexes():
    """Ensure MongoDB indexes exist for optimal performance"""
    try:
        db = get_db_handle()
        collection = db['leaderboard']
        
        collection.create_index([("role", pymongo.ASCENDING), ("points", pymongo.DESCENDING)])
        
        collection.create_index([("user_id", pymongo.ASCENDING), ("role", pymongo.ASCENDING)], unique=True)
        
        collection.create_index([("last_updated", pymongo.ASCENDING)])
        
        logger.info("MongoDB indexes ensured for leaderboard")
    except Exception as e:
        logger.error(f"Failed to ensure MongoDB indexes: {str(e)}")
        raise

def get_user_leaderboard_status(user, role):
    """
    Get current user's leaderboard status for a specific role
    Args:
        user: User object
        role: 'student', 'teacher', or 'school'
    Returns:
        dict with user's leaderboard data or None if not found
    """
    db = get_db_handle()
    collection = db['leaderboard']
    
    try:
        # First ensure ranks are up to date for this role
        recalculate_ranks(role)
        
        # Find the user in leaderboard
        user_entry = collection.find_one({
            "user_id": str(user.id),
            "role": role
        })
        
        if user_entry:
            return {
                "user_id": user_entry["user_id"],
                "user_name": user_entry["user_name"],
                "points": user_entry["points"],
                "rank": user_entry.get("rank"),
                "role": role,
                "is_on_leaderboard": True
            }
        return None
    except Exception as e:
        logger.error(f"Error getting user leaderboard status: {str(e)}")
        return None

def fast_verify_leaderboard():
    """
    Optimized verification using bulk operations and selective checking
    Returns count of corrected entries
    """
    db = get_db_handle()
    collection = db['leaderboard']
    corrections = 0
    
    # Only verify entries that haven't been checked recently
    cutoff_time = datetime.utcnow() - timedelta(minutes=5)
    
    try:
        # Get all leaderboard entries that need verification
        to_verify = list(collection.find({
            "$or": [
                {"last_verified": {"$exists": False}},
                {"last_verified": {"$lt": cutoff_time}}
            ]
        }))
        
        if not to_verify:
            return 0
            
        # Prepare bulk operations
        bulk_ops = []
        user_cache = {}
        
        for entry in to_verify:
            user_id = entry['user_id']
            role = entry['role']
            
            # Get source points (with caching)
            if (user_id, role) not in user_cache:
                try:
                    if role == 'student':
                        profile = apps.get_model('authentication', 'Student').objects.get(user__id=user_id)
                    elif role == 'teacher':
                        profile = apps.get_model('authentication', 'Teacher').objects.get(user__id=user_id)
                    elif role == 'school':
                        profile = apps.get_model('authentication', 'School').objects.get(user__id=user_id)
                    
                    user_cache[(user_id, role)] = profile.points
                except Exception as e:
                    logger.warning(f"Couldn't fetch profile for {user_id}: {str(e)}")
                    continue
            
            source_points = user_cache[(user_id, role)]
            
            if entry['points'] != source_points:
                bulk_ops.append(UpdateOne(
                    {"_id": entry['_id']},
                    {"$set": {
                        "points": source_points,
                        "last_updated": datetime.utcnow(),
                        "last_verified": datetime.utcnow()
                    }}
                ))
                corrections += 1
            else:
                bulk_ops.append(UpdateOne(
                    {"_id": entry['_id']},
                    {"$set": {"last_verified": datetime.utcnow()}}
                ))
        
        # Execute all updates in a single batch
        if bulk_ops:
            collection.bulk_write(bulk_ops)
            logger.info(f"Fast verification completed. Made {corrections} corrections.")
        
        return corrections
        
    except Exception as e:
        logger.error(f"Error in fast verification: {str(e)}")
        raise

from django.core.cache import cache

def get_cached_leaderboard():
    """
    Get leaderboard data with smart caching
    """
    cache_key = "leaderboard_data"
    data = cache.get(cache_key)
    
    if data is None:
        data = get_leaderboard_data()
        # Cache for 1 minute, but background verification will keep it fresh
        cache.set(cache_key, data, 60)
    
    return data