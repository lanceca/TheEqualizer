============================================================
THE EQUALIZER — DEVELOPMENT UPDATE
============================================================

Session: Article System & Image Attachments
Status: IN PROGRESS
Date: August 16, 2026
Time: 10:45 PM
============================================================


1. PROJECT STRUCTURE / ROLES
============================================================

Confirmed the current publication staff roles:

- Super Admin
- Admin
- Adviser
- Editor in Chief (EIC)
- Editor
- Staff

Role responsibilities remain:

SUPER ADMIN
- Add, delete, and manage Admin accounts.

ADMIN
- Add, delete, and manage publication staff accounts.
- Assign staff roles.

ADVISER
- View website analytics.
- View reactions, visits, and shares.
- View post statistics.
- View approved, rejected, revision, and pending submissions.

EDITOR IN CHIEF
- Approve submissions.
- Reject submissions.
- Send submissions back for revision.
- Create articles.
- Archive articles.
- Modify archived content.

EDITOR
- Create and submit content for EIC approval.
- Request edits to their own submissions.
- Request deletion of their own submissions.

STAFF
- Submit content reports.
- Notify Editors and EIC about content concerns.
- Manage their own submitted reports.
- Cancel reports.
- Add additional information to reports.

NOTIFICATION SYSTEM
- Notifications will connect related branches of the publication workflow.
- Staff will receive notifications when an action requires their attention.


2. WEBSITE CATEGORIES
============================================================

Homepage navigation will include:

- Home
- News
- Editorials
- Features
- Cartoonings
- Videos
- Special Showcase
- Sports
- Campus Life
- Opinion
- Search

Because there are several categories, the homepage navigation may use:

- Mega menu
OR
- Toggle sidebar


3. PUBLICATION MODELS
============================================================

Confirmed the Article model currently contains:

- title
- slug
- category
- tags
- author
- content
- featured_image
- is_published
- is_archived
- archived_at
- published_at
- created_at
- updated_at


4. ARTICLE TAGGING
============================================================

Confirmed:

- Articles can have multiple tags.
- Tags use a Many-to-Many relationship.
- Example tag:
  Basketball

Testing confirmed the Basketball tag exists.

The test article:

    Test Sports Article

also exists in the database.

Slug:

    test-sports-article


5. ARTICLE ATTACHMENT SYSTEM
============================================================

IMPORTANT:

Article image attachments are already implemented at the MODEL level.

The Article model contains:

    featured_image

This is intended for the main image of an article.

The ArticleAttachment model supports multiple additional images.

Structure:

    Article
    |
    +-- Featured Image
    |
    +-- Attachment 1
    +-- Attachment 2
    +-- Attachment 3
    +-- etc.

ArticleAttachment contains:

- article
- image
- caption
- uploaded_at

Additional image upload location:

    media/articles/attachments/


Featured image upload location:

    media/articles/


6. MEDIA CONFIGURATION
============================================================

Django media handling was added/planned.

settings.py should contain:

    MEDIA_URL = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"

config/urls.py should contain:

    if settings.DEBUG:
        urlpatterns += static(
            settings.MEDIA_URL,
            document_root=settings.MEDIA_ROOT,
        )

This allows uploaded images to be displayed while running
the Django development server.


7. ARTICLE ADMIN
============================================================

Django Admin should manage:

- Categories
- Tags
- Articles
- Article Attachments
- Submissions
- Edit Requests
- Deletion Requests
- Content Reports

ArticleAttachment should be registered in:

    publications/admin.py


8. BROWSER-BASED TESTING DECISION
============================================================

IMPORTANT CHANGE:

We are stopping the use of Django Shell as the primary
functional testing method.

Reason:

Shell testing was becoming confusing.

From this point forward, testing should primarily be done
through the actual website.

Preferred testing workflow:

    Browser
       |
       v
    Login
       |
       v
    User Dashboard
       |
       v
    Perform Action
       |
       v
    Verify Result Through Website / Admin


9. ARTICLE CREATION WORKFLOW
============================================================

The first browser-based workflow being developed is:

    Editor
       |
       v
    Create Article
       |
       +--> Title
       |
       +--> Category
       |
       +--> Tags
       |
       +--> Content
       |
       +--> Featured Image
       |
       +--> Multiple Attachments
       |
       v
    Create Article
       |
       v
    Article stored in database


10. ARTICLE IMAGE UPLOAD
============================================================

The article creation form must support:

A. Featured Image

    One main image representing the article.

B. Article Attachments

    Multiple additional images.

The HTML form must use:

    enctype="multipart/form-data"

The attachment input must use:

    multiple

Example:

    <input
        type="file"
        name="attachments"
        accept="image/*"
        multiple
    >


11. CURRENT DEVELOPMENT STATUS
============================================================

COMPLETED / CONFIRMED:

[✓] Django project structure
[✓] User roles
[✓] Custom User model
[✓] Dashboard routing
[✓] Publication categories
[✓] Category database entries
[✓] Article model
[✓] Tag model
[✓] Article tagging
[✓] Submission model
[✓] Edit Request model
[✓] Deletion Request model
[✓] Content Report model
[✓] Featured image field
[✓] ArticleAttachment model
[✓] Media configuration started
[✓] Browser-first testing approach established


CURRENTLY IN PROGRESS:

[>] Article creation page
[>] Featured image upload
[>] Multiple article attachment upload
[>] Browser-based article creation testing


NOT YET COMPLETED:

[ ] Submit Article for EIC Approval
[ ] EIC Submission Dashboard
[ ] Approve Submission
[ ] Reject Submission
[ ] Send Back for Revision
[ ] Editor Edit Request
[ ] Editor Deletion Request
[ ] Staff Content Reports
[ ] Report management
[ ] Notification System
[ ] Adviser Analytics
[ ] Archive Management
[ ] Public Article Pages
[ ] Public Category Pages
[ ] Search System
[ ] Homepage UI
[ ] Mega Menu / Sidebar
[ ] Final image validation
[ ] Improved automatic slug generation


12. NEXT SESSION
============================================================

CONTINUE FROM:

    6I.10 — Article Creation HTML

Immediate tasks:

1. Open:

    publications/templates/publications/create_article.html

2. Add:

    enctype="multipart/form-data"

3. Add Featured Image upload.

4. Add Multiple Attachments upload.

5. Confirm publications/views.py receives:

    request.FILES.get("featured_image")

    request.FILES.getlist("attachments")

6. Run:

    python manage.py check

7. Run:

    python manage.py runserver

8. Log in as an Editor.

9. Open the Create Article page.

10. Create a new test article.

11. Upload:
    - 1 featured image
    - 2-3 attachment images

12. Submit the article.

13. Verify the article through Django Admin.

14. Verify the Article Attachments through Django Admin.

15. Once successful, continue to:

    Editor -> Submit for EIC Approval
    EIC -> Review Submission
    EIC -> Approve / Reject / Revision


13. GIT / GITHUB
============================================================

Repository:

    TheEqualizer

Remote:

    https://github.com/lanceca/TheEqualizer.git

Primary branch:

    main

Before pushing the next update:

    git status

Then verify that these remain ignored:

    .venv/
    .env
    db.sqlite3
    media/

Then:

    git add .

    git status

    git commit -m "Implement article image attachments"

    git push origin main


============================================================
END OF SESSION UPDATE
============================================================