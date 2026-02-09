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
    path('sell/bank-account-required/', views.bank_account_required, name='bank_account_required'),
    path('shop/', views.product_list, name='product_list'),
    path('search/autocomplete/', views.search_autocomplete, name='search_autocomplete'),
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
    path('mypage/bank-accounts/', views.mypage_bank_account_list, name='mypage_bank_account_list'),
    path('mypage/bank-accounts/<int:bank_account_id>/edit/', views.bank_account_edit, name='bank_account_edit'),
    path('mypage/bank-accounts/<int:bank_account_id>/delete/', views.bank_account_delete, name='bank_account_delete'),
    path('mypage/credit-cards/', views.mypage_credit_card_list, name='mypage_credit_card_list'),
    path('mypage/credit-cards/<int:credit_card_id>/edit/', views.credit_card_edit, name='credit_card_edit'),
    path('mypage/credit-cards/<int:credit_card_id>/delete/', views.credit_card_delete, name='credit_card_delete'),

    # レンタル関連
    path('product/<int:product_id>/rental/', views.rental_request, name='rental_request'),
    path('product/<int:product_id>/rental/complete/', views.rental_request_complete, name='rental_request_complete'),
    path('mypage/rental-management/', views.mypage_rental_management, name='mypage_rental_management'),
    path('rental-request/<int:request_id>/approve/', views.rental_request_approve, name='rental_request_approve'),
    path('rental-request/<int:request_id>/reject/', views.rental_request_reject, name='rental_request_reject'),
    path('rental-request/<int:request_id>/start/', views.rental_start_page, name='rental_start_page'),
    path('rental-request/<int:request_id>/start/addresses/', views.rental_address_manage, name='rental_address_manage'),
    path('rental-request/<int:request_id>/start/cards/', views.rental_card_manage, name='rental_card_manage'),
    path('rental-request/<int:request_id>/start/confirm/', views.rental_request_start, name='rental_request_start'),
    path('rental-request/<int:request_id>/cancel/', views.rental_request_cancel, name='rental_request_cancel'),
    path('rental-request/<int:request_id>/cancel-seller/', views.rental_request_cancel_seller, name='rental_request_cancel_seller'),

    # 取引画面
    path('transaction/<int:rental_history_id>/', views.transaction_view, name='transaction'),
    path('transaction/<int:rental_history_id>/messages/', views.transaction_messages, name='transaction_messages'),
    path('transaction/<int:rental_history_id>/ship/', views.transaction_ship, name='transaction_ship'),
    path('transaction/<int:rental_history_id>/receive/', views.transaction_receive, name='transaction_receive'),
    path('transaction/<int:rental_history_id>/return-ship/', views.transaction_return_ship, name='transaction_return_ship'),
    path('transaction/<int:rental_history_id>/return-receive/', views.transaction_return_receive, name='transaction_return_receive'),
    path('transaction/<int:rental_history_id>/cancel/', views.transaction_cancel, name='transaction_cancel'),

    # 通知関連
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('notifications/read-all/', views.notification_mark_all_read, name='notification_mark_all_read'),

    # 保険関連
    path('mypage/insurance/', views.insurance_page, name='insurance_page'),
    path('mypage/insurance/enroll/', views.insurance_enroll, name='insurance_enroll'),
    path('mypage/insurance/cancel/', views.insurance_cancel, name='insurance_cancel'),
    path('mypage/insurance/claim/', views.insurance_claim_page, name='insurance_claim'),
    path('mypage/insurance/claim/submit/', views.insurance_claim_submit, name='insurance_claim_submit'),

    # 管理者：保険クレーム管理
    path('admin/insurance/claims/', views.admin_insurance_claims, name='admin_insurance_claims'),
    path('admin/insurance/claims/<int:claim_id>/', views.admin_insurance_claim_detail, name='admin_insurance_claim_detail'),
    path('admin/insurance/claims/<int:claim_id>/approve/', views.insurance_claim_approve, name='insurance_claim_approve'),
    path('admin/insurance/claims/<int:claim_id>/reject/', views.insurance_claim_reject, name='insurance_claim_reject'),
]