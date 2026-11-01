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
from django.urls import reverse_lazy

from accounts.forms import CHECKBOX_CLASS, INPUT_CLASS
from core.geo import COUNTRIES, cities_for
from employers.models import EmployerProfile
from matching.models import Job

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


# ---------------------------------------------------------------------------
# Job posting form (REQ-FR-025/026, pages #35-#37, batch 1.30)
# ---------------------------------------------------------------------------

# The textarea is built from scratch rather than from INPUT_CLASS: that class
# carries `h-touch` (44px), which a multi-line control must not inherit.
TEXTAREA_CLASS = (
    "block w-full rounded-sm border border-border-input bg-surface px-3 py-2 "
    "text-body text-ink placeholder:text-ink-4"
)

JOB_TITLE_HELP = "The role as candidates will see it."
JOB_DESCRIPTION_HELP = (
    "What the work is, in your own words. Markdown works: **bold**, *italic*, "
    "`code`, [links](https://example.com), - lists, > quotes and ## headings."
)
JOB_RESPONSIBILITIES_HELP = "What the person in this role will own."
JOB_REQUIREMENTS_HELP = "Skills and experience the role needs."
JOB_NICE_TO_HAVE_HELP = "Anything that helps but is not required."
JOB_ADDRESS_HELP = (
    "Street address or area. Shown on the job detail page, not on the card."
)
JOB_COUNTRY_HELP = "Where the role is based. Leave it blank for a fully remote role."
JOB_CITY_HELP = "City or district. The options depend on the country."
JOB_REMOTE_HELP = (
    "Candidates can work from anywhere. Leave it off for on-site or hybrid " "roles."
)


class JobForm(forms.ModelForm):
    """Pages #35-#37's job form: the same writable set as `POST /api/v1/jobs/`.

    **One whitelist, two surfaces.** The fields here are
    `JobCreateSerializer`'s, so the form cannot save something the API refuses.
    The API also accepts the legacy `location` string for clients created before
    2026-10-30; the form no longer shows it, because the structured fields are
    what page #36 draws. `status` is not a field: publishing is the Activate
    action in the overview (REQ-FR-027), not a select the browser can set.
    `employer` is not a field either -- it is the caller's profile, assigned by
    the view.

    **What the page spec draws and this form does not have, and why.**

    * *Required / nice-to-have skills* as chip lists: the structured side is
      `job_skills` (Arch Doc §5.1), which has no model yet. The free-text
      `requirements` and `nice_to_have` columns are what exists; they are what
      the ranker reads until 2.x adds the join table.
    * *Screening questions*: `jobs.screening_questions` is JSONB, but no
      document defines the element shape (a bare string? `{text, required}`?),
      and the API deliberately refuses it for the same reason. Writing a shape
      here would invent a contract the apply flow would then have to honour.
    * *Required assessments*: `job_assessment_requirements` is REQ-FR-051 and
      has no model yet.
    * *AI-suggested skills/questions*: Phase 2 (REQ-FR-025's second clause).
    * *The five-step stepper*: the sections are anchors on one page. A wizard
      whose steps have no separate validation does not make the form shorter,
      it only hides fields.

    Page #36 says "Auto-save draft"; that is `job_autosave` in the view, and it
    posts this same form, so a saved draft and an auto-saved draft cannot
    diverge.
    """

    # Declared rather than generated from the model so the two selects validate
    # their values: a plain `CharField` with choices only uses them for display.
    # `country_code` drives the city list over HTMX; the endpoint returns the
    # same option labels that `__init__` builds for the initial render.
    address_line = forms.CharField(
        required=False,
        max_length=255,
        label="Address",
        help_text=JOB_ADDRESS_HELP,
        widget=forms.TextInput(
            attrs={"class": INPUT_CLASS, "autocomplete": "street-address"}
        ),
    )
    country_code = forms.ChoiceField(
        required=False,
        choices=[("", "Select a country"), *COUNTRIES],
        label="Country",
        help_text=JOB_COUNTRY_HELP,
        widget=forms.Select(
            attrs={
                "class": INPUT_CLASS,
                "autocomplete": "country",
                "hx-get": reverse_lazy("employer_portal:job-cities"),
                "hx-target": "#id_city",
                "hx-swap": "innerHTML",
                "hx-trigger": "change",
                "hx-include": "this",
            }
        ),
    )
    # A plain CharField with a Select widget, not a ChoiceField: the exact
    # "choose a city from this country" message belongs in `clean`, where both
    # fields are available, and a ChoiceField would replace it with Django's
    # generic "Select a valid choice".
    city = forms.CharField(
        required=False,
        max_length=100,
        label="City / district",
        help_text=JOB_CITY_HELP,
        widget=forms.Select(
            attrs={"class": INPUT_CLASS, "autocomplete": "address-level2"}
        ),
    )

    class Meta:
        model = Job
        fields = (
            "title",
            "description",
            "responsibilities",
            "requirements",
            "nice_to_have",
            "address_line",
            "country_code",
            "city",
            "remote_allowed",
            "experience_level",
        )
        labels = {
            "title": "Job title",
            "description": "Description",
            "responsibilities": "Responsibilities",
            "requirements": "Requirements",
            "nice_to_have": "Nice to have",
            "remote_allowed": "Remote allowed",
            "experience_level": "Experience level",
        }
        help_texts = {
            "title": JOB_TITLE_HELP,
            "description": JOB_DESCRIPTION_HELP,
            "responsibilities": JOB_RESPONSIBILITIES_HELP,
            "requirements": JOB_REQUIREMENTS_HELP,
            "nice_to_have": JOB_NICE_TO_HAVE_HELP,
            "remote_allowed": JOB_REMOTE_HELP,
            "experience_level": "The seniority the role is posted at.",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={"class": INPUT_CLASS, "autocomplete": "off"}
            ),
            "description": forms.Textarea(attrs={"class": TEXTAREA_CLASS, "rows": 5}),
            "responsibilities": forms.Textarea(
                attrs={"class": TEXTAREA_CLASS, "rows": 4}
            ),
            "requirements": forms.Textarea(attrs={"class": TEXTAREA_CLASS, "rows": 4}),
            "nice_to_have": forms.Textarea(attrs={"class": TEXTAREA_CLASS, "rows": 3}),
            "experience_level": forms.Select(attrs={"class": INPUT_CLASS}),
            "remote_allowed": forms.CheckboxInput(attrs={"class": CHECKBOX_CLASS}),
        }

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # The model allows an empty level (`blank=True`), so the select needs an
        # explicit empty label rather than Django's "---------".
        self.fields["experience_level"].choices = [
            ("", "Not specified"),
            *Job.ExperienceLevel.choices,
        ]
        # The city choices depend on the country. On a bound form the submitted
        # country wins, so a failed save re-renders the list the user chose
        # rather than the instance's previous country.
        country_code = ""
        if self.is_bound:
            country_code = (
                (self.data.get(self.add_prefix("country_code")) or "").strip().upper()
            )
        elif self.instance.pk:
            country_code = self.instance.country_code

        selected_city = ""
        if self.is_bound:
            selected_city = (self.data.get(self.add_prefix("city")) or "").strip()
        elif self.instance.pk:
            selected_city = self.instance.city

        rows = cities_for(country_code) if country_code else ()
        if not country_code:
            empty_label = "Select a country first"
        elif not rows:
            empty_label = "No cities listed for this country"
        else:
            empty_label = "Select a city / district"

        choices: list[tuple[str, str]] = [("", empty_label)]
        for row in rows:
            label = row["name"]
            if row["region"]:
                label = f"{label} — {row['region']}"
            choices.append((row["name"], label))

        # A job saved before this list existed (or with a place the GeoNames
        # extract does not carry) must remain editable without silently
        # replacing its city. Only the row's own stored value is re-added.
        values = {value for value, _ in choices}
        if selected_city and selected_city not in values:
            if self.instance.pk and selected_city == self.instance.city:
                choices.append((selected_city, selected_city))
        self.fields["city"].choices = choices
        # A plain `CharField` has no `choices` of its own; the widget reads this
        # one when it renders the `<option>` list. Both are set so a later
        # refactor to `ChoiceField` (or back) cannot silently drop the options.
        self.fields["city"].widget.choices = choices

        # Each control points at its help and error paragraphs. `_field.html`
        # always renders both, so the description does not change shape after a
        # failed save (the same rule as the company form).
        for name, field in self.fields.items():
            if name == "remote_allowed":
                continue
            field.widget.attrs.setdefault(
                "aria-describedby",
                f"id_{name}-help id_{name}-error",
            )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("city") and not cleaned.get("country_code"):
            self.add_error("country_code", "Choose a country before a city / district.")
        if cleaned.get("country_code") and cleaned.get("city"):
            names = {row["name"] for row in cities_for(cleaned["country_code"])}
            # The exception is only for an unchanged pair: a stored place that
            # the extract does not carry stays editable, but changing the
            # country does not carry the old city into the new one.
            already_saved = (
                self.instance.pk
                and cleaned["city"] == self.instance.city
                and cleaned["country_code"] == self.instance.country_code
            )
            if cleaned["city"] not in names and not already_saved:
                self.add_error(
                    "city",
                    "Choose a city or district from the selected country.",
                )
        return cleaned
