from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from registry.models import Repository, Star
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a large dataset of users, repositories, and stars for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of users to create (default: 50)'
        )
        parser.add_argument(
            '--repos-per-user',
            type=int,
            default=5,
            help='Average number of repositories per user (default: 5)'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        repos_per_user = options['repos_per_user']

        self.stdout.write('🚀 Starting data generation...\n')

        # Repository name components for realistic names
        prefixes = [
            'docker', 'web', 'api', 'micro', 'cloud', 'data', 'app', 'service',
            'backend', 'frontend', 'mobile', 'desktop', 'server', 'client',
            'admin', 'user', 'auth', 'payment', 'billing', 'analytics',
            'monitoring', 'logging', 'cache', 'queue', 'worker', 'processor'
        ]

        suffixes = [
            'hub', 'server', 'client', 'api', 'service', 'app', 'platform',
            'system', 'tool', 'framework', 'library', 'engine', 'manager',
            'handler', 'controller', 'viewer', 'editor', 'builder', 'maker',
            'generator', 'parser', 'validator', 'converter', 'processor'
        ]

        technologies = [
            'python', 'node', 'java', 'go', 'rust', 'php', 'ruby', 'react',
            'vue', 'angular', 'django', 'flask', 'spring', 'express', 'fastapi',
            'postgres', 'mysql', 'mongodb', 'redis', 'nginx', 'apache', 'kafka'
        ]

        descriptions = [
            "A modern and efficient solution for your needs",
            "High-performance application with advanced features",
            "Easy to use and deploy containerized application",
            "Scalable microservice architecture",
            "Production-ready enterprise solution",
            "Open source project for developers",
            "Lightweight and fast implementation",
            "Secure and reliable platform",
            "Cloud-native application framework",
            "DevOps automation tool",
            "Real-time data processing engine",
            "RESTful API service",
            "Full-stack web application",
            "Monitoring and analytics dashboard",
            "Authentication and authorization service"
        ]

        # Create users
        self.stdout.write(f'📝 Creating {num_users} users...')
        users = []
        publisher_statuses = [
            (User.PublisherStatus.NONE, 0.7),  # 70% regular users
            (User.PublisherStatus.VERIFIED_PUBLISHER, 0.2),  # 20% verified
            (User.PublisherStatus.SPONSORED_OSS, 0.1),  # 10% sponsored
        ]

        for i in range(num_users):
            username = f'testuser{i + 1}'

            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                users.append(user)
                continue

            # Determine publisher status based on probabilities
            rand = random.random()
            cumulative = 0
            pub_status = User.PublisherStatus.NONE
            for status, prob in publisher_statuses:
                cumulative += prob
                if rand <= cumulative:
                    pub_status = status
                    break

            user = User.objects.create_user(
                username=username,
                email=f'testuser{i + 1}@example.com',
                password='lozinka123',
                role=User.UserRole.USER,
                publisher_status=pub_status
            )
            users.append(user)

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(users)} users'))

        # Count by publisher status
        verified_count = sum(1 for u in users if u.publisher_status == User.PublisherStatus.VERIFIED_PUBLISHER)
        sponsored_count = sum(1 for u in users if u.publisher_status == User.PublisherStatus.SPONSORED_OSS)
        self.stdout.write(f'    - Verified Publishers: {verified_count}')
        self.stdout.write(f'    - Sponsored OSS: {sponsored_count}')

        admin_user, _ = User.objects.get_or_create(
            username='testadmin',
            defaults={
                'email': 'admin@example.com',
                'role': User.UserRole.ADMIN,
                'is_staff': True
            }
        )
        if _:
            admin_user.set_password('lozinka123')
            admin_user.save()

        # Create official repositories
        self.stdout.write('\nCreating official repositories...')
        official_repos = []
        official_names = [
            ('ubuntu', 'Ubuntu Official Image - Reliable, secure and supported'),
            ('nginx', 'Official build of Nginx web server'),
            ('python', 'Python official runtime images'),
            ('node', 'Node.js official runtime'),
            ('postgres', 'PostgreSQL official database'),
            ('redis', 'Redis official in-memory data store'),
            ('mysql', 'MySQL official database server'),
            ('mongo', 'MongoDB official NoSQL database'),
            ('alpine', 'Alpine Linux official minimal image'),
            ('debian', 'Debian official base image'),
        ]

        for name, desc in official_names:
            repo, created = Repository.objects.get_or_create(
                owner=admin_user,
                name=name,
                defaults={
                    'description': desc,
                    'visibility': Repository.Visibility.PUBLIC,
                    'is_official': True,
                    'pull_count': random.randint(50000, 200000)
                }
            )
            official_repos.append(repo)
            if created:
                # Set random update time in last 60 days
                days_ago = random.randint(1, 60)
                repo.updated_at = timezone.now() - timedelta(days=days_ago)
                repo.save()

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {len(official_repos)} official repositories'))

        # Create user repositories
        self.stdout.write(f'\nCreating repositories for users...')
        all_repos = list(official_repos)
        repo_count = 0

        for user in users:
            num_repos = random.randint(max(1, repos_per_user - 2), repos_per_user + 3)

            for j in range(num_repos):
                # Generate repository name
                name_parts = [
                    random.choice(prefixes),
                    random.choice(suffixes)
                ]

                # Sometimes add technology
                if random.random() > 0.5:
                    name_parts.insert(1, random.choice(technologies))

                # Sometimes add number
                if random.random() > 0.7:
                    name_parts.append(str(random.randint(1, 10)))

                repo_name = '-'.join(name_parts)

                # Check if exists
                if Repository.objects.filter(owner=user, name=repo_name).exists():
                    continue

                # Random visibility (80% public, 20% private)
                visibility = Repository.Visibility.PUBLIC if random.random() > 0.2 else Repository.Visibility.PRIVATE

                # Only create public repos for testing search
                if visibility == Repository.Visibility.PRIVATE:
                    continue

                repo = Repository.objects.create(
                    owner=user,
                    name=repo_name,
                    description=random.choice(descriptions),
                    visibility=visibility,
                    is_official=False,
                    pull_count=random.randint(10, 50000)
                )

                days_ago = random.randint(1, 180)
                repo.updated_at = timezone.now() - timedelta(days=days_ago)
                repo.save()

                all_repos.append(repo)
                repo_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ Created {repo_count} user repositories'))

        # Create stars
        star_count = 0

        for repo in all_repos:
            # Official repos get more stars
            if repo.is_official:
                num_stars = random.randint(20, min(50, len(users)))
            # Verified publisher repos get medium stars
            elif repo.owner.publisher_status == User.PublisherStatus.VERIFIED_PUBLISHER:
                num_stars = random.randint(10, 30)
            # Sponsored OSS get some stars
            elif repo.owner.publisher_status == User.PublisherStatus.SPONSORED_OSS:
                num_stars = random.randint(5, 20)
            # Regular repos get few stars
            else:
                num_stars = random.randint(0, 10)

            # Randomly select users to star this repo
            starring_users = random.sample(users, min(num_stars, len(users)))

            for starring_user in starring_users:
                # Don't star your own repo
                if starring_user == repo.owner:
                    continue

                _, created = Star.objects.get_or_create(
                    user=starring_user,
                    repository=repo
                )
                if created:
                    star_count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ Added {star_count} stars'))

        # Update star_count for all repositories
        self.stdout.write('\n📊 Updating star_count for repositories...')
        from django.db.models import Count
        
        updated_count = 0
        for repo in Repository.objects.all():
            actual_star_count = Star.objects.filter(repository=repo).count()
            if repo.star_count != actual_star_count:
                repo.star_count = actual_star_count
                repo.save(update_fields=['star_count'])
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✓ Updated star_count for {updated_count} repositories'))

        # Summary
        total_repos = Repository.objects.filter(visibility=Repository.Visibility.PUBLIC).count()

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'  - Total users: {len(users)}')
        self.stdout.write(f'  - Total public repositories: {total_repos}')
        self.stdout.write(f'  - Official repositories: {len(official_repos)}')
        self.stdout.write(f'  - Total stars: {star_count}')
