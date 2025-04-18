from django.urls import path
from .views import (
    ContractListView,
    ContractDetailView,
    SchoolContractUpdateView,
    TeacherPaymentUpdateView
)

urlpatterns = [
    path('', ContractListView.as_view(), name='contract-list'),
    path('<str:_id>/', ContractDetailView.as_view(), name='contract-detail'),
    path('<str:_id>/school-update/', SchoolContractUpdateView.as_view(), name='school-contract-update'),
    path('<str:_id>/teacher-payment/', TeacherPaymentUpdateView.as_view(), name='teacher-payment'),
]