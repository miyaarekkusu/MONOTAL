/**
 * 取引画面 JavaScript
 */

const TransactionPage = {
    rentalHistoryId: null,
    pollInterval: null,
    lastMessageId: 0,
    countdownInterval: null,

    /**
     * 初期化
     */
    init(rentalHistoryId) {
        this.rentalHistoryId = rentalHistoryId;
        this.loadMessages();
        this.initChatInput();
        this.initActionButtons();
        this.initCancelModal();
        this.initShipModal();
        this.initReturnShipModal();
        this.initReturnRequestModal();
        this.initReturnActions();
        this.initReturnShipRefundModal();
        this.initTrackingModal();
        this.initCancellationModal();
        this.initCountdown();
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

    formatDateJST(isoStr) {
        if (!isoStr) return '';
        try {
            const d = new Date(isoStr);
            return d.toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' });
        } catch {
            return this.escapeHtml(isoStr);
        }
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
                showAlert(data.message || 'メッセージの送信に失敗しました');
            }
        } catch (error) {
            console.error('メッセージの送信に失敗しました:', error);
            showAlert('メッセージの送信に失敗しました');
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
        // 発送通知 → モーダルを開く
        const shipBtn = document.getElementById('shipBtn');
        if (shipBtn) {
            shipBtn.addEventListener('click', () => this.openModal('shipModal'));
        }

        // 受取通知
        const receiveBtn = document.getElementById('receiveBtn');
        if (receiveBtn) {
            receiveBtn.addEventListener('click', () => this.notifyReceipt());
        }

        // 返送通知 → モーダルを開く
        const returnShipBtn = document.getElementById('returnShipBtn');
        if (returnShipBtn) {
            returnShipBtn.addEventListener('click', () => this.openModal('returnShipModal'));
        }

        // 返却受取
        const returnReceiveBtn = document.getElementById('returnReceiveBtn');
        if (returnReceiveBtn) {
            returnReceiveBtn.addEventListener('click', () => this.notifyReturnReceive());
        }

        // 中止申請
        const cancellationRequestBtn = document.getElementById('cancellationRequestBtn');
        if (cancellationRequestBtn) {
            cancellationRequestBtn.addEventListener('click', () => this.openModal('cancellationRequestModal'));
        }

        // キャンセル
        const cancelBtn = document.getElementById('cancelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.openCancelModal());
        }

        // 返品申請 → モーダルを開く
        const returnRequestBtn = document.getElementById('returnRequestBtn');
        if (returnRequestBtn) {
            returnRequestBtn.addEventListener('click', () => this.openModal('returnRequestModal'));
        }

        // 返品発送 → モーダルを開く
        const returnShipRefundBtn = document.getElementById('returnShipRefundBtn');
        if (returnShipRefundBtn) {
            returnShipRefundBtn.addEventListener('click', () => this.openModal('returnShipRefundModal'));
        }
    },

    // ==========================================
    // モーダル共通
    // ==========================================

    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.remove('hidden');
    },

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) modal.classList.add('hidden');
    },

    // ==========================================
    // 発送モーダル
    // ==========================================

    initShipModal() {
        const modal = document.getElementById('shipModal');
        if (!modal) return;

        // 閉じるボタン
        modal.querySelectorAll('[data-modal="shipModal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal('shipModal'));
        });
        modal.querySelector('.modal-overlay')?.addEventListener('click', () => this.closeModal('shipModal'));

        // 発送確認ボタン
        const confirmBtn = document.getElementById('shipConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.submitShipping());
        }
    },

    async submitShipping() {
        const trackingNumber = document.getElementById('shipTrackingNumber')?.value.trim() || '';
        const carrierCode = document.getElementById('shipCarrierCode')?.value || '';
        const confirmBtn = document.getElementById('shipConfirmBtn');
        const errorEl = document.getElementById('shipError');

        if (errorEl) errorEl.classList.add('hidden');
        if (confirmBtn) confirmBtn.disabled = true;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/ship/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tracking_number: trackingNumber,
                    carrier_code: carrierCode
                })
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                if (errorEl) {
                    errorEl.textContent = data.message || '発送通知に失敗しました';
                    errorEl.classList.remove('hidden');
                } else {
                    showAlert(data.message || '発送通知に失敗しました');
                }
            }
        } catch (error) {
            console.error('発送通知に失敗しました:', error);
            showAlert('発送通知に失敗しました');
        } finally {
            if (confirmBtn) confirmBtn.disabled = false;
        }
    },

    // ==========================================
    // 返送モーダル
    // ==========================================

    initReturnShipModal() {
        const modal = document.getElementById('returnShipModal');
        if (!modal) return;

        // 閉じるボタン
        modal.querySelectorAll('[data-modal="returnShipModal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal('returnShipModal'));
        });
        modal.querySelector('.modal-overlay')?.addEventListener('click', () => this.closeModal('returnShipModal'));

        // 返送確認ボタン
        const confirmBtn = document.getElementById('returnShipConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.submitReturnShipping());
        }
    },

    async submitReturnShipping() {
        const trackingNumber = document.getElementById('returnTrackingNumber')?.value.trim() || '';
        const carrierCode = document.getElementById('returnCarrierCode')?.value || '';
        const confirmBtn = document.getElementById('returnShipConfirmBtn');
        const errorEl = document.getElementById('returnShipError');

        if (errorEl) errorEl.classList.add('hidden');
        if (confirmBtn) confirmBtn.disabled = true;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-ship/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tracking_number: trackingNumber,
                    carrier_code: carrierCode
                })
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                if (errorEl) {
                    errorEl.textContent = data.message || '返送通知に失敗しました';
                    errorEl.classList.remove('hidden');
                } else {
                    showAlert(data.message || '返送通知に失敗しました');
                }
            }
        } catch (error) {
            console.error('返送通知に失敗しました:', error);
            showAlert('返送通知に失敗しました');
        } finally {
            if (confirmBtn) confirmBtn.disabled = false;
        }
    },

    // ==========================================
    // 返品申請モーダル
    // ==========================================

    initReturnRequestModal() {
        const modal = document.getElementById('returnRequestModal');
        if (!modal) return;

        modal.querySelectorAll('[data-modal="returnRequestModal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal('returnRequestModal'));
        });
        modal.querySelector('.modal-overlay')?.addEventListener('click', () => this.closeModal('returnRequestModal'));

        const confirmBtn = document.getElementById('returnRequestConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.submitReturnRequest());
        }
    },

    async submitReturnRequest() {
        const reasonId = document.getElementById('returnRequestReasonSelect')?.value;
        const detail = document.getElementById('returnRequestReasonDetail')?.value || '';
        const confirmBtn = document.getElementById('returnRequestConfirmBtn');
        const errorEl = document.getElementById('returnRequestError');

        if (!reasonId) {
            if (errorEl) {
                errorEl.textContent = '返品理由を選択してください';
                errorEl.classList.remove('hidden');
            }
            return;
        }

        this.closeModal('returnRequestModal');

        if (!await showConfirm('返品を申請しますか？\n出品者の承認後に返品手続きが進みます。')) {
            this.openModal('returnRequestModal');
            return;
        }

        if (errorEl) errorEl.classList.add('hidden');
        if (confirmBtn) confirmBtn.disabled = true;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-request/`, {
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
                location.reload();
            } else {
                if (errorEl) {
                    errorEl.textContent = data.message || '返品申請に失敗しました';
                    errorEl.classList.remove('hidden');
                } else {
                    showAlert(data.message || '返品申請に失敗しました');
                }
            }
        } catch (error) {
            console.error('返品申請に失敗しました:', error);
            showAlert('返品申請に失敗しました');
        } finally {
            if (confirmBtn) confirmBtn.disabled = false;
        }
    },

    // ==========================================
    // 返品承認・拒否
    // ==========================================

    initReturnActions() {
        const approveBtn = document.getElementById('returnApproveBtn');
        if (approveBtn) {
            approveBtn.addEventListener('click', () => this.approveReturn());
        }

        const rejectBtn = document.getElementById('returnRejectBtn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => this.rejectReturn());
        }
    },

    async approveReturn() {
        if (!await showConfirm('返品申請を承認しますか？\n借り手に商品の返送を依頼します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-approve/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                showAlert(data.message || '承認に失敗しました');
            }
        } catch (error) {
            console.error('承認に失敗しました:', error);
            showAlert('承認に失敗しました');
        }
    },

    async rejectReturn() {
        if (!await showConfirm('返品申請を拒否しますか？\n取引はレンタル中の状態に戻ります。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-reject/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                showAlert(data.message || '拒否に失敗しました');
            }
        } catch (error) {
            console.error('拒否に失敗しました:', error);
            showAlert('拒否に失敗しました');
        }
    },

    // ==========================================
    // 返品発送モーダル
    // ==========================================

    initReturnShipRefundModal() {
        const modal = document.getElementById('returnShipRefundModal');
        if (!modal) return;

        modal.querySelectorAll('[data-modal="returnShipRefundModal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal('returnShipRefundModal'));
        });
        modal.querySelector('.modal-overlay')?.addEventListener('click', () => this.closeModal('returnShipRefundModal'));

        const confirmBtn = document.getElementById('returnShipRefundConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.submitReturnShipRefund());
        }
    },

    async submitReturnShipRefund() {
        const trackingNumber = document.getElementById('returnRefundTrackingNumber')?.value.trim() || '';
        const carrierCode = document.getElementById('returnRefundCarrierCode')?.value || '';
        const confirmBtn = document.getElementById('returnShipRefundConfirmBtn');
        const errorEl = document.getElementById('returnShipRefundError');

        if (errorEl) errorEl.classList.add('hidden');
        if (confirmBtn) confirmBtn.disabled = true;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-ship-refund/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tracking_number: trackingNumber,
                    carrier_code: carrierCode
                })
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                if (errorEl) {
                    errorEl.textContent = data.message || '返品発送通知に失敗しました';
                    errorEl.classList.remove('hidden');
                } else {
                    showAlert(data.message || '返品発送通知に失敗しました');
                }
            }
        } catch (error) {
            console.error('返品発送通知に失敗しました:', error);
            showAlert('返品発送通知に失敗しました');
        } finally {
            if (confirmBtn) confirmBtn.disabled = false;
        }
    },

    // ==========================================
    // 追跡情報モーダル
    // ==========================================

    initTrackingModal() {
        // 追跡リンククリック
        document.querySelectorAll('.tracking-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const type = link.dataset.trackingType;
                this.showTracking(type);
            });
        });

        // 閉じるボタン
        const modal = document.getElementById('trackingModal');
        if (!modal) return;
        modal.querySelectorAll('[data-modal="trackingModal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal('trackingModal'));
        });
        modal.querySelector('.modal-overlay')?.addEventListener('click', () => this.closeModal('trackingModal'));
    },

    async showTracking(type) {
        const body = document.getElementById('trackingModalBody');
        body.innerHTML = '<div class="chat-loading"><span class="iconify animate-spin" data-icon="lucide:loader-2" data-width="24"></span></div>';
        this.openModal('trackingModal');

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/tracking/${type}/`);
            const data = await response.json();

            if (!data.success) {
                body.innerHTML = `<div class="tracking-error">${this.escapeHtml(data.message)}</div>`;
                return;
            }

            let html = `<div class="tracking-info">`;
            html += `<div class="tracking-number-display"><strong>追跡番号:</strong> ${this.escapeHtml(data.tracking_number)}</div>`;

            if (data.latest_status) {
                html += `<div class="tracking-status-badge"><strong>ステータス:</strong> ${this.escapeHtml(data.latest_status)}</div>`;
            }

            if (data.message) {
                html += `<div class="tracking-notice">${this.escapeHtml(data.message)}</div>`;
            }

            if (data.events && data.events.length > 0) {
                html += '<div class="tracking-events">';
                data.events.forEach(event => {
                    html += `
                        <div class="tracking-event">
                            <div class="tracking-event-date">${this.formatDateJST(event.date)}</div>
                            <div class="tracking-event-status">${this.escapeHtml(event.status)}</div>
                            ${event.location ? `<div class="tracking-event-location">${this.escapeHtml(event.location)}</div>` : ''}
                        </div>
                    `;
                });
                html += '</div>';
            } else if (!data.message) {
                html += '<div class="tracking-notice">追跡情報はまだありません</div>';
            }

            html += '</div>';
            body.innerHTML = html;

        } catch (error) {
            console.error('追跡情報の取得に失敗しました:', error);
            body.innerHTML = '<div class="tracking-error">追跡情報の取得に失敗しました</div>';
        }
    },

    // ==========================================
    // カウントダウン
    // ==========================================

    initCountdown() {
        if (typeof RENTAL_DEADLINE_ISO === 'undefined' || !RENTAL_DEADLINE_ISO) return;

        const deadline = new Date(RENTAL_DEADLINE_ISO);
        this.updateCountdown(deadline);
        this.countdownInterval = setInterval(() => this.updateCountdown(deadline), 60000);
    },

    updateCountdown(deadline) {
        const timerEl = document.getElementById('countdownTimer');
        const countdownEl = document.getElementById('rentalCountdown');
        if (!timerEl) return;

        const now = new Date();
        const diff = deadline - now;

        if (diff <= 0) {
            timerEl.textContent = '期限超過';
            if (countdownEl) countdownEl.classList.add('overdue');
            return;
        }

        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

        let text = '';
        if (days > 0) text += `${days}日 `;
        text += `${hours}時間 ${minutes}分`;
        timerEl.textContent = `残り ${text}`;
    },

    // ==========================================
    // 既存: 受取・返却受取・キャンセル
    // ==========================================

    /**
     * 受取通知
     */
    async notifyReceipt() {
        if (!await showConfirm('商品を受け取りましたか？\n受取完了を通知します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/receive/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                showAlert(data.message || '受取通知に失敗しました');
            }
        } catch (error) {
            console.error('受取通知に失敗しました:', error);
            showAlert('受取通知に失敗しました');
        }
    },

    /**
     * 返却受取
     */
    async notifyReturnReceive() {
        if (!await showConfirm('商品が届きましたか？\n返却を確認します。')) return;

        try {
            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/return-receive/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': CSRF_TOKEN }
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                showAlert(data.message || '返却確認に失敗しました');
            }
        } catch (error) {
            console.error('返却確認に失敗しました:', error);
            showAlert('返却確認に失敗しました');
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
            showAlert('キャンセル理由を選択してください');
            return;
        }

        if (!await showConfirm('本当に取引をキャンセルしますか？\nこの操作は取り消せません。')) return;

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
                location.reload();
            } else {
                showAlert(data.message || 'キャンセルに失敗しました');
            }
        } catch (error) {
            console.error('キャンセルに失敗しました:', error);
            showAlert('キャンセルに失敗しました');
        }
    },

    // ==========================================
    // 中止申請モーダル
    // ==========================================

    initCancellationModal() {
        const modal = document.getElementById('cancellationRequestModal');
        if (!modal) return;

        modal.querySelectorAll('[data-modal="cancellationRequestModal"]').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal('cancellationRequestModal'));
        });
        modal.querySelector('.modal-overlay')?.addEventListener('click', () => this.closeModal('cancellationRequestModal'));

        const confirmBtn = document.getElementById('cancellationRequestConfirmBtn');
        if (confirmBtn) {
            confirmBtn.addEventListener('click', () => this.submitCancellationRequest());
        }
    },

    async submitCancellationRequest() {
        const reasonId = document.getElementById('cancellationReasonSelect')?.value;
        const detail = document.getElementById('cancellationDetail')?.value || '';
        const confirmBtn = document.getElementById('cancellationRequestConfirmBtn');
        const errorEl = document.getElementById('cancellationRequestError');

        if (!reasonId) {
            if (errorEl) {
                errorEl.textContent = '中止理由を選択してください';
                errorEl.classList.remove('hidden');
            }
            return;
        }

        this.closeModal('cancellationRequestModal');

        if (!await showConfirm('取引中止を申請しますか？\n運営の審査後に取引が中止されます。')) {
            this.openModal('cancellationRequestModal');
            return;
        }

        if (errorEl) errorEl.classList.add('hidden');
        if (confirmBtn) confirmBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('cancellation_reason_id', reasonId);
            formData.append('detail', detail);

            const response = await fetch(`/monotal/transaction/${this.rentalHistoryId}/cancellation-request/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': CSRF_TOKEN,
                },
                body: formData
            });
            const data = await response.json();

            if (data.success) {
                location.reload();
            } else {
                if (errorEl) {
                    errorEl.textContent = data.message || '中止申請に失敗しました';
                    errorEl.classList.remove('hidden');
                } else {
                    showAlert(data.message || '中止申請に失敗しました');
                }
            }
        } catch (error) {
            console.error('中止申請に失敗しました:', error);
            showAlert('中止申請に失敗しました');
        } finally {
            if (confirmBtn) confirmBtn.disabled = false;
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
    if (TransactionPage.countdownInterval) {
        clearInterval(TransactionPage.countdownInterval);
    }
});
