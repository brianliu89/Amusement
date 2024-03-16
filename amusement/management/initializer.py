from django.contrib.auth.models import User, Group, Permission

from .models import Chairman, Shareholders, Salesmanagers, Salespeople, Dealers, Players


class Initializer:
    def __init__(self):
        pass

    def initialize_all(self):
        if Chairman.objects.all():
            return '系統管理員已存在，若要初始化需先將資料庫清空重製'

        self.initialize_groups()
        chairman = self.initialize_chairman('yanboss666', 20000000)
        self.initialize_game_manager(chairman, 'gameManager')
        self.initialize_dealer()
        self.initialize_game()
        return '初始化成功，已建立群組、權限、系統管理員、荷官、第一局遊戲'

    def initialize_groups(self):
        chairmen = Group.objects.create(name='chairmen')
        shareholders = Group.objects.create(name='shareholders')
        salesmanagers = Group.objects.create(name='salesmanagers')
        salespeople = Group.objects.create(name='salespeople')
        players = Group.objects.create(name='players')

        for permission in self.get_group_permissions('chairmen'):
            chairmen.permissions.add(permission)
        for permission in self.get_group_permissions('shareholders'):
            shareholders.permissions.add(permission)
        for permission in self.get_group_permissions('salesmanagers'):
            salesmanagers.permissions.add(permission)
        for permission in self.get_group_permissions('salespeople'):
            salespeople.permissions.add(permission)
        for permission in self.get_group_permissions('players'):
            players.permissions.add(permission)

    def initialize_chairman(self, account, credits, password='168yan168'):
        chairman = Chairman.create_chairman(account, password, 'chairman', credits)
        return chairman

    def initialize_game_manager(self, chairman, account, password='168game168'):
        shareholder = Shareholders.create_shareholder(chairman, 'game_shareholder', '123456', 'game shareholders',
                                                      0, 0)
        salesmanager = Salesmanagers.create_salesmanager(shareholder, 'game_salesmanager', '123456',
                                                         'game salesmanager', 0)
        salesperson = Salespeople.create_salesperson(salesmanager, 'game_salesperson', '123456', 'game salesperson', 0)
        game_manager = Players.create_player(salesperson, account, password, 'game manager', 0, True)
        return game_manager

    def initialize_dealer(self):
        Dealers.objects.create(name='dealer1', ongame=True)
        Dealers.objects.create(name='dealer2')

    def initialize_puppets(self):
        pass

    def initialize_game(self):
        banker = Players.objects.get(is_gamemanager=True)
        dealer = Dealers.objects.get(ongame=True)
        game = dealer.games_set.create(leftpoints=4, rightpoints=9, resultpoints=10,
                                       intimes=-1, outtimes=1.52, ontimes=-1, result='B', status='已結算')
        banker.bets_set.create(game=game, is_banker=True)
        return game

    def clean_database(self):
        User.objects.all().delete()
        Group.objects.all().delete()
        Dealers.objects.all().delete()

    def get_group_permissions(self, group):
        chairmen_permissions = ['Can view chairman', 'Can add chairman', 'Can view shareholders',
                                'Can view salesmanagers', 'Can view salespeople', 'Can view players',
                                'Can view dealers', 'Can view tips', 'Can view games', 'Can view bets']
        shareholders_permissions = ['Can view salesmanagers', 'Can view salespeople', 'Can view players']
        salesmanagers_permissions = ['Can view salespeople', 'Can view players']
        salespeople_permissions = ['Can view players']
        players_permissions = []

        if group == 'chairmen':
            return Permission.objects.filter(name__in=chairmen_permissions)
        if group == 'shareholders':
            return Permission.objects.filter(name__in=shareholders_permissions)
        if group == 'salesmanagers':
            return Permission.objects.filter(name__in=salesmanagers_permissions)
        if group == 'salespeople':
            return Permission.objects.filter(name__in=salespeople_permissions)
        if group == 'players':
            return Permission.objects.filter(name__in=players_permissions)
