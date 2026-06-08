/**
 * 本人確認申請画面用JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('verificationForm');
    if (!form) return;

    // 生年月日セレクトの初期化
    initBirthdateSelects();

    // 画像アップロードエリアの設定
    setupImageUpload('id', 'idImage', 'idUploadArea', 'idPreview');
    setupImageUpload('id_back', 'idBackImage', 'idBackUploadArea', 'idBackPreview');
    setupSelfieUpload('face', 'faceImage', 'faceUploadArea', 'facePreview');

    // フォーム送信処理
    form.addEventListener('submit', handleFormSubmit);
});

/**
 * 生年月日セレクトの初期化
 */
function initBirthdateSelects() {
    const forms = document.querySelectorAll('.verification-form');
    forms.forEach(form => {
        const yearSelect = form.querySelector('select[name="birth_year"]');
        const monthSelect = form.querySelector('select[name="birth_month"]');
        const daySelect = form.querySelector('select[name="birth_day"]');
        const hiddenInput = form.querySelector('input[name="birth_date"]');

        if (!yearSelect || !monthSelect || !daySelect || !hiddenInput) return;

        // 年の選択肢を生成（現在の年から100年前まで）
        const currentYear = new Date().getFullYear();
        for (let year = currentYear; year >= currentYear - 100; year--) {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year + '年';
            yearSelect.appendChild(option);
        }

        // 日の選択肢を生成
        updateDayOptions(daySelect, monthSelect.value, yearSelect.value);

        // 既存の値がある場合は設定
        const existingValue = hiddenInput.value;
        if (existingValue) {
            const parts = existingValue.split('-');
            if (parts.length === 3) {
                yearSelect.value = parts[0];
                monthSelect.value = parseInt(parts[1], 10);
                updateDayOptions(daySelect, monthSelect.value, yearSelect.value);
                daySelect.value = parseInt(parts[2], 10);
            }
        }

        // 年または月が変わったら日の選択肢を更新
        yearSelect.addEventListener('change', () => {
            updateDayOptions(daySelect, monthSelect.value, yearSelect.value);
            updateHiddenBirthdate(yearSelect, monthSelect, daySelect, hiddenInput);
        });

        monthSelect.addEventListener('change', () => {
            updateDayOptions(daySelect, monthSelect.value, yearSelect.value);
            updateHiddenBirthdate(yearSelect, monthSelect, daySelect, hiddenInput);
        });

        daySelect.addEventListener('change', () => {
            updateHiddenBirthdate(yearSelect, monthSelect, daySelect, hiddenInput);
        });
    });
}

/**
 * 日の選択肢を更新
 */
function updateDayOptions(daySelect, month, year) {
    const currentValue = daySelect.value;
    const daysInMonth = getDaysInMonth(parseInt(month, 10) || 1, parseInt(year, 10) || new Date().getFullYear());

    // 現在の選択肢をクリア（最初のプレースホルダー以外）
    while (daySelect.options.length > 1) {
        daySelect.remove(1);
    }

    // 日の選択肢を追加
    for (let day = 1; day <= daysInMonth; day++) {
        const option = document.createElement('option');
        option.value = day;
        option.textContent = day + '日';
        daySelect.appendChild(option);
    }

    // 以前の値が有効なら復元
    if (currentValue && parseInt(currentValue, 10) <= daysInMonth) {
        daySelect.value = currentValue;
    }
}

/**
 * 指定月の日数を取得（うるう年考慮）
 */
function getDaysInMonth(month, year) {
    if (!month || month < 1 || month > 12) return 31;
    return new Date(year, month, 0).getDate();
}

/**
 * 非表示の生年月日フィールドを更新
 */
function updateHiddenBirthdate(yearSelect, monthSelect, daySelect, hiddenInput) {
    const year = yearSelect.value;
    const month = monthSelect.value;
    const day = daySelect.value;

    if (year && month && day) {
        const paddedMonth = String(month).padStart(2, '0');
        const paddedDay = String(day).padStart(2, '0');
        hiddenInput.value = `${year}-${paddedMonth}-${paddedDay}`;
    } else {
        hiddenInput.value = '';
    }
}

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
 * 画像アップロードエリアのセットアップ（身分証用）
 */
function setupImageUpload(type, inputId, areaId, previewId) {
    const input = document.getElementById(inputId);
    const area = document.getElementById(areaId);
    const preview = document.getElementById(previewId);

    if (!input || !area || !preview) return;

    // ファイル選択時の処理
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // バリデーション
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
        area.style.borderColor = '#f472b6';
        area.style.background = 'rgba(253, 242, 248, 0.1)';
    });

    area.addEventListener('dragleave', function(e) {
        e.preventDefault();
        if (!area.classList.contains('has-image')) {
            area.style.borderColor = '#d4d4d8';
            area.style.background = '#fafafa';
        } else {
            area.style.borderColor = '#22c55e';
            area.style.background = '#f0fdf4';
        }
    });

    area.addEventListener('drop', function(e) {
        e.preventDefault();
        if (area.classList.contains('has-image')) {
            area.style.borderColor = '#22c55e';
            area.style.background = '#f0fdf4';
        } else {
            area.style.borderColor = '#d4d4d8';
            area.style.background = '#fafafa';
        }

        const file = e.dataTransfer.files[0];
        if (file) {
            input.files = e.dataTransfer.files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

/**
 * セルフィーアップロードエリアのセットアップ（顔写真用）
 */
function setupSelfieUpload(type, inputId, areaId, previewId) {
    const input = document.getElementById(inputId);
    const area = document.getElementById(areaId);
    const preview = document.getElementById(previewId);

    if (!input || !area || !preview) return;

    // ファイル選択時の処理
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;

        // バリデーション
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

            // ガイドオーバーレイを非表示
            const overlay = area.querySelector('.selfie-guide-overlay');
            if (overlay) {
                overlay.style.display = 'none';
            }

            // プレースホルダーを非表示
            const placeholder = area.querySelector('.selfie-placeholder');
            if (placeholder) {
                placeholder.style.display = 'none';
            }
        };
        reader.readAsDataURL(file);
    });

    // ドラッグ&ドロップ対応
    area.addEventListener('dragover', function(e) {
        e.preventDefault();
        area.style.borderColor = '#f472b6';
        area.style.background = 'rgba(253, 242, 248, 0.1)';
    });

    area.addEventListener('dragleave', function(e) {
        e.preventDefault();
        if (!area.classList.contains('has-image')) {
            area.style.borderColor = '#d4d4d8';
            area.style.background = '#fafafa';
        } else {
            area.style.borderColor = '#22c55e';
            area.style.background = '#f0fdf4';
        }
    });

    area.addEventListener('drop', function(e) {
        e.preventDefault();
        if (area.classList.contains('has-image')) {
            area.style.borderColor = '#22c55e';
            area.style.background = '#f0fdf4';
        } else {
            area.style.borderColor = '#d4d4d8';
            area.style.background = '#fafafa';
        }

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

    const form = document.getElementById('verificationForm');

    // 個人情報フィールド
    const lastName = document.getElementById('lastName');
    const firstName = document.getElementById('firstName');
    const birthDate = form.querySelector('input[name="birth_date"]');
    const gender = document.getElementById('gender');

    // 画像フィールド
    const faceImage = document.getElementById('faceImage');
    const idImage = document.getElementById('idImage');
    const idBackImage = document.getElementById('idBackImage');

    // クライアント側バリデーション
    let hasError = false;

    // 個人情報バリデーション
    if (!lastName || !lastName.value.trim()) {
        showFieldError('last_name', '姓を入力してください');
        hasError = true;
    }

    if (!firstName || !firstName.value.trim()) {
        showFieldError('first_name', '名を入力してください');
        hasError = true;
    }

    if (!birthDate || !birthDate.value) {
        showFieldError('birth_date', '生年月日を入力してください');
        hasError = true;
    }

    if (!gender || !gender.value) {
        showFieldError('gender', '性別を選択してください');
        hasError = true;
    }

    // 画像バリデーション
    if (!idImage || !idImage.files[0]) {
        showFieldError('id_image', '身分証明書（表面）は必須です');
        hasError = true;
    }

    if (!idBackImage || !idBackImage.files[0]) {
        showFieldError('id_back_image', '身分証明書（裏面/厚み）は必須です');
        hasError = true;
    }

    if (!faceImage || !faceImage.files[0]) {
        showFieldError('face_image', '顔写真は必須です');
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
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            padding: 16px 24px;
            background: #18181b;
            color: #fff;
            border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            z-index: 1000;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        `;
        document.body.appendChild(toast);
    }
    toast.innerHTML = `<span class="iconify" data-icon="lucide:check-circle" data-width="20"></span>${message}`;
    toast.style.display = 'flex';

    setTimeout(() => {
        toast.style.display = 'none';
    }, 3000);
}
