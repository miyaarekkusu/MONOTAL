document.addEventListener('DOMContentLoaded', function () {
    const faceInput = document.getElementById('faceInput');
    const licenseInput = document.getElementById('licenseInput');
    const faceUploadArea = document.getElementById('faceUploadArea');
    const licenseUploadArea = document.getElementById('licenseUploadArea');
    const facePreview = document.getElementById('facePreview');
    const licensePreview = document.getElementById('licensePreview');
    const faceImage = document.getElementById('faceImage');
    const licenseImage = document.getElementById('licenseImage');
    const faceFileName = document.getElementById('faceFileName');
    const licenseFileName = document.getElementById('licenseFileName');
    const removeFace = document.getElementById('removeFace');
    const removeLicense = document.getElementById('removeLicense');
    const submitBtn = document.getElementById('submitBtn');
    const form = document.getElementById('verificationForm');

    let faceFile = null;
    let licenseFile = null;

    // ドラッグ&ドロップ対応
    function setupDragAndDrop(uploadArea, fileInput) {
        uploadArea.addEventListener('dragover', function (e) {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', function (e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', function (e) {
            e.preventDefault();
            uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        });
    }

    setupDragAndDrop(faceUploadArea, faceInput);
    setupDragAndDrop(licenseUploadArea, licenseInput);

    // 顔写真アップロード処理
    faceInput.addEventListener('change', function () {
        const file = this.files[0];
        if (file) {
            if (file.type.startsWith('image/')) {
                faceFile = file;
                const reader = new FileReader();
                reader.onload = function (e) {
                    faceImage.src = e.target.result;
                    faceFileName.textContent = file.name;
                    facePreview.style.display = 'block';
                    faceUploadArea.style.display = 'none';
                    checkSubmitButton();
                };
                reader.readAsDataURL(file);
            } else {
                alert('画像ファイルを選択してください。');
            }
        }
    });

    // 免許証写真アップロード処理
    licenseInput.addEventListener('change', function () {
        const file = this.files[0];
        if (file) {
            if (file.type.startsWith('image/')) {
                licenseFile = file;
                const reader = new FileReader();
                reader.onload = function (e) {
                    licenseImage.src = e.target.result;
                    licenseFileName.textContent = file.name;
                    licensePreview.style.display = 'block';
                    licenseUploadArea.style.display = 'none';
                    checkSubmitButton();
                };
                reader.readAsDataURL(file);
            } else {
                alert('画像ファイルを選択してください。');
            }
        }
    });

    // 顔写真削除
    removeFace.addEventListener('click', function () {
        faceFile = null;
        faceInput.value = '';
        facePreview.style.display = 'none';
        faceUploadArea.style.display = 'block';
        checkSubmitButton();
    });

    // 免許証写真削除
    removeLicense.addEventListener('click', function () {
        licenseFile = null;
        licenseInput.value = '';
        licensePreview.style.display = 'none';
        licenseUploadArea.style.display = 'block';
        checkSubmitButton();
    });

    // 送信ボタンの有効化チェック
    function checkSubmitButton() {
        if (faceFile && licenseFile) {
            submitBtn.disabled = false;
        } else {
            submitBtn.disabled = true;
        }
    }

    // フォーム送信処理
    form.addEventListener('submit', function (e) {
        e.preventDefault();

        if (faceFile && licenseFile) {
            // 本来はここでサーバーにファイルをアップロード
            alert('本人確認の申請を受け付けました。審査完了まで1〜3営業日お待ちください。');

            // FormDataを作成（実際のAPI送信用）
            const formData = new FormData();
            formData.append('facePhoto', faceFile);
            formData.append('licensePhoto', licenseFile);

            // ここで実際のAPI呼び出しを行う
            console.log('送信データ:', {
                facePhoto: faceFile.name,
                licensePhoto: licenseFile.name
            });

            // 実際のAPI送信例（コメントアウト状態）
            /*
            fetch('/api/verification', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('本人確認の申請を受け付けました。審査完了まで1〜3営業日お待ちください。');
                    // リダイレクトまたは次のページへ遷移
                } else {
                    alert('エラーが発生しました。もう一度お試しください。');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('エラーが発生しました。もう一度お試しください。');
            });
            */
        }
    });
});