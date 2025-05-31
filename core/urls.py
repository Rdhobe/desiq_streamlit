from django.urls import path
from . import views
from .health import health_check
from . import admin_views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.defaults import page_not_found

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('', page_not_found, kwargs={'exception': Exception('Page not found')}),
    path('feedback/', views.visitor_feedback, name='visitor_feedback'),
    path('items/', views.item_list, name='item_list'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('social-auth-error/', views.social_auth_error, name='social_auth_error'),
    path('demo/', views.demo_view, name='demo'),
    
    # Password reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='core/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='core/password_reset_confirm.html',
        success_url=reverse_lazy('core:password_reset_complete')
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='core/password_reset_complete.html'), name='password_reset_complete'),
    
    # Notification URLs
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/unread-count/', views.get_unread_notifications_count, name='get_unread_notifications_count'),
    
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('personality-test/', views.personality_test_view, name='personality_test'),
    path('personality-test/<slug:test_slug>/', views.personality_test_detail_view, name='personality_test_detail'),
    path('personality-test/<slug:test_slug>/take/', views.take_personality_test_view, name='take_personality_test'),
    path('personality-test/result/<int:result_id>/', views.personality_test_result_view, name='personality_test_result'),
    path('my-test-results/', views.my_test_results_view, name='my_test_results'),
    path('profile/', views.profile_view, name='profile'),
    path('setting/', views.setting_view, name='setting'),
    path('personalchat/', views.personal_chat_view, name='personal_chat'),
    path('support/', views.support_view, name='support'),
    path('support/create-issue/', views.create_issue_view, name='create_issue'),
    path('support/issues/', views.all_issues_view, name='all_issues'),
    path('support/issues/<int:issue_id>/', views.issue_detail_view, name='issue_detail'),
    path('progress/', views.progress_view, name='progress'),
    path('community/', views.community_view, name='community'),
    path('scenarios/', views.scenarios_view, name='scenarios'),
    path('mentor/', views.mentor_view, name='mentor'),
    path('mentors/<str:mentor_type>/', views.mentor_list, name='mentor_list'),
    path('chat/mentor/<int:mentor_id>/', views.chat_with_mentor, name='chat_with_mentor'),
    path('scenarios/generated/', views.generated_scenarios, name='generated_scenarios'),
    path('scenarios/completed/', views.completed_scenarios, name='completed_scenarios'),
    path('scenarios/<int:scenario_id>/', views.scenario_detail, name='scenario_detail'),
    path('scenarios/<int:scenario_id>/result/', views.scenario_result, name='scenario_result'),
    path('generate-scenario/<str:category>/', views.generate_scenario, name='generate_scenario'),
    path('subscription/upgrade/', views.upgrade_subscription_view, name='upgrade_subscription'),
    path('subscription/cancel/', views.cancel_subscription_view, name='cancel_subscription'),
    path('subscription/payment/', views.payment_view, name='payment'),
    path('subscription/payment/success/', views.payment_success_view, name='payment_success'),
    path('subscription/payment/failed/', views.payment_failed_view, name='payment_failed'),
    path('webhook/razorpay/', views.razorpay_webhook, name='razorpay_webhook'),
    
    # Footer pages
    path('about/', views.about_view, name='about'),
    path('contact/', views.contact_view, name='contact'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('support-public/', views.support_public_view, name='support_public'),
    path('community-public/', views.community_public_view, name='community_public'),
    
    # Chat URLs
    path('messages/', views.personal_chat_view, name='messages'),
    path('messages/<int:user_id>/', views.direct_message_view, name='direct_message'),
    path('search-users/', views.search_users, name='search_users'),
    
    # API endpoints
    path('api/search-users/', views.api_search_users, name='api_search_users'),
    path('api/share-scenario-result/', views.api_share_scenario_result, name='api_share_scenario_result'),
    path('api/share-result/', views.api_share_test_result, name='api_share_result'),
    
    # New SSE chat endpoints
    path('api/chat/<int:user_id>/messages/', views.sse_chat_messages, name='sse_chat_messages'),
    path('api/chat/<int:user_id>/send/', views.send_chat_message, name='send_chat_message'),
    path('api/chat/<int:user_id>/check-missed-messages/', views.check_missed_messages, name='check_missed_messages'),
    path('personal-chat/create/', views.create_personal_chat, name='create_personal_chat'),
    path('top-members/', views.top_members_view, name='top_members'),
    path('user-profile/<int:user_id>/', views.user_profile_view, name='user_profile'),
    path('recent-activities/', views.recent_activities_view, name='recent_activities'),
    
    # Community chat API endpoints
    path('api/community-messages/', views.get_community_messages, name='get_community_messages'),
    path('api/community-messages/send/', views.send_community_message, name='send_community_message'),
    path('api/community-messages/send-form/', views.send_community_message_form, name='send_community_message_form'),

    # Test error pages (for development only)
    path('test/404/', views.test_404, name='test_404'),
    path('test/500/', views.test_500, name='test_500'),
    path('test/403/', views.test_403, name='test_403'),
    path('test/400/', views.test_400, name='test_400'),
    path('test/408/', views.test_408, name='test_408'),

    # Dynamic scenario URLs
    path('generate-dynamic-scenario/<str:category>/', views.generate_dynamic_scenario, name='generate_dynamic_scenario'),
    path('dynamic-scenario/<int:scenario_id>/question/', views.dynamic_scenario_question, name='dynamic_scenario_question'),
    path('dynamic-scenario/<int:scenario_id>/question/<int:question_number>/', views.dynamic_scenario_question, name='dynamic_scenario_question_with_number'),
    path('dynamic-scenario/<int:scenario_id>/report/', views.dynamic_scenario_report, name='dynamic_scenario_report'),

    # Add a health check endpoint for deployment monitoring
    path('health/', health_check, name='health_check'),

    # Admin dashboard URLs
    path('admin-dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/run-command/<str:command>/', admin_views.admin_run_command, name='admin_run_command'),
    path('admin-dashboard/command-output/', admin_views.admin_command_output, name='admin_command_output'),
    path('admin-dashboard/backup-database/', admin_views.admin_backup_database, name='admin_backup_database'),
    path('admin-dashboard/clear-cache/', admin_views.admin_clear_cache, name='admin_clear_cache'),
    path('admin-dashboard/system-status/', admin_views.admin_system_status, name='admin_system_status'),
    path('admin-dashboard/user-management/', admin_views.admin_user_management, name='admin_user_management'),
    path('admin-dashboard/toggle-premium/', admin_views.admin_toggle_premium, name='admin_toggle_premium'),
    path('admin-dashboard/mentor-management/', admin_views.admin_mentor_management, name='admin_mentor_management'),
    path('admin-dashboard/toggle-mentor-status/', admin_views.admin_toggle_mentor_status, name='admin_toggle_mentor_status'),
    path('admin-dashboard/scenario-management/', admin_views.admin_scenario_management, name='admin_scenario_management'),
    path('admin-dashboard/toggle-scenario-status/', admin_views.admin_toggle_scenario_status, name='admin_toggle_scenario_status'),
    path('admin-dashboard/personality-test-management/', admin_views.admin_personality_test_management, name='admin_personality_test_management'),
    path('admin-dashboard/background-tasks/', admin_views.admin_background_tasks, name='admin_background_tasks'),
    path('admin-dashboard/analytics/', admin_views.admin_analytics_dashboard, name='admin_analytics_dashboard'),
    path('admin-dashboard/support-tickets/', admin_views.admin_support_tickets, name='admin_support_tickets'),

    # New admin features
    path('admin-dashboard/export-data/<str:data_type>/', admin_views.admin_export_data, name='admin_export_data'),
    path('admin-dashboard/ai-summarize/<int:ticket_id>/', admin_views.admin_ai_summarize_ticket, name='admin_ai_summarize_ticket'),
    path('admin-dashboard/permissions/', admin_views.admin_manage_permissions, name='admin_manage_permissions'),
    path('admin-dashboard/repl-console/', admin_views.admin_repl_console, name='admin_repl_console'),
    path('.well-known/appspecific/com.chrome.devtools.json', views.chrome_devtools_json, name='chrome_devtools_json')
] 