from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('register/form/', views.register_form, name='register_form'),
    path('register/complete/', views.register_complete, name='register_complete'),
    path('register/sent/', views.register_sent, name='register_sent'),
    path('verify/<uuid:token>/', views.email_verify, name='email_verify'),
    path('profile/<str:username>/', views.profile, name='profile'),
    path('profile/profile_setting/<str:username>/', views.profile_setting, name='profile_setting'),
    path('sell/', views.create_sell, name='create_sell'),
    path('sell/addresses/', views.sell_address_manage, name='sell_address_manage'),
    path('sell/verification-required/', views.verification_required, name='verification_required'),
    path('shop/', views.product_list, name='product_list'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('product/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('product/<int:product_id>/edit/addresses/', views.edit_address_manage, name='edit_address_manage'),
    path('product/<int:product_id>/status/', views.product_status_update, name='product_status_update'),
    path('product/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    path('product/<int:product_id>/bookmark/', views.bookmark_toggle, name='bookmark_toggle'),
    path('product/<int:product_id>/messages/', views.product_messages, name='product_messages'),
    path('product/<int:product_id>/messages/<int:message_id>/delete/', views.product_message_delete, name='product_message_delete'),
    path('interest/', views.interest_selection, name='interest_selection'),

    # 本人確認（ユーザー向け）
    path('identity-verification/', views.identity_verification, name='identity_verification'),

    # 管理者用本人確認審査
    path('admin/verifications/', views.admin_verification_list, name='admin_verification_list'),
    path('admin/verifications/<int:verification_id>/', views.admin_verification_detail, name='admin_verification_detail'),
    path('admin/verification-image/<int:image_id>/', views.verification_image, name='verification_image'),

    # フォロー関連
    path('user/<int:user_id>/follow/', views.follow_toggle, name='follow_toggle'),

    # マイページ
    path('mypage/follow-list/', views.mypage_follow_list, name='mypage_follow_list'),
    path('mypage/bookmark-list/', views.mypage_bookmark_list, name='mypage_bookmark_list'),
    path('mypage/browsing-history/', views.mypage_browsing_history, name='mypage_browsing_history'),
    path('mypage/listing/', views.mypage_listing, name='mypage_listing'),
    path('mypage/addresses/', views.mypage_address_list, name='mypage_address_list'),
    path('mypage/addresses/<int:address_id>/edit/', views.address_edit, name='address_edit'),
    path('mypage/addresses/<int:address_id>/delete/', views.address_delete, name='address_delete'),
]