from django.test import TestCase
from django.contrib.auth.models import Group

from .models import Chairman, Shareholders, Salesmanagers, Salespeople, Players
from .views import get_times, check_points_format


# Create your tests here.
class TimesTest(TestCase):
    def test_get_times_right_bigger_than_left(self):
        in_times, out_times, on_times = get_times(5, 10)
        self.assertEqual(in_times, 2.66)
        self.assertEqual(out_times, 1.52)
        self.assertEqual(on_times, 7)

    def test_get_times_left_equal_to_right(self):
        in_times, out_times, on_times = get_times(7, 7)
        self.assertEqual(in_times, 0)
        self.assertEqual(out_times, 1.02)
        self.assertEqual(on_times, 20)

    def test_check_points_format_in_range(self):
        self.assertIs(check_points_format('1'), True)
        self.assertIs(check_points_format('6'), True)
        self.assertIs(check_points_format('13'), True)

    def test_check_points_format_out_of_range(self):
        self.assertIs(check_points_format('0'), False)
        self.assertIs(check_points_format('14'), False)

    def test_check_points_format_not_integer(self):
        self.assertIs(check_points_format('string'), False)
        self.assertIs(check_points_format(True), False)

    def test_check_points_format_is_negative(self):
        self.assertIs(check_points_format('-5'), False)


class ModelsTest(TestCase):
    def test_create_chairman(self):
        chairman = Chairman.create_chairman('chairman', '123456', 'chairman', 20000000)
        self.assertEqual(chairman.user.user.groups.all()[0], Group.objects.get(name='chairmen'))
        self.assertEqual(chairman.creditsleft, 20000000)

    def test_create_shareholder(self):
        chairman = Chairman.create_chairman('chairman', '123456', 'chairman', 20000000)
        shareholder = Shareholders.create_shareholder(chairman, 'shareholder', '123456', 'shareholder', 5000000, 100)
        self.assertEqual(shareholder.user.user.groups.all()[0], Group.objects.get(name='shareholders'))
        self.assertEqual(shareholder.chairman, chairman)
        self.assertEqual(shareholder.creditsleft, 5000000)

    def test_create_salesmanager(self):
        chairman = Chairman.create_chairman('chairman', '123456', 'chairman', 20000000)
        shareholder = Shareholders.create_shareholder(chairman, 'shareholder', '123456', 'shareholder', 5000000, 100)
        salesmanager = Salesmanagers.create_salesmanager(shareholder, 'salesmanager', '123456', 'salesmanager', 1000000)
        self.assertEqual(salesmanager.user.user.groups.all()[0], Group.objects.get(name='salesmanagers'))
        self.assertEqual(salesmanager.shareholder, shareholder)
        self.assertEqual(salesmanager.creditsleft, 1000000)

    def test_create_salesperson(self):
        chairman = Chairman.create_chairman('chairman', '123456', 'chairman', 20000000)
        shareholder = Shareholders.create_shareholder(chairman, 'shareholder', '123456', 'shareholder', 5000000, 100)
        salesmanager = Salesmanagers.create_salesmanager(shareholder, 'salesmanager', '123456', 'salesmanager', 1000000)
        salesperson = Salespeople.create_salesperson(salesmanager, 'salesperson', '123456', 'salesperson', 300000)
        self.assertEqual(salesperson.user.user.groups.all()[0], Group.objects.get(name='salespeople'))
        self.assertEqual(salesperson.salesmanager, salesmanager)
        self.assertEqual(salesperson.creditsleft, 300000)

    def test_create_player(self):
        chairman = Chairman.create_chairman('chairman', '123456', 'chairman', 20000000)
        shareholder = Shareholders.create_shareholder(chairman, 'shareholder', '123456', 'shareholder', 5000000, 100)
        salesmanager = Salesmanagers.create_salesmanager(shareholder, 'salesmanager', '123456', 'salesmanager', 1000000)
        salesperson = Salespeople.create_salesperson(salesmanager, 'salesperson', '123456', 'salesperson', 300000)
        player = Players.create_player(salesperson, 'player', '123456', 'player', 100000)
        self.assertEqual(player.user.user.groups.all()[0], Group.objects.get(name='players'))
        self.assertEqual(player.salesperson, salesperson)
        self.assertEqual(player.creditsleft, 100000)
        self.assertIs(player.is_gamemanager, False)
