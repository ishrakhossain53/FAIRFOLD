"""Pagination.

The default DRF page-number paginator is deliberately replaced. Two reasons:

1. **A fixed page size is wrong for every list in the product.** An analytics
   table and a shortlist need different page sizes, and neither is 20.
2. **An unbounded ``page_size`` is a data-exfiltration path.** The employer
   candidates endpoint would return every candidate the employer can see,
   including names the anonymised screening view is meant to hide, in one
   response. The ceiling is enforced here rather than trusted to each view.

`max_page_size` exists, and it is capped at 100. The ranked-applications screen
is the heaviest query in the product (pgvector similarity plus a bias check per
row), so a generous page size is also a load risk.
"""

from __future__ import annotations

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """Page-number pagination with a hard ceiling."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("count", self.page.paginator.count),
                    ("num_pages", self.page.paginator.num_pages),
                    ("page", self.page.number),
                    ("page_size", self.get_page_size(self.request)),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )


class CompactPagination(StandardPagination):
    """For reference data rendered into a `<select>`: skills, categories, tags."""

    page_size = 50
    max_page_size = 200
