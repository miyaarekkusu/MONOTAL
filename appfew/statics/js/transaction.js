/**
 * 取引画面 JavaScript
 */

const TransactionPage = {
    rentalHistoryId: null,
    pollInterval: null,
    lastMessageId: 0,

    /**
     * 初期化
     */
    init(rentalHistoryId) {
        this.rentalHistoryId = rentalHistoryId;
        this.loadMessages();
        this.initChatInput();
        this.initActionButtons();
        this.initCancelModal();
        this.startPolling();
    },

    /**
     * メッセージ読み込み
     */
    async loadMessages() {
        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/messages/`);
            const data = await response.json();

            if (data.success) {
                this.renderMessages(data.messages);
                if (data.messages.length > 0) {
                    this.lastMessageId = data.messages[data.messages.length - 1].message_id;
                }
            }
        } catch (error) {
            console.error('メッセージの読み込みに失敗しました:', error);
        }
    },

    /**
     * メッセージ表示
     */
    renderMessages(messages) {
        const container = document.getElementById('chatMessages');

        if (messages.length === 0) {
            container.innerHTML = `
                <div class="chat-empty">
                    <span class="iconify" data-icon="lucide:message-square-dashed" data-width="32"></span>
                    <p>まだメッセージはありません</p>
                    <span>取引相手にメッセージを送りましょう</span>
                </div>
            `;
            return;
        }

        container.innerHTML = messages.map(msg => `
            <div class="message-item ${msg.is_mine ? 'mine' : ''}">
                <div class="message-avatar">
                    ${msg.user_image
                        ? `<img src="${msg.user_image}" alt="${msg.user_name}">`
                        : '<span class="iconify" data-icon="lucide:user" data-width="18"></span>'}
                </div>
                <div class="message-content">
                    <div class="message-header">
                        <span class="message-name">${this.escapeHtml(msg.user_name)}</span>
                        <span class="message-time">${msg.created_at}</span>
                    </div>
                    <div class="message-bubble">${this.escapeHtml(msg.content)}</div>
                </div>
            </div>
        `).join('');

        // スクロールを最下部に
        container.scrollTop = container.scrollHeight;
    },

    /**
     * HTMLエスケープ
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * チャット入力初期化
     */
    initChatInput() {
        const input = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');

        if (!input || !sendBtn) return;

        // Enterキーで送信（Shift+Enterは改行）
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 送信ボタン
        sendBtn.addEventListener('click', () => this.sendMessage());

        // 入力状態でボタン有効化
        input.addEventListener('input', () => {
            sendBtn.disabled = !input.value.trim();
        });
    },

    /**
     * メッセージ送信
     */
    async sendMessage() {
        const input = document.getElementById('messageInput');
        const sendBtn = document.getElementById('sendBtn');
        const content = input.value.trim();

        if (!content) return;

        sendBtn.disabled = true;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/messages/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });

            const data = await response.json();

            if (data.success) {
                input.value = '';
                this.loadMessages();
            } else {
                alert(data.message || 'メッセージの送信に失敗しました');
            }
        } catch (error) {
            console.error('メッセージの送信に失敗しました:', error);
            alert('メッセージの送信に失敗しました');
        } finally {
            sendBtn.disabled = false;
        }
    },

    /**
     * リアルタイム更新（ポーリング）
     */
    startPolling() {
        this.pollInterval = setInterval(() => {
            this.loadMessages();
        }, 5000);
    },

    /**
     * ポーリング停止
     */
    stopPolling() {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
    },

    /**
     * アクションボタン初期化
     */
    initActionButtons() {
        // 発送通知
        const shipBtn = document.getElementById('shipBtn');
        if (shipBtn) {
            shipBtn.addEventListener('click', () => this.notifyShipping());
        }

        // 受取通知
        const receiveBtn = document.getElementById('receiveBtn');
        if (receiveBtn) {
            receiveBtn.addEventListener('click', () => this.notifyReceipt());
        }

        // 返送通知
        const returnShipBtn = document.getElementById('returnShipBtn');
        if (returnShipBtn) {
            returnShipBtn.addEventListener('click', () => this.notifyReturnShip());
        }

        // 返却受取
        const returnReceiveBtn = document.getElementById('returnReceiveBtn');
        if (returnReceiveBtn) {
            returnReceiveBtn.addEventListener('click', () => this.notifyReturnReceive());
        }

        // キャンセル
        const cancelBtn = document.getElementById('cancelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.openCancelModal());
        }
    },

    /**
     * 発送通知
     */
    async notifyShipping() {
        if (!confirm('商品を発送しましたか？\n発送通知を送信します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/ship/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(data.message || '発送通知に失敗しました');
            }
        } catch (error) {
            console.error('発送通知に失敗しました:', error);
            alert('発送通知に失敗しました');
        }
    },

    /**
     * 受取通知
     */
    async notifyReceipt() {
        if (!confirm('商品を受け取りましたか？\n受取完了を通知します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/receive/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(data.message || '受取通知に失敗しました');
            }
        } catch (error) {
            console.error('受取通知に失敗しました:', error);
            alert('受取通知に失敗しました');
        }
    },

    /**
     * 返送通知
     */
    async notifyReturnShip() {
        if (!confirm('商品を返送しましたか？\n返送通知を送信します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-ship/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(data.message || '返送通知に失敗しました');
            }
        } catch (error) {
            console.error('返送通知に失敗しました:', error);
            alert('返送通知に失敗しました');
        }
    },

    /**
     * 返却受取
     */
    async notifyReturnReceive() {
        if (!confirm('商品が届きましたか？\n取引完了を確定します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-receive/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(data.message || '返却確認に失敗しました');
            }
        } catch (error) {
            console.error('返却確認に失敗しました:', error);
            alert('返却確認に失敗しました');
        }
    },

    /**
     * キャンセルモーダル初期化
     */
    initCancelModal() {
        const modal = document.getElementById('cancelModal');
        const closeBtn = document.getElementById('modalCloseBtn');
        const cancelBtn = document.getElementById('modalCancelBtn');
        const form = document.getElementById('cancelForm');
        const overlay = modal?.querySelector('.modal-overlay');

        if (!modal) return;

        // 閉じるボタン
        closeBtn?.addEventListener('click', () => this.closeCancelModal());
        cancelBtn?.addEventListener('click', () => this.closeCancelModal());
        overlay?.addEventListener('click', () => this.closeCancelModal());

        // フォーム送信
        form?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.cancelTransaction();
        });
    },

    /**
     * キャンセルモーダルを開く
     */
    openCancelModal() {
        const modal = document.getElementById('cancelModal');
        modal?.classList.remove('hidden');
    },

    /**
     * キャンセルモーダルを閉じる
     */
    closeCancelModal() {
        const modal = document.getElementById('cancelModal');
        modal?.classList.add('hidden');
        // フォームをリセット
        document.getElementById('cancelForm')?.reset();
    },

    /**
     * 取引キャンセル
     */
    async cancelTransaction() {
        const reasonId = document.getElementById('returnReasonSelect').value;
        const detail = document.getElementById('returnReasonDetail').value;

        if (!reasonId) {
            alert('キャンセル理由を選択してください');
            return;
        }

        if (!confirm('本当に取引をキャンセルしますか？\nこの操作は取り消せません。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/cancel/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    return_reason_id: reasonId,
                    return_reason_detail: detail
                })
            });
            const data = await response.json();

            if (data.success) {
                alert(data.message);
                location.reload();
            } else {
                alert(data.message || 'キャンセルに失敗しました');
            }
        } catch (error) {
            console.error('キャンセルに失敗しました:', error);
            alert('キャンセルに失敗しました');
        }
    }
};

// ページ読み込み時に初期化
document.addEventListener('DOMContentLoaded', () => {
    if (typeof RENTAL_HISTORY_ID !== 'undefined') {
        TransactionPage.init(RENTAL_HISTORY_ID);
    }
});

// ページ離脱時にポーリング停止
window.addEventListener('beforeunload', () => {
    TransactionPage.stopPolling();
});
