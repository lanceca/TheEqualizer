import io
from datetime import timedelta
from pathlib import Path
from django.core.exceptions import ValidationError
from django.template.loader import get_template
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from django.utils import timezone
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate
from accounts.models import User
from analytics.models import ArticlePdfDownloadTracker
from notifications.models import Notification
from .models import Article, Category, ContentReport, DeletionRequest, EditRequest, Submission
from .rich_text import article_html, article_pdf_html, article_plain_text, sanitize_article_content
from .validators import validate_article_text_fields


class RichTextTests(SimpleTestCase):
    def test_allowlist_and_legacy_text(self):
        safe = sanitize_article_content('<p onclick="evil()"><strong>Bold</strong><i>Italic</i><u>Under</u><s>Strike</s><img src=x onerror=evil()><script>evil()</script><a href="javascript:evil()">link</a></p>')
        for forbidden in ('onclick', '<img', '<script', '<a ', 'javascript:'):
            self.assertNotIn(forbidden, safe)
        for tag in ('strong', 'i', 'u', 's'):
            self.assertIn(f'<{tag}>', safe)
        self.assertEqual(sanitize_article_content('One & two\nThree < four'), 'One & two\nThree < four')
        self.assertEqual(article_html('One & two\nThree < four'), 'One &amp; two<br>Three &lt; four')
        self.assertEqual(article_plain_text('<p><b>A</b></p><p>B</p>').strip(), 'A\nB')
        encoded_attack = sanitize_article_content('<div>&lt;img src=x onerror=evil()&gt; &amp; text</div>')
        self.assertEqual(sanitize_article_content(encoded_attack), encoded_attack)
        self.assertNotIn('<img', article_html(encoded_attack))

    def test_limits_and_pdf_styles(self):
        validate_article_text_fields(content='<b>' + 'x' * 30000 + '</b>')
        with self.assertRaises(ValidationError):
            validate_article_text_fields(content='<b>' + 'x' * 30001 + '</b>')
        html = article_pdf_html('<p><strong>Bold</strong> <em>Italic</em> <u>Under</u> <s>Strike</s> &amp; &lt;x&gt;</p>')
        for value in ('<b>Bold</b>', '<i>Italic</i>', '<u>Under</u>', '<strike>Strike</strike>'):
            self.assertIn(value, html)
        output = io.BytesIO()
        SimpleDocTemplate(output).build([Paragraph(html, getSampleStyleSheet()['BodyText'])])
        self.assertTrue(output.getvalue().startswith(b'%PDF'))

    def test_all_templates_compile(self):
        root = Path(__file__).resolve().parent.parent
        for folder in [root / 'templates', *(root / app / 'templates' for app in ('home', 'accounts', 'publications', 'notifications'))]:
            for path in folder.rglob('*.html'):
                with self.subTest(template=str(path)):
                    get_template(path.relative_to(folder).as_posix())


class PublicationUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.editor = User.objects.create_user('editor', role=User.Role.EDITOR, email='editor@example.test', email_verified=True)
        cls.eic = User.objects.create_user('eic', role=User.Role.EIC, email='eic@example.test', email_verified=True)
        cls.category = Category.objects.create(name='News', slug='news')
        cls.other_category = Category.objects.create(name='Features', slug='features')
        User.objects.update(email_verified=True)

    def article(self, **overrides):
        values = dict(title='Historical story', slug=f'story-{Article.objects.count()}', category=self.category,
                      author=self.editor, content='<p><b>Bold story</b> <i>Italic</i> <u>Under</u> <s>Strike</s></p>',
                      is_published=True, published_at=timezone.now() - timedelta(days=45))
        values.update(overrides)
        return Article.objects.create(**values)

    def test_public_archive_filters_visibility_and_pdf(self):
        article = self.article(is_published=False, is_archived=True, archived_at=timezone.now())
        draft = self.article(is_published=False, published_at=None, title='Private draft')
        edit_copy = self.article(is_published=False, is_archived=True, draft_type=Article.DraftType.EDIT_REQUEST)
        archive = self.client.get(reverse('public_archive'))
        self.assertContains(archive, article.title)
        self.assertContains(archive, timezone.localtime(article.published_at).strftime('%B %Y'))
        self.assertNotContains(archive, draft.title)
        self.assertEqual(list(archive.context['articles']), [article])
        for route in ('home', 'category_articles'):
            args = [self.category.slug] if route == 'category_articles' else []
            self.assertNotContains(self.client.get(reverse(route, args=args)), article.title)
        reader = self.client.get(reverse('article_detail', args=[article.slug]))
        self.assertContains(reader, 'ARCHIVED')
        self.assertContains(reader, '<b>Bold story</b>', html=True)
        for hidden in (draft, edit_copy):
            self.assertEqual(self.client.get(reverse('article_detail', args=[hidden.slug])).status_code, 404)
            self.assertEqual(self.client.get(reverse('download_article_pdf', args=[hidden.slug])).status_code, 404)
        filters = {'q': 'Historical', 'category': self.category.pk, 'month': timezone.localtime(article.published_at).strftime('%Y-%m')}
        self.assertContains(self.client.get(reverse('public_archive'), filters), article.title)
        self.assertNotContains(self.client.get(reverse('public_archive'), {'category': self.other_category.pk}), article.title)
        self.assertEqual(self.client.get(reverse('public_archive'), {'month': '2026-99', 'start': 'bad', 'category': 'oops'}).status_code, 200)
        pdf = self.client.get(reverse('download_article_pdf', args=[article.slug]))
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertIn(f'{article.slug}.pdf', pdf['Content-Disposition'])
        self.assertEqual(ArticlePdfDownloadTracker.objects.filter(article=article).count(), 1)
        self.client.get(reverse('download_article_pdf', args=[article.slug]))
        self.assertEqual(ArticlePdfDownloadTracker.objects.filter(article=article).count(), 1)
        self.client.post(reverse('react_to_article', args=[article.slug]))
        self.client.post(reverse('share_article', args=[article.slug]))
        article.refresh_from_db()
        self.assertEqual(article.reaction_count, 1)
        self.assertEqual(article.share_count, 1)
        self.assertEqual(self.client.post(reverse('react_to_article', args=[draft.slug])).status_code, 404)
        self.assertEqual(self.client.post(reverse('share_article', args=[draft.slug])).status_code, 404)

    def test_published_candidates_preserve_ownership(self):
        old = self.article(title='Old owned')
        self.article(title='Recent owned', published_at=timezone.now())
        other = self.article(author=self.eic, title='Other author')
        self.article(title='Already archived', is_archived=True, is_published=False)
        self.client.force_login(self.editor)
        response = self.client.get(reverse('published_articles'), {'older': '30', 'category': self.category.pk, 'q': 'owned'})
        self.assertEqual(list(response.context['articles']), [old])
        self.client.force_login(self.eic)
        response = self.client.get(reverse('published_articles'), {'older': '30'})
        self.assertEqual(set(response.context['articles']), {old, other})

    def test_archive_request_restore_and_protected_deletion(self):
        article = self.article()
        self.client.force_login(self.editor)
        self.client.post(reverse('request_article_deletion', args=[article.pk]), {'reason': 'Past issue'})
        archive_request = DeletionRequest.objects.get(article=article)
        self.client.force_login(self.eic)
        self.client.post(reverse('review_deletion_request', args=[archive_request.pk]), {'action': 'approve'})
        article.refresh_from_db()
        self.assertTrue(article.is_archived)
        self.assertFalse(article.is_published)
        self.assertTrue(Notification.objects.filter(message__contains='archive request').exists())
        response = self.client.get(reverse('archived_articles'), {'month': timezone.localdate().strftime('%Y-%m'), 'category': self.category.pk})
        self.assertEqual(list(response.context['articles']), [article])
        edit = EditRequest.objects.create(article=article, requested_by=self.editor, reason='Fix')
        for route in ('restore_archived_article', 'permanently_delete_archived_article'):
            self.assertEqual(self.client.get(reverse(route, args=[article.pk])).status_code, 405)
            self.client.post(reverse(route, args=[article.pk]))
            article.refresh_from_db()
            self.assertTrue(article.is_archived)
        edit.delete()
        report = ContentReport.objects.create(article=article, reported_by=self.editor, description='Unresolved concern')
        for route in ('restore_archived_article', 'permanently_delete_archived_article'):
            self.client.post(reverse(route, args=[article.pk]))
            article.refresh_from_db()
            self.assertTrue(article.is_archived)
        report.delete()
        self.client.post(reverse('restore_archived_article', args=[article.pk]))
        article.refresh_from_db()
        self.assertTrue(article.is_published)
        self.assertFalse(article.is_archived)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.post(reverse('permanently_delete_archived_article', args=[article.pk])).status_code, 403)

    def test_snapshot_sanitization_and_resubmission_leaf_counts(self):
        article = self.article(is_published=False, content='<b>Safe</b><img src=x onerror=evil()>')
        self.assertEqual(article.content, '<b>Safe</b>')
        ancestor = Submission.objects.create(article=article, submitted_by=self.editor, status=Submission.Status.REVISION, snapshot_content='<b>First</b>')
        middle = Submission.objects.create(article=article, submitted_by=self.editor, status=Submission.Status.REVISION, resubmission_of=ancestor, snapshot_content='<i>Second</i>')
        leaf = Submission.objects.create(article=article, submitted_by=self.editor, status=Submission.Status.PENDING, resubmission_of=middle, snapshot_content='<u>Third</u><script>x</script>')
        self.client.force_login(self.editor)
        response = self.client.get(reverse('resubmitted_submissions'))
        self.assertEqual(list(response.context['submissions']), [leaf])
        self.assertEqual(response.context['sidebar_editor_resubmissions_count'], 1)
        self.client.force_login(self.eic)
        self.client.post(reverse('review_submission', args=[leaf.pk]), {'action': 'approve'})
        self.client.force_login(self.editor)
        response = self.client.get(reverse('resubmitted_submissions'))
        self.assertEqual(response.context['sidebar_editor_resubmissions_count'], 0)
        self.assertEqual(Submission.objects.filter(article=article).count(), 3)
        ancestor.refresh_from_db()
        self.assertEqual(ancestor.snapshot_content, '<b>First</b>')

    def test_rich_text_draft_submit_and_version(self):
        self.client.force_login(self.editor)
        data = {'title': 'Formatted draft', 'category': self.category.pk, 'content': '<b>First</b><img src=x onerror=evil()>', 'action': 'draft'}
        self.assertEqual(self.client.post(reverse('create_article'), data).status_code, 302)
        article = Article.objects.get(title='Formatted draft')
        self.assertEqual(article.content, '<b>First</b>')
        data.update(content='<p><b>Final</b><i>Italic</i><u>Under</u><s>Strike</s></p>', action='submit')
        self.assertEqual(self.client.post(reverse('edit_draft', args=[article.pk]), data).status_code, 302)
        submission = Submission.objects.get(article=article)
        self.assertEqual(submission.snapshot_content, data['content'])
        self.client.force_login(self.eic)
        self.client.post(reverse('review_submission', args=[submission.pk]), {'action': 'approve'})
        article.refresh_from_db()
        self.assertTrue(article.is_published)
        version = article.versions.first()
        self.assertEqual(version.content, data['content'])
        response = self.client.get(reverse('article_version_detail', args=[article.pk, version.version_number]))
        self.assertContains(response, '<b>Final</b>', html=True)

    def test_two_revision_rounds_and_approved_edit_draft(self):
        self.client.force_login(self.editor)
        data = {'title': 'Workflow story', 'category': self.category.pk, 'content': '<b>Original</b>', 'action': 'submit'}
        self.client.post(reverse('create_article'), data)
        article = Article.objects.get(title=data['title'])
        original = article.submissions.get()
        current = original
        for body in ('<i>Second</i>', '<u>Third</u><s>Corrected</s>'):
            self.client.force_login(self.eic)
            self.client.post(reverse('review_submission', args=[current.pk]), {'action': 'revision', 'reviewer_notes': 'Please revise.'})
            self.client.force_login(self.editor)
            data['content'] = body
            self.assertEqual(self.client.post(reverse('revise_submission', args=[current.pk]), data).status_code, 302)
            current = current.resubmissions.get()
            self.assertEqual(current.snapshot_content, body)
            page = self.client.get(reverse('resubmitted_submissions'))
            self.assertEqual(list(page.context['submissions']), [current])
            self.assertEqual(page.context['sidebar_editor_resubmissions_count'], 1)
        self.client.force_login(self.eic)
        self.client.post(reverse('review_submission', args=[current.pk]), {'action': 'approve'})
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(reverse('resubmitted_submissions')).context['sidebar_editor_resubmissions_count'], 0)
        self.assertEqual(article.submissions.count(), 3)
        original.refresh_from_db()
        self.assertEqual(original.snapshot_content, '<b>Original</b>')
        self.client.post(reverse('request_article_edit', args=[article.pk]), {'reason': 'Update the story'})
        edit = EditRequest.objects.get(article=article)
        self.client.force_login(self.eic)
        self.client.post(reverse('review_edit_request', args=[edit.pk]), {'action': 'approve'})
        edit.refresh_from_db()
        self.assertIsNotNone(edit.draft_article_id)
        self.client.force_login(self.editor)
        data['content'] = '<p><b>Updated</b> <i>edition</i></p>'
        self.client.post(reverse('edit_draft', args=[edit.draft_article_id]), data)
        pending = Submission.objects.get(article_id=edit.draft_article_id, status=Submission.Status.PENDING)
        self.client.force_login(self.eic)
        self.client.post(reverse('review_submission', args=[pending.pk]), {'action': 'approve'})
        article.refresh_from_db()
        self.assertEqual(article.content, data['content'])
        self.assertEqual(article.versions.count(), 2)
        self.assertEqual(article.versions.order_by('version_number').first().content, '<u>Third</u><s>Corrected</s>')

    def test_direct_eic_edit_preserves_versions_and_safe_diffs(self):
        self.client.force_login(self.eic)
        data = {'title': 'EIC story', 'category': self.category.pk, 'content': '<b>First edition</b>', 'action': 'publish'}
        self.client.post(reverse('create_article'), data)
        article = Article.objects.get(title=data['title'])
        data['content'] = '<p><i>Second edition</i><img src=x onerror=evil()></p>'
        self.client.post(reverse('edit_published_article', args=[article.pk]), data)
        article.refresh_from_db()
        self.assertEqual(article.content, '<p><i>Second edition</i></p>')
        self.assertEqual(article.versions.count(), 2)
        original, current = article.versions.order_by('version_number')
        self.assertEqual(original.content, '<b>First edition</b>')
        response = self.client.get(reverse('article_version_detail', args=[article.pk, current.version_number]))
        self.assertContains(response, '<i>Second edition</i>', html=True)
        self.assertNotContains(response, '&lt;i&gt;')
        self.assertNotContains(response, 'onerror=')
