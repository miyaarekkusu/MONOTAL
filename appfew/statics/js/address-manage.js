document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('addAddressModal');
    const openModalBtns = document.querySelectorAll('#openAddModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalBackdrop = document.getElementById('modalBackdrop');
    const addAddressForm = document.getElementById('addAddressForm');
    const autoFillBtn = document.getElementById('autoFillBtn');

    // 編集モード用の状態管理
    let isEditMode = false;
    let editAddressId = null;

    // ========================================
    // Modal Control
    // ========================================
    function openModal(editMode = false, addressData = null) {
        isEditMode = editMode;

        // モーダルのタイトルとボタンを切り替え
        const modalTitle = document.getElementById('modalTitle');
        const submitBtnIcon = document.getElementById('submitBtnIcon');
        const submitBtnText = document.getElementById('submitBtnText');
        const editAddressIdInput = document.getElementById('editAddressId');

        if (editMode && addressData) {
            modalTitle.textContent = '住所を編集';
            submitBtnIcon.setAttribute('data-icon', 'lucide:check');
            submitBtnText.textContent = '変更を保存';
            editAddressId = addressData.id;
            editAddressIdInput.value = addressData.id;

            // フォームに既存データを設定
            document.getElementById('postalCode').value = addressData.postalCode;
            document.getElementById('prefecture').value = addressData.prefectureId;
            document.getElementById('city').value = addressData.city;
            document.getElementById('streetAddress').value = addressData.streetAddress;
        } else {
            modalTitle.textContent = '住所を追加';
            submitBtnIcon.setAttribute('data-icon', 'lucide:plus');
            submitBtnText.textContent = '住所を追加';
            editAddressId = null;
            editAddressIdInput.value = '';
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
        editAddressId = null;
    }

    // 新規追加ボタン
    openModalBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            openModal(false);
        });
    });

    // 編集ボタン
    document.querySelectorAll('.edit-address-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const addressData = {
                id: this.dataset.addressId,
                postalCode: this.dataset.postalCode,
                prefectureId: this.dataset.prefectureId,
                city: this.dataset.city,
                streetAddress: this.dataset.streetAddress
            };
            openModal(true, addressData);
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
    // Auto Fill Address from Postal Code
    // ========================================
    if (autoFillBtn) {
        autoFillBtn.addEventListener('click', async function() {
            const postalCode = document.getElementById('postalCode').value.replace(/[^0-9]/g, '');

            if (postalCode.length !== 7) {
                showError('postalCode', '郵便番号は7桁で入力してください');
                return;
            }

            try {
                autoFillBtn.textContent = '検索中...';
                autoFillBtn.disabled = true;

                const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${postalCode}`);
                const data = await response.json();

                if (data.status === 200 && data.results && data.results.length > 0) {
                    const result = data.results[0];

                    // Set prefecture
                    const prefectureSelect = document.getElementById('prefecture');
                    const prefectureName = result.address1;
                    for (let option of prefectureSelect.options) {
                        if (option.text === prefectureName) {
                            prefectureSelect.value = option.value;
                            break;
                        }
                    }

                    // Set city
                    document.getElementById('city').value = result.address2 + result.address3;
                    clearError('postalCode');
                } else {
                    showError('postalCode', '住所が見つかりませんでした');
                }
            } catch (error) {
                console.error('Address lookup error:', error);
                showError('postalCode', '住所の取得に失敗しました');
            } finally {
                autoFillBtn.textContent = '自動入力';
                autoFillBtn.disabled = false;
            }
        });
    }

    // ========================================
    // Add/Edit Address Form Submit
    // ========================================
    if (addAddressForm) {
        addAddressForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            clearAllErrors();

            const formData = {
                postal_code: document.getElementById('postalCode').value.trim(),
                prefecture: document.getElementById('prefecture').value,
                city: document.getElementById('city').value.trim(),
                street_address: document.getElementById('streetAddress').value.trim()
            };

            // Validation
            let hasError = false;
            if (!formData.postal_code || formData.postal_code.replace(/[^0-9]/g, '').length !== 7) {
                showError('postalCode', '郵便番号は7桁で入力してください');
                hasError = true;
            }
            if (!formData.prefecture) {
                showError('prefecture', '都道府県を選択してください');
                hasError = true;
            }
            if (!formData.city) {
                showError('city', '市区町村・町域を入力してください');
                hasError = true;
            }
            if (!formData.street_address) {
                showError('streetAddress', '番地・建物名を入力してください');
                hasError = true;
            }

            if (hasError) return;

            const submitBtn = document.getElementById('submitAddressBtn');
            const submitBtnIcon = document.getElementById('submitBtnIcon');
            const submitBtnText = document.getElementById('submitBtnText');
            submitBtn.disabled = true;
            submitBtnIcon.setAttribute('data-icon', 'lucide:loader-2');
            submitBtnIcon.classList.add('animate-spin');
            submitBtnText.textContent = isEditMode ? '更新中...' : '追加中...';

            // 編集モードの場合は別のURLにPOST
            const url = isEditMode
                ? `/monotal/mypage/addresses/${editAddressId}/edit/`
                : '/monotal/mypage/addresses/';

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
                    // Reload page to show updated address
                    window.location.reload();
                } else {
                    if (data.errors) {
                        Object.keys(data.errors).forEach(field => {
                            showError(field === 'postal_code' ? 'postalCode' : field === 'street_address' ? 'streetAddress' : field, data.errors[field]);
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
                    submitBtnText.textContent = '住所を追加';
                }
            }
        });
    }

    // ========================================
    // Delete Address
    // ========================================
    document.querySelectorAll('.delete-address-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const addressId = this.dataset.addressId;
            const addressCard = this.closest('div[data-address-id]');

            if (!await showConfirm('この住所を削除しますか？', {danger: true})) {
                return;
            }

            try {
                const response = await fetch(`/monotal/mypage/addresses/${addressId}/delete/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Remove card with animation
                    addressCard.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    addressCard.style.opacity = '0';
                    addressCard.style.transform = 'translateX(-20px)';
                    setTimeout(() => {
                        addressCard.remove();
                        // Check if no addresses left
                        const remainingCards = document.querySelectorAll('div[data-address-id]').length;
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
        ['postalCode', 'prefecture', 'city', 'streetAddress'].forEach(clearError);
    }

    function clearForm() {
        document.getElementById('postalCode').value = '';
        document.getElementById('prefecture').value = '';
        document.getElementById('city').value = '';
        document.getElementById('streetAddress').value = '';
        document.getElementById('editAddressId').value = '';
    }
});
