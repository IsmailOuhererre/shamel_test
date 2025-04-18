from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.http import Http404
from .models import Contract
from .serializers import (
    ContractSerializer,
    ContractCreateSerializer,
    ContractStatusSerializer
)
from backend.apps.classrooms.models import Classroom
from backend.apps.authentication.permissions import IsTeacherUser, IsSchoolUser
from bson import ObjectId
from django.core.exceptions import ValidationError

class ContractListView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        return ContractCreateSerializer if self.request.method == 'POST' else ContractSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'teacher_profile'):
            return Contract.objects.filter(teacher=user)
        elif hasattr(user, 'school_profile'):
            return Contract.objects.filter(school=user)
        return Contract.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except ValidationError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ContractDetailView(generics.RetrieveAPIView):
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        contract_id = self.kwargs.get('_id')
        
        try:
            # Try to convert string to ObjectId
            object_id = ObjectId(contract_id)
            
            # Create appropriate filter based on user type
            user = self.request.user
            filter_kwargs = {'_id': object_id}
            
            if hasattr(user, 'teacher_profile'):
                filter_kwargs['teacher'] = user
            elif hasattr(user, 'school_profile'):
                filter_kwargs['school'] = user
                
            # Get the contract
            contract = Contract.objects.get(**filter_kwargs)
            return contract
            
        except (Contract.DoesNotExist, ValueError, TypeError) as e:
            raise Http404("Contract not found")

class SchoolContractUpdateView(generics.UpdateAPIView):
    serializer_class = ContractStatusSerializer
    permission_classes = [IsAuthenticated, IsSchoolUser]
    
    def get_object(self):
        contract_id = self.kwargs.get('_id')
        
        try:
           
            object_id = ObjectId(contract_id)
            
            
            contract = Contract.objects.get(_id=object_id, school=self.request.user)
            return contract
            
        except (Contract.DoesNotExist, ValueError, TypeError) as e:
            raise Http404("Contract not found")

    def update(self, request, *args, **kwargs):
        try:
            contract = self.get_object()
            
            
            new_status = request.data.get('status')
            
            if new_status not in ['processing', 'rejected', 'payment_pending']:
                return Response(
                    {"detail": "Invalid status for this action"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
           
            contract.status = new_status
            contract.save(update_fields=['status'])
            
            return Response(ContractSerializer(contract).data)
        except Http404:
            return Response({"detail": "Contract not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TeacherPaymentUpdateView(generics.UpdateAPIView):
    serializer_class = ContractStatusSerializer
    permission_classes = [IsAuthenticated, IsTeacherUser]
    
    def get_object(self):
        contract_id = self.kwargs.get('_id')
        
        try:
           
            object_id = ObjectId(contract_id)
      
            contract = Contract.objects.get(
                _id=object_id,
                teacher=self.request.user,
                status='payment_pending'
            )
            return contract
            
        except (Contract.DoesNotExist, ValueError, TypeError) as e:
            raise Http404("Contract not found")

    def update(self, request, *args, **kwargs):
        try:
            contract = self.get_object()
            payment_reference = request.data.get('payment_reference')
            
            if not payment_reference:
                return Response(
                    {"detail": "Payment reference is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
         
            contract.status = 'ready_for_enrollment'
            contract.payment_reference = payment_reference
            contract.save(update_fields=['status', 'payment_reference'])
            
            return Response(ContractSerializer(contract).data)
        except Http404:
            return Response({"detail": "Contract not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
