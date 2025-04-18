from rest_framework import serializers
from .models import Classroom
from backend.apps.authentication.serializers import UserProfileSerializer
from bson.objectid import ObjectId

class ClassroomSerializer(serializers.ModelSerializer):
    school = UserProfileSerializer(read_only=True)
    distance = serializers.SerializerMethodField()
    is_owned = serializers.SerializerMethodField()
    
    class Meta:
        model = Classroom
        fields = [
            '_id', 'school', 'name', 'description', 'capacity', 'price_per_hour',
            'location', 'address', 'amenities', 'is_available', 'images',
            'distance', 'is_owned', 'created_at', 'updated_at'
        ]
        read_only_fields = ['school', 'created_at', 'updated_at']
    
    def get_distance(self, obj):
        # Returns the distance that was calculated in the view
        if hasattr(obj, 'distance'):
            return round(obj.distance, 2)
        return None
    
    def get_is_owned(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.school == request.user
        return False

class ClassroomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Classroom
        fields = [
            'name', 'description', 'capacity', 'price_per_hour',
            'location', 'address', 'amenities', 'images'
        ]
    
    def validate_location(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("Location must be a dictionary")
        
        if value.get('type') != 'Point':
            raise serializers.ValidationError("GeoJSON type must be 'Point'")
        
        coordinates = value.get('coordinates')
        if not isinstance(coordinates, list) or len(coordinates) != 2:
            raise serializers.ValidationError("Coordinates must be a list of [longitude, latitude]")
        
        if not all(isinstance(coord, (int, float)) for coord in coordinates):
            raise serializers.ValidationError("Coordinates must be numbers")
        
        return value
    
    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authentication required")
        
        if not hasattr(request.user, 'school_profile'):
            raise serializers.ValidationError("Only schools can create classrooms")
        
        return Classroom.objects.create(school=request.user, **validated_data)