document.addEventListener('DOMContentLoaded', function () {
    const sellForm = document.getElementById('sellForm');

    // 画像管理
    let uploadedImages = [];
    const MAX_IMAGES = 10;

    if (sellForm) {
        sellForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            await submitProduct(false);
        });
    }

    // 下書き保存ボタン
    const draftBtn = document.getElementById('draftBtn');
    if (draftBtn) {
        draftBtn.addEventListener('click', async function (e) {
            e.preventDefault();
            await submitProduct(true);
        });
    }

    // ========================================
    // レンタル期間選択と価格フィールド管理
    // ========================================
    let selectedPeriods = {}; // { days: label } 形式で選択された期間を保持

    const periodButtons = document.querySelectorAll('.period-btn');
    const priceFieldsContainer = document.getElementById('priceFieldsContainer');

    periodButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const days = this.getAttribute('data-days');
            const label = this.getAttribute('data-label');

            if (this.classList.contains('active')) {
                // 選択解除
                this.classList.remove('active');
                delete selectedPeriods[days];
            } else {
                // 選択
                this.classList.add('active');
                selectedPeriods[days] = label;
            }

            renderPriceFields();
        });
    });

    function renderPriceFields() {
        priceFieldsContainer.innerHTML = '';

        // 日数順にソート
        const sortedPeriods = Object.keys(selectedPeriods).sort((a, b) => parseInt(a) - parseInt(b));

        sortedPeriods.forEach(days => {
            const label = selectedPeriods[days];
            const fieldItem = document.createElement('div');
            fieldItem.className = 'price-field-item';
            fieldItem.innerHTML = `
                <label class="price-field-label">
                    <span class="price-field-period">${label}</span> のレンタル料金
                </label>
                <div class="price-group">
                    <input type="number"
                           id="price_${days}"
                           class="form-input price-input"
                           data-days="${days}"
                           placeholder="0"
                           min="100">
                    <span class="currency">¥</span>
                </div>
                <div id="price_${days}_error"></div>
            `;
            priceFieldsContainer.appendChild(fieldItem);
        });
    }

    // ========================================
    // リアルタイムバリデーション設定
    // ========================================
    const productNameInput = document.getElementById('productName');
    const descriptionInput = document.getElementById('description');

    if (productNameInput) {
        productNameInput.addEventListener('input', function () {
            updateCharCount('productName', 'nameCount', 40);
            validateFieldRealtime('productName', 40);
        });
    }

    if (descriptionInput) {
        descriptionInput.addEventListener('input', function () {
            updateCharCount('description', 'descCount', 1000);
            validateFieldRealtime('description', 1000);
        });
    }

    // ========================================
    // 送信処理
    // ========================================
    async function submitProduct(isDraft) {
        clearErrors();

        // 選択された期間と価格を収集
        const rentalPeriods = [];
        Object.keys(selectedPeriods).forEach(days => {
            const priceInput = document.getElementById(`price_${days}`);
            const price = priceInput ? priceInput.value : '';
            rentalPeriods.push({
                days: parseInt(days),
                label: selectedPeriods[days],
                price: price
            });
        });

        const formData = {
            product_name: document.getElementById('productName').value,
            product_category: document.getElementById('category').value,
            brand: document.getElementById('brand').value,
            product_description: document.getElementById('description').value,
            product_condition: document.getElementById('condition').value,
            shipping_method: document.getElementById('shippingMethod').value,
            shipping_area: document.getElementById('shippingArea').value,
            shipping_days: document.getElementById('shippingDays').value,
            rental_periods: rentalPeriods,
            images: uploadedImages,
            is_draft: isDraft
        };

        const errors = validateForm(formData);
        if (Object.keys(errors).length > 0) {
            displayErrors(errors);
            return;
        }

        setLoadingState(true, isDraft);

        try {
            const submitData = new FormData();
            submitData.append('product_name', formData.product_name);
            submitData.append('product_category', formData.product_category);
            submitData.append('brand', formData.brand);
            submitData.append('product_description', formData.product_description);
            submitData.append('product_condition', formData.product_condition);
            submitData.append('shipping_method', formData.shipping_method);
            submitData.append('shipping_area', formData.shipping_area);
            submitData.append('shipping_days', formData.shipping_days);
            submitData.append('rental_periods', JSON.stringify(formData.rental_periods));
            submitData.append('is_draft', isDraft ? 'true' : 'false');

            uploadedImages.forEach(img => {
                submitData.append('images', img.file);
            });

            const response = await fetch('/monotal/sell/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: submitData
            });

            const data = await response.json();

            // ログインが必要な場合
            if (response.status === 401) {
                showErrorAt('termsError', data.message || 'ログインが必要です');
                setTimeout(() => {
                    window.location.href = data.redirect_url || '/monotal/login/';
                }, 1500);
                return;
            }

            if (response.ok && data.success) {
                sellForm.reset();
                uploadedImages = [];
                renderImagePreviews();
                window.location.href = data.redirect_url || '/monotal/';

            } else {
                if (data.errors) {
                    const fieldMap = {
                        'product_name': 'productName',
                        'product_category': 'category',
                        'product_description': 'description',
                        'product_condition': 'condition',
                        'shipping_method': 'shippingMethod',
                        'shipping_area': 'shippingArea',
                        'shipping_days': 'shippingDays',
                        'rental_periods': 'rentalPeriods'
                    };

                    const mappedErrors = {};
                    Object.keys(data.errors).forEach(field => {
                        const frontendField = fieldMap[field] || field;
                        mappedErrors[frontendField] = data.errors[field];
                    });
                    displayErrors(mappedErrors);
                } else if (data.message) {
                    showErrorAt('termsError', data.message);
                }
            }

        } catch (error) {
            console.error('Submit error:', error);
            showErrorAt('termsError', 'ネットワークエラーが発生しました。時間をおいて再度お試しください。');
        } finally {
            setLoadingState(false, isDraft);
        }
    }

    // ========================================
    // エラー表示（全て統一スタイル）
    // ========================================
    function displayErrors(errors) {
        Object.keys(errors).forEach(field => {
            if (field === 'images') {
                showErrorAt('imageError', errors[field]);
            } else if (field === 'agreeTerms') {
                showErrorAt('termsError', errors[field]);
            } else if (field === 'rentalPeriods') {
                showErrorAt('rentalPeriodsError', errors[field]);
            } else if (field.startsWith('price_')) {
                // 個別の価格フィールドエラー (例: price_1, price_30)
                showErrorAt(`${field}_error`, errors[field]);
                document.getElementById(field)?.classList.add('input-error');
            } else {
                const input = document.getElementById(field);
                if (input) {
                    showError(input, errors[field]);
                }
            }
        });

        // 最初のエラーにスクロール
        const firstError = document.querySelector('.error-message');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
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

    function showErrorAt(containerId, message) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = '';
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        container.appendChild(errorDiv);
    }

    function clearErrors() {
        document.querySelectorAll('.input-error').forEach(el => {
            el.classList.remove('input-error');
        });
        document.querySelectorAll('.error-message').forEach(el => {
            el.remove();
        });
        document.querySelectorAll('.char-count.error').forEach(el => {
            el.classList.remove('error');
        });

        // 専用エラーコンテナをクリア
        ['imageError', 'termsError', 'rentalPeriodsError', 'priceError'].forEach(id => {
            const container = document.getElementById(id);
            if (container) container.innerHTML = '';
        });

        // 動的に生成された価格フィールドのエラーもクリア
        document.querySelectorAll('[id^="price_"][id$="_error"]').forEach(el => {
            el.innerHTML = '';
        });
    }

    // ========================================
    // バリデーション
    // ========================================
    function validateForm(formData) {
        const errors = {};

        if (formData.is_draft) {
            // 下書きの場合は商品名のみ必須
            if (!formData.product_name) {
                errors.productName = '商品名は必須です';
            } else if (formData.product_name.length > 40) {
                errors.productName = '商品名は40文字以内で入力してください';
            }
        } else {
            // 出品の場合は全て必須
            if (!formData.images || formData.images.length === 0) {
                errors.images = '商品画像を1枚以上アップロードしてください';
            } else if (formData.images.length > MAX_IMAGES) {
                errors.images = `画像は最大${MAX_IMAGES}枚までです`;
            }

            if (!formData.product_name) {
                errors.productName = '商品名は必須です';
            } else if (formData.product_name.length > 40) {
                errors.productName = '商品名は40文字以内で入力してください';
            }

            if (!formData.product_category) {
                errors.category = 'カテゴリーを選択してください';
            }

            if (!formData.product_description) {
                errors.description = '商品の説明は必須です';
            } else if (formData.product_description.length > 1000) {
                errors.description = '商品の説明は1000文字以内で入力してください';
            }

            if (!formData.product_condition) {
                errors.condition = '商品の状態を選択してください';
            }

            if (!formData.shipping_method) {
                errors.shippingMethod = '配送方法を選択してください';
            }

            if (!formData.shipping_area) {
                errors.shippingArea = '発送元地域を選択してください';
            }

            if (!formData.shipping_days) {
                errors.shippingDays = '発送までの日数を選択してください';
            }

            // レンタル期間と価格のバリデーション
            if (!formData.rental_periods || formData.rental_periods.length === 0) {
                errors.rentalPeriods = '少なくとも1つのレンタル期間を選択してください';
            } else {
                // 各期間の価格をチェック
                let hasValidPrice = false;
                formData.rental_periods.forEach(period => {
                    const price = period.price ? parseInt(period.price) : 0;

                    if (price > 0) {
                        hasValidPrice = true;
                        if (price < 100 || price > 9999999) {
                            errors[`price_${period.days}`] = '料金は100円〜9,999,999円で設定してください';
                        }
                    }
                });

                if (!hasValidPrice) {
                    errors.rentalPeriods = '少なくとも1つの期間に料金を設定してください';
                }
            }

            const agreeTerms = document.getElementById('agreeTerms');
            if (!agreeTerms || !agreeTerms.checked) {
                errors.agreeTerms = '利用規約に同意してください';
            }
        }

        return errors;
    }

    // ========================================
    // リアルタイム文字数バリデーション
    // ========================================
    function validateFieldRealtime(inputId, maxLength) {
        const input = document.getElementById(inputId);
        if (!input) return;

        const currentLength = input.value.length;
        const charCount = document.getElementById(inputId === 'productName' ? 'nameCount' : 'descCount');

        // 既存のエラーメッセージを削除
        const existingError = input.parentElement.querySelector('.error-message');
        if (existingError) {
            existingError.remove();
        }

        if (currentLength > maxLength) {
            input.classList.add('input-error');
            if (charCount) {
                charCount.classList.add('error');
            }

            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = inputId === 'productName'
                ? '商品名は40文字以内で入力してください'
                : '商品の説明は1000文字以内で入力してください';
            input.parentElement.appendChild(errorDiv);
        } else {
            input.classList.remove('input-error');
            if (charCount) {
                charCount.classList.remove('error');
            }
        }
    }

    // ========================================
    // 文字数カウント
    // ========================================
    window.updateCharCount = function (inputId, countId, maxLength) {
        const input = document.getElementById(inputId);
        const countDisplay = document.getElementById(countId);

        if (input && countDisplay) {
            const currentLength = input.value.length;
            countDisplay.textContent = `${currentLength}/${maxLength}`;
        }
    };

    // ========================================
    // 画像アップロード
    // ========================================
    window.handleImageUpload = function (event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        // エラークリア
        const imageError = document.getElementById('imageError');
        if (imageError) imageError.innerHTML = '';

        const remainingSlots = MAX_IMAGES - uploadedImages.length;
        if (remainingSlots <= 0) {
            showErrorAt('imageError', `最大${MAX_IMAGES}枚までアップロードできます`);
            return;
        }

        Array.from(files).slice(0, remainingSlots).forEach(file => {
            if (!file.type.startsWith('image/')) {
                showErrorAt('imageError', '画像ファイルのみアップロードできます');
                return;
            }

            if (file.size > 10 * 1024 * 1024) {
                showErrorAt('imageError', '画像は10MB以下にしてください');
                return;
            }

            const reader = new FileReader();
            reader.onload = function (e) {
                uploadedImages.push({
                    file: file,
                    dataUrl: e.target.result
                });
                renderImagePreviews();
            };
            reader.readAsDataURL(file);
        });

        event.target.value = '';
    };

    window.removeImage = function (index) {
        uploadedImages.splice(index, 1);
        renderImagePreviews();
    };

    function renderImagePreviews() {
        const previewContainer = document.getElementById('imagePreview');
        if (!previewContainer) return;

        previewContainer.innerHTML = '';

        uploadedImages.forEach((image, index) => {
            const previewItem = document.createElement('div');
            previewItem.className = 'preview-item';
            previewItem.innerHTML = `
                <img src="${image.dataUrl}" alt="プレビュー ${index + 1}">
                <button type="button" class="remove-btn" onclick="removeImage(${index})" title="削除">×</button>
                ${index === 0 ? '<span class="main-badge">メイン</span>' : ''}
            `;
            previewContainer.appendChild(previewItem);
        });

        const uploadLimit = document.querySelector('.upload-limit');
        if (uploadLimit) {
            uploadLimit.textContent = uploadedImages.length > 0
                ? `${uploadedImages.length}/${MAX_IMAGES}枚`
                : `最大${MAX_IMAGES}枚まで`;
        }
    }

    // ========================================
    // ユーティリティ関数
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

    function setLoadingState(isLoading, isDraft) {
        const submitBtn = document.querySelector('.submit-btn');
        const draftBtn = document.getElementById('draftBtn');

        if (submitBtn) {
            submitBtn.disabled = isLoading;
            if (!isDraft) {
                submitBtn.textContent = isLoading ? '出品中...' : '出品する';
            }
        }
        if (draftBtn) {
            draftBtn.disabled = isLoading;
            if (isDraft) {
                draftBtn.textContent = isLoading ? '保存中...' : '下書き保存';
            }
        }
    }
});