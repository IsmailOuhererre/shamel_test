from rest_framework import serializers
from .models import Contract
from backend.apps.classrooms.serializers import ClassroomSerializer
from backend.apps.authentication.serializers import UserProfileSerializer
from bson import ObjectId
from decimal import Decimal

class ContractSerializer(serializers.ModelSerializer):
    classroom = ClassroomSerializer(read_only=True)
    teacher = UserProfileSerializer(read_only=True)
    school = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Contract
        fields = [
            '_id',
            'id',
            'classroom',
            'teacher',
            'school',
            'start_date',
            'end_date',
            'hours_per_week',
            'total_hours',
            'price_per_hour',
            'total_price',
            'status',
            'payment_reference',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            '_id',
            'id',
            'classroom',
            'teacher',
            'school',
            'total_price',
            'status',
            'payment_reference',
            'created_at',
            'updated_at'
        ]

class ContractCreateSerializer(serializers.ModelSerializer):
    classroom_id = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = Contract
        fields = [
            'classroom_id',
            'start_date',
            'end_date',
            'hours_per_week',
            'total_hours',
            'price_per_hour'
        ]
        extra_kwargs = {
            'start_date': {'required': True},
            'end_date': {'required': True},
            'hours_per_week': {'required': True, 'min_value': 1},
            'total_hours': {'required': True, 'min_value': 1},
            'price_per_hour': {'required': True, 'min_value': 0}
        }
    
    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise serializers.ValidationError("End date must be after start date")
        return data
    
    def create(self, validated_data):
        from backend.apps.classrooms.models import Classroom
        
        classroom_id = validated_data.pop('classroom_id')
        try:
            classroom = Classroom.objects.get(_id=ObjectId(classroom_id))
        except (Classroom.DoesNotExist, Exception):
            raise serializers.ValidationError({"classroom_id": "Invalid classroom ID"})
        
        contract = Contract(
            classroom=classroom,
            teacher=self.context['request'].user,
            school=classroom.school,
            price_per_hour=Decimal(str(validated_data['price_per_hour'])),
            total_hours=int(validated_data['total_hours']),
            start_date=validated_data['start_date'],
            end_date=validated_data['end_date'],
            hours_per_week=int(validated_data['hours_per_week']),
            status='processing'
        )
        contract.save()
        return contract

class ContractStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contract
        fields = ['status']