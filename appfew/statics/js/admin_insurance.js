/**
 * 管理者用補償申請審査画面JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeModal();
            closeRejectModal();
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
 * 却下理由モーダルを開く
 */
function openRejectModal() {
    const modal = document.getElementById('rejectModal');
    if (modal) {
        modal.classList.add('show');
        const textarea = document.getElementById('rejectReason');
        if (textarea) textarea.focus();
    }
}

/**
 * 却下理由モーダルを閉じる
 */
function closeRejectModal() {
    const modal = document.getElementById('rejectModal');
    if (modal) {
        modal.classList.remove('show');
    }
}

/**
 * トースト通知を表示
 */
function showToast(message, isSuccess) {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.style.background = isSuccess ? '#28a745' : '#dc3545';
        toast.classList.add('show');
        setTimeout(function() {
            toast.classList.remove('show');
        }, 3000);
    }
}

/**
 * 補償申請審査処理を送信
 */
async function submitClaimReview(action) {
    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');

    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;

    const formData = new FormData();
    formData.append('action', action);

    if (action === 'reject') {
        const reason = document.getElementById('rejectReason');
        formData.append('reason', reason ? reason.value : '');
        closeRejectModal();
    }

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
            setTimeout(function() {
                window.location.href = getClaimListUrl();
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
 * 一覧URLを取得
 */
function getClaimListUrl() {
    const listUrl = document.getElementById('claimListUrl');
    return listUrl ? listUrl.value : '/monotal/admin/insurance/claims/';
}
