"""Django forms for the registration and verification pages (REQ-FR-001).

The API serializer (`accounts.serializers`) and these forms carry the same rules
in the two shapes the product needs: JSON field errors for `/api/v1/auth/`, and a
server-rendered form with an error summary for pages #6 and #11. The rules
themselves are not copied -- both call `register_user`, `validate_password` and
`SELF_ASSIGNABLE_ROLES`.

`consent` is required but **not stored**: Arch Doc §5.1 has no consent column.
REQ-COM-004 asks for the checkbox, and recording the acceptance needs a schema
decision that this batch does not have. Flagged in HISTORY rather than invented
as a column here.

The role values are the group names (`candidate`, `employer_hr`), the same values
the API accepts; only the labels are the page's "Looking for work"/"Hiring"
wording, so a form and an API client cannot disagree about what was chosen.
"""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from accounts.models import CANDIDATE_ROLE, EMPLOYER_HR_ROLE, User

# 44px controls and the 4.76:1 input border from design.md §6.2 / §3.2. The
# classes live here rather than in the template so a field added to the form
# cannot end up as an unstyled browser default.
INPUT_CLASS = (
    "block h-touch w-full rounded-sm border border-border-input bg-surface "
    "px-3 text-body text-ink placeholder:text-ink-4"
)
CHECKBOX_CLASS = "mt-1 h-4 w-4 shrink-0 rounded-sm border-border-input"

# The two roles the public form may grant (REQ-FR-045, REQ-FR-047). The label is
# design.md page #6's wording; the value is the group the service assigns.
ROLE_CHOICES = (
    (CANDIDATE_ROLE, "Looking for work"),
    (EMPLOYER_HR_ROLE, "Hiring"),
)

CONSENT_REQUIRED_ERROR = (
    "You must accept the Privacy Policy and Terms to create an account."
)


class RegistrationForm(forms.Form):
    """Page #6 (design.md S01): role, name, email, password, consent."""

    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        label="I am…",
        initial=CANDIDATE_ROLE,
        # No `class` here: RadioSelect puts `widget.attrs.class` on its wrapping
        # `<div>`, not on the inputs, so a sizing class would shrink the group.
        # The radio inputs keep the browser's default control size and the label
        # supplies the 44px touch target (design.md §6.2).
        widget=forms.RadioSelect(attrs={"aria-describedby": "id_role-error"}),
        error_messages={
            "required": "Choose whether you are looking for work or hiring.",
            "invalid_choice": "Choose whether you are looking for work or hiring.",
        },
    )
    first_name = forms.CharField(
        max_length=150,
        label="First name",
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "autocomplete": "given-name",
                "aria-describedby": "id_first_name-error",
            }
        ),
    )
    last_name = forms.CharField(
        max_length=150,
        label="Last name",
        widget=forms.TextInput(
            attrs={
                "class": INPUT_CLASS,
                "autocomplete": "family-name",
                "aria-describedby": "id_last_name-error",
            }
        ),
    )
    email = forms.EmailField(
        max_length=255,
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": INPUT_CLASS,
                "autocomplete": "email",
                "aria-describedby": "id_email-error",
            }
        ),
    )
    password = forms.CharField(
        # `strip=False`: the service hashes exactly what was typed, so trimming
        # here would make the form and the API accept different passwords.
        strip=False,
        label="Password",
        help_text="At least 12 characters. We check against known breached passwords.",
        widget=forms.PasswordInput(
            attrs={
                "class": INPUT_CLASS + " pr-16",
                "autocomplete": "new-password",
                # Both ids exist on the page even before an error: the help text
                # is always rendered, the error paragraph exists but is `hidden`.
                "aria-describedby": "id_password-help id_password-error",
            }
        ),
    )
    consent = forms.BooleanField(
        required=True,
        label="I accept the Privacy Policy and Terms",
        error_messages={"required": CONSENT_REQUIRED_ERROR},
        widget=forms.CheckboxInput(
            attrs={"class": CHECKBOX_CLASS, "aria-describedby": "id_consent-error"}
        ),
    )

    def clean_email(self) -> str:
        """Store the address exactly as `users.email` does."""
        return User.objects.normalize_email(self.cleaned_data["email"]).lower()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()

        # Same validator call and the same provisional user as
        # `register_user`, so a password accepted here cannot be refused by the
        # service (and vice versa). Field-level, so the message lands under the
        # password input rather than in the summary only.
        password = cleaned.get("password")
        email = cleaned.get("email")
        if password and email:
            provisional = User(
                email=email,
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                validate_password(password, provisional)
            except DjangoValidationError as exc:
                self.add_error("password", exc)

        return cleaned

    def service_kwargs(self) -> dict[str, str]:
        """The keyword arguments `register_user` expects, from validated data."""
        data = self.cleaned_data
        return {
            "email": data["email"],
            "password": data["password"],
            "first_name": data["first_name"],
            "last_name": data["last_name"],
            "role": data["role"],
        }
