from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password


User = get_user_model()


# ==========================================================
# PROFILE FORM
# ==========================================================


class ProfileForm(forms.ModelForm):

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "First name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Last name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Email address",
                }
            ),
        }

    def clean_email(self):

        email = self.cleaned_data.get(
            "email",
            "",
        ).strip()

        if email:

            existing_user = (
                User.objects
                .filter(
                    email__iexact=email
                )
                .exclude(
                    id=self.instance.id
                )
                .exists()
            )

            if existing_user:

                raise forms.ValidationError(
                    "Another account is already using this email address."
                )

        return email


# ==========================================================
# SUPER ADMIN - CREATE ADMIN
# ==========================================================


class AdminAccountCreationForm(forms.ModelForm):

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(),
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]

    def clean_username(self):

        username = self.cleaned_data[
            "username"
        ].strip()

        if User.objects.filter(
            username__iexact=username
        ).exists():

            raise forms.ValidationError(
                "A user with this username already exists."
            )

        return username

    def clean_email(self):

        email = self.cleaned_data.get(
            "email",
            "",
        ).strip()

        if email and User.objects.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                "A user with this email address already exists."
            )

        return email

    def clean(self):

        cleaned_data = super().clean()

        password1 = cleaned_data.get(
            "password1"
        )

        password2 = cleaned_data.get(
            "password2"
        )

        if password1 and password2:

            if password1 != password2:

                self.add_error(
                    "password2",
                    "The passwords do not match.",
                )

                return cleaned_data

            prospective_user = User(
                username=cleaned_data.get(
                    "username",
                    "",
                ),
                first_name=cleaned_data.get(
                    "first_name",
                    "",
                ),
                last_name=cleaned_data.get(
                    "last_name",
                    "",
                ),
                email=cleaned_data.get(
                    "email",
                    "",
                ),
                role=User.Role.ADMIN,
            )

            try:

                validate_password(
                    password1,
                    user=prospective_user,
                )

            except forms.ValidationError as error:

                self.add_error(
                    "password1",
                    error,
                )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.role = User.Role.ADMIN

        user.set_password(
            self.cleaned_data["password1"]
        )

        if commit:
            user.save()

        return user


# ==========================================================
# ADMIN - CREATE PUBLICATION STAFF
# ==========================================================


class StaffAccountCreationForm(forms.ModelForm):

    ALLOWED_ROLES = [
        User.Role.ADVISER,
        User.Role.EIC,
        User.Role.EDITOR,
        User.Role.STAFF,
    ]

    role = forms.ChoiceField(
        choices=[
            (
                User.Role.ADVISER,
                User.Role.ADVISER.label,
            ),
            (
                User.Role.EIC,
                User.Role.EIC.label,
            ),
            (
                User.Role.EDITOR,
                User.Role.EDITOR.label,
            ),
            (
                User.Role.STAFF,
                User.Role.STAFF.label,
            ),
        ]
    )

    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(),
    )

    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(),
    )

    class Meta:
        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "role",
        ]

    def clean_username(self):

        username = self.cleaned_data[
            "username"
        ].strip()

        if User.objects.filter(
            username__iexact=username
        ).exists():

            raise forms.ValidationError(
                "A user with this username already exists."
            )

        return username

    def clean_email(self):

        email = self.cleaned_data.get(
            "email",
            "",
        ).strip()

        if email and User.objects.filter(
            email__iexact=email
        ).exists():

            raise forms.ValidationError(
                "A user with this email address already exists."
            )

        return email

    def clean_role(self):

        role = self.cleaned_data[
            "role"
        ]

        if role not in self.ALLOWED_ROLES:

            raise forms.ValidationError(
                "You cannot create an account with this role."
            )

        return role

    def clean(self):

        cleaned_data = super().clean()

        password1 = cleaned_data.get(
            "password1"
        )

        password2 = cleaned_data.get(
            "password2"
        )

        if password1 and password2:

            if password1 != password2:

                self.add_error(
                    "password2",
                    "The passwords do not match.",
                )

                return cleaned_data

            prospective_user = User(
                username=cleaned_data.get(
                    "username",
                    "",
                ),
                first_name=cleaned_data.get(
                    "first_name",
                    "",
                ),
                last_name=cleaned_data.get(
                    "last_name",
                    "",
                ),
                email=cleaned_data.get(
                    "email",
                    "",
                ),
                role=cleaned_data.get(
                    "role",
                    "",
                ),
            )

            try:

                validate_password(
                    password1,
                    user=prospective_user,
                )

            except forms.ValidationError as error:

                self.add_error(
                    "password1",
                    error,
                )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.set_password(
            self.cleaned_data["password1"]
        )

        if commit:
            user.save()

        return user


# ==========================================================
# SUPER ADMIN - EDIT ADMIN
# ==========================================================


class AdminAccountEditForm(forms.ModelForm):

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
            "is_active",
        ]

    def clean_email(self):

        email = self.cleaned_data.get(
            "email",
            "",
        ).strip()

        if email:

            existing_user = (
                User.objects
                .filter(
                    email__iexact=email
                )
                .exclude(
                    id=self.instance.id
                )
                .exists()
            )

            if existing_user:

                raise forms.ValidationError(
                    "Another account is already using this email address."
                )

        return email


# ==========================================================
# ADMIN - EDIT PUBLICATION STAFF
# ==========================================================


class StaffAccountEditForm(forms.ModelForm):

    ALLOWED_ROLES = [
        User.Role.ADVISER,
        User.Role.EIC,
        User.Role.EDITOR,
        User.Role.STAFF,
    ]

    role = forms.ChoiceField(
        choices=[
            (
                User.Role.ADVISER,
                User.Role.ADVISER.label,
            ),
            (
                User.Role.EIC,
                User.Role.EIC.label,
            ),
            (
                User.Role.EDITOR,
                User.Role.EDITOR.label,
            ),
            (
                User.Role.STAFF,
                User.Role.STAFF.label,
            ),
        ]
    )

    class Meta:
        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
            "is_active",
        ]

    def clean_email(self):

        email = self.cleaned_data.get(
            "email",
            "",
        ).strip()

        if email:

            existing_user = (
                User.objects
                .filter(
                    email__iexact=email
                )
                .exclude(
                    id=self.instance.id
                )
                .exists()
            )

            if existing_user:

                raise forms.ValidationError(
                    "Another account is already using this email address."
                )

        return email

    def clean_role(self):

        role = self.cleaned_data[
            "role"
        ]

        if role not in self.ALLOWED_ROLES:

            raise forms.ValidationError(
                "This account cannot be assigned that role."
            )

        return role