from django.urls import path
from . import views_stars

urlpatterns = [
    path("repositories/<uuid:repo_id>/star/", views_stars.star, name="repo_star"),
    path("repositories/<uuid:repo_id>/unstar/", views_stars.unstar, name="repo_unstar"),
]
