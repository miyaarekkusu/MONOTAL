/**
 * 本人確認申請画面用JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('verificationForm');
    if (!form) return;

    // 画像アップロードエリアの設定
    setupImageUpload('face', 'faceImage', 'faceUploadArea', 'facePreview');
    setupImageUpload('id', 'idImage', 'idUploadArea', 'idPreview');

    // フォーム送信処理
    form.addEventListener('submit', handleFormSubmit);
});

/**
 * CSRFトークンを取得
 */
function getCsrfToken() {
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    // フォームから取得
    const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return csrfInput ? csrfInput.value : '';
}

/**
 * 画像アップロードエリアのセットアップ
 */
function setupImageUpload(type, inputId, areaId, previewId) {
    const input = document.getElementById(inputId);
    const area = document.getElementById(areaId);
    const preview = document.getElementById(previewId);

    if (!input || !area || !preview) return;

    // エリアクリックでファイル選択
    area.addEventListener('click', function() {
        input.click();
    });

    // ファイル選択時の処理
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // バリデーション
        const errorElement = document.getElementById(`${type}_image-error`);

        if (file.size > 5 * 1024 * 1024) {
            showFieldError(`${type}_image`, '画像は5MB以下にしてください');
            input.value = '';
            return;
        }

        if (!file.type.startsWith('image/')) {
            showFieldError(`${type}_image`, '画像ファイルを選択してください');
            input.value = '';
            return;
        }

        clearFieldError(`${type}_image`);

        // プレビュー表示
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `<img src="${e.target.result}" alt="プレビュー">`;
            preview.classList.add('show');
            area.classList.add('has-image');
        };
        reader.readAsDataURL(file);
    });

    // ドラッグ&ドロップ対応
    area.addEventListener('dragover', function(e) {
        e.preventDefault();
        area.style.borderColor = '#007bff';
        area.style.background = '#f0f7ff';
    });

    area.addEventListener('dragleave', function(e) {
        e.preventDefault();
        if (!area.classList.contains('has-image')) {
            area.style.borderColor = '#ddd';
            area.style.background = '#fafafa';
        }
    });

    area.addEventListener('drop', function(e) {
        e.preventDefault();
        area.style.borderColor = area.classList.contains('has-image') ? '#28a745' : '#ddd';
        area.style.background = '#fafafa';

        const file = e.dataTransfer.files[0];
        if (file) {
            input.files = e.dataTransfer.files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

/**
 * フォーム送信処理
 */
async function handleFormSubmit(e) {
    e.preventDefault();

    clearAllErrors();

    const faceImage = document.getElementById('faceImage');
    const idImage = document.getElementById('idImage');

    // クライアント側バリデーション
    let hasError = false;

    if (!faceImage || !faceImage.files[0]) {
        showFieldError('face_image', '顔写真は必須です');
        hasError = true;
    }

    if (!idImage || !idImage.files[0]) {
        showFieldError('id_image', '身分証明書は必須です');
        hasError = true;
    }

    if (hasError) return;

    // ボタンをローディング状態に
    const submitBtn = document.getElementById('submitBtn');
    submitBtn.classList.add('loading');
    submitBtn.disabled = true;

    const formData = new FormData(document.getElementById('verificationForm'));

    try {
        const response = await fetch('/monotal/identity-verification/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.success) {
            showSuccessToast(data.message);
            setTimeout(() => {
                location.reload();
            }, 1500);
        } else {
            if (data.errors) {
                displayErrors(data.errors);
            } else {
                showGeneralError(data.message || 'エラーが発生しました');
            }
            submitBtn.classList.remove('loading');
            submitBtn.disabled = false;
        }
    } catch (error) {
        showGeneralError('ネットワークエラーが発生しました');
        submitBtn.classList.remove('loading');
        submitBtn.disabled = false;
    }
}

/**
 * フィールドエラーを表示
 */
function showFieldError(fieldName, message) {
    const errorElement = document.getElementById(`${fieldName}-error`);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }
}

/**
 * フィールドエラーをクリア
 */
function clearFieldError(fieldName) {
    const errorElement = document.getElementById(`${fieldName}-error`);
    if (errorElement) {
        errorElement.textContent = '';
        errorElement.classList.remove('show');
    }
}

/**
 * 全エラーをクリア
 */
function clearAllErrors() {
    document.querySelectorAll('.error-message').forEach(el => {
        el.textContent = '';
        el.classList.remove('show');
    });

    const generalError = document.getElementById('generalError');
    if (generalError) {
        generalError.textContent = '';
        generalError.classList.remove('show');
    }
}

/**
 * 複数エラーを表示
 */
function displayErrors(errors) {
    for (const [field, message] of Object.entries(errors)) {
        showFieldError(field, message);
    }
}

/**
 * 一般エラーを表示
 */
function showGeneralError(message) {
    const generalError = document.getElementById('generalError');
    if (generalError) {
        generalError.textContent = message;
        generalError.classList.add('show');
    }
}

/**
 * 成功トーストを表示
 */
function showSuccessToast(message) {
    // 既存のトーストがあれば使用、なければ作成
    let toast = document.getElementById('successToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'successToast';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            padding: 15px 25px;
            background: #28a745;
            color: #fff;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideIn 0.3s ease;
        `;
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.style.display = 'block';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}
