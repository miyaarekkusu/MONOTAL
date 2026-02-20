/**
 * カスタムモーダルダイアログ ユーティリティ
 * alert() / confirm() の代替としてサイトデザインに統一されたモーダルを提供
 */

(function() {
    'use strict';

    /**
     * alert() の代替。Promise を返す（OKボタン押下で resolve）
     * @param {string} message - 表示メッセージ
     * @param {Object} [options] - オプション
     * @param {string} [options.title] - モーダルタイトル
     * @param {string} [options.buttonText='OK'] - ボタンテキスト
     * @param {Function} [options.onClose] - 閉じた後のコールバック
     * @returns {Promise<void>}
     */
    window.showAlert = function(message, options = {}) {
        return new Promise(function(resolve) {
            const modal = document.getElementById('customAlertModal');
            const titleEl = document.getElementById('customModalTitle');
            const messageEl = document.getElementById('customModalMessage');
            const okBtn = document.getElementById('customModalOkBtn');
            const backdrop = document.getElementById('customModalBackdrop');

            // タイトル設定
            if (options.title) {
                titleEl.textContent = options.title;
                titleEl.classList.remove('hidden');
            } else {
                titleEl.classList.add('hidden');
            }

            // メッセージ設定
            messageEl.textContent = message;

            // ボタンテキスト設定
            okBtn.textContent = options.buttonText || 'OK';
            okBtn.className = 'w-full px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors bg-pink-600 text-white hover:bg-pink-700';

            // 確認ボタンを非表示
            document.getElementById('customModalConfirmBtns').classList.add('hidden');
            document.getElementById('customModalAlertBtn').classList.remove('hidden');

            function closeModal() {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
                cleanup();
                if (options.onClose) options.onClose();
                resolve();
            }

            function onKeydown(e) {
                if (e.key === 'Escape') closeModal();
            }

            function cleanup() {
                okBtn.removeEventListener('click', closeModal);
                backdrop.removeEventListener('click', closeModal);
                document.removeEventListener('keydown', onKeydown);
            }

            okBtn.addEventListener('click', closeModal);
            backdrop.addEventListener('click', closeModal);
            document.addEventListener('keydown', onKeydown);

            // モーダルを表示
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            okBtn.focus();
        });
    };

    /**
     * confirm() の代替。Promise を返す（確認→resolve(true)、キャンセル→resolve(false)）
     * @param {string} message - 表示メッセージ
     * @param {Object} [options] - オプション
     * @param {string} [options.title='確認'] - モーダルタイトル
     * @param {string} [options.confirmText='確認'] - 確認ボタンテキスト
     * @param {string} [options.cancelText='キャンセル'] - キャンセルボタンテキスト
     * @param {boolean} [options.danger=false] - trueなら確認ボタンを赤色に
     * @returns {Promise<boolean>}
     */
    window.showConfirm = function(message, options = {}) {
        return new Promise(function(resolve) {
            const modal = document.getElementById('customAlertModal');
            const titleEl = document.getElementById('customModalTitle');
            const messageEl = document.getElementById('customModalMessage');
            const confirmBtn = document.getElementById('customModalConfirmBtn');
            const cancelBtn = document.getElementById('customModalCancelBtn');
            const backdrop = document.getElementById('customModalBackdrop');

            // タイトル設定
            titleEl.textContent = options.title || '確認';
            titleEl.classList.remove('hidden');

            // メッセージ設定
            messageEl.textContent = message;

            // ボタンテキスト設定
            confirmBtn.textContent = options.confirmText || '確認';
            cancelBtn.textContent = options.cancelText || 'キャンセル';

            // danger モード
            if (options.danger) {
                confirmBtn.className = 'flex-1 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors bg-red-600 text-white hover:bg-red-700';
            } else {
                confirmBtn.className = 'flex-1 px-4 py-2.5 rounded-xl text-sm font-semibold transition-colors bg-pink-600 text-white hover:bg-pink-700';
            }

            // alert用ボタンを非表示、confirm用を表示
            document.getElementById('customModalAlertBtn').classList.add('hidden');
            document.getElementById('customModalConfirmBtns').classList.remove('hidden');

            function onConfirm() {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
                cleanup();
                resolve(true);
            }

            function onCancel() {
                modal.classList.add('hidden');
                document.body.style.overflow = '';
                cleanup();
                resolve(false);
            }

            function onKeydown(e) {
                if (e.key === 'Escape') onCancel();
            }

            function cleanup() {
                confirmBtn.removeEventListener('click', onConfirm);
                cancelBtn.removeEventListener('click', onCancel);
                backdrop.removeEventListener('click', onCancel);
                document.removeEventListener('keydown', onKeydown);
            }

            confirmBtn.addEventListener('click', onConfirm);
            cancelBtn.addEventListener('click', onCancel);
            backdrop.addEventListener('click', onCancel);
            document.addEventListener('keydown', onKeydown);

            // モーダルを表示
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
            cancelBtn.focus();
        });
    };
})();
