document.addEventListener('DOMContentLoaded', function () {
    const profileForm = document.getElementById('profileForm');
    const displayNameInput = document.getElementById('display_name');
    const bioInput = document.getElementById('bio');
    const userImageInput = document.getElementById('user_image');
    const imagePreview = document.getElementById('imagePreview');

    // 文字数カウント
    if (displayNameInput) {
        displayNameInput.addEventListener('input', function () {
            updateCharCount('display_name', this.value.length, 100);
        });
    }

    if (bioInput) {
        bioInput.addEventListener('input', function () {
            updateCharCount('bio', this.value.length, 160);
        });
    }

    // 画像プレビュー
    if (userImageInput) {
        userImageInput.addEventListener('change', function (e) {
            const file = e.target.files[0];
            if (file) {
                // バリデーション
                if (file.size > 5 * 1024 * 1024) {
                    showFieldError('user_image', '画像は5MB以下にしてください');
                    this.value = '';
                    return;
                }
                if (!file.type.startsWith('image/')) {
                    showFieldError('user_image', '画像ファイルを選択してください');
                    this.value = '';
                    return;
                }

                clearFieldError('user_image');

                // プレビュー表示
                const reader = new FileReader();
                reader.onload = function (e) {
                    imagePreview.innerHTML = `<img src="${e.target.result}" alt="プレビュー" id="previewImg">`;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // フォーム送信
    if (profileForm) {
        profileForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            clearAllErrors();

            const displayName = displayNameInput.value.trim();
            const bio = bioInput.value.trim();

            // バリデーション
            const errors = {};
            if (!displayName) {
                errors.display_name = '表示名は必須です';
            } else if (displayName.length > 100) {
                errors.display_name = '表示名は100文字以内で入力してください';
            }

            if (bio.length > 160) {
                errors.bio = '自己紹介は160文字以内で入力してください';
            }

            if (Object.keys(errors).length > 0) {
                Object.keys(errors).forEach(field => {
                    showFieldError(field, errors[field]);
                });
                return;
            }

            setLoadingState(true);

            try {
                const formData = new FormData(profileForm);

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
                    showSuccessToast(data.message || 'プロフィールを更新しました');

                    // 画像が更新された場合、input をリセット
                    if (userImageInput) {
                        userImageInput.value = '';
                    }
                } else {
                    if (data.errors) {
                        Object.keys(data.errors).forEach(field => {
                            showFieldError(field, data.errors[field]);
                        });
                    } else if (data.message) {
                        showGeneralError(data.message);
                    } else {
                        showGeneralError('更新中にエラーが発生しました');
                    }
                }

            } catch (error) {
                console.error('Profile update error:', error);
                showGeneralError('ネットワークエラーが発生しました。時間をおいて再度お試しください。');
            } finally {
                setLoadingState(false);
            }
        });
    }
});

function updateCharCount(fieldName, current, max) {
    const countSpan = document.getElementById(`${fieldName}-count`);
    const countP = countSpan?.parentElement;

    if (countSpan) {
        countSpan.textContent = current;
    }

    if (countP) {
        countP.classList.remove('warning', 'error');
        if (current > max) {
            countP.classList.add('error');
        } else if (current > max * 0.9) {
            countP.classList.add('warning');
        }
    }
}

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

function showFieldError(fieldName, message) {
    const input = document.getElementById(fieldName);
    const errorP = document.getElementById(`${fieldName}-error`);

    if (input) {
        input.classList.add('input-error');
    }

    if (errorP) {
        errorP.textContent = message;
    }
}

function clearFieldError(fieldName) {
    const input = document.getElementById(fieldName);
    const errorP = document.getElementById(`${fieldName}-error`);

    if (input) {
        input.classList.remove('input-error');
    }

    if (errorP) {
        errorP.textContent = '';
    }
}

function clearAllErrors() {
    document.querySelectorAll('.input-error').forEach(el => {
        el.classList.remove('input-error');
    });
    document.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
    });
    document.querySelectorAll('.general-error').forEach(el => {
        el.remove();
    });
}

function showGeneralError(message) {
    const form = document.getElementById('profileForm');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'general-error';
    errorDiv.textContent = message;
    errorDiv.style.cssText = 'background: #fff5f5; border: 1px solid #fed7d7; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; color: #c53030; font-size: 14px;';
    form.insertBefore(errorDiv, form.firstChild);
}

function showSuccessToast(message) {
    // 既存のトーストを削除
    document.querySelectorAll('.success-toast').forEach(el => el.remove());

    const toast = document.createElement('div');
    toast.className = 'success-toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    // 3秒後に削除
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function setLoadingState(isLoading) {
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn?.querySelector('.btn-text');
    const btnLoading = submitBtn?.querySelector('.btn-loading');

    if (submitBtn) {
        submitBtn.disabled = isLoading;
    }

    if (btnText && btnLoading) {
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnLoading.style.display = isLoading ? 'inline-flex' : 'none';
    }
}
