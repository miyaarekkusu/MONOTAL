document.addEventListener('DOMContentLoaded', function () {
    const filterBtns = document.querySelectorAll('.filter-btn');
    const itemCards = document.querySelectorAll('.item-card');
    const loadMoreBtn = document.querySelector('.load-more-btn');
    const viewAllReviewsBtn = document.querySelector('.view-all-reviews-btn');

    // フィルター機能
    filterBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const filter = this.getAttribute('data-filter');

            // アクティブ状態の切り替え
            filterBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // 商品の表示/非表示を切り替え
            filterProducts(filter);
        });
    });

    function filterProducts(filter) {
        itemCards.forEach(card => {
            const status = card.getAttribute('data-status');

            if (filter === 'all') {
                card.classList.remove('hidden');
                card.style.animation = 'fadeIn 0.3s ease';
            } else if (filter === 'available' && status === 'available') {
                card.classList.remove('hidden');
                card.style.animation = 'fadeIn 0.3s ease';
            } else if (filter === 'rented' && status === 'rented') {
                card.classList.remove('hidden');
                card.style.animation = 'fadeIn 0.3s ease';
            } else {
                card.classList.add('hidden');
            }
        });

        // フィルター後のカウント更新
        updateFilterCounts();
    }

    function updateFilterCounts() {
        const allCount = itemCards.length;
        const availableCount = document.querySelectorAll('.item-card[data-status="available"]').length;
        const rentedCount = document.querySelectorAll('.item-card[data-status="rented"]').length;

        document.querySelector('[data-filter="all"]').textContent = `すべて (${allCount})`;
        document.querySelector('[data-filter="available"]').textContent = `レンタル可能 (${availableCount})`;
        document.querySelector('[data-filter="rented"]').textContent = `レンタル中 (${rentedCount})`;
    }

    // さらに商品を読み込む機能
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', function () {
            // ローディング状態にする
            this.textContent = '読み込み中...';
            this.disabled = true;

            // 実際のAPI呼び出しをシミュレート
            setTimeout(() => {
                loadMoreProducts();
                this.textContent = 'さらに商品を見る';
                this.disabled = false;
            }, 1500);
        });
    }

    function loadMoreProducts() {
        // 追加商品のサンプルデータ
        const additionalProducts = [
            {
                id: 16,
                name: 'Nintendo Switch OLED',
                price: '1,500',
                condition: '目立った傷なし',
                status: 'available',
                views: 84,
                image: 'https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?w=250&h=250&fit=crop',
                rentalDetail: '最大レンタル期間：10日間'
            },
            {
                id: 17,
                name: 'iPad Air 第5世代',
                price: '3,200',
                condition: '新品、未使用',
                status: 'available',
                views: 67,
                image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=250&h=250&fit=crop',
                rentalDetail: '最大レンタル期間：21日間'
            }
        ];

        const itemGrid = document.querySelector('.item-grid');

        additionalProducts.forEach(product => {
            const productCard = createProductCard(product);
            itemGrid.appendChild(productCard);
        });

        // カウントを更新
        updateFilterCounts();
    }

    function createProductCard(product) {
        const card = document.createElement('div');
        card.className = 'item-card';
        card.setAttribute('data-status', product.status);

        const statusClass = product.status === 'available' ? 'available' : 'rented';
        const statusIcon = product.status === 'available' ? 'fas fa-check-circle' : 'fas fa-clock';
        const statusText = product.status === 'available' ? 'レンタル可能' : 'レンタル中';

        card.innerHTML = `
            <a href="/product/${product.id}" class="item-link">
                <div class="item-image-wrapper">
                    <img src="${product.image}" alt="${product.name}" class="item-image">
                    <div class="item-status ${statusClass}">
                        <i class="${statusIcon}"></i>
                        <span>${statusText}</span>
                    </div>
                </div>
                <div class="item-details">
                    <h3 class="item-name">${product.name}</h3>
                    <p class="rental-detail">${product.rentalDetail}</p>
                    <div class="item-meta">
                        <span class="item-condition">${product.condition}</span>
                        <span class="item-views">
                            <i class="fas fa-eye"></i> ${product.views}
                        </span>
                    </div>
                    <div class="item-price">¥${product.price}/日</div>
                </div>
            </a>
        `;

        return card;
    }

    // レビュー表示機能
    if (viewAllReviewsBtn) {
        viewAllReviewsBtn.addEventListener('click', function () {
            // レビュー一覧ページへの遷移や、モーダル表示などの処理
            showAllReviews();
        });
    }

    function showAllReviews() {
        // 実際の実装では、レビュー一覧ページへのリダイレクトまたはモーダル表示
        alert('すべてのレビューページへ移動します。');
        // window.location.href = '/profile/reviews';
    }

    // 評価バーのアニメーション
    function animateRatingBars() {
        const ratingFills = document.querySelectorAll('.rating-fill');

        ratingFills.forEach(fill => {
            const width = fill.style.width;
            fill.style.width = '0%';

            setTimeout(() => {
                fill.style.width = width;
            }, 500);
        });
    }

    // ページ読み込み時にアニメーションを実行
    animateRatingBars();

    // 商品カードのホバー効果を強化
    itemCards.forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.transform = 'translateY(-4px)';
        });

        card.addEventListener('mouseleave', function () {
            this.style.transform = 'translateY(0)';
        });
    });

    // スクロール時のナビゲーション固定
    let lastScrollTop = 0;
    const header = document.querySelector('.main-header');

    window.addEventListener('scroll', function () {
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

        if (scrollTop > lastScrollTop && scrollTop > 100) {
            // 下スクロール
            header.style.transform = 'translateY(-100%)';
        } else {
            // 上スクロール
            header.style.transform = 'translateY(0)';
        }

        lastScrollTop = scrollTop;
    });

    // レスポンシブ対応のためのリサイズイベント
    window.addEventListener('resize', function () {
        // ウィンドウサイズに応じてレイアウトを調整
        adjustLayoutForSize();
    });

    function adjustLayoutForSize() {
        const windowWidth = window.innerWidth;

        if (windowWidth <= 768) {
            // モバイル表示での調整
            adjustMobileLayout();
        } else {
            // デスクトップ表示での調整
            adjustDesktopLayout();
        }
    }

    function adjustMobileLayout() {
        // モバイル用の調整処理
        const profileStats = document.querySelector('.profile-stats');
        if (profileStats) {
            profileStats.style.flexDirection = 'column';
        }
    }

    function adjustDesktopLayout() {
        // デスクトップ用の調整処理
        const profileStats = document.querySelector('.profile-stats');
        if (profileStats) {
            profileStats.style.flexDirection = 'row';
        }
    }

    // 初期レイアウト調整
    adjustLayoutForSize();

    // 商品データの管理（実際のAPIとの連携用）
    const profileData = {
        userId: 'user123',
        products: [],
        reviews: [],
        stats: {
            totalProducts: 0,
            completedTransactions: 0,
            rentalCount: 0
        }
    };

    // API呼び出し関数（実際の実装用）
    async function fetchUserProfile(userId) {
        try {
            // const response = await fetch(`/api/users/${userId}/profile`);
            // const data = await response.json();
            // return data;

            // デモ用のモック処理
            return {
                success: true,
                user: profileData
            };
        } catch (error) {
            console.error('プロフィール取得エラー:', error);
            return { success: false, error: error.message };
        }
    }

    async function fetchUserProducts(userId, page = 1, filter = 'all') {
        try {
            // const response = await fetch(`/api/users/${userId}/products?page=${page}&filter=${filter}`);
            // const data = await response.json();
            // return data;

            // デモ用のモック処理
            return {
                success: true,
                products: [],
                hasMore: false
            };
        } catch (error) {
            console.error('商品取得エラー:', error);
            return { success: false, error: error.message };
        }
    }

    // 実際のC# Web API連携用のサンプル関数
    /*
    async function updateProfile(profileData) {
        try {
            const response = await fetch('/api/profile', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify(profileData)
            });
            
            if (!response.ok) {
                throw new Error('プロフィール更新に失敗しました');
            }
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('プロフィール更新エラー:', error);
            throw error;
        }
    }
    */
});