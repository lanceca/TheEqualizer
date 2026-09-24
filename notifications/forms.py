from django import forms

from accounts.models import User
from .models import SystemUpdate


class SystemUpdateForm(forms.ModelForm):
    target_roles = forms.MultipleChoiceField(
        choices=User.Role.choices, required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Leave all roles unchecked for All Staff.",
    )

    class Meta:
        model = SystemUpdate
        fields = ["title", "version", "summary", "change_notes", "update_type",
                  "target_roles", "show_popup", "require_acknowledgement"]
        widgets = {"summary": forms.Textarea(attrs={"rows": 3}),
                   "change_notes": forms.Textarea(attrs={"rows": 12})}
