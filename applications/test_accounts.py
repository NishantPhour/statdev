from __future__ import absolute_import, unicode_literals
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from mixer.backend.django import mixer

# from ledger.accounts.models import Organisation, Address
from ledger_api_client.ledger_models import Address
from .models import Delegate, Organisation
from .tests import StatDevTestCase


User = get_user_model()


#class AccountsTest(StatDevTestCase):
#    """Test views and business rules related to accounts models.
#    """
#
#    def setUp(self):
#        super(AccountsTest, self).setUp()
#        self.org1 = mixer.blend(Organisation)
#        # Make the test customer a delegate for org1
#        Delegate.objects.create(email_user=self.customer, organisation=self.org1)
#        self.org2 = mixer.blend(Organisation)
#
##    def test_user_account_get(self):
##        resp = self.client.get(reverse('user_account'))
##        self.assertEquals(resp.status_code, 200)
#
##    def test_user_account_update_get(self):
##        resp = self.client.get(reverse('user_account_update'))
##        self.assertEquals(resp.status_code, 200)
#
#    def test_user_account_update_post(self):
#        self.client.post(reverse('user_account_update'), {'phone_number': '12345678'})
#        user = User.objects.get(pk=self.user1.pk)
#        self.assertEquals(user.phone_number, '12345678')
#
##    def test_user_address_create_get(self):
##        url = reverse('address_create', args=['postal'])
##        resp = self.client.get(url)
##        self.assertEquals(resp.status_code, 200)
#
##    def test_user_address_create_post(self):
##        self.assertFalse(Address.objects.exists())
##        self.assertFalse(self.user1.billing_address)
##        self.client.post(
##            reverse('address_create', args=['billing']),
##            {'line1': '1 Test Street', 'locality': 'Perth', 'country': 'AU', 'postcode': '6000','user':self.user1}
##        )
##        self.assertTrue(Address.objects.exists())
##        user = User.objects.get(pk=self.user1.pk)
##        self.assertTrue(user.billing_address)
#
#    def test_user_address_update_get(self):
#        address = mixer.blend(Address)
#        self.user1.postal_address = address
#        self.user1.save()
#        url = reverse('address_update', args=[address.pk])
#        resp = self.client.get(url)
#        self.assertEquals(resp.status_code, 200)
#
#    def test_user_address_update_post(self):
#        address = mixer.blend(Address)
#        self.user1.postal_address = address
#        self.user1.is_staff = False
#        self.user1.save()
#        address.user = self.user1
#        address.save()
#        url = reverse('address_update', args=[address.pk])
#        self.client.post(
#            url,
#            {'line1': '1 Test Street', 'locality': 'Perth', 'country': 'AU', 'postcode': '6000'}
#        )
#        address = Address.objects.get(pk=address.pk)
#        self.assertEquals(address.line1, '1 Test Street')
#
##    def test_organisation_list(self):
##        resp = self.client.get(reverse('organisation_list'))
##        self.assertEquals(resp.status_code, 200)
#
##    def test_organisation_create_get(self):
##        resp = self.client.get(reverse('organisation_create'))
##        self.assertEquals(resp.status_code, 200)
#
##    def test_organisation_create_post(self):
##        self.client.post(reverse('organisation_create'), {'name': 'Test org'})
##        org = Organisation.objects.get(name='Test org')
##        # User should also be a delegate for the new organisation.
##        self.assertTrue(Delegate.objects.filter(email_user=self.user1, organisation=org).exists())
#
##    def test_organisation_detail(self):
##        resp = self.client.get(reverse('organisation_detail', args=[self.org1.pk]))
##        self.assertEquals(resp.status_code, 200)
#
#    def test_organisation_update_get(self):
#        # Log in as customer
#        self.client.logout()
#        self.client.login(email=self.customer.email, password='pass')
#        resp = self.client.get(reverse('organisation_update', args=[self.org1.pk]))
#        self.assertEquals(resp.status_code, 200)
#
##    def test_organisation_update_post(self):
##        # Log in as customer
## #       self.client.logout()
##        self.client.login(email=self.customer.email, password='pass')
##        url = reverse('organisation_update', args=[self.org1.pk])
##        self.client.post(url, {'name': 'Test org'})
##        self.assertTrue(Organisation.objects.filter(name='Test org').exists())
#
##    def test_organisation_address_create_get(self):
##        # Log in as customer
##        self.client.logout()
##        self.client.login(email=self.customer.email, password='pass')
##        resp = self.client.get(reverse('organisation_address_create', args=[self.org1.pk, 'postal']))
##        self.assertEquals(resp.status_code, 200)
#
##    def test_organisation_address_create_post(self):
##        self.assertFalse(self.org1.postal_address)
##        # Log in as customer
##        self.client.logout()
##        self.client.login(email=self.customer.email, password='pass')
##        url = reverse('organisation_address_create', args=[self.org1.pk, 'postal'])
##        self.client.post(
##            url,
##            {'line1': '1 Test Street', 'locality': 'Perth', 'country': 'AU', 'postcode': '6000'}
##        )
##        org = Organisation.objects.get(pk=self.org1.pk)
##        self.assertTrue(org.postal_address)
