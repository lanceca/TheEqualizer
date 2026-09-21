# The Equalizer — Alpha update review

Implemented locally on **alpha**, using the current repository as authorized after confirming that the referenced ZIP was unavailable. No commit, push, merge, branch switch, remote migration, or deployment was performed.

## Implemented features

1. **Public Archive:** `/archive/`, search/category/month/date filters, clear filters, result count, pagination, and grouping by original publication month. Only archived normal articles with a recorded publication date are public. Drafts and edit-request copies stay private. Archived articles stay out of current feeds.
2. **Archived reader:** archived status, original publication date, optional archive date, PDF access, and working existing Like/Share controls under the same public visibility rule.
3. **EIC Archive:** search plus category, archive-month, and date-range filtering. Original publication and archive dates remain visible. Existing restore/permanent-delete actions and edit-request protections remain in place. Restoration now also blocks active Content Reports, matching the requested protection; permanent deletion already checked both.
4. **Archive Requests:** user-facing headings, labels, notifications, confirmations, dashboards, and analytics labels updated. `DeletionRequest` and existing URL/Python identifiers remain unchanged. Existing notification records display the updated wording without rewriting their stored messages.
5. **Published Articles:** category, publication month/date range, and optional 30+ Days Old filters, combined with existing search. Editor ownership restrictions remain. This never automatically archives an article.
6. **Public footer:** publication branding, navigation, existing social links, copyright, developer-team link, and Back to Top. Footer stays in document flow; Archive is also in the public navigation.
7. **Account safety/privacy:** per-card masked emails with independent React reveal buttons. Status controls moved from cards and profile fields into the edit page's confirmed Danger Zone/Recovery area. Existing backend toggle routes and staff workflow blockers are reused.
8. **System Updates:** dedicated persistent release and per-user receipt models, Super Admin draft/edit/publish/hide-popup management, multi-role or All Staff targeting, staff history/detail pages, pending count, React popup, required acknowledgement, and CSRF-protected POST acknowledgement. Published releases are immutable through the manager; hiding a popup retains history. Public pages never mount the popup.
9. **PDF download:** inline Preparing/Downloading/percentage/Downloaded states, inline cancellation, real byte-based progress when available, nonpercentage loading otherwise, filename handling, and existing analytics. Fullscreen PDF overlay removed; image lightbox preserved.
10. **Article rich text:** Bold, Italic, Underline, Strikethrough, keyboard shortcuts, Django `content` form integration, visible-text character limits, retry restoration, safe unsaved previews, sanitized persisted bodies/snapshots, reader/workflow/version rendering, and safe ReportLab formatting. Version diffs compare readable text; current/previous snapshots retain formatting. Edit-request reasons remain plain text.

## Dependencies and migration

- Python dependency added to both requirements files: `bleach==6.2.0`. Installed in the local `.venv` for validation; its `webencodings` dependency was installed by pip.
- New migration: `notifications/migrations/0002_systemupdate_systemupdatereceipt.py`.
- Creates `SystemUpdate` and `SystemUpdateReceipt`, including a unique `(user, update)` constraint.
- **Migration required before serving the updated staff workspace.** No Article/account schema changes or `DeletionRequest` rename.
- No new npm dependencies.
- New React components: `ArticleRichTextEditor`, `AccountEmailToggle`, `InlineDownloadButton`, `SystemUpdatePopup`. Registered in the existing island registry.

## Commands for the Alpha environment

These are handoff commands; Alpha was not changed remotely. Run against the intended **Alpha** checkout/environment when its rollout is authorized.

```text
python -m pip install -r requirements-render.txt
python manage.py migrate
python manage.py check
```

For a local setup using the standard requirements file, use `python -m pip install -r requirements.txt` instead. The repository's existing deployment/static-file process remains unchanged.

Frontend source and generated bundles are included. To rebuild:

```text
cd frontend
npm ci
npm run build
```

Local regression tests (do not load `.env`; use an in-memory SQLite database and in-memory media):

```text
python manage.py test --settings=publications.test_settings --noinput
python manage.py makemigrations --check --dry-run --settings=publications.test_settings
```

Browser interaction tests, after the frontend build:

```text
cd frontend
node tests/interactions.mjs
```

The browser test defaults to installed Windows Chrome. Set `CHROME_PATH` for another Chrome executable. It uses a temporary browser profile, serves only the local fixture/built assets, and intercepts its synthetic PDF download.

## Validation and limits

- Full Django test suite: **24 tests passing**, including the existing email/account security tests.
- Includes actual draft submission, two revision/resubmission rounds, final approval, approved edit-request draft publication, direct EIC editing, version preservation, archive/restore permissions and blockers, public draft exclusion, PDF generation/tracking, role-targeted changelog access, CSRF, receipt uniqueness, and account status controls.
- All project Django templates compile. Django system checks pass. Migration drift check passes.
- Vite build passes; generated assets are built from source, not hand-edited.
- New React interaction files and registry pass targeted ESLint. Full-project lint has **seven pre-existing errors**: `AdviserAnalytics.jsx` (immutability), `AuditLogPanel.jsx`, `DigitalPublicationViewer.jsx` (two), `PageLoadingSkeleton.jsx`, `PeopleAndTeams.jsx`, and `StaffSidebarToggle.jsx`. The analytics component's only functional edit here is its Archive Request label.
- Headless Chrome smoke tests pass for popup focus/acknowledgement/count, independent email visibility, all four editor styles, safe preview, retry restoration, over-limit form validation/focus, PDF inline state and encoded filename.
- The build retains Vite's warning about a bundle over 500 kB. No unrelated bundle refactor was made.
- No Alpha/production database or Supabase media access was used for testing. PostgreSQL, real media, email delivery, mobile-browser behavior, and full-page visual checks still need Alpha verification below.

## Exact Alpha testing checklist

Use disposable Alpha test accounts and articles, including an Editor-owned older article (30+ days), a recent article, articles in two categories, an EIC-owned article, and an unpublished draft. Use a separate browser/private window for anonymous reader checks.

### Public archive and reader

1. Publish a formatted Editor article, request archive, and approve as EIC.
2. Check that it disappears from Home and its current category feed, but appears in `/archive/`.
3. Search by title/content. Combine category, publication month, and date-range filters; clear filters. Check empty results and pagination preserve filter values.
4. Verify the month section uses `published_at`, even when `archived_at` is in another month.
5. Open the archived article anonymously; verify ARCHIVED and publication/archive dates, media, formatting, Like/Share, and PDF download.
6. Open a draft URL and an edit-request draft URL anonymously; both reader and PDF endpoints must return 404.
7. Check Archive navigation and footer links, social destinations, Back to Top, and that the footer does not cover content on desktop/mobile.

### EIC archive and requests

8. Search/filter the EIC Archive by category, archive month, and date range. Verify both date labels.
9. Confirm all Editor/EIC request pages, notifications, dashboards, and analytics use Archive Request wording.
10. Reject one request and confirm its notification. Approve another and confirm the article is archived, not deleted.
11. Restore an archived article and confirm it returns to current Published/category feeds. Re-archive it.
12. With an active Edit Request or Content Report, confirm restore/permanent deletion remain blocked. Repeat after resolving the workflow.
13. On a disposable article, test EIC permanent-delete confirmation. Verify non-EIC access is denied and GET requests do not mutate state.

### Published filters

14. Test search, category, publication month, start/end dates, and combinations.
15. Turn on 30+ Days Old: recent, archived, and edit-request draft articles must not appear. No article should be archived automatically.
16. Confirm Editors only see their own permitted articles; EIC sees all currently permitted normal articles. Clear filters and reload a copied filtered URL.

### Account management

17. As Super Admin, check Manage Admins; as Admin, check Manage Staff. Cards should show Edit Account without activation/deactivation buttons.
18. Verify emails begin masked; toggle two cards independently using both pointer and keyboard.
19. Edit an active disposable account: verify Danger Zone copy, cancel confirmation, then confirm deactivation. Verify sign-in is blocked and records remain.
20. Edit the inactive account: verify Recovery/Reactivate and successful reactivation.
21. Save ordinary profile changes and confirm they cannot silently change account status. Try deactivating staff with unresolved workflow responsibilities and confirm the existing blocker messages.

### System Updates

22. As Super Admin, create a draft with title/version/summary/notes/type. Edit it; confirm staff cannot see it before publication.
23. Publish targeted to Editor only. Editor sees the popup and badge; EIC cannot see its popup, history entry, or direct detail URL.
24. Click Got it; refresh and check the same popup does not return, the badge decreases, and history remains even after clearing normal notifications.
25. Publish for multiple roles, then All Staff. Verify each intended role independently. Test a required-acknowledgement update and its full-detail link.
26. Hide a published popup in the manager. Confirm it stops appearing but remains in targeted history.
27. Attempt manager/create/edit/publish/hide URLs as every non-Super Admin role; access must be denied. Confirm no popup appears on public pages while logged in.

### Rich text, workflow, and versions

28. Test B/I/U/S, combinations, Ctrl/Cmd+B/I/U, paragraph breaks, undo/redo, plain-text paste, and long text.
29. Run Editor Create → Save Draft → Edit Draft → Submit → EIC Revision → Resubmit → EIC Revision → Resubmit → Approve.
30. Check each preview, including previous submissions; only the latest resubmission card should stand alone. Old snapshots remain and the sidebar attention count clears after approval.
31. Request edit access for a published Editor article; approve as EIC; edit the generated draft, submit, and approve. Verify the plain-text request reason did not become a rich-text editor.
32. Directly edit an EIC-owned published article. Verify both old and new versions retain formatting; expand Text changes and check readable escaped diffs, including formatting-only changes.
33. Cause a form validation error and verify entered formatted content is restored. Check 30,000 visible-character limits and confirmation-dialog validation.
34. Submit `<script>alert(1)</script>` and `<img src=x onerror=alert(1)>`; verify no execution, unsafe attributes, or dangerous stored markup. Check legacy plain-text articles with ampersands, angle brackets, and line breaks.

### PDF, media, and responsive UI

35. Download current and archived formatted articles with real featured images/attachments. Verify logo, footer, page numbers, filename, and bold/italic/underline/strikethrough in the PDF.
36. Check inline Preparing → progress or nonpercentage Downloading → Downloaded → normal state. Confirm cancellation, error/retry, and page interaction without a fullscreen overlay.
37. Verify existing unique-download analytics behavior: successful generation increments once for the same browser/device fingerprint, and unrelated counters/real media remain correct.
38. Check desktop and narrow mobile widths, keyboard focus, rich-text toolbar/selection, email controls, popup scrolling, filters, and footer. Repeat important editor interactions in the browsers your staff actually use.

## Assumptions and notable review points

- The current Alpha checkout is authoritative, per the user's clarification; no ZIP contents were available or applied.
- The public archive excludes archived rows without an original publication date. This avoids exposing never-published content. Review legacy records if any legitimate historical articles lack `published_at`.
- Public archive pagination is 24 articles per page. A publication-month heading may repeat on the next page when that month spans pages.
- EIC archive filters use `archived_at`; public archive and Published filters use `published_at`. The 30-day cutoff uses the site's local calendar date.
- Sanitization occurs before form persistence and on article/version/submission save signals. Existing records are sanitized when displayed; there is no bulk rewrite of historical content. Raw ORM `QuerySet.update()`/bulk operations bypass save signals, as usual, and must not be used to store untrusted bodies without the sanitizer.
- The rich editor deliberately pastes plain text. No fonts, colors, links, headings, raw-HTML control, or additional npm editor framework was introduced. Browser-native editing commands are used; cross-browser/manual keyboard testing remains important.
- PDF bodies use only sanitized ReportLab markup; multi-page PDFs with long real articles and media deserve a visual Alpha check.
- System update notes are plain text. Empty target-role selection means All Staff; published releases cannot be edited through the manager. Required updates stay pending until explicit acknowledgement. A normal popup dismissed with Escape remains pending on the next workspace page until Got it is used.
- The update popup displays the newest pending popup-enabled release per workspace visit. Older pending releases remain in history and can appear on subsequent visits. Detail pages suppress the popup so the full release can be read.
- Account deactivation remains a POST through the original toggle routes; records and role rules are preserved. Original GET redirects for account toggles are preserved.
- No changes to `main`, `.env`, secrets, deployment/infrastructure configuration, Supabase configuration, mobile source, `accounts/models.py`, or `publications/models.py`.
- No new System Update content has been published to Alpha; the Super Admin will create the first release after migration.

## File inventory

The exact modified/new-file lists follow. The two React distribution files are generated build outputs.

### Modified files

- `accounts/forms.py`
- `accounts/templates/accounts/dashboards/editor.html`
- `accounts/templates/accounts/dashboards/eic.html`
- `accounts/templates/accounts/dashboards/super_admin.html`
- `accounts/templates/accounts/edit_admin_account.html`
- `accounts/templates/accounts/edit_staff_account.html`
- `accounts/templates/accounts/manage_admins.html`
- `accounts/templates/accounts/manage_staff.html`
- `accounts/views.py`
- `frontend/src/AdviserAnalytics.jsx`
- `frontend/src/EditorialWorkspaceEnhancer.jsx`
- `frontend/src/main.jsx`
- `home/templates/home/article_detail.html`
- `home/urls.py`
- `home/views.py`
- `notifications/context_processors.py`
- `notifications/models.py`
- `notifications/urls.py`
- `publications/apps.py`
- `publications/templates/publications/archive.html`
- `publications/templates/publications/article_version_detail.html`
- `publications/templates/publications/create_article.html`
- `publications/templates/publications/edit_draft.html`
- `publications/templates/publications/edit_published_article.html`
- `publications/templates/publications/eic_content_reports.html`
- `publications/templates/publications/eic_deletion_requests.html`
- `publications/templates/publications/eic_edit_requests.html`
- `publications/templates/publications/my_content_reports.html`
- `publications/templates/publications/my_deletion_requests.html`
- `publications/templates/publications/my_drafts.html`
- `publications/templates/publications/my_edit_requests.html`
- `publications/templates/publications/my_submissions.html`
- `publications/templates/publications/pending_submissions.html`
- `publications/templates/publications/published_articles.html`
- `publications/templates/publications/report_article_content.html`
- `publications/templates/publications/request_article_deletion.html`
- `publications/templates/publications/request_article_edit.html`
- `publications/templates/publications/resubmitted_submissions.html`
- `publications/templates/publications/revise_submission.html`
- `publications/validators.py`
- `publications/views.py`
- `requirements-render.txt`
- `requirements.txt`
- `static/react-dist/assets/equalizer-react.css`
- `static/react-dist/assets/equalizer-react.js`
- `templates/base.html`
- `templates/notifications/notification_list.html`
- `templates/public_base.html`
- `templates/staff_base.html`

### New files

- `ALPHA_UPDATE_REVIEW.md`
- `accounts/templates/accounts/_account_status.html`
- `accounts/test_account_safety.py`
- `frontend/src/AccountEmailToggle.jsx`
- `frontend/src/ArticleRichTextEditor.jsx`
- `frontend/src/InlineDownloadButton.jsx`
- `frontend/src/PublicationInteractions.css`
- `frontend/src/SystemUpdatePopup.jsx`
- `frontend/src/articleRichText.js`
- `frontend/tests/interactions.mjs`
- `home/templates/home/archive.html`
- `notifications/forms.py`
- `notifications/migrations/0002_systemupdate_systemupdatereceipt.py`
- `notifications/templates/notifications/manage_updates.html`
- `notifications/templates/notifications/update_detail.html`
- `notifications/templates/notifications/update_form.html`
- `notifications/templates/notifications/update_history.html`
- `notifications/test_updates.py`
- `notifications/update_views.py`
- `notifications/updates.py`
- `publications/filters.py`
- `publications/rich_text.py`
- `publications/signals.py`
- `publications/templates/publications/_library_filters.html`
- `publications/templatetags/__init__.py`
- `publications/templatetags/article_text.py`
- `publications/test_settings.py`
- `publications/test_updates.py`
- `static/css/publication-updates.css`
- `templates/includes/public_footer.html`
