from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from math import radians, sin, cos, sqrt, atan2
from django.utils import timezone

from backend.apps.authentication.permissions import IsSchoolUser
from .models import Classroom
from .serializers import ClassroomSerializer
from django.db import connections
from bson.objectid import ObjectId
import json
import logging
from datetime import datetime
from backend.apps.authentication.models import User

logger = logging.getLogger(__name__)

class NearbyClassroomsView(APIView):
    permission_classes = [IsAuthenticated]
    EARTH_RADIUS_KM = 6371 

    def get(self, request):
        try:
            lat = float(request.query_params.get('lat'))
            lng = float(request.query_params.get('lng'))
            distance = float(request.query_params.get('distance', 10))  # Default 10km radius
            
            # Try MongoDB geospatial query first
            try:
                db = connections['mongodb'].connection
                collection = db['classrooms']
                
               
                if 'location_2dsphere' not in collection.index_information():
                    collection.create_index([('location', '2dsphere')], name='location_2dsphere')
                
                
                results = collection.find({
                    'location': {
                        '$nearSphere': {
                            '$geometry': {
                                'type': 'Point',
                                'coordinates': [lng, lat]
                            },
                            '$maxDistance': distance * 1000  # meters
                        }
                    }
                })
                
                classroom_ids = [str(res['_id']) for res in results]
                classrooms = Classroom.objects.filter(_id__in=classroom_ids)
                
                # Calculate distances for each classroom
                for classroom in classrooms:
                    coords = classroom.location['coordinates']
                    classroom.distance = self._haversine(lat, lng, coords[1], coords[0])
                
                classrooms = sorted(classrooms, key=lambda x: x.distance)
                serializer = ClassroomSerializer(classrooms, many=True)
                
                return Response({
                    'results': serializer.data,
                    'search_metrics': {
                        'center': {'lat': lat, 'lng': lng},
                        'radius_km': distance,
                        'count': len(classrooms)
                    }
                })
                
            except Exception as mongo_error:
                logger.warning(f"MongoDB geospatial query failed, falling back to manual calculation: {str(mongo_error)}")
                return self._fallback_distance_calculation(lat, lng, distance)
                
        except ValueError as ve:
            return Response(
                {"error": f"Invalid parameters: {str(ve)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error in nearby search: {str(e)}")
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _fallback_distance_calculation(self, lat, lng, distance):
        """Manual distance calculation fallback"""
        classrooms = Classroom.objects.all()
        results = []
        
        for classroom in classrooms:
            try:
                coords = classroom.location['coordinates']
                dist = self._haversine(lat, lng, coords[1], coords[0])
                if dist <= distance:
                    classroom.distance = dist
                    results.append(classroom)
            except:
                continue
        
        results = sorted(results, key=lambda x: x.distance)
        serializer = ClassroomSerializer(results, many=True)
        
        return Response({
            'results': serializer.data,
            'search_metrics': {
                'center': {'lat': lat, 'lng': lng},
                'radius_km': distance,
                'count': len(results)
            },
            'warning': 'Used fallback distance calculation'
        })

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return self.EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1-a))


class ClassroomView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSchoolUser()]
        return [IsAuthenticated()]

    def get(self, request):
        if request.user.role == 'school':
            classrooms = Classroom.objects.filter(school=request.user)
        else:
            classrooms = Classroom.objects.filter(is_available=True)
        
        serializer = ClassroomSerializer(classrooms, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ClassroomSerializer(data=request.data)
        if serializer.is_valid():
          
            if not hasattr(request.user, 'school_profile'):
                return Response(
                    {"error": "Only schools can create classrooms"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            serializer.save(school=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ClassroomDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            clean_pk = pk.rstrip('/')
            return Classroom.objects.get(_id=ObjectId(clean_pk))
        except Exception as e:
            logger.error(f"Error getting classroom: {str(e)}")
            return None

    def get(self, request, pk):
        """Allow both teachers and schools to view classroom details"""
        classroom = self.get_object(pk)
        if not classroom:
            return Response(
                {"error": "Classroom not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Allow access for:
        # 1. The school that owns the classroom
        # 2. Any authenticated teacher (for viewing available classrooms)
        # 3. School users (for viewing any classrooms)
        if (request.user.role == 'teacher' and classroom.is_available) or \
           request.user.role == 'school' or \
           (hasattr(request.user, 'school_profile') and classroom.school == request.user):
            serializer = ClassroomSerializer(classroom)
            return Response(serializer.data)
        
        return Response(
            {"error": "You don't have permission to view this classroom"},
            status=status.HTTP_403_FORBIDDEN
        )

    def put(self, request, pk):
        """Update ONLY the is_available field - restricted to classroom owner"""
        clean_pk = pk.rstrip('/')
        
        # 1. Validate input
        if 'is_available' not in request.data or len(request.data) > 1:
            return Response(
                {"error": "Only is_available field can be updated"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_availability = bool(request.data['is_available'])
        except Exception:
            return Response(
                {"error": "is_available must be true or false"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Get classroom
        classroom = self.get_object(clean_pk)
        if not classroom:
            return Response(
                {"error": "Classroom not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Verify ownership - only the school that owns the classroom can update
        if not hasattr(request.user, 'school_profile') or classroom.school != request.user:
            return Response(
                {"error": "Permission denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. Check contracts if making unavailable
        if not new_availability:
            try:
                from backend.apps.contracts.models import Contract
                if Contract.objects.filter(
                    classroom=classroom,
                    end_date__gte=timezone.now().date(),
                    status__in=['active', 'pending']
                ).exists():
                    return Response(
                        {"error": "Classroom has active contracts"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ImportError:
                logger.warning("Contracts app not available")

        # 5. Update - Bypass serializer completely
        try:
            # Update MongoDB directly
            db = connections['mongodb'].connection
            result = db.classrooms.update_one(
                {'_id': ObjectId(clean_pk)},
                {'$set': {'is_available': new_availability}}
            )
            
            # Update Django model
            classroom.is_available = new_availability
            classroom.save(update_fields=['is_available'])

            return Response(
                {
                    "success": True,
                    "is_available": new_availability,
                    "message": "Availability updated"
                },
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f"Update failed: {str(e)}")
            return Response(
                {"error": "Database update failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, pk):
        """Delete classroom - restricted to classroom owner"""
        logger.debug(f"DELETE request for classroom {pk}")
        
        # Clean the ID first
        clean_pk = pk.rstrip('/')
        
        try:
            obj_id = ObjectId(clean_pk)
        except Exception as e:
            logger.error(f"Invalid classroom ID format {clean_pk}: {str(e)}")
            return Response(
                {"error": "Invalid classroom ID format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        classroom = self.get_object(clean_pk)
        if not classroom:
            logger.warning(f"Classroom {clean_pk} not found for deletion")
            return Response({"error": "Classroom not found"}, status=status.HTTP_404_NOT_FOUND)
            
        # Check ownership - only the school that owns the classroom can delete
        if not hasattr(request.user, 'school_profile') or classroom.school != request.user:
            logger.warning(f"User {request.user.id} unauthorized to delete classroom {clean_pk}")
            return Response(
                {"error": "You can only delete your own classrooms"},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check for active contracts
        try:
            from backend.apps.contracts.models import Contract
            if Contract.objects.filter(
                classroom=classroom,
                end_date__gte=datetime.now().date()
            ).exists():
                logger.warning(f"Classroom {clean_pk} has active contracts, cannot delete")
                return Response(
                    {"error": "Cannot delete classroom with active contracts"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ImportError:
            logger.warning("Contracts app not available, skipping contract check")

        # Delete from MongoDB
        try:
            db = connections['mongodb'].connection
            result = db.classrooms.delete_one({'_id': obj_id})
            if result.deleted_count == 0:
                logger.error(f"MongoDB deletion failed for classroom {clean_pk}")
                return Response(
                    {"error": "Failed to delete classroom from database"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            logger.debug(f"Deleted classroom {clean_pk} from MongoDB")
        except Exception as e:
            logger.error(f"Error deleting from MongoDB: {str(e)}")
            return Response(
                {"error": "Database error during deletion"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Delete from Django ORM
        try:
            classroom.delete()
            logger.info(f"Successfully deleted classroom {clean_pk}")
            return Response(
                {"message": "Classroom deleted successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error deleting from Django ORM: {str(e)}")
            return Response(
                {"error": "Error completing deletion"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )