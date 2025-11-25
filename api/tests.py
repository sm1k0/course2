from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User, CustomerProfile
from catalog.models import Category, Supplier, Product, Stock
from orders.models import Order


class ReportsPermissionTests(APITestCase):
    def setUp(self):
        self.role_admin = Role.objects.create(code='ADMIN', name='Админ')
        self.role_manager = Role.objects.create(code='MANAGER', name='Менеджер')
        self.role_customer = Role.objects.create(code='CUSTOMER', name='Покупатель')

        self.admin = User.objects.create_user(
            username='admin',
            password='adminpass',
            role=self.role_admin,
        )
        self.manager = User.objects.create_user(
            username='manager',
            password='managerpass',
            role=self.role_manager,
        )
        self.customer = User.objects.create_user(
            username='customer',
            password='customerpass',
            role=self.role_customer,
        )

        self.url = reverse('report-sales-daily')

    def test_admin_can_see_report(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(self.url)
        self.assertNotEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_see_report(self):
        self.client.force_authenticate(self.manager)
        res = self.client.get(self.url)
        self.assertNotEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_customer_forbidden(self):
        self.client.force_authenticate(self.customer)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class SqlInjectionSafetyTests(APITestCase):
    def setUp(self):
        self.role_customer = Role.objects.create(code='CUSTOMER', name='Покупатель')
        self.user = User.objects.create_user(
            username='user',
            password='userpass',
            role=self.role_customer,
        )
        self.url = reverse('product-list')

    def test_search_injection_does_not_break(self):
        self.client.force_authenticate(self.user)
        res = self.client.get(self.url, {'search': "'; DROP TABLE products; --"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class SalesReportCsvTests(APITestCase):
    def setUp(self):
        role_admin = Role.objects.create(code='ADMIN', name='Админ')
        role_customer = Role.objects.create(code='CUSTOMER', name='Покупатель')
        self.admin = User.objects.create_user(
            username='report_admin',
            password='pass123',
            role=role_admin,
        )
        customer_user = User.objects.create_user(
            username='buyer',
            password='pass123',
            role=role_customer,
        )
        customer_profile = CustomerProfile.objects.create(
            user=customer_user,
            full_name='Test Buyer',
            phone='123456',
            default_address='Test address',
        )
        category = Category.objects.create(name='Овощи', slug='ovoshi')
        supplier = Supplier.objects.create(name='Поставщик')
        self.product = Product.objects.create(
            name='Картофель',
            sku='POT-1',
            category=category,
            supplier=supplier,
            price=Decimal('100.00'),
        )
        Stock.objects.create(product=self.product, quantity=5)
        self.order = Order.objects.create(
            customer=customer_profile,
            status=Order.Status.COMPLETED,
            total_amount=Decimal('200.00'),
            created_by=self.admin,
            delivery_address='Test address',
            comment='',
        )

    def test_sales_report_endpoint_accessible(self):
        self.client.force_authenticate(self.admin)
        url = reverse('report-sales-daily')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
