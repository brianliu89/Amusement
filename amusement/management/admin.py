from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Myuser, Chairman, Shareholders, Salesmanagers, Salespeople, Players, Dealers, Games, Bets, Waitinglines
from .models import ChairmanTransaction, ShareholdersTransaction, SalesmanagerTransaction, SalespeopleTransaction, PlayersTransaction, TipsTransaction


class MyuserInline(admin.StackedInline):
    model = Myuser
    can_delete = False
    verbose_name_plural = "Myuser"


class UserAdmin(BaseUserAdmin):
    inlines = (MyuserInline,)


# Register your models here.
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Chairman)
admin.site.register(Shareholders)
admin.site.register(Salesmanagers)
admin.site.register(Salespeople)
admin.site.register(Players)
admin.site.register(Dealers)
admin.site.register(Games)
admin.site.register(Bets)
admin.site.register(Waitinglines)
admin.site.register(ChairmanTransaction)
admin.site.register(ShareholdersTransaction)
admin.site.register(SalesmanagerTransaction)
admin.site.register(SalespeopleTransaction)
admin.site.register(PlayersTransaction)
admin.site.register(TipsTransaction)
