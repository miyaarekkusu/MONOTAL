document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('addCardModal');
    const openModalBtns = document.querySelectorAll('#openAddModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const addCardForm = document.getElementById('addCardForm');

    // 編集モード用の状態管理
    let isEditMode = false;
    let editCardId = null;

    // ========================================
    // Modal Control
    // ========================================
    function openModal(editMode = false, cardData = null) {
        isEditMode = editMode;

        // モーダルのタイトルとボタンを切り替え
        const modalTitle = document.getElementById('modalTitle');
        const submitBtnIcon = document.getElementById('submitBtnIcon');
        const submitBtnText = document.getElementById('submitBtnText');
        const editCardIdInput = document.getElementById('editCardId');

        if (editMode && cardData) {
            modalTitle.textContent = 'カードを編集';
            submitBtnIcon.setAttribute('data-icon', 'lucide:check');
            submitBtnText.textContent = '変更を保存';
            editCardId = cardData.id;
            editCardIdInput.value = cardData.id;

            // フォームに既存データを設定
            // 編集時はカード番号は下4桁のみ表示（ユーザーは再入力が必要）
            document.getElementById('cardNumber').value = '';
            document.getElementById('cardNumber').placeholder = '**** **** **** ' + cardData.cardNumberLast4;
            document.getElementById('expiryMonth').value = cardData.expiryMonth;
            document.getElementById('expiryYear').value = cardData.expiryYear;
            document.getElementById('cardHolderName').value = cardData.cardHolderName;
        } else {
            modalTitle.textContent = 'カードを追加';
            submitBtnIcon.setAttribute('data-icon', 'lucide:plus');
            submitBtnText.textContent = 'カードを追加';
            editCardId = null;
            editCardIdInput.value = '';
            document.getElementById('cardNumber').placeholder = '1234 5678 9012 3456';
        }

        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        clearForm();
        clearAllErrors();
        isEditMode = false;
        editCardId = null;
    }

    // 新規追加ボタン
    openModalBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            openModal(false);
        });
    });

    // 編集ボタン
    document.querySelectorAll('.edit-card-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const cardData = {
                id: this.dataset.cardId,
                cardNumberLast4: this.dataset.cardNumberLast4,
                expiryMonth: this.dataset.expiryMonth,
                expiryYear: this.dataset.expiryYear,
                cardHolderName: this.dataset.cardHolderName
            };
            openModal(true, cardData);
        });
    });

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    if (modalBackdrop) {
        modalBackdrop.addEventListener('click', closeModal);
    }

    // ESC key to close modal
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    // ========================================
    // Card Number Formatting
    // ========================================
    const cardNumberInput = document.getElementById('cardNumber');
    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', function(e) {
            // 数字以外を削除
            let value = e.target.value.replace(/\D/g, '');
            // 4桁ごとにスペースを挿入
            let formatted = value.replace(/(\d{4})(?=\d)/g, '$1 ');
            e.target.value = formatted;
        });
    }

    // ========================================
    // Add/Edit Card Form Submit
    // ========================================
    if (addCardForm) {
        addCardForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearAllErrors();

            const cardNumber = document.getElementById('cardNumber').value.replace(/\s/g, '');
            const expiryMonth = document.getElementById('expiryMonth').value;
            const expiryYear = document.getElementById('expiryYear').value.trim();
            const cardHolderName = document.getElementById('cardHolderName').value.trim();

            // Validation
            let hasError = false;
            if (!cardNumber) {
                showError('cardNumber', 'カード番号を入力してください');
                hasError = true;
            } else if (!/^\d{13,19}$/.test(cardNumber)) {
                showError('cardNumber', 'カード番号が正しくありません');
                hasError = true;
            }
            if (!expiryMonth) {
                showError('expiryMonth', '有効期限（月）を選択してください');
                hasError = true;
            }
            if (!expiryYear) {
                showError('expiryYear', '有効期限（年）を入力してください');
                hasError = true;
            } else if (!/^\d{4}$/.test(expiryYear)) {
                showError('expiryYear', '有効期限（年）は4桁で入力してください');
                hasError = true;
            }
            if (!cardHolderName) {
                showError('cardHolderName', 'カード名義人を入力してください');
                hasError = true;
            }

            if (hasError) return;

            const formData = {
                card_number: cardNumber,
                expiry_month: expiryMonth,
                expiry_year: expiryYear,
                card_holder_name: cardHolderName
            };

            const submitBtn = document.getElementById('submitCardBtn');
            const submitBtnIcon = document.getElementById('submitBtnIcon');
            const submitBtnText = document.getElementById('submitBtnText');
            submitBtn.disabled = true;
            submitBtnIcon.setAttribute('data-icon', 'lucide:loader-2');
            submitBtnIcon.classList.add('animate-spin');
            submitBtnText.textContent = isEditMode ? '更新中...' : '追加中...';

            // 編集モードの場合は別のURLにPOST
            const url = isEditMode
                ? `/monotal/mypage/credit-cards/${editCardId}/edit/`
                : '/monotal/mypage/credit-cards/';

            try {
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: new URLSearchParams(formData)
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Reload page to show updated card
                    window.location.reload();
                } else {
                    if (data.errors) {
                        Object.keys(data.errors).forEach(field => {
                            const fieldMap = {
                                'card_number': 'cardNumber',
                                'expiry_month': 'expiryMonth',
                                'expiry_year': 'expiryYear',
                                'card_holder_name': 'cardHolderName'
                            };
                            showError(fieldMap[field] || field, data.errors[field]);
                        });
                    } else if (data.message) {
                        showAlert(data.message);
                    }
                }
            } catch (error) {
                console.error('Submit error:', error);
                showAlert('エラーが発生しました。もう一度お試しください。');
            } finally {
                submitBtn.disabled = false;
                submitBtnIcon.classList.remove('animate-spin');
                if (isEditMode) {
                    submitBtnIcon.setAttribute('data-icon', 'lucide:check');
                    submitBtnText.textContent = '変更を保存';
                } else {
                    submitBtnIcon.setAttribute('data-icon', 'lucide:plus');
                    submitBtnText.textContent = 'カードを追加';
                }
            }
        });
    }

    // ========================================
    // Delete Card
    // ========================================
    document.querySelectorAll('.delete-card-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const cardId = this.dataset.cardId;
            const cardElement = this.closest('div[data-card-id]');

            if (!await showConfirm('このカードを削除しますか？', {danger: true})) {
                return;
            }

            try {
                const response = await fetch(`/monotal/mypage/credit-cards/${cardId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Remove card with animation
                    cardElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    cardElement.style.opacity = '0';
                    cardElement.style.transform = 'translateX(-20px)';
                    setTimeout(() => {
                        cardElement.remove();
                        // Check if no cards left
                        const remainingCards = document.querySelectorAll('div[data-card-id]').length;
                        if (remainingCards === 0) {
                            window.location.reload();
                        }
                    }, 300);
                } else {
                    showAlert(data.message || '削除に失敗しました');
                }
            } catch (error) {
                console.error('Delete error:', error);
                showAlert('エラーが発生しました。もう一度お試しください。');
            }
        });
    });

    // ========================================
    // Utility Functions
    // ========================================
    function getCsrfToken() {
        const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
        if (csrfInput) {
            return csrfInput.value;
        }
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') {
                return value;
            }
        }
        return '';
    }

    function showError(fieldId, message) {
        const errorDiv = document.getElementById(fieldId + 'Error');
        const input = document.getElementById(fieldId);
        if (errorDiv) {
            errorDiv.textContent = message;
            errorDiv.classList.remove('hidden');
        }
        if (input) {
            input.classList.add('border-red-500');
        }
    }

    function clearError(fieldId) {
        const errorDiv = document.getElementById(fieldId + 'Error');
        const input = document.getElementById(fieldId);
        if (errorDiv) {
            errorDiv.textContent = '';
            errorDiv.classList.add('hidden');
        }
        if (input) {
            input.classList.remove('border-red-500');
        }
    }

    function clearAllErrors() {
        ['cardNumber', 'expiryMonth', 'expiryYear', 'cardHolderName'].forEach(clearError);
    }

    function clearForm() {
        document.getElementById('cardNumber').value = '';
        document.getElementById('cardNumber').placeholder = '1234 5678 9012 3456';
        document.getElementById('expiryMonth').value = '';
        document.getElementById('expiryYear').value = '';
        document.getElementById('cardHolderName').value = '';
        document.getElementById('editCardId').value = '';
    }
});
