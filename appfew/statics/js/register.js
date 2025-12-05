document.addEventListener('DOMContentLoaded', function () {
    const registerForm = document.getElementById('registerForm');

    if (registerForm) {
        registerForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            clearErrors();

            const formData = {
                email: document.getElementById('email').value,
                user_name: document.getElementById('user_name').value,
                phone_number: document.getElementById('phone_number').value,
                password: document.getElementById('password').value,
                password_confirm: document.getElementById('password_confirm').value
            };

            const errors = validateForm(formData);
            if (Object.keys(errors).length > 0) {
                Object.keys(errors).forEach(field => {
                    const input = document.getElementById(field);
                    if (input) {
                        showError(input, errors[field]);
                    }
                });
                return;
            }

            setLoadingState(true);

            try {
                const response = await fetch('/monotal/register/form/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    registerForm.reset();
                    window.location.href = data.redirect_url || '/monotal/';

                } else {
                    if (data.errors) {
                        Object.keys(data.errors).forEach(field => {
                            const input = document.getElementById(field);
                            if (input) {
                                showError(input, data.errors[field]);
                            }
                        });
                    } else if (data.message) {
                        showGeneralError(data.message);
                    } else {
                        showGeneralError('登録中にエラーが発生しました');
                    }
                }

            } catch (error) {
                console.error('Registration error:', error);
                showGeneralError('ネットワークエラーが発生しました。時間をおいて再度お試しください。');
            } finally {
                setLoadingState(false);
            }
        });
    }
});

function validateForm(formData) {
    const errors = {};

    if (!formData.email) {
        errors.email = 'メールアドレスは必須です';
    } else if (!isValidEmail(formData.email)) {
        errors.email = '有効なメールアドレスを入力してください';
    }

    if (!formData.user_name) {
        errors.user_name = 'ユーザー名は必須です';
    } else if (!/^[a-zA-Z0-9]+$/.test(formData.user_name)) {
        errors.user_name = 'ユーザー名は半角英数字のみで入力してください';
    }

    if (!formData.phone_number) {
        errors.phone_number = '電話番号は必須です';
    } else if (!/^[0-9]+$/.test(formData.phone_number)) {
        errors.phone_number = '電話番号は数字のみで入力してください';
    }

    if (!formData.password) {
        errors.password = 'パスワードは必須です';
    } else if (formData.password.length < 8) {
        errors.password = 'パスワードは8文字以上で入力してください';
    }

    if (!formData.password_confirm) {
        errors.password_confirm = 'パスワード（確認）は必須です';
    } else if (formData.password !== formData.password_confirm) {
        errors.password_confirm = 'パスワードが一致しません';
    }

    return errors;
}

function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
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

function showError(input, message) {
    input.classList.add('input-error');

    const existingError = input.parentElement.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }

    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    input.parentElement.appendChild(errorDiv);
}

function clearErrors() {
    document.querySelectorAll('.input-error').forEach(el => {
        el.classList.remove('input-error');
    });
    document.querySelectorAll('.error-message').forEach(el => {
        el.remove();
    });
    document.querySelectorAll('.general-error').forEach(el => {
        el.remove();
    });
    document.querySelectorAll('.success-message').forEach(el => {
        el.remove();
    });
}

function showGeneralError(message) {
    const form = document.getElementById('registerForm');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'general-error';
    errorDiv.textContent = message;
    form.insertBefore(errorDiv, form.firstChild);
}

function showSuccess(message) {
    const form = document.getElementById('registerForm');
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;
    form.insertBefore(successDiv, form.firstChild);
}

function setLoadingState(isLoading) {
    const submitBtn = document.querySelector('.submit-btn');
    if (submitBtn) {
        submitBtn.disabled = isLoading;
        submitBtn.textContent = isLoading ? '登録中...' : '登録する';
    }
}
