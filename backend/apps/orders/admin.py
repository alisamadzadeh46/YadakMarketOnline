from django.contrib import admin
from django.utils import timezone

from .models import Cart, CartItem, Order, OrderItem, PaymentReceipt


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "color_name", "unit_price", "quantity")


class PaymentReceiptInline(admin.StackedInline):
    model = PaymentReceipt
    extra = 0
    readonly_fields = ("confirmed_by", "confirmed_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "payment_method", "total", "created_at")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("number", "user__phone", "ship_to_name")
    readonly_fields = ("number", "subtotal", "discount_amount", "total", "created_at")
    inlines = (OrderItemInline, PaymentReceiptInline)
    actions = ("confirm_payment", "mark_shipped")

    @admin.action(description="تایید پرداخت سفارش‌های انتخاب‌شده")
    def confirm_payment(self, request, queryset):
        for order in queryset:
            order.status = Order.Status.CONFIRMED
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "paid_at"])

    @admin.action(description="ثبت به‌عنوان ارسال‌شده")
    def mark_shipped(self, request, queryset):
        queryset.update(status=Order.Status.SHIPPED)


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "subtotal", "updated_at")
    inlines = (CartItemInline,)
