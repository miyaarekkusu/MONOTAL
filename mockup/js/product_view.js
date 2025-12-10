// product_filter.js - フィルター機能
document.addEventListener('DOMContentLoaded', function() {
    // フィルターセクションの開閉機能を初期化
    initFilterSections();
    
    // カテゴリーの開閉機能を初期化
    initCategoryToggle();
    
    // デフォルトで最初のフィルターを開く
    openDefaultFilters();
});

/**
 * フィルターセクションの開閉機能を初期化
 */
function initFilterSections() {
    const filterTitles = document.querySelectorAll('.filter-title');
    
    filterTitles.forEach(title => {
        title.addEventListener('click', function() {
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
        link.addEventListener('click', function(event) {
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