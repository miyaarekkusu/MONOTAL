/**
 * 管理者用本人確認審査画面JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // ESCキーでモーダルを閉じる
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
        }
    });
});

/**
 * CSRFトークンを取得
 */
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    return '';
}

/**
 * 画像モーダルを開く
 */
function openModal(src) {
    const modal = document.getElementById('imageModal');
    const modalImage = document.getElementById('modalImage');
    if (modal && modalImage) {
        modalImage.src = src;
        modal.classList.add('show');
    }
}

/**
 * 画像モーダルを閉じる
 */
function closeModal() {
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * トースト通知を表示
 */
function showToast(message, isSuccess = true) {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.style.background = isSuccess ? '#28a745' : '#dc3545';
        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

/**
 * 審査処理を送信
 */
async function submitReview(action) {
    const actionText = action === 'approve' ? '承認' : '却下';
    if (!confirm(`この申請を${actionText}しますか？`)) {
        return;
    }

    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');

    // ボタンを無効化
    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;

    const formData = new FormData();
    formData.append('action', action);

    try {
        const response = await fetch(window.location.href, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showToast(data.message, true);
            setTimeout(() => {
                window.location.href = getVerificationListUrl();
            }, 1500);
        } else {
            showToast(data.message || 'エラーが発生しました', false);
            if (approveBtn) approveBtn.disabled = false;
            if (rejectBtn) rejectBtn.disabled = false;
        }
    } catch (error) {
        showToast('ネットワークエラーが発生しました', false);
        if (approveBtn) approveBtn.disabled = false;
        if (rejectBtn) rejectBtn.disabled = false;
    }
}

/**
 * 一覧URLを取得（テンプレートから設定される）
 */
function getVerificationListUrl() {
    const listUrl = document.getElementById('verificationListUrl');
    return listUrl ? listUrl.value : '/monotal/admin/verifications/';
}
