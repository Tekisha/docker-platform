from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .permissions import user_management_permission_required

User = get_user_model()


@user_management_permission_required
def admin_user_list(request):
    """
    Admins can search ordinary users and assign publisher_status.
    """
    q = (request.GET.get('q') or '').strip()

    users = User.objects.all().order_by('role', 'username')

    if q:
        users = users.filter(
            Q(username__icontains=q)
            | Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )

    return render(request, 'accounts/admin_user_list.html', {'users': users, 'q': q})


@user_management_permission_required
@require_POST
def set_publisher_status(request, user_id):
    """
    Admin assigns publisher_status to a USER account.
    Only regular users can have their publisher status modified.
    """
    target = get_object_or_404(User, id=user_id)
    
    # Only allow publisher status changes for regular users
    if target.role != 'USER':
        # Silently ignore attempts to modify admin users
        q = (request.POST.get('q') or '').strip()
        return redirect(f'/accounts/admin/users/?q={q}')

    status = request.POST.get('publisher_status', 'NONE')

    allowed = {choice[0] for choice in User.PublisherStatus.choices}
    if status not in allowed:
        status = 'NONE'

    target.publisher_status = status
    target.save(update_fields=['publisher_status'])

    # keep search query in redirect
    q = (request.POST.get('q') or '').strip()
    return redirect(f'/accounts/admin/users/?q={q}')
