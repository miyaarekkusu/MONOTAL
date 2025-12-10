// 画像アップロード関連の変数
let uploadedImages = [];

// 画像アップロード処理
function handleImageUpload(event) {
    const files = event.target.files;
    const maxImages = 10;

    // 最大枚数チェック
    if (uploadedImages.length + files.length > maxImages) {
        alert(`画像は最大${maxImages}枚まで追加できます。`);
        return;
    }
    // 各ファイルを処理
    for (let file of files) {
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const imageData = {
                    id: Date.now() + Math.random(),
                    src: e.target.result,
                    file: file
                };
                uploadedImages.push(imageData);
                displayImages();
                validateForm();
            };
            reader.readAsDataURL(file);
        }
    }
}

// 画像表示処理
function displayImages() {
    const preview = document.getElementById('imagePreview');
    preview.innerHTML = '';
    uploadedImages.forEach(image => {
        const imageDiv = document.createElement('div');
        imageDiv.className = 'image-item';
        imageDiv.innerHTML = `
            <img src="${image.src}" alt="商品画像">
            <button type="button" class="remove-image" onclick="removeImage('${image.id}')">×</button>
        `;
        preview.appendChild(imageDiv);
    });
}

// 画像削除処理
function removeImage(imageId) {
    uploadedImages = uploadedImages.filter(img => img.id !== imageId);
    displayImages();
    validateForm();
}

// 文字数カウント更新
function updateCharCount(inputId, countId, maxLength) {
    const input = document.getElementById(inputId);
    const counter = document.getElementById(countId);
    const currentLength = input.value.length;
    counter.textContent = `${currentLength}/${maxLength}`;

    if (currentLength > maxLength * 0.8) {
        counter.style.color = '#ff6b7a';
    } else {
        counter.style.color = '#999';
    }

    validateForm();
}

// 手数料計算処理
function calculateFees() {
    const price = parseInt(document.getElementById('price').value) || 0;
    const salesFeeRate = 0.10; // 10%
    const shippingCost = 200; // 仮の送料
    const salesFee = Math.floor(price * salesFeeRate);
    const profit = price - salesFee - shippingCost;
    document.getElementById('salesFee').textContent = `¥${salesFee.toLocaleString()}`;
    document.getElementById('shippingFee').textContent = `¥${shippingCost.toLocaleString()}`;
    document.getElementById('profit').textContent = `¥${Math.max(0, profit).toLocaleString()}`;

    validateForm();
}

// フォームバリデーション
function validateForm() {
    const required = [
        uploadedImages.length > 0, // 画像が1枚以上
        document.getElementById('productName').value.trim(), // 商品名
        document.getElementById('category').value, // カテゴリー
        document.getElementById('description').value.trim(), // 商品説明
        document.getElementById('condition').value, // 商品状態
        document.getElementById('shippingMethod').value, // 配送方法
        document.getElementById('shippingArea').value, // 発送地域
        document.getElementById('shippingDays').value, // 発送日数
        parseInt(document.getElementById('rentalDays').value) >= 1, // レンタル期間 (1日以上)
        parseInt(document.getElementById('price').value) >= 300, // 価格（最低300円）
        document.getElementById('agreeTerms').checked // 利用規約同意
    ];
    const allValid = required.every(condition => condition);
    document.querySelector('.submit-btn').disabled = !allValid;
}

// 商品出品処理
function submitProduct() {
    if (document.querySelector('.submit-btn').disabled) {
        return;
    }
    const formData = {
        images: uploadedImages,
        productName: document.getElementById('productName').value,
        category: document.getElementById('category').value,
        brand: document.getElementById('brand').value,
        description: document.getElementById('description').value,
        condition: document.getElementById('condition').value,
        shippingMethod: document.getElementById('shippingMethod').value,
        shippingArea: document.getElementById('shippingArea').value,
        shippingDays: document.getElementById('shippingDays').value,
        rentalDays: document.getElementById('rentalDays').value, // 変更
        price: document.getElementById('price').value
    };
    // 確認ダイアログ
    if (confirm('この内容で商品を出品しますか？')) {
        // 実際のサーバー送信処理をここに実装
        alert('商品が出品されました！');
        console.log('出品データ:', formData);
    }
}

// イベントリスナー設定
document.addEventListener('DOMContentLoaded', function () {
    // フォーム要素の変更監視
    const formElements = document.querySelectorAll('input, select, textarea');
    formElements.forEach(element => {
        element.addEventListener('change', validateForm);
        element.addEventListener('input', validateForm);
    });
    // 初期バリデーション
    validateForm();
});