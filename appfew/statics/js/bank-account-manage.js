document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('addAccountModal');
    const openModalBtns = document.querySelectorAll('#openAddModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const addAccountForm = document.getElementById('addAccountForm');

    // 編集モード用の状態管理
    let isEditMode = false;
    let editAccountId = null;

    // ========================================
    // Modal Control
    // ========================================
    function openModal(editMode = false, accountData = null) {
        isEditMode = editMode;

        // モーダルのタイトルとボタンを切り替え
        const modalTitle = document.getElementById('modalTitle');
        const submitBtnIcon = document.getElementById('submitBtnIcon');
        const submitBtnText = document.getElementById('submitBtnText');
        const editAccountIdInput = document.getElementById('editAccountId');

        if (editMode && accountData) {
            modalTitle.textContent = '口座を編集';
            submitBtnIcon.setAttribute('data-icon', 'lucide:check');
            submitBtnText.textContent = '変更を保存';
            editAccountId = accountData.id;
            editAccountIdInput.value = accountData.id;

            // フォームに既存データを設定
            document.getElementById('bankName').value = accountData.bankName;
            document.getElementById('branchName').value = accountData.branchName;
            document.querySelector(`input[name="account_type"][value="${accountData.accountType}"]`).checked = true;
            document.getElementById('accountNumber').value = accountData.accountNumber;
            document.getElementById('accountHolder').value = accountData.accountHolder;
        } else {
            modalTitle.textContent = '口座を追加';
            submitBtnIcon.setAttribute('data-icon', 'lucide:plus');
            submitBtnText.textContent = '口座を追加';
            editAccountId = null;
            editAccountIdInput.value = '';
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
        editAccountId = null;
    }

    // 新規追加ボタン
    openModalBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            openModal(false);
        });
    });

    // 編集ボタン
    document.querySelectorAll('.edit-account-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const accountData = {
                id: this.dataset.accountId,
                bankName: this.dataset.bankName,
                branchName: this.dataset.branchName,
                accountType: this.dataset.accountType,
                accountNumber: this.dataset.accountNumber,
                accountHolder: this.dataset.accountHolder
            };
            openModal(true, accountData);
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
    // Add/Edit Account Form Submit
    // ========================================
    if (addAccountForm) {
        addAccountForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearAllErrors();

            const formData = {
                bank_name: document.getElementById('bankName').value.trim(),
                branch_name: document.getElementById('branchName').value.trim(),
                account_type: document.querySelector('input[name="account_type"]:checked').value,
                account_number: document.getElementById('accountNumber').value.trim(),
                account_holder: document.getElementById('accountHolder').value.trim()
            };

            // Validation
            let hasError = false;
            if (!formData.bank_name) {
                showError('bankName', '銀行名を入力してください');
                hasError = true;
            }
            if (!formData.branch_name) {
                showError('branchName', '支店名を入力してください');
                hasError = true;
            }
            if (!formData.account_number) {
                showError('accountNumber', '口座番号を入力してください');
                hasError = true;
            } else if (!/^\d+$/.test(formData.account_number)) {
                showError('accountNumber', '口座番号は数字のみ入力してください');
                hasError = true;
            }
            if (!formData.account_holder) {
                showError('accountHolder', '口座名義を入力してください');
                hasError = true;
            }

            if (hasError) return;

            const submitBtn = document.getElementById('submitAccountBtn');
            const submitBtnIcon = document.getElementById('submitBtnIcon');
            const submitBtnText = document.getElementById('submitBtnText');
            submitBtn.disabled = true;
            submitBtnIcon.setAttribute('data-icon', 'lucide:loader-2');
            submitBtnIcon.classList.add('animate-spin');
            submitBtnText.textContent = isEditMode ? '更新中...' : '追加中...';

            // 編集モードの場合は別のURLにPOST
            const url = isEditMode
                ? `/monotal/mypage/bank-accounts/${editAccountId}/edit/`
                : '/monotal/mypage/bank-accounts/';

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
                    // Reload page to show updated account
                    window.location.reload();
                } else {
                    if (data.errors) {
                        Object.keys(data.errors).forEach(field => {
                            const fieldMap = {
                                'bank_name': 'bankName',
                                'branch_name': 'branchName',
                                'account_number': 'accountNumber',
                                'account_holder': 'accountHolder'
                            };
                            showError(fieldMap[field] || field, data.errors[field]);
                        });
                    } else if (data.message) {
                        alert(data.message);
                    }
                }
            } catch (error) {
                console.error('Submit error:', error);
                alert('エラーが発生しました。もう一度お試しください。');
            } finally {
                submitBtn.disabled = false;
                submitBtnIcon.classList.remove('animate-spin');
                if (isEditMode) {
                    submitBtnIcon.setAttribute('data-icon', 'lucide:check');
                    submitBtnText.textContent = '変更を保存';
                } else {
                    submitBtnIcon.setAttribute('data-icon', 'lucide:plus');
                    submitBtnText.textContent = '口座を追加';
                }
            }
        });
    }

    // ========================================
    // Delete Account
    // ========================================
    document.querySelectorAll('.delete-account-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const accountId = this.dataset.accountId;
            const accountCard = this.closest('[data-account-id]');

            if (!confirm('この口座を削除しますか？')) {
                return;
            }

            try {
                const response = await fetch(`/monotal/mypage/bank-accounts/${accountId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Remove card with animation
                    accountCard.style.opacity = '0';
                    accountCard.style.transform = 'translateX(-20px)';
                    setTimeout(() => {
                        accountCard.remove();
                        // Check if no accounts left
                        const remainingCards = document.querySelectorAll('[data-account-id]').length;
                        if (remainingCards === 0) {
                            window.location.reload();
                        }
                    }, 300);
                } else {
                    alert(data.message || '削除に失敗しました');
                }
            } catch (error) {
                console.error('Delete error:', error);
                alert('エラーが発生しました。もう一度お試しください。');
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
        ['bankName', 'branchName', 'accountNumber', 'accountHolder'].forEach(clearError);
    }

    function clearForm() {
        document.getElementById('bankName').value = '';
        document.getElementById('branchName').value = '';
        document.querySelector('input[name="account_type"][value="1"]').checked = true;
        document.getElementById('accountNumber').value = '';
        document.getElementById('accountHolder').value = '';
        document.getElementById('editAccountId').value = '';
    }
});
