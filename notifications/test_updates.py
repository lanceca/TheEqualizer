from django.test import TestCase, Client
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from .models import SystemUpdate, SystemUpdateReceipt
from .updates import pending_updates, visible_updates


class SystemUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = User.objects.create_user('super', role=User.Role.SUPER_ADMIN, email='super@example.test')
        cls.editor = User.objects.create_user('editor', role=User.Role.EDITOR, email='editor@example.test')
        cls.eic = User.objects.create_user('eic', role=User.Role.EIC, email='eic@example.test')
        User.objects.update(email_verified=True)

    def release(self, **values):
        defaults = dict(title='Release', summary='Summary', change_notes='NEW\n• Archive', is_published=True, published_at=timezone.now(), target_roles=['EDITOR'])
        defaults.update(values)
        return SystemUpdate.objects.create(**defaults)

    def test_targeting_acknowledgement_and_permanent_history(self):
        update = self.release()
        self.release(is_published=False, title='Private draft')
        self.assertEqual(list(visible_updates(self.editor)), [update])
        self.assertFalse(visible_updates(self.eic).exists())
        self.client.force_login(self.editor)
        popup = self.client.get(reverse('system_update_popup')).json()['update']
        self.assertEqual(popup['id'], update.pk)
        self.assertEqual(self.client.get(popup['ackUrl']).status_code, 405)
        self.assertEqual(self.client.post(popup['ackUrl']).status_code, 302)
        self.assertIsNone(self.client.get(reverse('system_update_popup')).json()['update'])
        self.assertContains(self.client.get(reverse('system_update_history')), update.title)
        self.client.post(reverse('clear_all_notifications'))
        self.assertTrue(SystemUpdateReceipt.objects.filter(user=self.editor, update=update).exists())
        self.assertEqual(pending_updates(self.editor).count(), 0)
        self.client.force_login(self.eic)
        self.assertEqual(self.client.get(popup['url']).status_code, 404)
        self.assertEqual(self.client.post(popup['ackUrl']).status_code, 404)

    def test_all_staff_required_receipts_and_uniqueness(self):
        update = self.release(target_roles=[], require_acknowledgement=True)
        receipt = SystemUpdateReceipt.objects.create(user=self.editor, update=update, seen_at=timezone.now())
        self.assertTrue(visible_updates(self.eic).exists())
        self.assertTrue(pending_updates(self.editor).exists())
        with self.assertRaises(IntegrityError), transaction.atomic():
            SystemUpdateReceipt.objects.create(user=self.editor, update=update)
        receipt.acknowledged_at = timezone.now()
        receipt.save()
        self.assertFalse(pending_updates(self.editor).exists())

    def test_manager_publish_hide_and_permissions(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('manage_system_updates')).status_code, 403)
        self.assertEqual(self.client.post(reverse('create_system_update'), {}).status_code, 403)
        self.client.force_login(self.manager)
        data = dict(title='v2 launch', version='v2', summary='New tools', change_notes='FIXED\nSafe text', update_type='FIXED', target_roles=['EIC', 'EDITOR'], show_popup='on')
        self.assertEqual(self.client.post(reverse('create_system_update'), data).status_code, 302)
        update = SystemUpdate.objects.get(title='v2 launch')
        self.assertFalse(update.is_published)
        action_url = reverse('system_update_action', args=[update.pk])
        self.assertEqual(self.client.get(action_url).status_code, 405)
        self.client.post(action_url, {'action': 'publish'})
        update.refresh_from_db()
        self.assertTrue(update.is_published)
        self.assertIsNotNone(update.published_at)
        self.assertEqual(self.client.post(reverse('edit_system_update', args=[update.pk]), data).status_code, 404)
        self.client.post(action_url, {'action': 'hide_popup'})
        update.refresh_from_db()
        self.assertFalse(update.show_popup)
        self.assertTrue(visible_updates(self.editor).filter(pk=update.pk).exists())

    def test_csrf_and_no_public_popup(self):
        update = self.release()
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.editor)
        self.assertEqual(csrf_client.post(reverse('acknowledge_system_update', args=[update.pk])).status_code, 403)
        self.client.force_login(self.editor)
        self.assertNotContains(self.client.get(reverse('home')), 'data-react-component="SystemUpdatePopup"')
        self.assertContains(self.client.get(reverse('system_update_history')), 'data-react-component="SystemUpdatePopup"')
