from django.urls import path

from . import views

app_name = 'management'
urlpatterns = [
    path('', views.Login.as_view(), name='login'),  # done
    path('logout/', views.logout, name='logout'),  # done
    path('private/', views.Private.as_view(), name='private'),  # done
    path('register_chairman/', views.RegisterChairman.as_view(), name='register_chairman'),  # done
    path('register_shareholder/', views.RegisterShareholder.as_view(), name='register_shareholder'),  # done
    path('register_salesmanager/', views.RegisterSalesmanager.as_view(), name='register_salesmanager'),  # done
    path('register_salesperson/', views.RegisterSalesperson.as_view(), name='register_salesperson'),  # done
    path('register_player/', views.RegisterPlayer.as_view(), name='register_player'),  # done
    path('register_dealer/', views.RegisterDealer.as_view(), name='register_dealer'),  # done
    path('staff_shareholders/', views.StaffShareholders.as_view(), name='staff_shareholders'),  # done
    path('staff_salesmanagers/', views.StaffSalesmanagers.as_view(), name='staff_salesmanagers'),  # done
    path('staff_salespeople/', views.StaffSalespeople.as_view(), name='staff_salespeople'),  # done
    path('staff_players/', views.StaffPlayers.as_view(), name='staff_players'),  # done
    path('staff_dealers/', views.StaffDealers.as_view(), name='staff_dealers'),  # done
    path('change_credits_shareholder/', views.ChangeCreditsShareholder.as_view(), name='change_credits_shareholder'),  # done
    path('change_credits_salesmanager/', views.ChangeCreditsSalesmanager.as_view(), name='change_credits_salesmanager'),  # done
    path('change_credits_salesperson/', views.ChangeCreditsSalesperson.as_view(), name='change_credits_salesperson'),  # done
    path('change_credits_player/', views.ChangeCreditsPlayer.as_view(), name='change_credits_player'),  # done
    path('change_basebonus/', views.ChangeBasebonus.as_view(), name='change_basebonus'),  # done
    path('change_status/', views.ChangeStatus.as_view(), name='change_status'),  # 區段1:以上為人員管理 done
    path('record_dealertips/', views.RecordDealerTips.as_view(), name='record_dealer_tips'),  # done
    path('record_playertips/', views.RecordPlayerTips.as_view(), name='record_player_tips'),  # done
    path('record_bets/', views.RecordBets.as_view(), name='record_bets'),  # done
    path('record_games/', views.RecordGames.as_view(), name='record_games'),  # done
    path('record_shareholders/', views.RecordShareholders.as_view(), name='record_shareholders'),  # 有沒有查詢功能? done
    path('record_salesmanagers/', views.RecordSalesmanagers.as_view(), name='record_salesmanagers'),  # done
    path('record_salespeople/', views.RecordSalespeople.as_view(), name='record_salespeople'),  # done
    path('record_players/', views.RecordPlayers.as_view(), name='record_players'),  # done
    path('benefit_shareholders/', views.BenefitShareholders.as_view(), name='benefit_shareholders'),  # done
    path('benefit_salesmanagers/', views.BenefitSalesmanagers.as_view(), name='benefit_salesmanagers'),  # done
    path('benefit_salespeople/', views.BenefitSalespeople.as_view(), name='benefit_salespeople'),  # 區段2:以上為報表管理 done
    path('accounts_management/', views.AccountsManagement.as_view(), name='accounts_management'),  # done
    path('reset/', views.Reset.as_view(), name='reset'),  # 區段3:以上為帳號管理 done
    path('game_execute/', views.GameExecute.as_view(), name='game_execute'),  # 牌型輸入
    path('choose_dealer/', views.ChooseDealer.as_view(), name='choose_dealer'),  # 遊戲管理中可選荷官
    path('game_result/', views.GameResult.as_view(), name='game_result'),  # 結果輸入
    path('current_times/', views.CurrentTimes.as_view(), name='current_times'),
    path('game_record/', views.GameRecord.as_view(), name='game_record'),
    path('delete_game/', views.DeleteGame.as_view(), name='delete_game'),
    path('change_game/', views.ChangeGame.as_view(), name='change_game'),  # 區段4:以上為遊戲管理
    # game_record為遊戲的結果與狀態(針對遊戲管理)，record_game為遊戲的玩家下注與流水等(針對報表管理，顯示詳細資訊)
    path('edit_profile/', views.EditProfile.as_view(), name='edit_profile'),  # 改個人資料
    path('player_private/', views.PlayerPrivate.as_view(), name='player_private'),
    path('back_stage/', views.Backstage.as_view(), name='back_stage'),
    path('initialize/', views.Initialize.as_view(), name='initialize'),
    path('callback/', views.callback, name='callback'),  # line聊天功能
]
