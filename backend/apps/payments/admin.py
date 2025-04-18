from django.contrib import admin
from .models import Payment, PlatformFee

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'recipient', 'gross_amount', 'status', 'transaction_type')
    list_filter = ('status', 'transaction_type')
    search_fields = ('sender__email', 'recipient__email', 'invoice_number')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        (None, {
            'fields': ('sender', 'recipient', 'transaction_type', 'status')
        }),
        ('Financial Details', {
            'fields': ('gross_amount', 'platform_fee', 'net_amount')
        }),
        ('Payment Info', {
            'fields': ('payment_method', 'chargily_id', 'invoice_number')
        }),
        ('Relationships', {
            'fields': ('contract', 'course')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )

@admin.register(PlatformFee)
class PlatformFeeAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'amount', 'collected_at')
    readonly_fields = ('collected_at',)
    search_fields = ('payment__invoice_number',)