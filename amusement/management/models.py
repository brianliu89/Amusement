from django.contrib.auth.models import User, Group
from django.db import models
from django.conf import settings

GAME_STATUS = [
    ('初始化', '初始化'), ('初始化完成', '初始化完成'),
    ('下注中', '下注中'), ('開牌中', '開牌中'),
    ('已結算', '已結算'), ('已取消', '已取消'),
]


class Myuser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    password_visible = models.CharField(max_length=20)
    name = models.CharField(max_length=20, default='先生/小姐')
    is_chairman = models.BooleanField(default=False)
    is_shareholder = models.BooleanField(default=False)
    is_salesmanager = models.BooleanField(default=False)
    is_salesperson = models.BooleanField(default=False)
    is_player = models.BooleanField(default=False)


class Chairman(models.Model):
    user = models.OneToOneField(Myuser, on_delete=models.CASCADE)
    position = models.CharField(max_length=10, default='系統管理者')
    authority = models.CharField(max_length=10, null=True)
    credits = models.IntegerField(default=0, null=True)  # 到時候再訂系統總額度
    creditsleft = models.IntegerField(default=0, null=True)  # 到時候再訂
    balance = models.IntegerField(default=0, null=True)
    volumes = models.IntegerField(default=0, null=True)
    commission = models.FloatField(default=0, null=True)
    tips = models.IntegerField(default=0)
    querybalance = models.IntegerField(default=0)
    queryvolumes = models.IntegerField(default=0)
    querycommission = models.FloatField(default=0)
    querytips = models.IntegerField(default=0)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)
    others = models.CharField(max_length=50, null=True)

    @staticmethod
    def create_chairman(account, password, name, credits):
        group, created = Group.objects.get_or_create(name='chairmen')
        user = User.objects.create(username=account, password=password)
        my_user = Myuser.objects.create(user=user, name=name, password_visible=password, is_chairman=True)
        chairman = Chairman.objects.create(user=my_user, credits=credits, creditsleft=credits)
        user.groups.add(group)
        user.save()
        return chairman


class Shareholders(models.Model):
    user = models.OneToOneField(Myuser, on_delete=models.CASCADE)
    chairman = models.ForeignKey(Chairman, on_delete=models.CASCADE)
    credits = models.IntegerField(default=0)
    creditsleft = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    volumes = models.IntegerField(default=0)
    commission = models.FloatField(default=0)
    tips = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    basebonus = models.IntegerField(default=0)
    querybalance = models.IntegerField(default=0)
    queryvolumes = models.IntegerField(default=0)
    querycommission = models.FloatField(default=0)
    querytips = models.IntegerField(default=0)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    @staticmethod
    def create_shareholder(chairman, account, password, name, credits, basebonus):
        group, created = Group.objects.get_or_create(name='shareholders')
        user = User.objects.create(username=account, password=password)
        my_user = Myuser.objects.create(user=user, name=name, password_visible=password, is_shareholder=True)
        shareholder = Shareholders.objects.create(user=my_user, chairman=chairman, credits=credits,
                                                  creditsleft=credits, basebonus=basebonus)
        user.groups.add(group)
        user.save()
        return shareholder


class Salesmanagers(models.Model):
    user = models.OneToOneField(Myuser, on_delete=models.CASCADE)
    shareholder = models.ForeignKey(Shareholders, on_delete=models.CASCADE)
    credits = models.IntegerField(default=0)
    creditsleft = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    volumes = models.IntegerField(default=0)
    commission = models.FloatField(default=0)
    tips = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    querybalance = models.IntegerField(default=0)
    queryvolumes = models.IntegerField(default=0)
    querycommission = models.FloatField(default=0)
    querytips = models.IntegerField(default=0)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    @staticmethod
    def create_salesmanager(shareholder, account, password, name, credits):
        group, created = Group.objects.get_or_create(name='salesmanagers')
        user = User.objects.create(username=account, password=password)
        my_user = Myuser.objects.create(user=user, name=name, password_visible=password, is_salesmanager=True)
        salesmanager = Salesmanagers.objects.create(user=my_user, shareholder=shareholder, credits=credits,
                                                    creditsleft=credits)
        user.groups.add(group)
        user.save()
        return salesmanager


class Salespeople(models.Model):
    user = models.OneToOneField(Myuser, on_delete=models.CASCADE)
    salesmanager = models.ForeignKey(Salesmanagers, on_delete=models.CASCADE)
    credits = models.IntegerField(default=0)
    creditsleft = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    volumes = models.IntegerField(default=0)
    commission = models.FloatField(default=0)
    tips = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)
    querybalance = models.IntegerField(default=0)
    queryvolumes = models.IntegerField(default=0)
    querycommission = models.FloatField(default=0)
    querytips = models.IntegerField(default=0)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    @staticmethod
    def create_salesperson(salesmanager, account, password, name, credits):
        group, created = Group.objects.get_or_create(name='salespeople')
        user = User.objects.create(username=account, password=password)
        my_user = Myuser.objects.create(user=user, name=name, password_visible=password, is_salesperson=True)
        salespeople = Salespeople.objects.create(user=my_user, salesmanager=salesmanager, credits=credits,
                                                 creditsleft=credits)
        user.groups.add(group)
        user.save()
        return salespeople


class Players(models.Model):
    user = models.OneToOneField(Myuser, on_delete=models.CASCADE)
    salesperson = models.ForeignKey(Salespeople, on_delete=models.CASCADE)
    lineid = models.CharField(max_length=50, null=True)
    credits = models.IntegerField(default=0)
    creditsleft = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    volumes = models.IntegerField(default=0)
    commission = models.FloatField(default=0)
    tips = models.IntegerField(default=0)
    querybalance = models.IntegerField(default=0)
    queryvolumes = models.IntegerField(default=0)
    querycommission = models.FloatField(default=0)
    querytips = models.IntegerField(default=0)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)
    is_gamemanager = models.BooleanField(default=False)  # game manager存在players

    @staticmethod
    def create_player(salesperson, account, password, name, credits, is_gamemanager=False):
        group, created = Group.objects.get_or_create(name='players')
        user = User.objects.create(username=account, password=password)
        my_user = Myuser.objects.create(user=user, name=name, password_visible=password, is_player=True)
        player = Players.objects.create(user=my_user, salesperson=salesperson, credits=credits, creditsleft=credits,
                                        is_gamemanager=is_gamemanager)
        user.groups.add(group)
        user.save()
        return player


class Dealers(models.Model):
    name = models.CharField(max_length=20)
    tips = models.IntegerField(default=0)
    ongame = models.BooleanField(default=False)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)


# 這是以chairman角度
class ChairmanTransaction(models.Model):
    chairman = models.ForeignKey(Chairman, on_delete=models.CASCADE)
    targetname = models.CharField(max_length=20, null=True)
    type = models.CharField(max_length=5)
    number = models.IntegerField()
    before = models.IntegerField()
    after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)


# 以shareholder角度，記錄收到chairman的影響，與自己對salesmanager的影響
class ShareholdersTransaction(models.Model):
    shareholder = models.ForeignKey(Shareholders, on_delete=models.CASCADE)
    targetname = models.CharField(max_length=20, null=True)
    type = models.CharField(max_length=5)
    number = models.IntegerField()
    before = models.IntegerField()
    after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)


class SalesmanagerTransaction(models.Model):
    salesmanager = models.ForeignKey(Salesmanagers, on_delete=models.CASCADE)
    targetname = models.CharField(max_length=20)
    type = models.CharField(max_length=5)
    number = models.IntegerField()
    before = models.IntegerField()
    after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)


class SalespeopleTransaction(models.Model):
    salesperson = models.ForeignKey(Salespeople, on_delete=models.CASCADE)
    targetname = models.CharField(max_length=20)
    type = models.CharField(max_length=5)
    number = models.IntegerField()
    before = models.IntegerField()
    after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)


class PlayersTransaction(models.Model):
    player = models.ForeignKey(Players, on_delete=models.CASCADE)
    targetname = models.CharField(max_length=20, null=True)
    type = models.CharField(max_length=5)
    number = models.IntegerField()
    before = models.IntegerField()
    after = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)


class TipsTransaction(models.Model):
    player = models.ForeignKey(Players, on_delete=models.CASCADE)
    dealer = models.ForeignKey(Dealers, on_delete=models.CASCADE)
    tips = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)


class Games(models.Model):
    dealer = models.ForeignKey(Dealers, on_delete=models.CASCADE)
    leftpoints = models.IntegerField(null=True)
    rightpoints = models.IntegerField(null=True)
    resultpoints = models.IntegerField(null=True)
    intimes = models.FloatField(null=True)
    outtimes = models.FloatField(null=True)
    ontimes = models.FloatField(null=True)
    inlimit = models.IntegerField(default=settings.GAME_BASELIMIT)
    outlimit = models.IntegerField(default=settings.GAME_BASELIMIT)
    onlimit = models.IntegerField(default=settings.GAME_BASELIMIT)
    result = models.CharField(max_length=1, null=True)
    times = models.IntegerField(default=1)
    status = models.CharField(max_length=5, choices=GAME_STATUS, default='初始化')
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)

    class Meta:
        get_latest_by = 'createtime'


class Bets(models.Model):
    game = models.ForeignKey(Games, on_delete=models.CASCADE)
    player = models.ForeignKey(Players, on_delete=models.CASCADE)
    is_banker = models.BooleanField(default=False)
    abets = models.IntegerField(default=0)
    bbets = models.IntegerField(default=0)
    cbets = models.IntegerField(default=0)
    totalbets = models.IntegerField(default=0)
    balance = models.IntegerField(default=0)
    commission = models.FloatField(default=0)
    updatetime = models.DateTimeField(auto_now=True)
    createtime = models.DateTimeField(auto_now_add=True)


class Waitinglines(models.Model):
    player = models.ForeignKey(Players, on_delete=models.CASCADE)
    linename = models.CharField(max_length=30, null=True)
    jointime = models.DateTimeField(auto_now_add=True)
    times = models.IntegerField(default=1)
