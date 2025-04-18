from djongo import models
from django.core.validators import MinValueValidator, MaxValueValidator
from backend.apps.authentication.models import User

class Classroom(models.Model):
    _id = models.ObjectIdField()
    school = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classrooms')
    name = models.CharField(max_length=255)
    description = models.TextField()
    capacity = models.IntegerField()
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.JSONField()  
    address = models.TextField()
    amenities = models.JSONField(default=list) 
    is_available = models.BooleanField(default=True)
    images = models.JSONField(default=list)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'classrooms'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['school']),
            models.Index(fields=['is_available']),
          
        ]
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
       # debug the 2dsphere index creation
        from django.db import connections
        db = connections['mongodb'].connection
        db['classrooms'].create_index([("location", "2dsphere")])
    
    def __str__(self):
        return f"{self.name} at {self.school.school_name}"