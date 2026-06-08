from django.urls import path
from . import views

urlpatterns = [
    # ログイン・ログアウト
    path('login/', views.admin_login, name='admin_login'),
    path('logout/', views.admin_logout, name='admin_logout'),

    # ダッシュボード
    path('', views.admin_dashboard, name='admin_dashboard'),

    # 本人確認審査
    path('verifications/', views.admin_verification_list, name='admin_verification_list'),
    path('verifications/<int:verification_id>/', views.admin_verification_detail, name='admin_verification_detail'),
    path('verification-image/<int:image_id>/', views.verification_image, name='verification_image'),

    # 取引中止審査
    path('cancellations/', views.admin_cancellation_list, name='admin_cancellation_list'),
    path('cancellations/<int:cancellation_request_id>/', views.admin_cancellation_detail, name='admin_cancellation_detail'),

    # アカウント初期化
    path('user-reset/', views.admin_user_reset_list, name='admin_user_reset_list'),
    path('user-reset/<int:user_id>/', views.admin_user_reset_execute, name='admin_user_reset_execute'),

    # 補償申請審査
    path('insurance/claims/', views.admin_insurance_claims, name='admin_insurance_claims'),
    path('insurance/claims/<int:claim_id>/', views.admin_insurance_claim_detail, name='admin_insurance_claim_detail'),
    path('insurance/claims/<int:claim_id>/approve/', views.insurance_claim_approve, name='insurance_claim_approve'),
    path('insurance/claims/<int:claim_id>/reject/', views.insurance_claim_reject, name='insurance_claim_reject'),
]
