"""Django forms for candidate onboarding and profile editing (REQ-FR-009).

The form and the API serializer carry the same four fields and the same
200-character title limit. The rules are not duplicated in two hand-written
copies: `CandidateProfileForm` is a `ModelForm`, so the limit comes from
`CandidateProfile.title`, and the API serializer declares the same limit against
the same model field.

**Why four one-field forms for the profile page.** design.md S02 asks for
"inline edit per section". Posting the whole `CandidateProfileForm` from a
section would blank the other three fields whenever they were omitted. Each
section therefore has its own form containing exactly the column that section
edits; the view calls `save(update_fields=[section])` so a request cannot write
another section's column.
"""

from __future__ import annotations

from django import forms

from accounts.forms import CHECKBOX_CLASS, INPUT_CLASS
from candidates.models import CandidateProfile

TITLE_HELP = "A short headline, for example “Backend developer”."
BIO_HELP = "A few sentences about your experience and what you are looking for."
LOCATION_HELP = "City or region. Leave it blank if you prefer not to say."
REMOTE_HELP = "You can change this later."


def _text_attrs(*, error_id: str, help_id: str | None = None, **extra: str) -> dict:
    """Input attributes shared by every text field on these pages.

    `aria-describedby` always points at the error paragraph, which `_field.html`
    renders even when it is hidden. Including it only after a failure would make
    the control's accessible description change shape between requests.
    """
    described_by = f"{help_id} {error_id}" if help_id else error_id
    return {
        "class": INPUT_CLASS,
        "aria-describedby": described_by,
        **extra,
    }


class CandidateProfileForm(forms.ModelForm):
    """Page #14's manual profile step: title, bio, location, remote preference.

    The onboarding wizard in design.md S02 also contains a resume-upload step and
    a skills step. Those are out of scope for batch 1.16 (resume upload is 1.17,
    skills is 1.18), so this form is the manual-build path: it creates exactly the
    four columns REQ-FR-009 names and nothing else.
    """

    class Meta:
        model = CandidateProfile
        fields = ("title", "bio", "location", "remote_ok")
        labels = {
            "title": "Headline",
            "bio": "About",
            "location": "Location",
            "remote_ok": "Open to remote work",
        }
        help_texts = {
            "title": TITLE_HELP,
            "bio": BIO_HELP,
            "location": LOCATION_HELP,
            "remote_ok": REMOTE_HELP,
        }
        widgets = {
            "title": forms.TextInput(
                attrs=_text_attrs(
                    error_id="id_title-error",
                    help_id="id_title-help",
                    autocomplete="organization-title",
                )
            ),
            "bio": forms.Textarea(
                attrs={
                    **_text_attrs(
                        error_id="id_bio-error",
                        help_id="id_bio-help",
                    ),
                    "rows": 5,
                }
            ),
            "location": forms.TextInput(
                attrs=_text_attrs(
                    error_id="id_location-error",
                    help_id="id_location-help",
                    autocomplete="address-level2",
                )
            ),
            "remote_ok": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                    "aria-describedby": "id_remote_ok-help id_remote_ok-error",
                }
            ),
        }


class TitleSectionForm(forms.Form):
    """Inline edit of the headline (page #16, design.md S02)."""

    title = forms.CharField(
        max_length=CandidateProfile._meta.get_field("title").max_length,
        required=False,
        label="Headline",
        widget=forms.TextInput(
            attrs=_text_attrs(
                error_id="id_title-error",
                autocomplete="organization-title",
            )
        ),
    )


class BioSectionForm(forms.Form):
    """Inline edit of the about text."""

    bio = forms.CharField(
        required=False,
        label="About",
        widget=forms.Textarea(
            attrs={
                **_text_attrs(error_id="id_bio-error"),
                "rows": 5,
            }
        ),
    )


class LocationSectionForm(forms.Form):
    """Inline edit of the location."""

    location = forms.CharField(
        required=False,
        label="Location",
        widget=forms.TextInput(
            attrs=_text_attrs(
                error_id="id_location-error",
                autocomplete="address-level2",
            )
        ),
    )


class RemoteOkSectionForm(forms.Form):
    """Inline edit of the remote preference.

    An unchecked checkbox submits nothing, which is exactly what this form
    stores: `False`. The section key is the field name, so the view can call
    `setattr(profile, "remote_ok", ...)` without a translation table.
    """

    remote_ok = forms.BooleanField(
        required=False,
        label="Open to remote work",
        widget=forms.CheckboxInput(
            attrs={
                "class": CHECKBOX_CLASS,
                "aria-describedby": "id_remote_ok-error",
            }
        ),
    )


# Section key -> form class. The key is also the model column, which is what
# keeps `profile_edit` from needing a second mapping that could drift.
SECTION_FORMS: dict[str, type[forms.Form]] = {
    "title": TitleSectionForm,
    "bio": BioSectionForm,
    "location": LocationSectionForm,
    "remote_ok": RemoteOkSectionForm,
}

SECTION_LABELS: dict[str, str] = {
    "title": "Headline",
    "bio": "About",
    "location": "Location",
    "remote_ok": "Remote preference",
}
