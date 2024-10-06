from django.urls import path
from django.urls.conf import include

from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.generators import OpenAPISchemaGenerator

from rest_framework.permissions import AllowAny

from api.api import (
    VolunteerApi, LinkApiView, TaskApi, TokenApi,
    MyTaskApi, ManageTaskApi, MyApi, CommentApi
)

api_routes = [
    path("volunteer/", VolunteerApi.as_view()),
    path("link/<int:unit_id>/", LinkApiView.as_view()),
    path("task/", TaskApi.as_view()),
    path("comment/task/<int:task_id>/", CommentApi.as_view()),
    path("my/task/", MyTaskApi.as_view()),
    path("my/task/<int:task_id>/", ManageTaskApi.as_view()),
    path("my/", MyApi.as_view())
]


SchemaView = get_schema_view(
    openapi.Info(
        title="Volunteer Api",
        default_version="v1",
        description="API to work with data from Database",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="bogdanbelenesku@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    generator_class=OpenAPISchemaGenerator,
    public=True,
    permission_classes=[AllowAny],
)


urlpatterns = [
    path("", include(api_routes)),
    path("token/", TokenApi.as_view(), name="token_obtain"),
    path(
        "swagger<format>/", SchemaView.without_ui(cache_timeout=0), name="schema-json"
    ),
    path(
        "swagger/",
        SchemaView.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
]
