"""Shared utilities, middleware, security and cross-cutting models."""

from django.test import TestCase
from django.urls import reverse


class HomePageTests(TestCase):
    def test_homepage_renders(self):
        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "FairFold")
        self.assertContains(response, "AI-powered")
