// 取引認証ページ JavaScript

// DOMが読み込まれた後に実行
document.addEventListener('DOMContentLoaded', function () {
    initializeTradeVerification();
});

// 初期化処理
function initializeTradeVerification() {
    // フィルタータブの初期化
    initializeFilterTabs();

    // 未承認の申請件数をカウントしてタイトルに表示
    updatePageTitle();

    // その他の初期化処理があればここに追加
    console.log('取引認証ページが初期化されました');
}

// フィルタータブの初期化
function initializeFilterTabs() {
    const filterTabs = document.querySelectorAll('.filter-tab');

    filterTabs.forEach(tab => {
        tab.addEventListener('click', function () {
            handleFilterTabClick(this);
        });
    });
}

// フィルタータブクリック処理
function handleFilterTabClick(clickedTab) {
    // アクティブタブの切り替え
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    clickedTab.classList.add('active');

    // フィルタリング実行
    const status = clickedTab.getAttribute('data-status');
    filterTradeRequests(status);
}

// 取引申請のフィルタリング
function filterTradeRequests(status) {
    const items = document.querySelectorAll('.trade-request-item');
    let visibleCount = 0;

    items.forEach(item => {
        const itemStatus = item.getAttribute('data-status');

        if (status === 'all' || status === itemStatus) {
            item.style.display = 'block';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });

    // 結果が0件の場合のメッセージ表示
    showEmptyStateIfNeeded(visibleCount, status);
}

// 空の状態メッセージを表示
function showEmptyStateIfNeeded(visibleCount, status) {
    const container = document.querySelector('.trade-requests-list');
    const existingEmptyState = container.querySelector('.empty-state');

    // 既存の空状態メッセージを削除
    if (existingEmptyState) {
        existingEmptyState.remove();
    }

    // 表示する項目がない場合
    if (visibleCount === 0) {
        const emptyMessage = createEmptyStateMessage(status);
        container.appendChild(emptyMessage);
    }
}

// 空状態メッセージの作成
function createEmptyStateMessage(status) {
    const emptyDiv = document.createElement('div');
    emptyDiv.className = 'empty-state';

    let message = '';
    let description = '';

    switch (status) {
        case 'pending':
            message = '未承認の取引申請はありません';
            description = '新しい取引申請が来るまでお待ちください';
            break;
        case 'approved':
            message = '承認済みの取引申請はありません';
            description = '承認した取引がある場合、ここに表示されます';
            break;
        case 'rejected':
            message = '却下した取引申請はありません';
            description = '却下した取引がある場合、ここに表示されます';
            break;
        default:
            message = '取引申請がありません';
            description = '商品への申請が来るとここに表示されます';
    }

    emptyDiv.innerHTML = `
        <div class="empty-icon">
            <i class="fas fa-inbox"></i>
        </div>
        <div class="empty-message">${message}</div>
        <div class="empty-description">${description}</div>
    `;

    return emptyDiv;
}

// ページタイトルの更新
function updatePageTitle() {
    const pendingCount = document.querySelectorAll('[data-status="pending"]').length;

    if (pendingCount > 0) {
        document.title = `取引認証 (${pendingCount}) - monotal`;
    }
}

// 取引承認処理
function approveTrade(requestId) {
    if (!confirm('この取引申請を承認しますか？')) {
        return;
    }

    // ローディング状態の表示
    showLoadingState(requestId);

    // 実際の実装では、ここでサーバーにAjaxリクエストを送信
    // 例: await fetch('/api/trade-requests/approve', { method: 'POST', body: JSON.stringify({ requestId }) });

    // デモ用の遅延処理
    setTimeout(() => {
        updateTradeRequestStatus(requestId, 'approved');
        showSuccessMessage('取引申請を承認しました。');
        updatePageTitle();
    }, 1000);
}

// 取引却下処理
function rejectTrade(requestId) {
    if (!confirm('この取引申請を却下しますか？')) {
        return;
    }

    // ローディング状態の表示
    showLoadingState(requestId);

    // 実際の実装では、ここでサーバーにAjaxリクエストを送信
    // 例: await fetch('/api/trade-requests/reject', { method: 'POST', body: JSON.stringify({ requestId }) });

    // デモ用の遅延処理
    setTimeout(() => {
        updateTradeRequestStatus(requestId, 'rejected');
        showSuccessMessage('取引申請を却下しました。');
        updatePageTitle();
    }, 1000);
}

// ローディング状態の表示
function showLoadingState(requestId) {
    const item = document.querySelector(`[data-request="${requestId}"]`);
    if (!item) return;

    const buttons = item.querySelector('.action-buttons');
    const originalButtons = buttons.innerHTML;

    // ローディングボタンを表示
    buttons.innerHTML = `
        <button class="btn btn-outline" disabled>
            <i class="fas fa-spinner fa-spin"></i> 処理中...
        </button>
    `;

    // 元のボタンを一時保存
    buttons.setAttribute('data-original', originalButtons);
}

// 取引申請ステータスの更新
function updateTradeRequestStatus(requestId, newStatus) {
    const item = document.querySelector(`[data-request="${requestId}"]`);
    if (!item) return;

    // ステータスの更新
    const statusElement = item.querySelector('.request-status');
    item.setAttribute('data-status', newStatus);

    switch (newStatus) {
        case 'approved':
            statusElement.textContent = '承認済み';
            statusElement.className = 'request-status status-approved';
            updateButtonsForApproved(item, requestId);
            break;
        case 'rejected':
            statusElement.textContent = '却下';
            statusElement.className = 'request-status status-rejected';
            updateButtonsForRejected(item);
            break;
    }
}

// 承認済み用ボタンの更新
function updateButtonsForApproved(item, requestId) {
    const buttons = item.querySelector('.action-buttons');
    const userId = extractUserIdFromItem(item);

    buttons.innerHTML = `
        <button class="btn btn-outline" onclick="viewProfile('${userId}')">
            <i class="fas fa-user"></i> プロフィール確認
        </button>
        <button class="btn btn-primary" onclick="startTrade('${requestId}')">
            <i class="fas fa-handshake"></i> 取引開始
        </button>
    `;
}

// 却下済み用ボタンの更新
function updateButtonsForRejected(item) {
    const buttons = item.querySelector('.action-buttons');
    const userId = extractUserIdFromItem(item);

    buttons.innerHTML = `
        <button class="btn btn-outline" onclick="viewProfile('${userId}')">
            <i class="fas fa-user"></i> プロフィール確認
        </button>
    `;
}

// アイテムからユーザーIDを取得（実際の実装では適切なIDを使用）
function extractUserIdFromItem(item) {
    const userName = item.querySelector('.user-name').textContent;
    // 実際の実装では、data属性などから適切なユーザーIDを取得
    return userName.replace(/\s/g, '').toLowerCase();
}

// プロフィール確認
function viewProfile(userId) {
    // 実際の実装では、ユーザープロフィールページに遷移
    // window.location.href = `/profile/${userId}`;

    showInfoMessage(`ユーザー ${userId} のプロフィールページに移動します。`);
}

// 取引開始
function startTrade(requestId) {
    // 実際の実装では、取引チャットページに遷移
    // window.location.href = `/trade/${requestId}/chat`;

    showInfoMessage('取引チャットページに移動します。');
}

// 成功メッセージの表示
function showSuccessMessage(message) {
    showNotification(message, 'success');
}

// 情報メッセージの表示
function showInfoMessage(message) {
    showNotification(message, 'info');
}

// エラーメッセージの表示
function showErrorMessage(message) {
    showNotification(message, 'error');
}

// 通知メッセージの表示（共通関数）
function showNotification(message, type = 'info') {
    // 既存の通知を削除
    const existingNotification = document.querySelector('.notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    // 通知要素を作成
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas ${getNotificationIcon(type)}"></i>
            <span>${message}</span>
        </div>
        <button class="notification-close" onclick="closeNotification()">
            <i class="fas fa-times"></i>
        </button>
    `;

    // スタイルを追加
    addNotificationStyles();

    // ページに追加
    document.body.appendChild(notification);

    // 自動で削除（5秒後）
    setTimeout(() => {
        if (notification && notification.parentNode) {
            notification.remove();
        }
    }, 5000);

    // アニメーション
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);
}

// 通知アイコンの取得
function getNotificationIcon(type) {
    switch (type) {
        case 'success':
            return 'fa-check-circle';
        case 'error':
            return 'fa-exclamation-triangle';
        case 'warning':
            return 'fa-exclamation-circle';
        default:
            return 'fa-info-circle';
    }
}

// 通知を閉じる
function closeNotification() {
    const notification = document.querySelector('.notification');
    if (notification) {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    }
}

// 通知スタイルの追加（動的に追加）
function addNotificationStyles() {
    // スタイルが既に追加されているかチェック
    if (document.querySelector('#notification-styles')) {
        return;
    }

    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 10000;
            min-width: 300px;
            transform: translateX(100%);
            transition: transform 0.3s ease-in-out;
            border-left: 4px solid #007bff;
        }
        
        .notification.show {
            transform: translateX(0);
        }
        
        .notification-success {
            border-left-color: #28a745;
        }
        
        .notification-error {
            border-left-color: #dc3545;
        }
        
        .notification-warning {
            border-left-color: #ffc107;
        }
        
        .notification-content {
            display: flex;
            align-items: center;
            gap: 8px;
            flex: 1;
            font-size: 14px;
            color: #333;
        }
        
        .notification-content i {
            font-size: 16px;
        }
        
        .notification-success .notification-content i {
            color: #28a745;
        }
        
        .notification-error .notification-content i {
            color: #dc3545;
        }
        
        .notification-warning .notification-content i {
            color: #ffc107;
        }
        
        .notification-info .notification-content i {
            color: #007bff;
        }
        
        .notification-close {
            background: none;
            border: none;
            color: #666;
            cursor: pointer;
            padding: 4px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        
        .notification-close:hover {
            background-color: #f8f9fa;
        }
        
        @media (max-width: 480px) {
            .notification {
                right: 10px;
                left: 10px;
                min-width: auto;
            }
        }
    `;

    document.head.appendChild(style);
}

// API通信用のヘルパー関数
async function apiRequest(url, method = 'GET', data = null) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                // 認証トークンがある場合
                // 'Authorization': `Bearer ${getAuthToken()}`
            }
        };

        if (data && method !== 'GET') {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

// 認証トークンの取得（実装例）
function getAuthToken() {
    // ローカルストレージまたはセッションストレージからトークンを取得
    return localStorage.getItem('authToken') || sessionStorage.getItem('authToken');
}

// データの再読み込み
async function refreshTradeRequests() {
    try {
        showLoadingOverlay();

        // 実際の実装では、APIからデータを取得
        // const data = await apiRequest('/api/trade-requests');
        // updateTradeRequestsList(data);

        // デモ用
        setTimeout(() => {
            hideLoadingOverlay();
            showSuccessMessage('データを更新しました。');
        }, 1000);

    } catch (error) {
        hideLoadingOverlay();
        showErrorMessage('データの取得に失敗しました。');
        console.error('Error refreshing trade requests:', error);
    }
}

// ローディングオーバーレイの表示
function showLoadingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.innerHTML = `
        <div class="loading-spinner">
            <i class="fas fa-spinner fa-spin"></i>
            <p>読み込み中...</p>
        </div>
    `;

    // ローディングオーバーレイのスタイル
    const style = document.createElement('style');
    style.textContent = `
        #loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 255, 255, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
        
        .loading-spinner {
            text-align: center;
            color: #666;
        }
        
        .loading-spinner i {
            font-size: 32px;
            margin-bottom: 16px;
            color: #ff4757;
        }
        
        .loading-spinner p {
            margin: 0;
            font-size: 14px;
        }
    `;

    document.head.appendChild(style);
    document.body.appendChild(overlay);
}

// ローディングオーバーレイの非表示
function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// ページの状態管理
const pageState = {
    currentFilter: 'all',
    isLoading: false
};

// 状態の更新
function updatePageState(newState) {
    Object.assign(pageState, newState);
}

// エラーハンドリング
window.addEventListener('error', function (event) {
    console.error('JavaScript Error:', event.error);
    showErrorMessage('予期しないエラーが発生しました。');
});

// 未処理のPromise拒否をキャッチ
window.addEventListener('unhandledrejection', function (event) {
    console.error('Unhandled Promise Rejection:', event.reason);
    showErrorMessage('通信エラーが発生しました。');
});

// ユーティリティ関数
const utils = {
    // 日付フォーマット
    formatDate: function (dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

        if (diffHours < 1) {
            return '1時間未満前';
        } else if (diffHours < 24) {
            return `${diffHours}時間前`;
        } else {
            return `${diffDays}日前`;
        }
    },

    // 価格フォーマット
    formatPrice: function (price) {
        return `¥${price.toLocaleString()}`;
    },

    // テキストの切り詰め
    truncateText: function (text, maxLength) {
        if (text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + '...';
    }
};

// デバッグモード（開発時のみ）
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    window.tradeVerificationDebug = {
        pageState,
        utils,
        refreshData: refreshTradeRequests,
        showNotification,
        apiRequest
    };
    console.log('デバッグモードが有効です。window.tradeVerificationDebug でデバッグ関数にアクセスできます。');
}