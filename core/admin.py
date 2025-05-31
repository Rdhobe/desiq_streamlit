from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from admin_auto_filters.filters import AutocompleteFilter
from guardian.admin import GuardedModelAdmin
from django.db.models import Count, Avg
from .models import (
    Profile, Scenario, ScenarioOption, UserScenarioProgress,
    PersonalityTest, PersonalityTestQuestion, PersonalityTestResult,
    UserTestResult, Mentor, UserActivity, Item, DailyChallenge, 
    SupportIssue, IssueComment, ChatRoom, ChatMessage
)

# Resources for import/export
class ProfileResource(resources.ModelResource):
    class Meta:
        model = Profile
        fields = ('id', 'user__username', 'user__email', 'xp_points', 'level', 'is_premium', 'daily_streak')
        export_order = ('id', 'user__username', 'user__email', 'xp_points', 'level', 'is_premium')

class ScenarioResource(resources.ModelResource):
    class Meta:
        model = Scenario
        fields = ('id', 'title', 'category', 'difficulty', 'xp_reward', 'created_at')

class UserScenarioProgressResource(resources.ModelResource):
    class Meta:
        model = UserScenarioProgress
        fields = ('id', 'user__username', 'scenario__title', 'completed', 'completed_at')

class SupportIssueResource(resources.ModelResource):
    class Meta:
        model = SupportIssue
        fields = ('id', 'title', 'user__username', 'status', 'created_at')

# Filters
class UserFilter(AutocompleteFilter):
    title = 'User'
    field_name = 'user'

class ScenarioFilter(AutocompleteFilter):
    title = 'Scenario'
    field_name = 'scenario'

# Add a link to our custom admin dashboard
class CustomAdminSite(admin.AdminSite):
    site_header = 'Desiq Admin'
    site_title = 'Desiq Admin Portal'
    index_title = 'Welcome to Desiq Admin Portal'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(lambda r: redirect('core:admin_dashboard')), name='custom_dashboard'),
        ]
        return custom_urls + urls
    
    def each_context(self, request):
        context = super().each_context(request)
        context['custom_dashboard_url'] = 'core:admin_dashboard'
        return context

# Create a custom admin site instance
admin_site = CustomAdminSite(name='admin')

# Register existing models
@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)

@admin.register(Profile)
class ProfileAdmin(ImportExportModelAdmin, GuardedModelAdmin):
    resource_class = ProfileResource
    list_display = ('user', 'xp_points', 'level', 'is_premium', 'daily_streak')
    list_filter = ('is_premium', 'level')
    search_fields = ('user__username', 'user__email')
    autocomplete_fields = ['user']
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')

@admin.register(Scenario)
class ScenarioAdmin(ImportExportModelAdmin, GuardedModelAdmin):
    resource_class = ScenarioResource
    list_display = ('title', 'category', 'difficulty', 'xp_reward', 'completion_rate')
    list_filter = ('category', 'difficulty')
    search_fields = ('title', 'description')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'category')
        }),
        ('Difficulty Settings', {
            'fields': ('difficulty', 'xp_reward'),
            'classes': ('collapse',)
        }),
        ('Advanced Settings', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def completion_rate(self, obj):
        total = UserScenarioProgress.objects.filter(scenario=obj).count()
        if total == 0:
            return "0%"
        completed = UserScenarioProgress.objects.filter(scenario=obj, completed=True).count()
        rate = (completed / total) * 100
        return f"{rate:.1f}%"
    
    completion_rate.short_description = 'Completion Rate'

@admin.register(ScenarioOption)
class ScenarioOptionAdmin(admin.ModelAdmin):
    list_display = ('scenario', 'text')
    search_fields = ('scenario__title', 'text')
    autocomplete_fields = ['scenario']

@admin.register(UserScenarioProgress)
class UserScenarioProgressAdmin(ImportExportModelAdmin):
    resource_class = UserScenarioProgressResource
    list_display = ('user', 'scenario', 'completed', 'completed_at')
    list_filter = (UserFilter, ScenarioFilter, 'completed')
    search_fields = ('user__username', 'scenario__title')
    autocomplete_fields = ['user', 'scenario']
    readonly_fields = ('completed_at',)
    date_hierarchy = 'completed_at'

@admin.register(DailyChallenge)
class DailyChallengeAdmin(admin.ModelAdmin):
    list_display = ('user', 'scenario', 'date_created', 'completed', 'completed_at')
    list_filter = (UserFilter, ScenarioFilter, 'date_created', 'completed')
    search_fields = ('user__username', 'scenario__title')
    autocomplete_fields = ['user', 'scenario']
    readonly_fields = ('completed_at',)
    date_hierarchy = 'date_created'

@admin.register(SupportIssue)
class SupportIssueAdmin(ImportExportModelAdmin):
    resource_class = SupportIssueResource
    list_display = ('title', 'user', 'status', 'created_at', 'ai_summary')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description', 'user__username')
    autocomplete_fields = ['user']
    readonly_fields = ('created_at',)
    
    def ai_summary(self, obj):
        # This will be replaced with AI summary - for now just show a shortened description
        if obj.description and len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description
    
    ai_summary.short_description = 'AI Summary'

@admin.register(IssueComment)
class IssueCommentAdmin(admin.ModelAdmin):
    list_display = ('issue', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('issue__title', 'user__username', 'text')
    autocomplete_fields = ['user', 'issue']

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at', 'message_count')
    list_filter = ('created_at',)
    search_fields = ('name',)
    autocomplete_fields = ['created_by']
    
    def message_count(self, obj):
        return ChatMessage.objects.filter(room=obj).count()
    
    message_count.short_description = 'Messages'

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'timestamp', 'preview')
    list_filter = ('timestamp',)
    search_fields = ('room__name', 'sender__username', 'content')
    autocomplete_fields = ['sender', 'room']
    
    def preview(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    
    preview.short_description = 'Content Preview'

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'created_at')
    list_filter = ('activity_type', 'created_at')
    search_fields = ('user__username', 'activity_type')
    date_hierarchy = 'created_at'
    autocomplete_fields = ['user']
    readonly_fields = ('created_at',)

@admin.register(PersonalityTest)
class PersonalityTestAdmin(admin.ModelAdmin):
    search_fields = ('title', 'description')
    list_display = ('title', 'question_count', 'result_count', 'completion_rate')
    
    def question_count(self, obj):
        return PersonalityTestQuestion.objects.filter(test=obj).count()
    
    def result_count(self, obj):
        return PersonalityTestResult.objects.filter(test=obj).count()
    
    def completion_rate(self, obj):
        total = UserTestResult.objects.filter(test=obj).count()
        return f"{total}" if total > 0 else "0"
    
    question_count.short_description = 'Questions'
    result_count.short_description = 'Results'
    completion_rate.short_description = 'Completions'

@admin.register(PersonalityTestQuestion)
class PersonalityTestQuestionAdmin(admin.ModelAdmin):
    list_display = ('test', 'order', 'text_preview')
    list_filter = ('test',)
    search_fields = ('text',)
    autocomplete_fields = ['test']
    
    def text_preview(self, obj):
        if len(obj.text) > 50:
            return f"{obj.text[:50]}..."
        return obj.text
    
    text_preview.short_description = 'Question'

@admin.register(PersonalityTestResult)
class PersonalityTestResultAdmin(admin.ModelAdmin):
    list_filter = ('test',)
    search_fields = ('title', 'description')
    list_display = ('test', 'title', 'description_preview')
    autocomplete_fields = ['test']
    
    def description_preview(self, obj):
        if obj.description and len(obj.description) > 50:
            return f"{obj.description[:50]}..."
        return obj.description or "-"
    
    description_preview.short_description = 'Description'

@admin.register(UserTestResult)
class UserTestResultAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'result', 'timestamp')
    list_filter = ('test', 'timestamp')
    search_fields = ('user__username',)
    autocomplete_fields = ['user', 'test', 'result']
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'

@admin.register(Mentor)
class MentorAdmin(GuardedModelAdmin):
    list_display = ('name', 'expertise', 'is_premium', 'chat_count')
    list_filter = ('is_premium',)
    search_fields = ('name', 'description', 'expertise')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'expertise', 'image')
        }),
        ('Settings', {
            'fields': ('is_premium',),
            'classes': ('collapse',)
        }),
    )
    
    def chat_count(self, obj):
        # This would need to be adapted based on how mentor chats are stored
        return "N/A"
    
    chat_count.short_description = 'Chat Interactions'

# Inline admin for Profile
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profile'

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_premium', 'last_login', 'date_joined')
    list_filter = BaseUserAdmin.list_filter + ('profile__is_premium', 'last_login', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    date_hierarchy = 'date_joined'
    list_per_page = 25
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    filter_horizontal = ('groups', 'user_permissions',)
    
    def is_premium(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.is_premium
        return False
    is_premium.boolean = True
    is_premium.short_description = 'Premium'

# Re-register UserAdmin with the default admin site
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
