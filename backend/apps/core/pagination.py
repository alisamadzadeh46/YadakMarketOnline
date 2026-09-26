"""Shared pagination.

Plain ``PageNumberPagination`` silently ignores ``?page_size=``, so callers that
need a different-sized page (the home-page carousels ask for 16) quietly got the
project default instead. This subclass honours the parameter while capping it so
nobody can request the whole catalogue in one response.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size_query_param = "page_size"
    max_page_size = 60
