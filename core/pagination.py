from rest_framework.exceptions import NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Shared pagination class for all list endpoints.

    Defaults:
        page_size      = 20
        max_page_size  = 100
        page_size_query_param = "page_size"

    Response envelope includes:
        count         – total number of items across all pages
        current_page  – the page number returned in this response
        total_pages   – total number of pages for the current query
        next          – absolute URL of the next page, or null
        previous      – absolute URL of the previous page, or null
        results       – the list of serialized items for this page

    Raises NotFound (HTTP 404) when the requested page exceeds total_pages.

    Requirements: 23.1, 23.2, 23.3, 23.4
    """

    page_size = 20
    max_page_size = 100
    page_size_query_param = "page_size"

    def paginate_queryset(self, queryset, request, view=None):
        """
        Delegates to PageNumberPagination which already raises NotFound when the
        requested page number exceeds the total number of pages.
        Requirement 23.4: page parameter exceeding total pages → 404.
        """
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        """
        Return a Response with the standard pagination envelope.
        Requirements: 23.1, 23.2, 23.3
        """
        return Response(
            {
                "count": self.page.paginator.count,
                "current_page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )

    def get_paginated_response_schema(self, schema):
        """OpenAPI schema hint for the paginated envelope."""
        return {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "example": 42},
                "current_page": {"type": "integer", "example": 1},
                "total_pages": {"type": "integer", "example": 3},
                "next": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "example": "http://api.example.com/items/?page=2",
                },
                "previous": {
                    "type": "string",
                    "nullable": True,
                    "format": "uri",
                    "example": None,
                },
                "results": schema,
            },
        }
