/**
 * 管理者用中止申請審査画面JavaScript
 */

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
 * 中止申請審査処理を送信
 */
async function submitCancellationReview(action) {
    const approveBtn = document.getElementById('approveBtn');
    const rejectBtn = document.getElementById('rejectBtn');

    const confirmMsg = action === 'approve'
        ? '取引を中止しますか？\n商品は貸出可能に戻ります。'
        : '中止申請を却下しますか？\n取引は元のステータスに復元されます。';

    const confirmed = await showConfirm(confirmMsg, {
        title: action === 'approve' ? '取引中止' : '申請却下',
        confirmText: action === 'approve' ? '中止する' : '却下する',
        danger: true
    });
    if (!confirmed) {
        return;
    }

    if (approveBtn) approveBtn.disabled = true;
    if (rejectBtn) rejectBtn.disabled = true;

    const formData = new FormData();
    formData.append('action', action);

    const adminNote = document.getElementById('adminNote');
    if (adminNote) {
        formData.append('admin_note', adminNote.value);
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
                const listUrl = document.getElementById('cancellationListUrl');
                window.location.href = listUrl ? listUrl.value : '/monotal/admin/cancellations/';
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
