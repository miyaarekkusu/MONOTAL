document.addEventListener('DOMContentLoaded', function () {
    const editForm = document.getElementById('editForm');
    const productId = editForm ? editForm.dataset.productId : null;

    // 画像管理
    let newImages = [];  // 新しく追加する画像
    let deleteImageIds = [];  // 削除する既存画像のID
    const MAX_IMAGES = 10;

    // レンタルプラン管理
    let planRowId = document.querySelectorAll('.rental-plan-row').length;

    if (editForm) {
        editForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            await submitEdit();
        });
    }

    // ========================================
    // 既存画像の削除
    // ========================================
    document.querySelectorAll('.delete-image-btn').forEach(btn => {
        btn.addEventListener('click', function () {
            const imageId = this.dataset.imageId;
            const imageItem = this.closest('.existing-image-item');

            if (imageId && imageItem) {
                deleteImageIds.push(imageId);
                imageItem.remove();
                updateUploadBoxVisibility();
            }
        });
    });

    // ========================================
    // 新規画像アップロード
    // ========================================
    const imageInput = document.getElementById('imageInput');
    if (imageInput) {
        imageInput.addEventListener('change', handleImageUpload);
    }

    function handleImageUpload(event) {
        const files = event.target.files;
        if (!files || files.length === 0) return;

        clearError('imageError');

        const existingCount = document.querySelectorAll('.existing-image-item').length;
        const newCount = newImages.length;
        const remainingSlots = MAX_IMAGES - existingCount - newCount;

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
                newImages.push({
                    file: file,
                    dataUrl: e.target.result
                });
                renderNewImagePreviews();
            };
            reader.readAsDataURL(file);
        });

        event.target.value = '';
    }

    function renderNewImagePreviews() {
        const imageGrid = document.getElementById('imageGrid');
        if (!imageGrid) return;

        const uploadBox = document.getElementById('uploadBox');

        // 新規画像のプレビューを削除
        const existingPreviews = imageGrid.querySelectorAll('.preview-item');
        existingPreviews.forEach(el => el.remove());

        // プレビューを追加
        newImages.forEach((image, index) => {
            const previewItem = document.createElement('div');
            previewItem.className = 'preview-item';
            previewItem.innerHTML = `
                <img src="${image.dataUrl}" alt="新規画像 ${index + 1}">
                <button type="button" class="remove-btn" data-index="${index}" title="削除">
                    <span class="iconify" data-icon="lucide:x" data-width="12"></span>
                </button>
            `;
            imageGrid.insertBefore(previewItem, uploadBox);

            previewItem.querySelector('.remove-btn').addEventListener('click', function () {
                removeNewImage(index);
            });
        });

        updateUploadBoxVisibility();
    }

    function removeNewImage(index) {
        newImages.splice(index, 1);
        renderNewImagePreviews();
    }

    function updateUploadBoxVisibility() {
        const uploadBox = document.getElementById('uploadBox');
        const existingCount = document.querySelectorAll('.existing-image-item').length;
        const totalCount = existingCount + newImages.length;

        if (totalCount >= MAX_IMAGES) {
            uploadBox.style.display = 'none';
        } else {
            uploadBox.style.display = 'flex';
        }

        const uploadLimit = uploadBox.querySelector('.upload-limit');
        if (uploadLimit) {
            uploadLimit.textContent = totalCount > 0
                ? `${totalCount}/${MAX_IMAGES}枚`
                : `最大${MAX_IMAGES}枚`;
        }
    }

    // ========================================
    // レンタルプラン動的追加・削除
    // ========================================
    const addPlanBtn = document.getElementById('addPlanBtn');
    const rentalPlansContainer = document.getElementById('rentalPlansContainer');

    if (addPlanBtn) {
        addPlanBtn.addEventListener('click', addPlanRow);
    }

    if (rentalPlansContainer) {
        rentalPlansContainer.addEventListener('click', function (e) {
            const deleteBtn = e.target.closest('.delete-plan-btn');
            if (deleteBtn && !deleteBtn.disabled) {
                const row = deleteBtn.closest('.rental-plan-row');
                if (row) {
                    row.remove();
                    updateDeleteButtons();
                }
            }
        });
    }

    function addPlanRow() {
        planRowId++;
        const newRow = document.createElement('div');
        newRow.className = 'rental-plan-row';
        newRow.dataset.rowId = planRowId;
        newRow.innerHTML = `
            <div class="col-days">
                <input type="number" class="plan-input days-input" placeholder="日付を入力" min="1">
                <span class="input-suffix">日</span>
            </div>
            <div class="col-price">
                <span class="input-prefix">¥</span>
                <input type="number" class="plan-input price-input" placeholder="金額を入力" min="100">
            </div>
            <div class="col-action">
                <button type="button" class="delete-plan-btn">
                    <span class="iconify" data-icon="lucide:trash-2" data-width="16"></span>
                </button>
            </div>
        `;
        rentalPlansContainer.appendChild(newRow);
        updateDeleteButtons();
    }

    function updateDeleteButtons() {
        const rows = rentalPlansContainer.querySelectorAll('.rental-plan-row');
        rows.forEach((row) => {
            const deleteBtn = row.querySelector('.delete-plan-btn');
            if (deleteBtn) {
                deleteBtn.disabled = (rows.length === 1);
            }
        });
    }

    // ========================================
    // 郵便番号から住所自動入力
    // ========================================
    const autoFillBtn = document.getElementById('autoFillBtn');
    if (autoFillBtn) {
        autoFillBtn.addEventListener('click', autoFillAddress);
    }

    async function autoFillAddress() {
        const postalCode = document.getElementById('postalCode').value.replace(/[^0-9]/g, '');

        if (postalCode.length !== 7) {
            showErrorAt('postalCode', '郵便番号は7桁で入力してください');
            return;
        }

        try {
            autoFillBtn.textContent = '検索中...';
            autoFillBtn.disabled = true;

            const response = await fetch(`https://zipcloud.ibsnet.co.jp/api/search?zipcode=${postalCode}`);
            const data = await response.json();

            if (data.status === 200 && data.results && data.results.length > 0) {
                const result = data.results[0];

                const prefectureSelect = document.getElementById('prefecture');
                const prefectureName = result.address1;
                for (let option of prefectureSelect.options) {
                    if (option.text === prefectureName) {
                        prefectureSelect.value = option.value;
                        break;
                    }
                }

                document.getElementById('city').value = result.address2 + result.address3;
            } else {
                showErrorAt('postalCode', '住所が見つかりませんでした');
            }
        } catch (error) {
            console.error('Address lookup error:', error);
            showErrorAt('postalCode', '住所の取得に失敗しました');
        } finally {
            autoFillBtn.textContent = '住所を自動入力';
            autoFillBtn.disabled = false;
        }
    }

    // ========================================
    // リアルタイム文字数カウント
    // ========================================
    const productNameInput = document.getElementById('productName');
    const descriptionInput = document.getElementById('description');

    if (productNameInput) {
        productNameInput.addEventListener('input', function () {
            updateCharCount('productName', 'nameCount', 40);
        });
    }

    if (descriptionInput) {
        descriptionInput.addEventListener('input', function () {
            updateCharCount('description', 'descCount', 1000);
        });
    }

    function updateCharCount(inputId, countId, maxLength) {
        const input = document.getElementById(inputId);
        const countDisplay = document.getElementById(countId);

        if (input && countDisplay) {
            const currentLength = input.value.length;
            countDisplay.textContent = `${currentLength}/${maxLength}`;

            if (currentLength > maxLength) {
                countDisplay.classList.add('error');
                input.classList.add('input-error');
            } else {
                countDisplay.classList.remove('error');
                input.classList.remove('input-error');
            }
        }
    }

    // ========================================
    // 送信処理
    // ========================================
    async function submitEdit() {
        clearAllErrors();

        // レンタルプランを収集
        const rentalPlans = [];
        const planRows = document.querySelectorAll('.rental-plan-row');
        planRows.forEach(row => {
            const daysInput = row.querySelector('.days-input');
            const priceInput = row.querySelector('.price-input');
            if (daysInput && priceInput) {
                const days = parseInt(daysInput.value) || 0;
                const price = parseInt(priceInput.value) || 0;
                if (days > 0 || price > 0) {
                    rentalPlans.push({ days, price });
                }
            }
        });

        // 画像数チェック
        const existingCount = document.querySelectorAll('.existing-image-item').length;
        const totalImages = existingCount + newImages.length;

        const formData = {
            product_name: document.getElementById('productName').value.trim(),
            product_category: document.getElementById('category').value,
            product_description: document.getElementById('description').value.trim(),
            product_condition: document.getElementById('condition').value,
            product_status: document.getElementById('productStatus').value,
            shipping_days: document.getElementById('shippingDays').value,
            shipping_burden: document.getElementById('shippingBurden').value,
            postal_code: document.getElementById('postalCode').value.trim(),
            prefecture: document.getElementById('prefecture').value,
            city: document.getElementById('city').value.trim(),
            street_address: document.getElementById('streetAddress').value.trim(),
            rental_plans: rentalPlans,
            total_images: totalImages
        };

        const errors = validateForm(formData);
        if (Object.keys(errors).length > 0) {
            displayErrors(errors);
            return;
        }

        setLoadingState(true);

        try {
            const submitData = new FormData();
            submitData.append('product_name', formData.product_name);
            submitData.append('product_category', formData.product_category);
            submitData.append('product_description', formData.product_description);
            submitData.append('product_condition', formData.product_condition);
            submitData.append('product_status', formData.product_status);
            submitData.append('shipping_days', formData.shipping_days);
            submitData.append('shipping_burden', formData.shipping_burden);
            submitData.append('postal_code', formData.postal_code);
            submitData.append('prefecture', formData.prefecture);
            submitData.append('city', formData.city);
            submitData.append('street_address', formData.street_address);
            submitData.append('rental_plans', JSON.stringify(formData.rental_plans));

            // 削除する画像ID
            deleteImageIds.forEach(id => {
                submitData.append('delete_images', id);
            });

            // 新しい画像
            newImages.forEach(img => {
                submitData.append('images', img.file);
            });

            const response = await fetch(`/monotal/product/${productId}/edit/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: submitData
            });

            const data = await response.json();

            if (response.ok && data.success) {
                window.location.href = data.redirect_url || `/monotal/product/${productId}/`;
            } else {
                if (data.errors) {
                    displayErrors(data.errors);
                } else if (data.message) {
                    showErrorAt('imageError', data.message);
                }
            }

        } catch (error) {
            console.error('Submit error:', error);
            showErrorAt('imageError', 'ネットワークエラーが発生しました。時間をおいて再度お試しください。');
        } finally {
            setLoadingState(false);
        }
    }

    // ========================================
    // バリデーション
    // ========================================
    function validateForm(formData) {
        const errors = {};

        // 画像
        if (formData.total_images < 1) {
            errors.images = '商品画像を1枚以上登録してください';
        } else if (formData.total_images > MAX_IMAGES) {
            errors.images = `画像は最大${MAX_IMAGES}枚までです`;
        }

        // 商品名
        if (!formData.product_name) {
            errors.productName = '商品名は必須です';
        } else if (formData.product_name.length > 40) {
            errors.productName = '商品名は40文字以内で入力してください';
        }

        // カテゴリー
        if (!formData.product_category) {
            errors.category = 'カテゴリーを選択してください';
        }

        // 商品の説明
        if (!formData.product_description) {
            errors.description = '商品の説明は必須です';
        } else if (formData.product_description.length > 1000) {
            errors.description = '商品の説明は1000文字以内で入力してください';
        }

        // 商品の状態
        if (!formData.product_condition) {
            errors.condition = '商品の状態を選択してください';
        }

        // 発送までの日数
        if (!formData.shipping_days) {
            errors.shippingDays = '発送までの日数を選択してください';
        }

        // レンタルプラン
        if (!formData.rental_plans || formData.rental_plans.length === 0) {
            errors.rentalPlans = '少なくとも1つのレンタルプランを設定してください';
        } else {
            let hasValidPlan = false;
            formData.rental_plans.forEach((plan) => {
                if (plan.days > 0 && plan.price >= 100) {
                    hasValidPlan = true;
                }
                if (plan.days > 0 && plan.price > 0 && plan.price < 100) {
                    errors.rentalPlans = '金額は100円以上で設定してください';
                }
            });
            if (!hasValidPlan && !errors.rentalPlans) {
                errors.rentalPlans = '日数と金額を正しく入力してください';
            }
        }

        // 住所（郵便番号）
        if (!formData.postal_code) {
            errors.postalCode = '郵便番号は必須です';
        } else if (formData.postal_code.replace(/[^0-9]/g, '').length !== 7) {
            errors.postalCode = '郵便番号は7桁で入力してください';
        }

        // 住所（都道府県）
        if (!formData.prefecture) {
            errors.prefecture = '都道府県を選択してください';
        }

        // 住所（市区町村・町域）
        if (!formData.city) {
            errors.city = '市区町村・町域は必須です';
        }

        // 住所（番地・建物名）
        if (!formData.street_address) {
            errors.streetAddress = '番地・建物名は必須です';
        }

        return errors;
    }

    // ========================================
    // エラー表示
    // ========================================
    function displayErrors(errors) {
        Object.keys(errors).forEach(field => {
            if (field === 'images') {
                showErrorAt('imageError', errors[field]);
            } else if (field === 'rentalPlans') {
                showErrorAt('rentalPlansError', errors[field]);
            } else {
                const input = document.getElementById(field);
                if (input) {
                    showError(input, errors[field]);
                }
            }
        });

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

    function clearError(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
        }
    }

    function clearAllErrors() {
        document.querySelectorAll('.input-error').forEach(el => {
            el.classList.remove('input-error');
        });
        document.querySelectorAll('.error-message').forEach(el => {
            el.remove();
        });
        document.querySelectorAll('.char-count.error').forEach(el => {
            el.classList.remove('error');
        });

        ['imageError', 'rentalPlansError'].forEach(id => {
            const container = document.getElementById(id);
            if (container) container.innerHTML = '';
        });
    }

    // ========================================
    // ユーティリティ
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

    function setLoadingState(isLoading) {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            submitBtn.disabled = isLoading;
            if (isLoading) {
                submitBtn.innerHTML = '<span class="iconify" data-icon="lucide:loader-2" data-width="18"></span> 保存中...';
            } else {
                submitBtn.innerHTML = '<span class="iconify" data-icon="lucide:save" data-width="18"></span> 変更を保存する';
            }
        }
    }

    // 初期化
    updateUploadBoxVisibility();
    updateDeleteButtons();
});
