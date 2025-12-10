document.addEventListener('DOMContentLoaded', () => {
    // 画像データ
    const images = [
        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500&h=500&fit=crop",
        "https://images.unsplash.com/photo-1572569511254-d8f925fe2cbb?w=500&h=500&fit=crop",
        "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=500&h=500&fit=crop",
        "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=500&h=500&fit=crop"
    ];

    let currentImageIndex = 0;
    let currentRating = 5;

    // DOM要素の取得
    const thumbnails = document.querySelectorAll('.thumbnail');
    const mainImage = document.getElementById('main-product-image');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');
    const currentImageIndexEl = document.getElementById('currentImageIndex');
    const totalImagesEl = document.getElementById('totalImages');
    const favoriteBtn = document.getElementById('favoriteBtn');
    const commentForm = document.getElementById('commentForm');
    const commentText = document.getElementById('commentText');
    const starRating = document.getElementById('starRating');
    const commentsList = document.getElementById('commentsList');
    const rentalButton = document.getElementById('rentalButton');

    // 初期設定
    totalImagesEl.textContent = images.length;

    // サムネイル画像にクリックイベントを追加
    thumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener('click', () => {
            selectImage(index);
        });
    });

    // ナビゲーションボタンのイベントリスナー
    prevBtn.addEventListener('click', previousImage);
    nextBtn.addEventListener('click', nextImage);

    // 画像選択関数
    function selectImage(index) {
        currentImageIndex = index;
        updateMainImage();
        updateThumbnailActive();
        updateImageCounter();
    }

    // メイン画像更新
    function updateMainImage() {
        mainImage.src = images[currentImageIndex];
        mainImage.alt = `製品画像${currentImageIndex + 1}`;
    }

    // サムネイルのアクティブ状態更新
    function updateThumbnailActive() {
        thumbnails.forEach((thumb, index) => {
            thumb.classList.toggle('active', index === currentImageIndex);
        });
    }

    // 画像カウンター更新
    function updateImageCounter() {
        currentImageIndexEl.textContent = currentImageIndex + 1;
    }

    // 前の画像
    function previousImage() {
        currentImageIndex = (currentImageIndex - 1 + images.length) % images.length;
        updateMainImage();
        updateThumbnailActive();
        updateImageCounter();
    }

    // 次の画像
    function nextImage() {
        currentImageIndex = (currentImageIndex + 1) % images.length;
        updateMainImage();
        updateThumbnailActive();
        updateImageCounter();
    }

    // お気に入りボタンのトグル
    favoriteBtn.addEventListener('click', () => {
        favoriteBtn.classList.toggle('favorited');
        const heartIcon = favoriteBtn.querySelector('i');
        const span = favoriteBtn.querySelector('span');

        if (favoriteBtn.classList.contains('favorited')) {
            heartIcon.style.color = '#ff4757';
            span.textContent = 'いいね済み';
        } else {
            heartIcon.style.color = '';
            span.textContent = 'いいね!';
        }
    });

    // 星評価のイベントリスナー
    const stars = starRating.querySelectorAll('.star');
    stars.forEach((star, index) => {
        star.addEventListener('click', () => {
            currentRating = index + 1;
            updateStarRating();
        });

        star.addEventListener('mouseenter', () => {
            highlightStars(index + 1);
        });
    });

    starRating.addEventListener('mouseleave', () => {
        updateStarRating();
    });

    // 星の表示更新
    function updateStarRating() {
        stars.forEach((star, index) => {
            star.classList.toggle('active', index < currentRating);
        });
    }

    // 星のハイライト（ホバー時）
    function highlightStars(rating) {
        stars.forEach((star, index) => {
            star.classList.toggle('active', index < rating);
        });
    }

    // コメント投稿フォームのイベントリスナー
    commentForm.addEventListener('submit', (e) => {
        e.preventDefault();

        const comment = commentText.value.trim();
        if (comment) {
            addNewComment(comment, currentRating);
            commentText.value = '';
            currentRating = 5;
            updateStarRating();
        }
    });

    // 新しいコメントを追加
    function addNewComment(comment, rating) {
        const newComment = document.createElement('div');
        newComment.className = 'comment-item';

        const starsHtml = '★'.repeat(rating) + '☆'.repeat(5 - rating);

        newComment.innerHTML = `
            <div class="comment-header">
                <div class="comment-avatar">あなた</div>
                <div class="comment-user-info">
                    <h4>あなた</h4>
                    <div class="comment-meta">
                        <span class="stars">${starsHtml}</span>
                        <span>•</span>
                        <span>今</span>
                    </div>
                </div>
            </div>
            <p class="comment-text">${comment}</p>
        `;

        commentsList.insertBefore(newComment, commentsList.firstChild);

        // アニメーション効果
        newComment.style.opacity = '0';
        newComment.style.transform = 'translateY(-10px)';
        setTimeout(() => {
            newComment.style.transition = 'all 0.3s ease';
            newComment.style.opacity = '1';
            newComment.style.transform = 'translateY(0)';
        }, 10);
    }

    // レンタルボタンのクリックイベント
    rentalButton.addEventListener('click', () => {
        // アラートまたはモーダルで確認
        if (confirm('7日間のレンタルでよろしいですか？')) {
            alert('レンタル申請を受け付けました！詳細は別途ご連絡いたします。');
            // ここで実際のレンタル処理やページ遷移を行う
        }
    });

    // シェアボタンの機能
    const shareBtn = document.querySelector('.share-btn');
    shareBtn.addEventListener('click', () => {
        if (navigator.share) {
            navigator.share({
                title: document.querySelector('.product-title').textContent,
                text: '高品質なBluetoothヘッドフォンをレンタルできます！',
                url: window.location.href
            });
        } else {
            // フォールバック: URLをクリップボードにコピー
            navigator.clipboard.writeText(window.location.href).then(() => {
                alert('URLをクリップボードにコピーしました！');
            }).catch(() => {
                alert('シェア機能が利用できません。');
            });
        }
    });

    // キーボードナビゲーション
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            e.preventDefault();
            previousImage();
        } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            nextImage();
        }
    });

    // 画像の遅延読み込み
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    });

    // 遅延読み込み対象の画像があれば監視開始
    document.querySelectorAll('img[data-src]').forEach(img => {
        imageObserver.observe(img);
    });

    // タッチスワイプ対応（モバイル用）
    let touchStartX = 0;
    let touchEndX = 0;

    mainImage.addEventListener('touchstart', e => {
        touchStartX = e.changedTouches[0].screenX;
    }, { passive: true });

    mainImage.addEventListener('touchend', e => {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, { passive: true });

    function handleSwipe() {
        const swipeThreshold = 50;
        const swipeDistance = touchEndX - touchStartX;

        if (Math.abs(swipeDistance) > swipeThreshold) {
            if (swipeDistance > 0) {
                previousImage();
            } else {
                nextImage();
            }
        }
    }
});