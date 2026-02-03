from django.urls import path

from . import views, views_stars

urlpatterns = [
    # Public repository view (accessible to all)
    path('public/<uuid:repo_id>/', views.public_repository_detail, name='public_repository_detail'),
    
    # Repository management URLs (for owners)
    path('repositories/', views.repository_list, name='repository_list'),
    path('repositories/create/', views.repository_create, name='repository_create'),
    path(
        'repositories/<uuid:repo_id>/',
        views.repository_detail,
        name='repository_detail',
    ),
    path(
        'repositories/<uuid:repo_id>/edit/',
        views.repository_edit,
        name='repository_edit',
    ),
    path(
        'repositories/<uuid:repo_id>/delete/',
        views.repository_delete,
        name='repository_delete',
    ),
    # Star functionality URLs
    path('repositories/<uuid:repo_id>/star/', views_stars.star, name='repo_star'),
    path('repositories/<uuid:repo_id>/unstar/', views_stars.unstar, name='repo_unstar'),
    # Admin repository management URLs
    path(
        'admin/repositories/', views.admin_repository_list, name='admin_repository_list'
    )
]
