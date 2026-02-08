from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Repository

User = get_user_model()


class RepositoryForm(forms.ModelForm):
    class Meta:
        model = Repository
        fields = ['name', 'description', 'visibility']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Repository name',
                'maxlength': '200'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of your repository',
                'rows': 3,
                'maxlength': '500'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, *args, user=None, **kwargs):

        self.user = user
        super().__init__(*args, **kwargs)
        
        # Add help text for visibility field
        self.fields['visibility'].help_text = (
            "Public repositories can be viewed by anyone. "
            "Private repositories are only visible to you."
        )
        
        # Add validation help text for name field
        self.fields['name'].help_text = (
            "Repository names must be unique within your account. "
            "Use lowercase letters, numbers, hyphens, and underscores only."
        )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name
            
        # Convert to lowercase and validate format
        name = name.lower().strip()
        
        # Basic validation for allowed characters
        import re
        if not re.match(r'^[a-z0-9_-]+$', name):
            raise ValidationError(
                "Repository name can only contain lowercase letters, numbers, hyphens, and underscores."
            )
        
        # Check for reserved names
        reserved_names = ['api', 'admin', 'www', 'mail', 'ftp', 'blog', 'help', 'support']
        if name in reserved_names:
            raise ValidationError(f"'{name}' is a reserved name and cannot be used.")
        
        # Check uniqueness within user's repositories
        if self.user:
            queryset = Repository.objects.filter(owner=self.user, name=name)
            # If editing existing repository, exclude it from the check
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise ValidationError("You already have a repository with this name.")
                
        return name

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        return description


class OfficialRepositoryForm(RepositoryForm):
    """Form for creating official repositories (admin only)"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update help text for official repos
        self.fields['name'].help_text = (
            "Official repository name (no username prefix required). "
            "Use lowercase letters, numbers, hyphens, and underscores only."
        )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            return name
            
        # Convert to lowercase and validate format
        name = name.lower().strip()
        
        # Basic validation for allowed characters
        import re
        if not re.match(r'^[a-z0-9_-]+$', name):
            raise ValidationError(
                "Repository name can only contain lowercase letters, numbers, hyphens, and underscores."
            )
        
        # Check for reserved names
        reserved_names = ['api', 'admin', 'www', 'mail', 'ftp', 'blog', 'help', 'support']
        if name in reserved_names:
            raise ValidationError(f"'{name}' is a reserved name and cannot be used.")
        
        # Check uniqueness among all official repositories
        queryset = Repository.objects.filter(is_official=True, name=name)
        # If editing existing repository, exclude it from the check
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise ValidationError("An official repository with this name already exists.")
                
        return name


class RepositoryEditForm(forms.ModelForm):
    """Form for editing repository settings (description and visibility only)"""
    
    class Meta:
        model = Repository
        fields = ['description', 'visibility']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of your repository',
                'rows': 3,
                'maxlength': '500'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-select'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['visibility'].help_text = (
            "Public repositories can be viewed by anyone. "
            "Private repositories are only visible to you."
        )

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        return description


class RepositorySearchForm(forms.Form):
    """Simple form for searching repositories by name"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search repositories by name...'
        })
    )

class PublicSearchForm(forms.Form):
    q = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search repositories...',
            'class': 'form-control'
        })
    )

    BADGE_CHOICES = [
        ('OFFICIAL', 'Docker Official Image'),
        ('VERIFIED', 'Verified Publisher'),
        ('SPONSORED', 'Sponsored OSS'),
    ]

    badges = forms.MultipleChoiceField(
        choices=BADGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label='Filter by Badges'
    )
