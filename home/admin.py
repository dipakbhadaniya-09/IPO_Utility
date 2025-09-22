from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

# from .models import PremiumOrderDetail
# from .models import PremiumGroupDetail
# Register your models here.
from .models import (
    ClientDetail,
    CurrentIpoName,
    CustomUser,
    GroupDetail,
    Order,
    OrderDetail,
    RateList,
)


class UserModel(UserAdmin):
    list_display = UserAdmin.list_display + (
        "IPO_limit",
        "Order_limit",
        "Premium_Order_limit",
        "Client_limit",
        "Group_limit",
        "Allotment_access",
        "Expiry_Date",
        "AppPassword",
        "TelegramApi_id",
        "TelegramApi_key",
        "Mobileno",
        "Telegram_session",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Custom Fields",
            {
                "fields": (
                    "IPO_limit",
                    "Order_limit",
                    "Premium_Order_limit",
                    "Client_limit",
                    "Group_limit",
                    "Allotment_access",
                    "Expiry_Date",
                    "AppPassword",
                    "TelegramApi_id",
                    "TelegramApi_key",
                    "Mobileno",
                    "Telegram_session",
                )
            },
        ),
    )
    # field = ('Broker_id')
    pass


admin.site.register(CustomUser, UserModel)
admin.site.register(CurrentIpoName)
admin.site.register(GroupDetail)
admin.site.register(OrderDetail)
admin.site.register(ClientDetail)
# admin.site.register(PremiumOrderDetail)
# admin.site.register(PremiumGroupDetail)
admin.site.register(RateList)
admin.site.register(Order)
