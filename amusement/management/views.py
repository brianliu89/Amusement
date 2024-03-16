from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views import View, generic
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User, Group
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as django_logout
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import F

import datetime
import re

from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextSendMessage

from .models import Myuser, Chairman, Shareholders, Salesmanagers, Salespeople, Dealers, Players
from .models import ChairmanTransaction, ShareholdersTransaction, SalesmanagerTransaction, SalespeopleTransaction,\
    PlayersTransaction, TipsTransaction
from .models import Games, Bets
from .initializer import Initializer

line_bot_api = LineBotApi(settings.LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(settings.LINE_CHANNEL_SECRET)


# Create your views here.
class Login(View):
    template_name = 'management/index.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        password = request.POST['password']
        user = authenticate(request, username=account, password=password)
        if user is not None:
            # check status
            if user.myuser.is_shareholder:
                if not user.myuser.shareholders.status:
                    return render(request, self.template_name, {'message': '登入失敗，帳號權限已被封鎖'})
            if user.myuser.is_salesmanager:
                if not (user.myuser.salesmanagers.status and user.myuser.salesmanagers.shareholder.status):
                    return render(request, self.template_name, {'message': '登入失敗，帳號權限已被封鎖'})
            if user.myuser.is_salesperson:
                if not (user.myuser.salespeople.status and user.myuser.salespeople.salesmanager.status and user.myuser.salespeople.salesmanager.shareholder.status):
                    return render(request, self.template_name, {'message': '登入失敗，帳號權限已被封鎖'})
            if user.myuser.is_player:
                if not (user.myuser.players.status and user.myuser.players.salesperson.status and user.myuser.players.salesperson.salesmanager.status and user.myuser.players.salesperson.salesmanager.shareholder.status):
                    return render(request, self.template_name, {'message': '登入失敗，帳號權限已被封鎖'})

            login(request, user)

            if user.myuser.is_player:
                return HttpResponseRedirect(reverse('management:player_private'))
            else:
                return HttpResponseRedirect(reverse('management:private'))
        else:
            return render(request, self.template_name, {'message': "登入失敗，請檢查帳號和密碼是否正確"})


def logout(request):
    django_logout(request)
    return HttpResponseRedirect(reverse('management:login'))


class Private(LoginRequiredMixin, View):
    login_url = '/management/login/'
    template_name = 'management/private.html'

    def get(self, request, *args, **kwargs):
        context = {}
        user = request.user.myuser
        if user.is_chairman:
            context['profile'] = user.chairman
        elif user.is_shareholder:
            context['profile'] = user.shareholders
        elif user.is_salesmanager:
            context['profile'] = user.salesmanagers
        elif user.is_salesperson:
            context['profile'] = user.salespeople

        return render(request, self.template_name, context)


class RegisterChairman(PermissionRequiredMixin, View):
    permission_required = 'management.view_chairman'  # 注意權限設定，帳號管理那邊有補充說明
    template_name = 'management/account_manage.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:accounts_management'))

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        name = request.POST['name']
        position = request.POST['position']
        authority = request.POST['authority']
        others = request.POST['others']

        context = {'chairman_list': Chairman.objects.all(), 'message': ''}
        if User.objects.filter(username=account):
            context['message'] = '此帳號已被使用'
        if Myuser.objects.filter(name=name):
            context['message'] = '此名稱已被使用'
        if account.strip() == '' or password1.strip() == '' or password2.strip() == '' or name.strip() == '':
            context['message'] = '帳號、密碼和名稱不得為空'
        if len(name) > 20:
            context['message'] = '名稱需小於20個字元'
        if len(password1) > 20:
            context['message'] = '密碼需小於20個字元'
        if password1 != password2:
            context['message'] = '密碼輸入不一致，請檢查'
        if not context['message'] == '':
            return render(request, self.template_name, context)

        try:
            user = User.objects.create_user(username=account, password=password1)
            myuser = Myuser.objects.create(user=user, name=name, password_visible=password1, is_chairman=True)
        except:
            context['message'] = '帳號和名稱不能包含特殊符號，請檢查❌'
            return render(request, self.template_name, context)
        # chairman先不加group，要給總負責人、監官和會計不同權限
        Chairman.objects.create(user=myuser, position=position, authority=authority, others=others)
        return HttpResponseRedirect(reverse('management:account_management'))


class RegisterShareholder(PermissionRequiredMixin, View):
    permission_required = 'management.view_shareholders'
    template_name = 'management/manage_shareholders.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_shareholders'))

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        name = request.POST['name']
        credits = request.POST['credits']  # 初始信用額度

        context = {'shareholder_list': request.user.myuser.chairman.shareholders_set.all(), 'message': ''}
        chairman = request.user.myuser.chairman
        if User.objects.filter(username=account):
            context['message'] = '此帳號已被使用'
        if Myuser.objects.filter(name=name):
            context['message'] = '此名稱已被使用'
        if account.strip() == '' or password1.strip() == '' or password2.strip() == '' or name.strip() == '':
            context['message'] = '所有欄位不得為空'
        if len(name) > 20:
            context['message'] = '名稱需小於20個字元'
        if len(password1) > 20:
            context['message'] = '密碼需小於20個字元'
        if password1 != password2:
            context['message'] = '密碼輸入不一致，請檢查'
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)
        if chairman.creditsleft < credits:
            context['message'] = '信用餘額不足，請檢查'
        if context['message']:
            return render(request, self.template_name, context)

        try:
            user = User.objects.create_user(username=account, password=password1)
            myuser = Myuser.objects.create(user=user, name=name, password_visible=password1, is_shareholder=True)
        except:
            context['message'] = '帳號和名稱不能包含特殊符號，請檢查❌'
            return render(request, self.template_name, context)
        shareholder = Shareholders.objects.create(user=myuser, chairman=chairman, credits=credits, creditsleft=credits,
                                                  basebonus=100)
        group = Group.objects.get(name='shareholders')
        user.groups.add(group)
        user.save()
        ChairmanTransaction.objects.create(chairman=chairman, targetname=name, number=credits, type='轉入',
                                           before=chairman.creditsleft, after=chairman.creditsleft - credits)
        ShareholdersTransaction.objects.create(shareholder=shareholder, targetname=chairman.user.name, number=credits,
                                               type='被轉入', before=0, after=credits)
        chairman.creditsleft -= credits
        chairman.save()
        return HttpResponseRedirect(reverse('management:staff_shareholders'))


class RegisterSalesmanager(PermissionRequiredMixin, View):
    permission_required = 'management.view_salesmanagers'
    template_name = 'management/manage_salesmanagers.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_salesmanagers'))

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        name = request.POST['name']
        credits = request.POST['credits']  # 初始信用額度
        shareholderid = request.POST['shareholderid']

        context = {'salesmanager_list': get_salesmanager_list(request), 'message': ''}
        if User.objects.filter(username=account):
            context['message'] = '此帳號已被使用'
        if Myuser.objects.filter(name=name):
            context['message'] = '此名稱已被使用'
        if account.strip() == '' or password1.strip() == '' or password2.strip() == '' or name.strip() == '':
            context['message'] = '所有欄位不得為空'
        if len(name) > 20:
            context['message'] = '名稱需小於20個字元'
        if len(password1) > 20:
            context['message'] = '密碼需小於20個字元'
        if password1 != password2:
            context['message'] = '密碼輸入不一致，請檢查'
        try:
            shareholder = Shareholders.objects.get(id=shareholderid)
        except:
            context['message'] = '該股東不存在，請檢查股東編號'
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)
        if shareholder.creditsleft < credits:
            context['message'] = '信用餘額不足，請檢查'
        if context['message']:
            return render(request, self.template_name, context)

        try:
            user = User.objects.create_user(username=account, password=password1)
            myuser = Myuser.objects.create(user=user, name=name, password_visible=password1, is_salesmanager=True)
        except:
            context['message'] = '帳號和名稱不能包含特殊符號，請檢查❌'
            return render(request, self.template_name, context)
        salesmanager = Salesmanagers.objects.create(user=myuser, shareholder=shareholder, credits=credits,
                                                    creditsleft=credits)
        group = Group.objects.get(name='salesmanagers')
        user.groups.add(group)
        user.save()
        shareholder.shareholderstransaction_set.create(targetname=name, number=credits, type='轉入',
                                                       before=shareholder.creditsleft,
                                                       after=shareholder.creditsleft - credits)
        salesmanager.salesmanagertransaction_set.create(targetname=shareholder.user.name, number=credits, type='被轉入',
                                                        before=0, after=credits)
        shareholder.creditsleft -= credits
        shareholder.save()
        return HttpResponseRedirect(reverse('management:staff_salesmanagers'))


class RegisterSalesperson(PermissionRequiredMixin, View):
    permission_required = 'management.view_salespeople'
    template_name = 'management/manage_salespeople.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_salespeople'))

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        name = request.POST['name']
        credits = request.POST['credits']
        salesmanagerid = request.POST['salesmanagerid']

        context = {'salesperson_list': get_salesperson_list(request), 'message': ''}
        if User.objects.filter(username=account):
            context['message'] = '此帳號已被使用'
        if Myuser.objects.filter(name=name):
            context['message'] = '此名稱已被使用'
        if account.strip() == '' or password1.strip() == '' or password2.strip() == '' or name.strip() == '' or salesmanagerid.strip() == '':
            context['message'] = '所有欄位不得為空'
        if len(name) > 20:
            context['message'] = '名稱需小於20個字元'
        if len(password1) > 20:
            context['message'] = '密碼需小於20個字元'
        if password1 != password2:
            context['message'] = '密碼輸入不一致，請檢查'
        try:
            salesmanager = Salesmanagers.objects.get(id=salesmanagerid)
        except:
            context['message'] = '該總代不存在，請檢查總代編號'
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)
        if salesmanager.creditsleft < credits:
            context['message'] = '信用餘額不足，請檢查'
        if context['message']:
            return render(request, self.template_name, context)

        try:
            user = User.objects.create_user(username=account, password=password1)
            myuser = Myuser.objects.create(user=user, name=name, password_visible=password1, is_salesperson=True)
        except:
            context['message'] = '帳號和名稱不能包含特殊符號，請檢查❌'
            return render(request, self.template_name, context)
        salesperson = Salespeople.objects.create(user=myuser, salesmanager=salesmanager, credits=credits,
                                                 creditsleft=credits)
        group = Group.objects.get(name='salespeople')
        user.groups.add(group)
        salesmanager.save()
        user.save()
        salesmanager.salesmanagertransaction_set.create(targetname=name, number=credits, type='轉入',
                                                        before=salesmanager.creditsleft,
                                                        after=salesmanager.creditsleft - credits)
        salesperson.salespeopletransaction_set.create(targetname=salesmanager.user.name, number=credits, type='被轉入',
                                                      before=0, after=credits)
        salesmanager.creditsleft -= credits
        salesmanager.save()
        return HttpResponseRedirect(reverse('management:staff_salespeople'))


class RegisterPlayer(View):
    template_name = 'management/register_player.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        name = request.POST['name']
        salespersonid = request.POST['salespersonid']

        message = ''
        try:
            salesperson = Salespeople.objects.get(id=salespersonid)
        except:
            message = '該代理不存在，請檢查代理編號'
        if User.objects.filter(username=account):
            message = '此帳號已被使用'
        if Myuser.objects.filter(name=name):
            message = '此名稱已被使用'
        if account.strip() == '' or password1.strip() == '' or password2.strip() == '' or name.strip() == '' or salespersonid.strip() == '':
            message = '所有欄位不得為空'
        if len(name) > 20:
            message = '名稱需小於20個字元'
        if len(password1) > 20:
            message = '密碼需小於20個字元'
        if password1 != password2:
            message = '密碼輸入不一致，請檢查'
        if not message == '':
            return render(request, self.template_name, {'message': message})

        try:
            user = User.objects.create_user(username=account, password=password1)
            myuser = Myuser.objects.create(user=user, name=name, password_visible=password1, is_player=True)
        except:
            return render(request, self.template_name, {'message': '帳號和名稱不能包含特殊符號，請檢查❌'})
        Players.objects.create(user=myuser, salesperson=salesperson)
        group = Group.objects.get(name='players')  # chairman group權限設定時，要有觀看所有人的權限
        user.groups.add(group)
        user.save()
        return render(request, self.template_name, {'message': '註冊成功'})


class RegisterDealer(PermissionRequiredMixin, View):
    permission_required = 'management.view_dealers'
    template_name = 'management/manage_dealers.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_dealers'))

    def post(self, request, *args, **kwargs):
        name = request.POST['name']

        context = {'dealer_list': Dealers.objects.all(), 'message': ''}
        if name.strip() == '':
            context['message'] = '名稱不得為空'
            return render(request, self.template_name, context)
        if Dealers.objects.filter(name=name) or Myuser.objects.filter(name=name):
            context['message'] = '此名稱已被使用'
            return render(request, self.template_name, context)
        if len(name) > 20:
            context['message'] = '名稱不得超過20個字元'
            return render(request, self.template_name, context)

        try:
            Dealers.objects.create(name=name)
        except:
            context['message'] = '名稱不能包含特殊符號，請檢查❌'
            return render(request, self.template_name, context)
        return HttpResponseRedirect(reverse('management:staff_dealers'))


class StaffShareholders(PermissionRequiredMixin, View):
    permission_required = 'management.view_shareholders'
    template_name = 'management/manage_shareholders.html'

    def get(self, request, *args, **kwargs):
        shareholder_list = request.user.myuser.chairman.shareholders_set.all()
        return render(request, self.template_name, {'shareholder_list': shareholder_list})


class StaffSalesmanagers(PermissionRequiredMixin, View):
    permission_required = 'management.view_salesmanagers'
    template_name = 'management/manage_salesmanagers.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'salesmanager_list': get_salesmanager_list(request)})


class StaffSalespeople(PermissionRequiredMixin, View):
    permission_required = 'management.view_salespeople'
    template_name = 'management/manage_salespeople.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'salesperson_list': get_salesperson_list(request)})


class StaffPlayers(PermissionRequiredMixin, View):
    permission_required = 'management.view_players'
    template_name = 'management/manage_players.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'player_list': get_player_list(request)})


class StaffDealers(PermissionRequiredMixin, generic.ListView):
    permission_required = 'management.view_dealers'
    template_name = 'management/manage_dealers.html'
    model = Dealers
    context_object_name = 'dealer_list'


class ChangeCreditsShareholder(PermissionRequiredMixin, View):
    permission_required = 'management.view_shareholders'
    template_name = 'management/manage_shareholders.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_shareholders'))

    def post(self, request, *args, **kwargs):
        shareholderid = request.POST['shareholderid']  # 要更改目標的id
        credits = request.POST['credits']

        context = {'shareholder_list': request.user.myuser.chairman.shareholders_set.all(), 'message': ''}
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)

        # 有五種type: 轉入、轉出、被轉入、被轉出、歸零
        shareholder = Shareholders.objects.get(id=shareholderid)
        chairman = shareholder.chairman
        number = shareholder.credits - credits  # 正的話對chairman來說是轉出，負為轉入shareholder
        if number < 0:
            if abs(number) > chairman.creditsleft:
                context['message'] = '餘額不足'
                return render(request, self.template_name, context)
            chairman.chairmantransaction_set.create(targetname=shareholder.user.name, type='轉入', number=abs(number),
                                                    before=chairman.creditsleft, after=chairman.creditsleft + number)
            shareholder.shareholderstransaction_set.create(targetname=chairman.user.name, type='被轉入',
                                                           number=abs(number), before=shareholder.creditsleft,
                                                           after=shareholder.creditsleft - number)
        elif number > 0:
            if shareholder.creditsleft < number:
                context['message'] = '目標剩餘信用不足無法收回'
                return render(request, self.template_name, context)
            chairman.chairmantransaction_set.create(targetname=shareholder.user.name, type='轉出', number=abs(number),
                                                    before=chairman.creditsleft, after=chairman.creditsleft + number)
            shareholder.shareholderstransaction_set.create(targetname=chairman.user.name, type='被轉出',
                                                           number=abs(number), before=shareholder.creditsleft,
                                                           after=shareholder.creditsleft - number)
        else:
            context['message'] = '更改失敗'
            return render(request, self.template_name, context)
        chairman.creditsleft += number
        shareholder.credits = credits
        shareholder.creditsleft -= number
        chairman.save()
        shareholder.save()
        return HttpResponseRedirect(reverse('management:staff_shareholders'))


class ChangeCreditsSalesmanager(PermissionRequiredMixin, View):
    permission_required = 'management.view_salesmanagers'
    template_name = 'management/manage_salesmanagers.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_salesmanagers'))

    def post(self, request, *args, **kwargs):
        salesmanagerid = request.POST['salesmanagerid']
        credits = request.POST['credits']

        context = {'salesmanager_list': get_salesmanager_list(request), 'message': ''}
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)

        salesmanager = Salesmanagers.objects.get(id=salesmanagerid)
        shareholder = salesmanager.shareholder
        number = salesmanager.credits - credits
        if number < 0:  # 轉入總代
            if abs(number) > shareholder.creditsleft:
                context['message'] = '餘額不足'
                return render(request, self.template_name, context)
            shareholder.shareholderstransaction_set.create(targetname=salesmanager.user.name, type='轉入',
                                                           number=abs(number), before=shareholder.creditsleft,
                                                           after=shareholder.creditsleft + number)
            salesmanager.salesmanagertransaction_set.create(targetname=shareholder.user.name, type='被轉入',
                                                            number=abs(number), before=salesmanager.creditsleft,
                                                            after=salesmanager.creditsleft - number)
        elif number > 0:
            if salesmanager.creditsleft < number:
                context['message'] = '目標剩餘信用不足無法收回'
                return render(request, self.template_name, context)
            shareholder.shareholderstransaction_set.create(targetname=salesmanager.user.name, type='轉出',
                                                           number=abs(number), before=shareholder.creditsleft,
                                                           after=shareholder.creditsleft + number)
            salesmanager.salesmanagertransaction_set.create(targetname=shareholder.user.name, type='被轉出',
                                                            number=abs(number), before=salesmanager.creditsleft,
                                                            after=salesmanager.creditsleft - number)
        else:
            context['message'] = '更改失敗'
            return render(request, self.template_name, context)
        shareholder.creditsleft += number
        salesmanager.credits = credits
        salesmanager.creditsleft -= number
        shareholder.save()
        salesmanager.save()
        return HttpResponseRedirect(reverse('management:staff_salesmanagers'))


class ChangeCreditsSalesperson(PermissionRequiredMixin, View):
    permission_required = 'management.view_salespeople'
    template_name = 'management/manage_salespeople.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_salespeople'))

    def post(self, request, *args, **kwargs):
        salespersonid = request.POST['salespersonid']
        credits = request.POST['credits']

        context = {'salesperson_list': get_salesperson_list(request), 'message': ''}
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)

        salesperson = Salespeople.objects.get(id=salespersonid)
        salesmanager = salesperson.salesmanager
        number = salesperson.credits - credits
        if number < 0:  # 轉入代理
            if abs(number) > salesmanager.creditsleft:
                context['message'] = '餘額不足'
                return render(request, self.template_name, context)
            salesmanager.salesmanagertransaction_set.create(targetname=salesperson.user.name, type='轉入',
                                                            number=abs(number), before=salesmanager.creditsleft,
                                                            after=salesmanager.creditsleft + number)
            salesperson.salespeopletransaction_set.create(targetname=salesmanager.user.name, type='被轉入',
                                                          number=abs(number), before=salesperson.creditsleft,
                                                          after=salesperson.creditsleft - number)
        elif number > 0:
            if salesperson.creditsleft < number:
                context['message'] = '目標剩餘信用不足無法收回'
                return render(request, self.template_name, context)
            salesmanager.salesmanagertransaction_set.create(targetname=salesperson.user.name, type='轉出',
                                                            number=abs(number), before=salesmanager.creditsleft,
                                                            after=salesmanager.creditsleft + number)
            salesperson.salespeopletransaction_set.create(targetname=salesmanager.user.name, type='被轉出',
                                                          number=abs(number), before=salesperson.creditsleft,
                                                          after=salesperson.creditsleft - number)
        else:
            context['message'] = '更改失敗'
            return render(request, self.template_name, context)
        salesmanager.creditsleft += number
        salesperson.credits = credits
        salesperson.creditsleft -= number
        salesmanager.save()
        salesperson.save()
        return HttpResponseRedirect(reverse('management:staff_salespeople'))


class ChangeCreditsPlayer(PermissionRequiredMixin, View):
    permission_required = 'management.view_players'
    template_name = 'management/manage_players.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_players'))

    def post(self, request, *args, **kwargs):
        playerid = request.POST['playerid']
        credits = request.POST['credits']

        context = {'player_list': get_player_list(request), 'message': ''}
        if not re.match(r'\d+', credits):
            context['message'] = '信用額度請輸入正整數或0'
            return render(request, self.template_name, context)
        credits = int(credits)

        player = Players.objects.get(id=playerid)
        salesperson = player.salesperson
        number = player.credits - credits
        if number < 0:  # 轉入玩家
            if abs(number) > salesperson.creditsleft:
                context['message'] = '餘額不足'
                return render(request, self.template_name, context)
            salesperson.salespeopletransaction_set.create(targetname=player.user.name, type='轉入', number=abs(number),
                                                          before=salesperson.creditsleft,
                                                          after=salesperson.creditsleft + number)
            player.playerstransaction_set.create(targetname=salesperson.user.name, type='被轉入', number=abs(number),
                                                 before=player.creditsleft, after=player.creditsleft - number)
        elif number > 0:
            if player.creditsleft < number:
                context['message'] = '目標剩餘信用不足無法收回'
                return render(request, self.template_name, context)
            salesperson.salespeopletransaction_set.create(targetname=player.user.name, type='轉出', number=abs(number),
                                                          before=salesperson.creditsleft,
                                                          after=salesperson.creditsleft + number)
            player.playerstransaction_set.create(targetname=salesperson.user.name, type='被轉出', number=abs(number),
                                                 before=player.creditsleft, after=player.creditsleft - number)
        else:
            context['message'] = '更改失敗'
            return render(request, self.template_name, context)
        salesperson.creditsleft += number
        player.credits = credits
        player.creditsleft -= number
        salesperson.save()
        player.save()
        return HttpResponseRedirect(reverse('management:staff_players'))


class ChangeBasebonus(PermissionRequiredMixin, View):
    permission_required = 'management.view_shareholders'
    template_name = 'management/manage_shareholders.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:staff_shareholders'))

    def post(self, request, *args, **kwargs):
        shareholderid = request.POST['shareholderid']
        basebonus = request.POST['basebonus']

        context = {'shareholder_list': request.user.myuser.chairman.shareholders_set.all(), 'message': ''}
        if not re.match(r'\d+', basebonus):
            context['message'] = '基數請輸入正整數或0'
            return render(request, self.template_name, context)
        basebonus = int(basebonus)
        if basebonus > 1000:
            context['message'] = '基數範圍為0-1000'
            return render(request, self.template_name, context)

        shareholder = Shareholders.objects.get(id=shareholderid)
        shareholder.basebonus = basebonus
        shareholder.save()
        return HttpResponseRedirect(reverse('management:staff_shareholders'))


class ChangeStatus(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:private'))

    def post(self, request, *args, **kwargs):
        identityid = request.POST['identityid']
        identity = request.POST['identity']

        if identity == 'shareholder':
            shareholder = Shareholders.objects.get(id=identityid)
            salesmanagers_set = shareholder.salesmanagers_set.all()
            salespeople_set = Salespeople.objects.filter(salesmanager__in=salesmanagers_set)
            players_set = Players.objects.filter(salesperson__in=salespeople_set)
            if shareholder.status:
                shareholder.status = False
                salesmanagers_set.update(status=False)
                salespeople_set.update(status=False)
                players_set.update(status=False)
            else:
                shareholder.status = True
                salesmanagers_set.update(status=True)
                salespeople_set.update(status=True)
                players_set.update(status=True)
            shareholder.save()
        elif identity == 'salesmanager':
            salesmanager = Salesmanagers.objects.get(id=identityid)
            salespeople_set = salesmanager.salespeople_set.all()
            players_set = Players.objects.filter(salesperson__in=salespeople_set)
            if salesmanager.status:
                salesmanager.status = False
                salespeople_set.update(status=False)
                players_set.update(status=False)
            else:
                salesmanager.status = True
                salespeople_set.update(status=True)
                players_set.update(status=True)
            salesmanager.save()
        elif identity == 'salesperson':
            salesperson = Salespeople.objects.get(id=identityid)
            players_set = salesperson.players_set.all()
            if salesperson.status:
                salesperson.status = False
                players_set.update(status=False)
            else:
                salesperson.status = True
                players_set.update(status=True)
            salesperson.save()
        elif identity == 'player':
            player = Players.objects.get(id=identityid)
            if player.status:
                player.status = False
            else:
                player.status = True
            player.save()

        if identity == 'shareholder':
            return HttpResponseRedirect(reverse('management:staff_shareholders'))
        elif identity == 'salesmanager':
            return HttpResponseRedirect(reverse('management:staff_salesmanagers'))
        elif identity == 'salesperson':
            return HttpResponseRedirect(reverse('management:staff_salespeople'))
        elif identity == 'player':
            return HttpResponseRedirect(reverse('management:staff_players'))


# 根據身分傳回對應的list
def get_salesmanager_list(request):
    user = request.user.myuser
    if user.is_chairman:
        salesmanager_list = Salesmanagers.objects.filter(shareholder__in=user.chairman.shareholders_set.all())
    elif user.is_shareholder:
        salesmanager_list = user.shareholders.salesmanagers_set.all()
    return salesmanager_list


def get_salesperson_list(request):
    user = request.user.myuser
    if user.is_chairman:
        salesperson_list = Salespeople.objects.filter(
            salesmanager__in=Salesmanagers.objects.filter(shareholder__in=user.chairman.shareholders_set.all()))
    elif user.is_shareholder:
        salesperson_list = Salespeople.objects.filter(
            salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders))
    elif user.is_salesmanager:
        salesperson_list = Salespeople.objects.filter(salesmanager=user.salesmanagers)
    return salesperson_list


def get_player_list(request):
    user = request.user.myuser
    if user.is_chairman:
        player_list = Players.objects.filter(salesperson__in=Salespeople.objects.filter(
            salesmanager__in=Salesmanagers.objects.filter(shareholder__in=user.chairman.shareholders_set.all())))
    elif user.is_shareholder:
        player_list = Players.objects.filter(salesperson__in=Salespeople.objects.filter(
            salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)))
    elif user.is_salesmanager:
        player_list = Players.objects.filter(
            salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers))
    elif user.is_salesperson:
        player_list = Players.objects.filter(salesperson=user.salespeople)
    return player_list


class RecordDealerTips(PermissionRequiredMixin, View):
    permission_required = 'management.view_dealers'
    template_name = 'management/reward_dealers.html'

    def get(self, request, *args, **kwargs):
        context = {'tip_list': TipsTransaction.objects.order_by('-timestamp')[:50], 'dealer_list': Dealers.objects.all()}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        name = request.POST['name']
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')

        context = {}
        if name.strip() == '':
            context['tip_list'] = TipsTransaction.objects.filter(timestamp__gte=timestart).filter(
                timestamp__lte=timeend)
        else:
            context['tip_list'] = TipsTransaction.objects.filter(dealer=Dealers.objects.get(name=name)).filter(
                timestamp__gte=timestart).filter(timestamp__lte=timeend)
        context['dealer_list'] = Dealers.objects.all()
        return render(request, self.template_name, context)


class RecordPlayerTips(PermissionRequiredMixin, View):
    permission_required = 'management.view_players'
    template_name = 'management/reward_player.html'

    def get(self, request, *args, **kwargs):
        tip_list = TipsTransaction.objects.order_by('-timestamp')[:50]
        return render(request, self.template_name, {'tip_list': tip_list})

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        try:
            player = User.objects.get(username=account).myuser.players
        except:
            player = None

        if not player:
            tip_list = TipsTransaction.objects.filter(timestamp__gte=timestart).filter(timestamp__lte=timeend)
        else:
            tip_list = TipsTransaction.objects.filter(player=player).filter(
                timestamp__gte=timestart).filter(timestamp__lte=timeend)
        return render(request, self.template_name, {'tip_list': tip_list})


class RecordBets(PermissionRequiredMixin, View):
    permission_required = 'management.view_bets'
    template_name = 'management/player_betting.html'

    def get(self, request, *args, **kwargs):
        bet_list = Bets.objects.order_by('-createtime')[:50]
        return render(request, self.template_name, {'bet_list': bet_list})

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        try:
            player = User.objects.get(username=account).myuser.players
        except:
            player = None

        if not player:
            bet_list = Bets.objects.filter(createtime__gte=timestart).filter(createtime__lte=timeend)
        else:
            bet_list = Bets.objects.filter(player=player).filter(createtime__gte=timestart).filter(
                createtime__lte=timeend)
        return render(request, self.template_name, {'bet_list': bet_list})


class RecordGames(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/authority_details.html'

    def get(self, request, *args, **kwargs):
        query_game = Games.objects.order_by('-createtime')[0]
        context = {'query_game': query_game,
                   'bet_list': Bets.objects.filter(game=Games.objects.order_by('-createtime')[0])}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        id = request.POST['id']
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        try:
            game = Games.objects.get(pk=id)
        except:
            game = None

        context = {}
        if not game:
            context['bet_list'] = Bets.objects.filter(createtime__gte=timestart).filter(createtime__lte=timeend)
        else:
            context['bet_list'] = game.bets_set.all()
            context['query_game'] = game
        return render(request, self.template_name, context)


class RecordShareholders(PermissionRequiredMixin, View):
    permission_required = 'management.view_shareholders'
    template_name = 'management/credits_shareholder.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST.get('account', '')
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            shareholder = User.objects.get(username=account).myuser.shareholders
        except:
            shareholder = None

        if not shareholder:
            if user.is_chairman:
                transaction_list = ShareholdersTransaction.objects.filter(
                    shareholder__in=user.chairman.shareholders_set.all()).filter(timestamp__gte=timestart).filter(
                    timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = user.shareholders.shareholderstransaction_set.filter(
                    timestamp__gte=timestart).filter(
                    timestamp__lte=timeend)
        else:
            if user.is_chairman:
                transaction_list = ShareholdersTransaction.objects.filter(
                    shareholder__in=user.chairman.shareholders_set.all()).filter(shareholder=shareholder).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
        return render(request, self.template_name, {'transaction_list': transaction_list})


class RecordSalesmanagers(PermissionRequiredMixin, View):
    permission_required = 'management.view_salesmanagers'
    template_name = 'management/credits_salesmanagers.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST.get('account', '')
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            salesmanager = User.objects.get(username=account).myuser.salesmanagers
        except:
            salesmanager = None

        if not salesmanager:
            if user.is_chairman:
                transaction_list = SalesmanagerTransaction.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all())).filter(timestamp__gte=timestart).filter(
                    timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = SalesmanagerTransaction.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesmanager:
                transaction_list = user.salesmanagers.salesmanagertransaction_set.filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
        else:
            if user.is_chairman:
                transaction_list = SalesmanagerTransaction.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all())).filter(salesmanager=salesmanager).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = SalesmanagerTransaction.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)).filter(
                    salesmanager=salesmanager).filter(timestamp__gte=timestart).filter(timestamp__lte=timeend)
        return render(request, self.template_name, {'transaction_list': transaction_list})


class RecordSalespeople(PermissionRequiredMixin, View):
    permission_required = 'management.view_salespeople'
    template_name = 'management/credits_salespeople.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST.get('account', '')
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            salesperson = User.objects.get(username=account).myuser.salespeople
        except:
            salesperson = None

        if not salesperson:
            if user.is_chairman:
                transaction_list = SalespeopleTransaction.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all()))).filter(timestamp__gte=timestart).filter(
                    timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = SalespeopleTransaction.objects.filter(
                    salesperson__in=Salespeople.objects.filter(
                        salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders))).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesmanager:
                transaction_list = SalespeopleTransaction.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers)).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesperson:
                transaction_list = user.salespeople.salespeopletransaction_set.filter(timestamp__gte=timestart).filter(
                    timestamp__lte=timeend)
        else:
            if user.is_chairman:
                transaction_list = SalespeopleTransaction.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all()))).filter(salesperson=salesperson).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = SalespeopleTransaction.objects.filter(
                    salesperson__in=Salespeople.objects.filter(
                        salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders))).filter(
                    salesperson=salesperson).filter(timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesmanager:
                transaction_list = SalespeopleTransaction.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers)).filter(
                    salesperson=salesperson).filter(timestamp__gte=timestart).filter(timestamp__lte=timeend)
        return render(request, self.template_name, {'transaction_list': transaction_list})


class RecordPlayers(PermissionRequiredMixin, View):
    permission_required = 'management.view_players'
    template_name = 'management/credits_players.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST['account']
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            player = User.objects.get(username=account).myuser.players
        except:
            player = None

        if not player:
            if user.is_chairman:
                transaction_list = PlayersTransaction.objects.filter(player__in=Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all())))).filter(
                    timestamp__gte=timestart).filter(
                    timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = PlayersTransaction.objects.filter(player__in=Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(
                        salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)))).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesmanager:
                transaction_list = PlayersTransaction.objects.filter(player__in=Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers))).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesperson:
                transaction_list = PlayersTransaction.objects.filter(
                    player__in=Players.objects.filter(salesperson=user.salespeople)).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
        else:
            if user.is_chairman:
                transaction_list = PlayersTransaction.objects.filter(player__in=Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all())))).filter(player=player).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_shareholder:
                transaction_list = PlayersTransaction.objects.filter(player__in=Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(
                        salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)))).filter(
                    player=player).filter(timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesmanager:
                transaction_list = PlayersTransaction.objects.filter(player__in=Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers))).filter(
                    player=player).filter(timestamp__gte=timestart).filter(timestamp__lte=timeend)
            elif user.is_salesperson:
                transaction_list = PlayersTransaction.objects.filter(
                    player__in=Players.objects.filter(salesperson=user.salespeople)).filter(player=player).filter(
                    timestamp__gte=timestart).filter(timestamp__lte=timeend)
        return render(request, self.template_name, {'transaction_list': transaction_list})


class BenefitShareholders(PermissionRequiredMixin, View):
    permission_required = 'management.view_shareholders'
    template_name = 'management/share_shareholder.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST.get('account', '')
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            shareholder = User.objects.get(username=account).myuser.shareholders
            shareholder = user.chairman.shareholders_set.get(id=shareholder.id)
        except:
            shareholder = None

        if shareholder:
            sum_shareholder_benefit(shareholder, timestart, timeend)
            if user.is_chairman:
                salesmanager_list = Salesmanagers.objects.filter(
                    shareholder__in=user.chairman.shareholders_set.filter(id=shareholder.id))
        else:
            if user.is_chairman:
                sum_chairman_benefit(user.chairman, timestart, timeend)
                salesmanager_list = Salesmanagers.objects.filter(shareholder__in=user.chairman.shareholders_set.all())
            elif user.is_shareholder:
                sum_shareholder_benefit(user.shareholders, timestart, timeend)
                salesmanager_list = user.shareholders.salesmanagers_set.all()
        return render(request, self.template_name, {'salesmanager_list': salesmanager_list})


class BenefitSalesmanagers(PermissionRequiredMixin, View):
    permission_required = 'management.view_salesmanagers'
    template_name = 'management/share_salesmanagers.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST.get('account', '')
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            salesmanager = User.objects.get(username=account).myuser.salesmanagers
            if user.is_chairman:
                salesmanager = Salesmanagers.objects.filter(shareholder__in=user.chairman.shareholders_set.all()).get(
                    id=salesmanager.id)
            elif user.is_shareholder:
                salesmanager = user.shareholders.salesmanagers_set.get(id=salesmanager.id)
        except:
            salesmanager = None

        if salesmanager:
            sum_salesmanager_benefit(salesmanager, timestart, timeend)
            if user.is_chairman:
                salesperson_list = Salespeople.objects.filter(salesmanager__in=Salesmanagers.objects.filter(
                    shareholder__in=user.chairman.shareholders_set.all()).filter(id=salesmanager.id))
            elif user.is_shareholder:
                salesperson_list = Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders).filter(id=salesmanager.id))
        else:
            if user.is_chairman:
                sum_chairman_benefit(user.chairman, timestart, timeend)
                salesperson_list = Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder__in=user.chairman.shareholders_set.all()))
            elif user.is_shareholder:
                sum_shareholder_benefit(user.shareholders, timestart, timeend)
                salesperson_list = Salespeople.objects.filter(
                    salesmanager__in=user.shareholders.salesmanagers_set.all())
            elif user.is_salesmanager:
                sum_salesmanager_benefit(user.salesmanagers, timestart, timeend)
                salesperson_list = user.salesmanagers.salespeople_set.all()
        return render(request, self.template_name, {'salesperson_list': salesperson_list})


class BenefitSalespeople(PermissionRequiredMixin, View):
    permission_required = 'management.view_salespeople'
    template_name = 'management/share_salespeople.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        account = request.POST.get('account', '')
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        user = request.user.myuser
        try:
            salesperson = User.objects.get(username=account).myuser.salespeople
            if user.is_chairman:
                salesperson = Salespeople.objects.filter(salesmanager__in=Salesmanagers.objects.filter(
                    shareholder__in=user.chairman.shareholders_set.all())).get(id=salesperson.id)
            elif user.is_shareholder:
                salesperson = Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)).get(
                    id=salesperson.id)
            elif user.is_salesmanager:
                salesperson = user.salesmanagers.salespeople_set.get(id=salesperson.id)
        except:
            salesperson = None

        if salesperson:
            sum_salesperson_benefit(salesperson, timestart, timeend)
            if user.is_chairman:
                player_list = Players.objects.filter(salesperson__in=Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all())).filter(id=salesperson.id))
            elif user.is_shareholder:
                player_list = Players.objects.filter(salesperson__in=Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)).filter(
                    id=salesperson.id))
            elif user.is_salesmanager:
                player_list = Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers).filter(
                        id=salesperson.id))
        else:
            if user.is_chairman:
                sum_chairman_benefit(user.chairman, timestart, timeend)
                player_list = Players.objects.filter(salesperson__in=Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(
                        shareholder__in=user.chairman.shareholders_set.all())))
            elif user.is_shareholder:
                sum_shareholder_benefit(user.shareholders, timestart, timeend)
                player_list = Players.objects.filter(salesperson__in=Salespeople.objects.filter(
                    salesmanager__in=Salesmanagers.objects.filter(shareholder=user.shareholders)))
            elif user.is_salesmanager:
                sum_salesmanager_benefit(user.salesmanagers, timestart, timeend)
                player_list = Players.objects.filter(
                    salesperson__in=Salespeople.objects.filter(salesmanager=user.salesmanagers))
            elif user.is_salesperson:
                sum_salesperson_benefit(user.salespeople, timestart, timeend)
                player_list = user.salespeople.players_set.all()
        return render(request, self.template_name, {'player_list': player_list})


class AccountsManagement(PermissionRequiredMixin, generic.ListView):
    permission_required = 'management.add_chairman'  # 注意帳號管理頁面的權限要另外加給顏哥的帳號，跟監官和會計區分開來
    template_name = 'management/account_manage.html'
    model = Chairman
    context_object_name = 'chairman_list'


class Reset(View):
    permission_required = 'management.add_chairman'
    template_name = 'management/private.html'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('management:private'))

    def post(self, request, *args, **kwargs):
        chairman = request.user.myuser.chairman
        shareholder_set = chairman.shareholders_set.all()
        salesmanager_set = Salesmanagers.objects.filter(shareholder__in=shareholder_set)
        salesperson_set = Salespeople.objects.filter(salesmanager__in=salesmanager_set)
        player_set = Players.objects.filter(salesperson__in=salesperson_set)
        context = {'profile': chairman, 'message': '歸零成功'}

        # 寫入紀錄
        for player in player_set:
            player.playerstransaction_set.create(targetname='系統管理員', type='歸零', number=player.creditsleft,
                                                 before=player.creditsleft, after=0)
        for salesperson in salesperson_set:
            salesperson.salespeopletransaction_set.create(targetname='系統管理員', type='歸零', number=salesperson.creditsleft,
                                                          before=salesperson.creditsleft, after=0)
        for salesmanager in salesmanager_set:
            salesmanager.salesmanagertransaction_set.create(targetname='系統管理員', type='歸零',
                                                            number=salesmanager.creditsleft,
                                                            before=salesmanager.creditsleft, after=0)
        for shareholder in shareholder_set:
            shareholder.shareholderstransaction_set.create(targetname='系統管理員', type='歸零',
                                                           number=shareholder.creditsleft,
                                                           before=shareholder.creditsleft, after=0)
            shareholder.shareholderstransaction_set.create(targetname='系統管理員', type='被轉入', number=shareholder.credits,
                                                           before=0, after=shareholder.credits)

        player_set.update(credits=0, creditsleft=0, balance=0, volumes=0, commission=0, tips=0)
        salesperson_set.update(credits=0, creditsleft=0, balance=0, volumes=0, commission=0, tips=0)
        salesmanager_set.update(credits=0, creditsleft=0, balance=0, volumes=0, commission=0, tips=0)
        shareholder_set.update(creditsleft=F('credits'), balance=0, volumes=0, commission=0, tips=0)
        chairman.balance = 0
        chairman.volumes = 0
        chairman.commission = 0
        chairman.tips = 0
        chairman.save()
        return render(request, self.template_name, context)


class GameExecute(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/game_acquiring.html'

    def get(self, request, *args, **kwargs):
        context = {}
        if Dealers.objects.filter(ongame=True):
            context['now_dealer'] = Dealers.objects.get(ongame=True)
        if Games.objects.all():
            context['game'] = Games.objects.order_by('-createtime')[0]
        context['dealer_list'] = Dealers.objects.all()
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        left_points = request.POST['left_points']
        right_points = request.POST['right_points']
        game = Games.objects.order_by('-createtime')[0]
        context = {'now_dealer': Dealers.objects.get(ongame=True),
                   'dealer_list': Dealers.objects.all(),
                   'game': game}

        if game.status != '初始化':
            context['message'] = '遊戲尚未開始'
            return render(request, self.template_name, context)
        if not (check_points_format(left_points) and check_points_format(right_points)):
            context['message'] = '牌型輸入錯誤'
            return render(request, self.template_name, context)
        left_points, right_points = int(left_points), int(right_points)
        if left_points > right_points:
            temp = int(left_points)
            left_points = int(right_points)
            right_points = temp

        in_times, out_times, on_times = get_times(left_points, right_points)
        game.leftpoints = left_points
        game.rightpoints = right_points
        game.intimes = in_times
        game.outtimes = out_times
        game.ontimes = on_times
        game.status = '初始化完成'
        game.save()
        return redirect('/management/game_result')


class ChooseDealer(PermissionRequiredMixin, View):
    permission_required = 'management.view_dealers'
    template_name = 'management/game_acquiring.html'

    def get(self, request, *args, **kwargs):
        return redirect('/management/game_execute')

    def post(self, request, *args, **kwargs):
        name = request.POST['name']

        Dealers.objects.update(ongame=False)
        dealer = Dealers.objects.get(name=name)
        dealer.ongame = True
        dealer.save()
        return redirect('/management/game_execute')


class GameResult(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/game_result.html'

    def get(self, request):
        game = Games.objects.order_by('-createtime')[0]
        now_dealer = Dealers.objects.get(ongame=True)

        return render(request, self.template_name, {'game': game, 'now_dealer': now_dealer})

    def post(self, request):
        result_points = request.POST['result_points']
        game = Games.objects.order_by('-createtime')[0]
        context = {'now_dealer': Dealers.objects.get(ongame=True),
                   'game': game}

        if game.status != '開牌中':
            context['message'] = '非開牌階段'
            return render(request, self.template_name, context)
        if not check_points_format(result_points):
            context['message'] = '牌型輸入錯誤'
            return render(request, self.template_name, context)

        game_result(game, int(result_points))
        player_result(game)
        game.resultpoints = int(result_points)
        game.status = '已結算'
        game.save()
        return redirect('/management/game_execute')


class CurrentTimes(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/current_times.html'

    def get(self, request):
        game = Games.objects.latest()
        return render(request, self.template_name, {'game_id': game.id, 'in_times': game.intimes,
                                                    'out_times': game.outtimes, 'on_times': game.ontimes})


class GameRecord(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/game_history.html'

    def get(self, request):
        return render(request, self.template_name, {'game_list': Games.objects.order_by('-createtime')[:50]})

    def post(self, request):
        id = request.POST['id']
        dates = request.POST['dates']
        timestart = datetime.datetime.strptime(dates.split(' - ')[0], '%Y年%m月%d日 %H:%M')
        timeend = datetime.datetime.strptime(dates.split(' - ')[1], '%Y年%m月%d日 %H:%M')
        try:
            game = Games.objects.get(pk=id)
        except ObjectDoesNotExist:
            game = None

        if game:
            game_list = Games.objects.filter(pk=id)
        else:
            game_list = Games.objects.filter(createtime__gte=timestart).filter(createtime__lte=timeend)
        return render(request, self.template_name, {'game_list': game_list})


class DeleteGame(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/game_history.html'

    def post(self, request, *args, **kwargs):
        id = request.POST['id']
        game = Games.objects.get(pk=id)

        game.status = '已取消'
        game.save()

        if game.status == '已結算':
            for bets in game.bets_set.all():
                player = bets.player
                salesperson = player.salesperson
                salesmanager = salesperson.salesmanager
                shareholder = salesmanager.shareholder
                chairman = shareholder.chairman

                player.playerstransaction_set.create(type='派彩', number=(-bets.balance), before=player.creditsleft, after=player.creditsleft-bets.balance)
                player.creditsleft -= bets.balance
                player.balance -= bets.balance
                player.volumes -= bets.totalbets
                player.commission -= bets.commission
                player.save()
                salesperson.balance -= bets.balance
                salesperson.volumes -= bets.totalbets
                salesperson.commission -= bets.commission
                salesperson.save()
                salesmanager.balance -= bets.balance
                salesmanager.volumes -= bets.totalbets
                salesmanager.commission -= bets.commission
                salesmanager.save()
                shareholder.balance -= bets.balance
                shareholder.volumes -= bets.totalbets
                shareholder.commission -= bets.commission
                shareholder.save()
                chairman.balance -= bets.balance
                chairman.volumes -= bets.totalbets
                chairman.commission -= bets.commission
                chairman.save()
        else:
            for bets in game.bets_set.all():
                player = bets.player
                if bets.is_banker:
                    number = game.times * settings.CREDITS_BASELIMIT
                else:
                    number = bets.totalbets
                player.playerstransaction_set.create(type='派彩', number=number, before=player.creditsleft, after=player.creditsleft+number)
                player.creditsleft += number
                player.save()
        game.bets_set.all().delete()
        return HttpResponseRedirect(reverse('management:game_record'))


class ChangeGame(PermissionRequiredMixin, View):
    permission_required = 'management.view_games'
    template_name = 'management/game_acquiring.html'

    def post(self, request, *args, **kwargs):
        id = request.POST['id']
        left_points = request.POST['left_points']
        right_points = request.POST['right_points']
        result_points = request.POST['result_points']

        context = {'dealer_list': Dealers.objects.all(), 'message': ''}
        if Dealers.objects.filter(ongame=True):
            context['now_dealer'] = Dealers.objects.get(ongame=True)
        if Games.objects.all():
            context['game'] = Games.objects.latest()
        try:
            game = Games.objects.get(pk=id)
        except ObjectDoesNotExist:
            context['message'] = '此局號不存在'
            return render(request, self.template_name, context)
        if game.status != '已結算':
            context['message'] = '欲更改牌局未結算，無法更改'
            return render(request, self.template_name, context)
        if not (check_points_format(left_points) and check_points_format(right_points) and check_points_format(result_points)):
            context['message'] = '牌型輸入錯誤'
            return render(request, self.template_name, context)
        left_points, right_points, result_points = int(left_points), int(right_points), int(result_points)
        if left_points > right_points:
            temp = int(left_points)
            left_points = int(right_points)
            right_points = temp

        # undo
        for bets in game.bets_set.all():
            player = bets.player
            salesperson = player.salesperson
            salesmanager = salesperson.salesmanager
            shareholder = salesmanager.shareholder
            chairman = shareholder.chairman

            if bets.is_banker:
                number = game.times * settings.CREDITS_BASELIMIT + bets.balance
            else:
                number = bets.totalbets + bets.balance
            player.playerstransaction_set.create(type='下注', number=number, before=player.creditsleft,
                                                 after=player.creditsleft-number)
            player.creditsleft -= number
            player.balance -= bets.balance
            player.volumes -= bets.totalbets
            player.commission -= bets.commission
            player.save()
            salesperson.balance -= bets.balance
            salesperson.volumes -= bets.totalbets
            salesperson.commission -= bets.commission
            salesperson.save()
            salesmanager.balance -= bets.balance
            salesmanager.volumes -= bets.totalbets
            salesmanager.commission -= bets.commission
            salesmanager.save()
            shareholder.balance -= bets.balance
            shareholder.volumes -= bets.totalbets
            shareholder.commission -= bets.commission
            shareholder.save()
            chairman.balance -= bets.balance
            chairman.volumes -= bets.totalbets
            chairman.commission -= bets.commission
            chairman.save()

        # redo
        in_times, out_times, on_times = get_times(left_points, right_points)
        game.leftpoints, game.rightpoints, game.resultpoints = left_points, right_points, result_points
        game.intimes, game.outtimes, game.ontimes = in_times, out_times, on_times
        game.save()
        game_result(game, result_points)
        player_result(game)
        return HttpResponseRedirect(reverse('management:game_execute'))


class EditProfile(LoginRequiredMixin, View):
    template_name = 'management/private.html'

    def get(self, request, *args, **kwargs):
        user = request.user.myuser
        if user.is_chairman:
            profile = user.chairman
        elif user.is_shareholder:
            profile = user.shareholders
        elif user.is_salesmanager:
            profile = user.salesmanagers
        elif user.is_salesperson:
            profile = user.salespeople
        return render(request, self.template_name, {'profile': profile})

    def post(self, request, *args, **kwargs):
        name = request.POST['name']
        password = request.POST['password']

        context = {'message': ''}
        user = request.user
        if user.myuser.is_chairman:
            context['profile'] = user.myuser.chairman
        elif user.myuser.is_shareholder:
            context['profile'] = user.myuser.shareholders
        elif user.myuser.is_salesmanager:
            context['profile'] = user.myuser.salesmanagers
        elif user.myuser.is_salesperson:
            context['profile'] = user.myuser.salespeople

        if len(name) > 20:
            context['message'] = '姓名需小於20個字元'
        if len(password) > 20:
            context['message'] = '密碼需小於20個字元'
        if Myuser.objects.filter(name=name):
            context['message'] = '此名稱已被使用'
        if context['message']:
            return render(request, self.template_name, context)

        myuser = Myuser.objects.get(user=user)
        if password.strip():
            user.set_password(password)
            user.save()
            myuser.password_visible = password
            myuser.save()
            login(request, user)
        if name.strip():
            try:
                myuser.name = name
                myuser.save()
            except:
                context['message'] = '名稱不能包含特殊符號，請檢查❌'
                return render(request, self.template_name, context)

        return HttpResponseRedirect(reverse('management:private'))


class PlayerPrivate(LoginRequiredMixin, View):
    login_url = '/management/login/'
    template_name = 'management/player_private.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {'profile': request.user.myuser.players})

    def post(self, request, *args, **kwargs):
        name = request.POST['name']

        context = {'profile': request.user.myuser.players, 'message': ''}
        if name.strip():
            if len(name) > 20:
                context['message'] = '姓名需小於20個字元'
                return render(request, self.template_name, context)
            if Myuser.objects.filter(name=name):
                context['message'] = '此名稱已被使用'
                return render(request, self.template_name, context)
            user = request.user.myuser
            try:
                user.name = name
                user.save()
            except:
                context['message'] = '名稱不能包含特殊符號，請檢查❌'
                return render(request, self.template_name, context)
            context['profile']: user.players
        return render(request, self.template_name, context)


class Backstage(View):
    template_name = 'management/back_stage.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden()

        player_list = []
        for player in Players.objects.all():
            if (player.credits - player.balance) != player.creditsleft:
                player_list.append(player.user.user.username)
        return render(request, self.template_name, {'player_list': player_list})


class Initialize(View):
    template_name = 'management/back_stage.html'

    def post(self, request):
        if not request.user.is_superuser:
            return HttpResponseForbidden()

        initializer = Initializer()
        message = initializer.initialize_all()
        return render(request, self.template_name, {'message': message})


# 回傳使用者傳來的訊息
@csrf_exempt
def callback(request):
    if request.method == 'POST':
        signature = request.META['HTTP_X_LINE_SIGNATURE']
        body = request.body.decode('utf-8')

        try:
            events = parser.parse(body, signature)  # 傳入的事件
        except InvalidSignatureError:
            return HttpResponseForbidden()
        except LineBotApiError:
            return HttpResponseBadRequest()

        for event in events:
            if isinstance(event, MessageEvent):  # 如果有訊息事件
                receive_message = event.message.text
                send_message = ''
                user_id = event.source.user_id

                if event.source.type == 'group':
                    display_name = line_bot_api.get_group_member_profile(event.source.group_id, user_id).display_name

                    if event.source.group_id == 'Cf3cca6c9388b241df69ea5de82185f30':  # 群組訊息
                        try:
                            player = Players.objects.get(lineid=user_id)
                        except ObjectDoesNotExist:
                            player = None

                        if check_player(player):
                            if player.is_gamemanager:
                                if receive_message == '遊戲開始':
                                    send_message = game_start(player)
                                elif receive_message == '開始下注':
                                    send_message = start_place_bet()
                                elif receive_message == '停止下注':
                                    send_message = stop_place_bet()
                                elif receive_message == '最新戰績':
                                    send_message = report_game_result_newest()
                                elif re.match(r'歷史戰績 \d+', receive_message):
                                    send_message = game_history(receive_message[5:])
                            else:
                                if re.match(r'[a-cA-C]{1}\d+', receive_message):
                                    abets, bbets, cbets = 0, 0, 0
                                    try:
                                        for bets in receive_message.split(' '):
                                            if bets[0].lower() == 'a':
                                                abets = int(bets[1:])
                                            elif bets[0].lower() == 'b':
                                                bbets = int(bets[1:])
                                            elif bets[0].lower() == 'c':
                                                cbets = int(bets[1:])
                                        send_message = place_bet(abets, bbets, cbets, player)
                                    except:
                                        send_message = display_name + ' 下注失敗，下注格式為\'a500 B1000 C1000\'(大小寫皆可，須為正整數)'
                                elif receive_message == '取消下注':
                                    send_message = cancel_place_bet(player)
                                elif re.match(r'打賞 \d+', receive_message):
                                    send_message = give_tips(int(receive_message[3:]), player)
                                elif re.findall(r'打賞|打賞\d+', receive_message):
                                    send_message = display_name + '打賞失敗，打賞格式為\'打賞 1000\'(須注意空格)'
                        else:
                            send_message = display_name + ' 尚未註冊或綁定，請檢查❌'
                elif event.source.type == 'user':
                    display_name = line_bot_api.get_profile(user_id).display_name
                    if receive_message == '綁定':
                        send_message = '舉例=>\n帳號:selina999\n密碼:123456\n\n指令=>\n綁定 selina999//123456'
                    elif re.match(r'綁定 [a-zA-Z0-9]+//[a-zA-Z0-9]+', receive_message):
                        account = receive_message[3:].split('//')[0]
                        password = receive_message[3:].split('//')[1]
                        send_message = bind(request, account, password, user_id)
                    elif receive_message == '解綁':
                        send_message = unbind(user_id)
                    elif receive_message == '餘額':
                        send_message = player_creditsleft(user_id)
                    elif receive_message == '紀錄':
                        send_message = player_bets(user_id)
                    elif receive_message == '牌路':
                        send_message = report_game_result()

                if send_message:
                    line_bot_api.reply_message(  # 回復傳入的訊息文字
                        event.reply_token,
                        TextSendMessage(text=send_message)
                    )

        return HttpResponse()
    else:
        return HttpResponseBadRequest()


# 用於依照時間計算分潤
def sum_chairman_benefit(chairman, timestart, timeend):
    querybalance = 0
    queryvolumes = 0
    querycommission = 0
    querytips = 0
    for shareholder in chairman.shareholders_set.all():
        sum_shareholder_benefit(shareholder, timestart, timeend)
        querybalance += shareholder.querybalance
        queryvolumes += shareholder.queryvolumes
        querycommission += shareholder.querycommission
        querytips += shareholder.querytips
    chairman.querybalance = querybalance
    chairman.queryvolumes = queryvolumes
    chairman.querycommission = querycommission
    chairman.querytips = querytips
    chairman.save()


def sum_shareholder_benefit(shareholder, timestart, timeend):
    querybalance = 0
    queryvolumes = 0
    querycommission = 0
    querytips = 0
    for salesmanager in shareholder.salesmanagers_set.all():
        sum_salesmanager_benefit(salesmanager, timestart, timeend)
        querybalance += salesmanager.querybalance
        queryvolumes += salesmanager.queryvolumes
        querycommission += salesmanager.querycommission
        querytips += salesmanager.querytips
    shareholder.querybalance = querybalance
    shareholder.queryvolumes = queryvolumes
    shareholder.querycommission = querycommission
    shareholder.querytips = querytips
    shareholder.save()


def sum_salesmanager_benefit(salesmanager, timestart, timeend):
    querybalance = 0
    queryvolumes = 0
    querycommission = 0
    querytips = 0
    for salesperson in salesmanager.salespeople_set.all():
        sum_salesperson_benefit(salesperson, timestart, timeend)
        querybalance += salesperson.querybalance
        queryvolumes += salesperson.queryvolumes
        querycommission += salesperson.querycommission
        querytips += salesperson.querytips
    salesmanager.querybalance = querybalance
    salesmanager.queryvolumes = queryvolumes
    salesmanager.querycommission = querycommission
    salesmanager.querytips = querytips
    salesmanager.save()


def sum_salesperson_benefit(salesperson, timestart, timeend):
    querybalance = 0
    queryvolumes = 0
    querycommission = 0
    querytips = 0
    for player in salesperson.players_set.all():
        sum_player_bets(player, timestart, timeend)
        querybalance += player.querybalance
        queryvolumes += player.queryvolumes
        querycommission += player.querycommission
        querytips += player.querytips
    salesperson.querybalance = querybalance
    salesperson.queryvolumes = queryvolumes
    salesperson.querycommission = querycommission
    salesperson.querytips = querytips
    salesperson.save()


def sum_player_bets(player, timestart, timeend):
    querybalance = 0
    queryvolumes = 0
    querycommission = 0
    querytips = 0
    for bet in player.bets_set.filter(createtime__gte=timestart).filter(createtime__lte=timeend):
        querybalance += bet.balance
        queryvolumes += bet.totalbets
        querycommission += bet.commission
    for tips in player.tipstransaction_set.filter(timestamp__gte=timestart).filter(timestamp__lte=timeend):
        querytips += tips.tips
    player.querybalance = querybalance - querytips
    player.queryvolumes = queryvolumes
    player.querycommission = querycommission
    player.querytips = querytips
    player.save()


# 計算倍率，必須right > left
def get_times(left_points, right_points):
    num_to_times = {0: 0.00, 1: 10.00, 2: 5.19, 3: 3.46, 4: 2.66, 5: 2.13, 6: 1.77,
                    7: 1.52, 8: 1.41, 9: 1.29, 10: 1.19, 11: 1.08, 12: 1.02}
    if right_points == left_points:
        in_times = num_to_times[0]
        out_times = num_to_times[12]
        on_times = 20
    else:
        in_times = num_to_times[right_points-left_points-1]
        out_times = num_to_times[13-right_points+left_points-1]
        on_times = 7
    return in_times, out_times, on_times


# 遊戲結算
def game_result(game, result_points):
    left_points = game.leftpoints
    right_points = game.rightpoints

    if left_points < result_points < right_points:
        game.result = 'A'
        game.outtimes, game.ontimes = -1, -1
    elif result_points < left_points or result_points > right_points:
        game.result = 'B'
        game.intimes, game.ontimes = -1, -1
    else:
        game.result = 'C'
        game.intimes, game.outtimes = -1, -1
    game.save()


def player_result(game):
    banker_balance = 0
    banker_totalbets = 0

    # 一般玩家結算
    for bet in game.bets_set.exclude(is_banker=True):
        player = bet.player

        # 輸贏與抽水計算
        a_balance = bet.abets * game.intimes
        b_balance = bet.bbets * game.outtimes
        c_balance = bet.cbets * game.ontimes
        banker_balance -= a_balance + b_balance + c_balance
        banker_totalbets += bet.totalbets

        commission = 0
        if a_balance > 0:
            commission = round(a_balance * settings.COMMISSION_PERCENTAGE / 100)
            a_balance -= commission
        elif b_balance > 0:
            commission = round(b_balance * settings.COMMISSION_PERCENTAGE / 100)
            b_balance -= commission
        elif c_balance > 0:
            commission = round(c_balance * settings.COMMISSION_PERCENTAGE / 100)
            c_balance -= commission

        bet.balance = a_balance + b_balance + c_balance
        bet.commission = commission
        bet.save()

        player.playerstransaction_set.create(type='派彩', number=bet.totalbets + bet.balance, before=player.creditsleft,
                                             after=player.creditsleft + bet.totalbets + bet.balance)
        player.creditsleft += bet.totalbets + bet.balance
        player.balance += bet.balance
        player.volumes += bet.totalbets
        player.commission += bet.commission
        player.save()

    # 莊家結算(等banker_balance計算好)
    bet = game.bets_set.get(is_banker=True)
    player = bet.player
    bet.totalbets = banker_totalbets

    # 莊家bet資訊計算
    if banker_balance > 0:
        bet.commission = round(banker_balance * settings.COMMISSION_PERCENTAGE / 100)
        bet.balance = banker_balance - bet.commission
    else:
        bet.commission = 0
        bet.balance = banker_balance
    bet.save()
    # 莊家player處理
    number = game.times * settings.CREDITS_BASELIMIT + bet.balance  # 要返還的莊家信用
    player.playerstransaction_set.create(type='派彩', number=number, before=player.creditsleft,
                                         after=player.creditsleft + number)
    player.creditsleft += number
    player.balance += bet.balance
    player.volumes += bet.totalbets
    player.commission += bet.commission
    player.save()

    # 資料往上更新
    for bet in game.bets_set.all():
        salesperson = bet.player.salesperson
        salesmanager = salesperson.salesmanager
        shareholder = salesmanager.shareholder
        chairman = shareholder.chairman

        salesperson.volumes += bet.totalbets
        salesperson.balance += bet.balance
        salesperson.commission += bet.commission
        salesperson.save()
        salesmanager.volumes += bet.totalbets
        salesmanager.balance += bet.balance
        salesmanager.commission += bet.commission
        salesmanager.save()
        shareholder.volumes += bet.totalbets
        shareholder.balance += bet.balance
        shareholder.commission += bet.commission
        shareholder.save()
        chairman.volumes += bet.totalbets
        chairman.balance += bet.balance
        chairman.commission += bet.commission
        chairman.save()


# 初始化遊戲
def game_start(player):
    last_game = Games.objects.latest()

    if not (last_game.status == '已結算' or last_game.status == '已取消'):
        return '前一局尚未結算完成❌'
    if player.creditsleft < settings.CREDITS_BASELIMIT:
        return player.user.name + '莊家餘額不足❌'

    # 建立遊戲
    game = Dealers.objects.get(ongame=True).games_set.create()
    player.playerstransaction_set.create(type='下注', number=settings.CREDITS_BASELIMIT, before=player.creditsleft,
                                         after=player.creditsleft - settings.CREDITS_BASELIMIT)
    player.creditsleft -= settings.CREDITS_BASELIMIT
    player.save()
    player.bets_set.create(game=game, is_banker=True)

    message = '開始遊戲▶️\n\n' \
              '♥️♠️牌局資訊♦️♣️\n'
    message += '局號：' + str(game.id) + '\n'
    message += '每門上限：' + str(settings.GAME_BASELIMIT) + '\n'
    message += '單注上限：' + str(settings.BETS_BASELIMIT)
    return message


# 開始下注
def start_place_bet():
    game = Games.objects.latest()

    if game.status != '初始化完成':
        return '尚未完成初始化❌'

    game.status = '下注中'
    game.save()

    message = '💰開始下注💰 ️\n\n' \
              '♥️♠️牌局資訊♦️♣️\n'
    message += '局號：' + str(game.id) + '\n'
    message += '每門上限：' + str(settings.GAME_BASELIMIT) + '\n'
    message += '單注上限：' + str(settings.BETS_BASELIMIT) + '\n'
    message += 'A門賠率: ' + str(game.intimes) + '\n'
    message += 'B門賠率: ' + str(game.outtimes) + '\n'
    message += 'C門賠率: ' + str(game.ontimes) + '\n'
    return message


# 停止下注
def stop_place_bet():
    game = Games.objects.latest()
    if game.status != '下注中':
        return '目前非下注階段❌'
    game.status = '開牌中'
    game.save()

    abets_total = settings.GAME_BASELIMIT - game.inlimit
    bbets_total = settings.GAME_BASELIMIT - game.outlimit
    cbets_total = settings.GAME_BASELIMIT - game.onlimit
    allbets_total = abets_total + bbets_total + cbets_total
    message = '♥️♠️下注列表♦️♣️\n'
    message += '局號：' + str(game.id) + '\n'
    message += '每門上限：' + str(settings.GAME_BASELIMIT) + '\n'
    message += '單注上限：' + str(settings.BETS_BASELIMIT) + '\n'
    message += 'A門賠率: ' + str(game.intimes) + '\n'
    message += 'B門賠率: ' + str(game.outtimes) + '\n'
    message += 'C門賠率: ' + str(game.ontimes) + '\n'
    message += '==================\n\n'
    for bets in game.bets_set.exclude(is_banker=True):
        message += bets.player.user.name + ' 🚀\n'
        if bets.abets > 0:
            message += 'A | ' + str(bets.abets) + '\n'
        if bets.bbets > 0:
            message += 'B | ' + str(bets.bbets) + '\n'
        if bets.cbets > 0:
            message += 'C | ' + str(bets.cbets) + '\n'
        message += '------------------------\n'
    message += '\n======下注總額======\n'
    message += 'A | ' + str(abets_total) + '\n'
    message += 'B | ' + str(bbets_total) + '\n'
    message += 'C | ' + str(cbets_total) + '\n'
    message += '總計：' + str(allbets_total)
    return message


# 最新戰積
def report_game_result_newest():
    game = Games.objects.filter(status='已結算').latest()

    message = '♥️♠️戰績結算♦️♣️\n'
    message += '局號：' + str(game.id) + '\n'
    message += '每門上限：' + str(settings.GAME_BASELIMIT) + '\n'
    message += '單注上限：' + str(settings.BETS_BASELIMIT) + '\n'
    message += 'A門賠率: ' + str(game.intimes) + '\n'
    message += 'B門賠率: ' + str(game.outtimes) + '\n'
    message += 'C門賠率: ' + str(game.ontimes) + '\n\n'
    message += '龍門\n'
    message += '┏━┓    ┏━┓\n'
    message += '┃' + number_sign(game.leftpoints) + '┃' + number_sign(game.resultpoints) + '┃' + number_sign(game.rightpoints) + '┃\n'
    message += '┗━┛    ┗━┛\n'
    message += '\n======玩家輸贏======\n\n'
    for bets in game.bets_set.exclude(is_banker=True):
        message += bets.player.user.name + ' 🚀\n'
        if bets.abets > 0:
            message += 'A | ' + str(round(bets.abets * game.intimes)) + '\n'
        if bets.bbets > 0:
            message += 'B | ' + str(round(bets.bbets * game.outtimes)) + '\n'
        if bets.cbets > 0:
            message += 'C | ' + str(round(bets.cbets * game.ontimes)) + '\n'
        message += '總計：' + str(bets.balance) + '\n'
        message += '------------------------\n'
    message += '\n======莊家輸贏======\n'
    message += '總計：' + str(game.bets_set.get(is_banker=True).balance)
    return message


# 歷史戰績
def game_history(game_id):
    try:
        game = Games.objects.get(pk=game_id)
    except ObjectDoesNotExist:
        return '該遊戲局號不存在❌'

    if game.status == '已取消':
        return '局號: ' + str(game_id) + ' ❌已取消❌'

    message = '♥️♠️戰績結算♦️♣️\n'
    message += '局號：' + str(game.id) + '\n'
    message += '每門上限：' + str(settings.GAME_BASELIMIT) + '\n'
    message += '單注上限：' + str(settings.BETS_BASELIMIT) + '\n'
    message += 'A門賠率: ' + str(game.intimes) + '\n'
    message += 'B門賠率: ' + str(game.outtimes) + '\n'
    message += 'C門賠率: ' + str(game.ontimes) + '\n\n'
    message += '龍門\n'
    message += '┏━┓    ┏━┓\n'
    message += '┃' + number_sign(game.leftpoints) + '┃' + number_sign(game.resultpoints) + '┃' + number_sign(
        game.rightpoints) + '┃\n'
    message += '┗━┛    ┗━┛\n'
    message += '\n======玩家輸贏======\n\n'
    for bets in game.bets_set.exclude(is_banker=True):
        message += bets.player.user.name + ' 🚀\n'
        if bets.abets > 0:
            message += 'A | ' + str(round(bets.abets * game.intimes)) + '\n'
        if bets.bbets > 0:
            message += 'B | ' + str(round(bets.bbets * game.outtimes)) + '\n'
        if bets.cbets > 0:
            message += 'C | ' + str(round(bets.cbets * game.ontimes)) + '\n'
        message += '總計：' + str(bets.balance) + '\n'
        message += '------------------------\n'
    message += '\n======莊家輸贏======\n'
    message += '總計：' + str(game.bets_set.get(is_banker=True).balance)
    return message


# 下注
def place_bet(abets, bbets, cbets, player):
    game = Games.objects.latest()
    banker = game.bets_set.get(is_banker=True)
    totalbets = abets + bbets + cbets

    if game.status != '下注中':
        return '非下注階段❌'
    if banker.player == player:
        return player.user.name + ' 莊家無法下注❌'
    if totalbets > player.creditsleft:
        return player.user.name + ' 餘額不足，請檢查餘額再下注❌'
    if not (check_bets(abets) and check_bets(bbets) and check_bets(cbets)):
        return player.user.name + ' 下注最低為100❌'

    bets, created = game.bets_set.get_or_create(player=player)
    if abets > game.inlimit or bets.abets + abets > settings.BETS_BASELIMIT:
        return player.user.name + ' 超過本局總上限或單注上限，下注失敗❌'
    if bbets > game.outlimit or bets.bbets + bbets > settings.BETS_BASELIMIT:
        return player.user.name + ' 超過本局總上限或單注上限，下注失敗❌'
    if cbets > game.onlimit or bets.cbets + cbets > settings.BETS_BASELIMIT:
        return player.user.name + ' 超過本局總上限或單注上限，下注失敗❌'
    if not created:
        last_totalbets = bets.abets + bets.bbets + bets.cbets
        if last_totalbets + totalbets > player.creditsleft:
            return player.user.name + ' 餘額不足，請檢查餘額再下注❌'

    player.playerstransaction_set.create(type='下注', number=totalbets, before=player.creditsleft,
                                         after=player.creditsleft - totalbets)
    player.creditsleft -= totalbets
    player.save()
    game.inlimit -= abets
    game.outlimit -= bbets
    game.onlimit -= cbets
    game.save()
    bets.abets += abets
    bets.bbets += bbets
    bets.cbets += cbets
    bets.totalbets += totalbets
    bets.save()

    message = player.user.name + ' 🚀\n'
    if bets.abets > 0:
        message += 'A | ' + str(bets.abets) + '🉐\n'
        message += '單門剩餘：' + str(game.inlimit) + '\n'
    if bets.bbets > 0:
        message += 'B | ' + str(bets.bbets) + '🉐\n'
        message += '單門剩餘：' + str(game.outlimit) + '\n'
    if bets.cbets > 0:
        message += 'C | ' + str(bets.cbets) + '🉐\n'
        message += '單門剩餘：' + str(game.onlimit) + '\n'
    message += '🎉🎉🎉🎉🎉'
    return message


# 取消下注
def cancel_place_bet(player):
    game = Games.objects.latest()
    if game.status != '下注中':
        return '非下注階段❌'

    if game.bets_set.filter(player=player):
        last_bets = player.bets_set.latest('createtime')
        if last_bets.is_banker:
            return player.user.name + '遊戲中莊家無法下莊❌'
        player.playerstransaction_set.create(number=last_bets.totalbets, type='派彩', before=player.creditsleft,
                                             after=player.creditsleft + last_bets.totalbets)
        player.creditsleft += last_bets.totalbets
        player.save()
        game.inlimit += last_bets.abets
        game.outlimit += last_bets.bbets
        game.onlimit += last_bets.cbets
        game.save()
        last_bets.delete()
        return player.user.name + ' 取消下注成功✔️'


# 打賞
def give_tips(tips, player):
    try:
        dealer = Dealers.objects.get(ongame=True)
    except ObjectDoesNotExist:
        return player.user.name + '無荷官在線，無法打賞❌'

    if tips > player.creditsleft:
        return player.user.name + ' 打賞失敗❌'
    if tips <= 0:
        return player.user.name + '打賞請輸入正整數❌'
    if player.is_gamemanager:
        return player.user.name + '打賞失敗❌'

    salesperson = player.salesperson
    salesmanager = salesperson.salesmanager
    shareholder = salesmanager.shareholder
    chairman = shareholder.chairman
    player.tipstransaction_set.create(dealer=dealer, tips=tips)
    dealer.tips += tips
    player.creditsleft -= tips
    player.balance -= tips
    player.tips += tips
    salesperson.tips += tips
    salesmanager.tips += tips
    shareholder.tips += tips
    chairman.tips += tips
    dealer.save()
    player.save()
    salesperson.save()
    salesmanager.save()
    shareholder.save()
    chairman.save()
    return player.user.name + ' 打賞成功🎉🎉🎉'


# Line個人聊天室功能
# 綁定
def bind(request, account, password, lineid):
    user = authenticate(request, username=account, password=password)
    if user is not None:
        player = user.myuser.players
        if player.lineid == lineid:
            return '已綁定'
        elif player.lineid:
            return '您的遊戲帳號已被其他Line帳號綁定❌'
        elif Players.objects.filter(lineid=lineid):
            return '您的line帳號已綁定至其他遊戲帳號❌'
        player.lineid = lineid
        player.save()
        return '綁定成功✔️'
    else:
        return '綁定失敗，請檢查帳號密碼❌'


# 解綁
def unbind(lineid):
    try:
        player = Players.objects.get(lineid=lineid)
    except ObjectDoesNotExist:
        player = None

    if not check_player(player):
        return '尚未綁定或註冊，請檢查❌'
    player.lineid = ''
    player.save()
    return '解除綁定成功✔️'


# 餘額
def player_creditsleft(lineid):
    try:
        player = Players.objects.get(lineid=lineid)
    except ObjectDoesNotExist:
        player = None

    if not check_player(player):
        return '尚未綁定或註冊，請檢查❌'
    message = '帳號: ' + player.user.user.username
    message += '\n名稱: ' + player.user.name
    message += '\n信用: ' + str(player.credits)
    message += '\n可用額度: ' + str(player.creditsleft)
    message += '\n輸贏: ' + str(player.balance)
    return message


# 最近五局下注紀錄
def player_bets(lineid):
    try:
        player = Players.objects.get(lineid=lineid)
    except ObjectDoesNotExist:
        player = None

    if not check_player(player):
        return '尚未綁定或註冊，請檢查❌'

    message = ''
    if player.bets_set.count() >= 5:
        bets = player.bets_set.order_by('-createtime')[:4]
    else:
        bets = player.bets_set.all()
    for bet in bets:
        message += '局號：' + str(bet.game.id) + '\n下注：'
        message += 'A' + str(bet.abets) + ' B' + str(bet.bbets) + ' C' + str(bet.cbets)
        message += '\n總額： ' + str(bet.totalbets)
        message += '\n輸贏： ' + str(bet.balance) + '\n\n'
    return message


# 牌路(最近十局)
def report_game_result():
    games = Games.objects.order_by('-createtime')[0:10]

    message = '牌路為前十局每門輸贏倍數。0為該門輸莊家，1為該門贏莊家。\n\n'
    message += '　Ａ　Ｂ　Ｃ　局號\n'
    message += '┏━┳━┳━┓\n'
    for game in games:
        aresult = 0 if game.intimes == -1 else 1
        bresult = 0 if game.outtimes == -1 else 1
        cresult = 0 if game.ontimes == -1 else 1

        message += '┃' + number_sign(aresult) + '┃'
        message += number_sign(bresult) + '┃'
        message += number_sign(cresult) + '┃' + str(game.id) + '\n'
        message += '┣━╋━╋━┫\n'
    message = message[:len(message)-8]
    message += '┗━┻━┻━┛'
    return message


def number_sign(number):
    sign = {-1: '⓪', 0: '⓪', 1: '❶', 2: '❷', 3: '➌', 4: '❹', 5: '❺', 6: '❻',
            7: '❼', 8: '❽', 9: '❾', 10: '❿', 11: '⓫', 12: '⓬', 13: '⓭'}
    return sign[number]


def check_points_format(points):
    points_list = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13']
    if points in points_list:
        return True
    else:
        return False


# 檢查玩家是否已註冊、綁定、啟用
def check_player(player):
    if not player:
        return False
    if not player.status or player.lineid == '':
        return False
    return True


# 檢查下注是否大於100
def check_bets(bets):
    if bets != 0 and bets < 100:
        return False
    return True
