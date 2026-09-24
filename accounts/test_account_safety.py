from django.test import TestCase
from django.urls import reverse
from .forms import AdminAccountEditForm, StaffAccountEditForm
from .models import User


class AccountSafetyTests(TestCase):
    def setUp(self):
        self.super_admin = User.objects.create_user('super', role=User.Role.SUPER_ADMIN, email='super@example.test')
        self.admin = User.objects.create_user('admin', role=User.Role.ADMIN, email='admin@example.test')
        self.staff = User.objects.create_user('staff', role=User.Role.STAFF, email='staff@example.test')
        User.objects.update(email_verified=True)

    def test_cards_edit_zones_and_toggles(self):
        for manager, account, manage, edit, toggle in (
            (self.super_admin, self.admin, 'manage_admin_accounts', 'edit_admin_account', 'toggle_admin_account_status'),
            (self.admin, self.staff, 'manage_staff_accounts', 'edit_staff_account', 'toggle_staff_account_status'),
        ):
            self.client.force_login(manager)
            page = self.client.get(reverse(manage))
            self.assertContains(page, 'data-react-component="AccountEmailToggle"')
            self.assertNotContains(page, reverse(toggle, args=[account.pk]))
            page = self.client.get(reverse(edit, args=[account.pk]))
            self.assertContains(page, 'Danger Zone')
            self.assertContains(page, 'data-confirm-title="Deactivate Account"')
            self.assertEqual(self.client.get(reverse(toggle, args=[account.pk])).status_code, 302)
            account.refresh_from_db()
            self.assertTrue(account.is_active)
            self.client.post(reverse(toggle, args=[account.pk]))
            account.refresh_from_db()
            self.assertFalse(account.is_active)
            self.assertContains(self.client.get(reverse(edit, args=[account.pk])), 'Reactivate Account')
            self.client.post(reverse(toggle, args=[account.pk]))
            account.refresh_from_db()
            self.assertTrue(account.is_active)

    def test_profile_forms_cannot_change_status(self):
        for form_class, user in ((AdminAccountEditForm, self.admin), (StaffAccountEditForm, self.staff)):
            form = form_class({'email': user.email, 'first_name': 'Updated', 'last_name': '', 'is_active': ''}, instance=user)
            self.assertNotIn('is_active', form.fields)
            self.assertTrue(form.is_valid(), form.errors)
            form.save()
            user.refresh_from_db()
            self.assertTrue(user.is_active)
