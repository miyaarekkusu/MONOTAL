// product_filter.js - フィルター機能
document.addEventListener('DOMContentLoaded', function () {
    // フィルターセクションの開閉機能を初期化
    initFilterSections();
    // カテゴリーの開閉機能を初期化
    initCategoryToggle();
    // デフォルトで最初のフィルターを開く
    openDefaultFilters();
    // クリアボタンの機能を初期化
    initClearButton();
});

/**
 * フィルターセクションの開閉機能を初期化
 */
function initFilterSections() {
    const filterTitles = document.querySelectorAll('.filter-title');
    filterTitles.forEach(title => {
        title.addEventListener('click', function () {
            const filterSection = this.closest('.filter-section');
            if (filterSection) {
                filterSection.classList.toggle('open');
            }
        });
    });
}

/**
 * カテゴリーの開閉機能を初期化
 */
function initCategoryToggle() {
    const categoryLinks = document.querySelectorAll('.category-item > .category-link');
    categoryLinks.forEach(link => {
        link.addEventListener('click', function (event) {
            event.preventDefault();
            const categoryItem = this.closest('.category-item');
            if (categoryItem) {
                // 他のカテゴリーを閉じる
                const allCategories = document.querySelectorAll('.category-item');
                allCategories.forEach(item => {
                    if (item !== categoryItem) {
                        item.classList.remove('open');
                    }
                });
                // クリックされたカテゴリーをトグル
                categoryItem.classList.toggle('open');
            }
        });
    });
}

/**
 * デフォルトで最初のフィルターを開く
 */
function openDefaultFilters() {
    // カテゴリーフィルターをデフォルトで開く
    const categoryFilter = document.querySelector('.category-filter');
    if (categoryFilter) {
        categoryFilter.classList.add('open');
    }
}

/**
 * クリアボタンの機能を初期化
 */
function initClearButton() {
    const clearBtn = document.querySelector('.clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function () {
            // すべての入力フィールドをクリア
            const inputs = document.querySelectorAll('.category-sidebar input');
            inputs.forEach(input => {
                if (input.type === 'checkbox') {
                    input.checked = false;
                } else {
                    input.value = '';
                }
            });

            // すべてのカテゴリーを閉じる
            const categoryItems = document.querySelectorAll('.category-item');
            categoryItems.forEach(item => {
                item.classList.remove('open');
            });

            // アクティブなカテゴリーリンクをリセット
            const activeLinks = document.querySelectorAll('.category-link.active, .subcategory-link.active');
            activeLinks.forEach(link => {
                link.classList.remove('active');
            });

            // 「すべて」をアクティブに
            const allLink = document.querySelector('.category-list > li:first-child .category-link');
            if (allLink) {
                allLink.classList.add('active');
            }
        });
    }
}