document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('loginForm');

    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            clearErrors();

            const formData = {
                username: document.getElementById('username').value,
                password: document.getElementById('password').value
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
                const response = await fetch('/monotal/login/', {
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
                    window.location.href = data.redirect_url || '/monotal/';
                } else {
                    if (data.errors) {
                        if (data.errors.general) {
                            showGeneralError(data.errors.general);
                        } else {
                            Object.keys(data.errors).forEach(field => {
                                const input = document.getElementById(field);
                                if (input) {
                                    showError(input, data.errors[field]);
                                }
                            });
                        }
                    } else if (data.message) {
                        showGeneralError(data.message);
                    } else {
                        showGeneralError('ログイン中にエラーが発生しました');
                    }
                }

            } catch (error) {
                console.error('Login error:', error);
                showGeneralError('ネットワークエラーが発生しました。時間をおいて再度お試しください。');
            } finally {
                setLoadingState(false);
            }
        });
    }
});

function validateForm(formData) {
    const errors = {};

    if (!formData.username) {
        errors.username = '電話番号またはメールアドレスを入力してください';
    }

    if (!formData.password) {
        errors.password = 'パスワードを入力してください';
    }

    return errors;
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
}

function showGeneralError(message) {
    const form = document.getElementById('loginForm');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'general-error';
    errorDiv.textContent = message;
    form.insertBefore(errorDiv, form.firstChild);
}

function setLoadingState(isLoading) {
    const submitBtn = document.querySelector('.submit-btn');
    if (submitBtn) {
        submitBtn.disabled = isLoading;
        submitBtn.textContent = isLoading ? 'ログイン中...' : 'ログイン';
    }
}
