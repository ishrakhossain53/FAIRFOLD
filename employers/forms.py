"""Django forms for employer onboarding and company editing (REQ-FR-045).

The form and the API serializer carry the same four columns and the same
100-character industry limit. The limit comes from `EmployerProfile.industry`,
not from a second hand-written constant, so the two surfaces cannot drift.

**What this form deliberately does not contain.** design.md W10 also draws a
logo, a website and a three-step stepper (Details / Team / Preferences). Arch
Doc §5.1 has no `logo` or `website` column, and team management is REQ-FR-047;
inventing either would be a schema change, not a form field. The page spec's
"Skip for now" is a link to the landing page, so a company with no logo or
website can still finish.

**Why company_size is a number input, not W10's select.** The DDL stores a
single INTEGER and the model deliberately has no `choices`. A band select
("11–50") would have to invent a mapping from a range to one integer, and the
stored value would then disagree with the label. The number input stores what
the column means. Industry is a text input for the same reason: §5.1 has no
industry lookup table to populate a select from.
"""

from __future__ import annotations

from django import forms

from accounts.forms import CHECKBOX_CLASS, INPUT_CLASS
from employers.models import EmployerProfile

COMPANY_NAME_HELP = "The name job seekers will see if you choose to show it."
INDUSTRY_HELP = "For example, Software, Healthcare or Logistics."
COMPANY_SIZE_HELP = (
    "Total number of people who work at the company. Leave it blank if you "
    "prefer not to say."
)
SHOW_COMPANY_NAME_HELP = (
    "When this is off, job seekers see the role but not your company name. "
    "Turning it on shows your company name on public job listings. It never "
    "affects how candidates are ranked."
)


def _text_attrs(*, error_id: str, help_id: str, **extra: str) -> dict:
    """Input attributes shared by every text field on the company form.

    `aria-describedby` always points at the help and error paragraphs, which
    `_field.html` renders even when the error is hidden. Building the attribute
    only after a failure would make the control's accessible description change
    shape between requests.
    """
    return {
        "class": INPUT_CLASS,
        "aria-describedby": f"{help_id} {error_id}",
        **extra,
    }


class EmployerProfileForm(forms.ModelForm):
    """Page #33's company details form: the four columns §5.1 documents.

    `company_name` is required here even though the model column is
    `blank=True`: REQ-FR-045 says the profile is created *with* a company name,
    and W10 marks it with an asterisk. The model keeps `blank=True` because an
    empty string is the "not provided" value the DDL permits; the UI is the
    stricter surface. "Skip for now" is the documented way to leave onboarding
    without creating a row at all.
    """

    class Meta:
        model = EmployerProfile
        fields = (
            "company_name",
            "industry",
            "company_size",
            "show_company_name",
        )
        labels = {
            "company_name": "Company name",
            "industry": "Industry",
            "company_size": "Company size",
            "show_company_name": "Show my company name on public job listings",
        }
        help_texts = {
            "company_name": COMPANY_NAME_HELP,
            "industry": INDUSTRY_HELP,
            "company_size": COMPANY_SIZE_HELP,
            "show_company_name": SHOW_COMPANY_NAME_HELP,
        }
        widgets = {
            "company_name": forms.TextInput(
                attrs=_text_attrs(
                    error_id="id_company_name-error",
                    help_id="id_company_name-help",
                    autocomplete="organization",
                )
            ),
            "industry": forms.TextInput(
                attrs=_text_attrs(
                    error_id="id_industry-error",
                    help_id="id_industry-help",
                )
            ),
            "company_size": forms.NumberInput(
                attrs=_text_attrs(
                    error_id="id_company_size-error",
                    help_id="id_company_size-help",
                    inputmode="numeric",
                )
            ),
            "show_company_name": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                    "aria-describedby": (
                        "id_show_company_name-help id_show_company_name-error"
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # See the class docstring: REQ-FR-045 and W10 require a name. The model
        # stays permissive because the DDL does.
        self.fields["company_name"].required = True
