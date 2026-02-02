from urllib.parse import unquote
import base64
import json
import logging
import os
import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import Q
from django.http import HttpResponse, JsonResponse, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from jose import jwt

from .models import Repository, Tag

logger = logging.getLogger(__name__)


def get_x5c_chain():
    """
    Loads the public certificate from auth.crt file and formats it for x5c jwT header
    """
    try:
        certificate = getattr(settings, 'REGISTRY_PUBLIC_CERTIFICATE', '')
        lines = certificate.splitlines()
        clean_lines = [
            line.strip() for line in lines if '-----' not in line and line.strip()
        ]

        cert_content = ''.join(clean_lines)

        return [cert_content]
    except FileNotFoundError:
        print('ERROR: auth.crt not found for x5c header!')
        return []


@csrf_exempt
def docker_auth(request):
    user = None
    if request.method != "GET":
            return HttpResponseNotAllowed(["GET"])
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2 and auth[0].lower() == 'basic':
            try:
                username, password = (
                    base64.b64decode(auth[1]).decode('utf-8').split(':')
                )
                user = authenticate(username=username, password=password)
                if user is None:
                    return JsonResponse({'error': 'Invalid credentials'}, status=401)
            except:
                return JsonResponse({'error': 'Invalid authorization header'}, status=401)
        else:
            return JsonResponse({'error': 'Invalid authorization format'}, status=401)

    service = request.GET.get(
        'service', getattr(settings, 'REGISTRY_SERVICE', 'my-docker-registry')
    )
    scope_params = request.GET.getlist('scope')

    access_list = []

    for scope_param in scope_params:
        if scope_param:
            try:
                # Format: "repository:name:actions"
                # (User): "repository:mika/web-app:pull,push"
                # (Official): "repository:ubuntu:pull,push"
                scope_param = unquote(scope_param)
                typ, name, actions = scope_param.split(':')
                requested_actions = actions.split(',')

                repo = None

                parts = name.split('/')

                if len(parts) == 2:
                    repo_owner_username = parts[0]
                    repo_name = parts[1]

                    try:
                        repo = Repository.objects.get(
                            owner__username=repo_owner_username,
                            name=repo_name,
                            is_official=False,  # only user repos here
                        )
                    except Repository.DoesNotExist:
                        repo = None

                elif len(parts) == 1:
                    repo_name = parts[0]
                    try:
                        repo = Repository.objects.get(name=repo_name, is_official=True)
                    except Repository.DoesNotExist:
                        repo = None

                allowed_actions = []

                is_public = False
                if repo:
                    if repo.visibility == Repository.Visibility.PUBLIC:
                        is_public = True

                if 'pull' in requested_actions:
                    if is_public:
                        allowed_actions.append('pull')
                    elif repo and user and repo.owner == user:
                        allowed_actions.append('pull')
                    elif repo and not is_public and not user:
                        # Private repo access requires authentication
                        return JsonResponse({'error': 'Authentication required'}, status=401)
                    elif not repo and user:
                        # Allow pull for non-existent repos if user is authenticated
                        # (needed for some base images)
                        allowed_actions.append('pull')

                if 'push' in requested_actions:
                    if user and repo:
                        if repo.owner == user:
                            allowed_actions.append('push')
                    elif repo and not user:
                        # Push operations always require authentication
                        return JsonResponse({'error': 'Authentication required'}, status=401)

                if allowed_actions:
                    access_list.append(
                        {'type': typ, 'name': name, 'actions': allowed_actions}
                    )

            except ValueError:
                # Invalid scope format, skip
                pass

    now = int(time.time())
    payload = {
        'iss': getattr(settings, 'REGISTRY_ISSUER', 'docker-platform'),
        'sub': user.username if user else 'anonymous',
        'aud': service,
        'exp': now + 300,
        'nbf': now,
        'iat': now,
        'access': access_list,
        'jti': base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8'),
    }
    custom_headers = {'typ': 'JWT', 'x5c': get_x5c_chain(), 'alg': 'RS256'}

    private_key = getattr(settings, 'REGISTRY_PRIVATE_KEY', '')
    token = jwt.encode(payload, private_key, algorithm='RS256', headers=custom_headers)

    return JsonResponse({'token': token, 'access_token': token})


@csrf_exempt
def registry_webhook(request):
    logger.info(f"Registry webhook received: method={request.method}")
    loggerr = logging.getLogger(__name__)
    if request.method != 'POST':
        logger.warning(f"Invalid method for webhook: {request.method}")
        return HttpResponse(status=405)

    try:
        body_text = request.body.decode('utf-8')

        data = json.loads(body_text)
        events = data.get('events', [])

        for i, event in enumerate(events):
            action = event.get('action')

            if action == 'push' or action == 'pull':
                target = event['target']
                full_name = target['repository']  # can be "user/app" or "ubuntu"
                tag_name = target.get('tag')
                digest = target['digest']
                size = target['size']

                if not tag_name:
                    logger.warning(f"Skipping event without tag name for repo {full_name}")
                    continue

                parts = full_name.split('/')
                repo = None

                try:
                    if len(parts) == 2:
                        # User repository: user/repo
                        repo = Repository.objects.get(
                            owner__username=parts[0], name=parts[1], is_official=False
                        )
                        logger.info(f"Found user repository: {repo}")
                    elif len(parts) == 1:
                        # Official repository: repo
                        repo = Repository.objects.get(name=parts[0], is_official=True)
                        logger.info(f"Found official repository: {repo}")
                    else:
                        logger.warning(f"Invalid repository name format: {full_name}")
                        continue

                except Repository.DoesNotExist:
                    logger.warning(f"Repository not found in database: {full_name}")
                    continue

                if repo:
                    if action == 'push':
                        tag, created = Tag.objects.update_or_create(
                            repository=repo,
                            name=tag_name,
                            defaults={'digest': digest, 'size': size},
                        )
                        action_word = "Created" if created else "Updated"
                        logger.info(f"{action_word} tag: {repo.name}:{tag_name}")
                    else:
                        repo.pull_count += 1
                        repo.save()
                        logger.info(f"Incremented pull count for {repo.name}: {repo.pull_count}")
                else:
                    logger.error(f"Repository object is None for {full_name}")
            else:
                logger.info(f"Ignoring non-push/pull event: {action}")

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook body: {e}")
        return HttpResponse('Invalid JSON', status=400)
    except KeyError as e:
        logger.error(f"Missing required field in webhook data: {e}")
        return HttpResponse(f'Missing field: {e}', status=400)
    except Exception as e:
        logger.error(f"Unexpected webhook error: {e}", exc_info=True)
        return HttpResponse('Internal server error', status=500)

    logger.info("Webhook processed successfully")
    return HttpResponse('OK')
