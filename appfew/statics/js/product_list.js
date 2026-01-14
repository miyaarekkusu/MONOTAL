// AP Collections - JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all functionality
    initializeFilters();
    initializeSearch();
    initializePricePresets();
});

// Filter accordion functionality
function initializeFilters() {
    const filterSections = document.querySelectorAll('.filter-section details');
    
    filterSections.forEach(section => {
        const summary = section.querySelector('summary');
        summary.addEventListener('click', function(e) {
            // Default behavior handles open/close
        });
    });

    // Clear all filters
    const clearBtn = document.querySelector('.clear-btn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            // Clear all checkboxes
            document.querySelectorAll('.filter-section input[type="checkbox"]').forEach(cb => {
                cb.checked = false;
            });
            
            // Clear all text inputs
            document.querySelectorAll('.filter-section input[type="text"], .filter-section input[type="number"]').forEach(input => {
                input.value = '';
            });
            
            // Reset selects to first option
            document.querySelectorAll('.filter-section select').forEach(select => {
                select.selectedIndex = 0;
            });
        });
    }
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('.search-input');
    const searchBtn = document.querySelector('.search-btn');
    
    if (searchInput && searchBtn) {
        searchBtn.addEventListener('click', function() {
            performSearch(searchInput.value);
        });
        
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                performSearch(searchInput.value);
            }
        });
    }
    
    // Brand search
    const brandSearch = document.querySelector('.filter-search input');
    if (brandSearch) {
        brandSearch.addEventListener('input', function() {
            filterBrands(this.value);
        });
    }
}

function performSearch(query) {
    if (query.trim()) {
        console.log('検索中:', query);
        // Add actual search logic here
    }
}

function filterBrands(query) {
    const brandLabels = document.querySelectorAll('.brand-checkbox');
    const lowerQuery = query.toLowerCase();
    
    brandLabels.forEach(label => {
        const brandName = label.querySelector('span').textContent.toLowerCase();
        if (brandName.includes(lowerQuery) || query === '') {
            label.style.display = 'flex';
        } else {
            label.style.display = 'none';
        }
    });
}

// Price preset buttons
function initializePricePresets() {
    const presets = document.querySelectorAll('.price-preset');
    const minInput = document.querySelector('.price-inputs input:first-child');
    const maxInput = document.querySelector('.price-inputs input:last-of-type');
    
    presets.forEach(preset => {
        preset.addEventListener('click', function() {
            const range = this.dataset.range;
            
            if (range === 'under-1000') {
                minInput.value = '';
                maxInput.value = '1000';
            } else if (range === '1000-5000') {
                minInput.value = '1000';
                maxInput.value = '5000';
            } else if (range === '5000-10000') {
                minInput.value = '5000';
                maxInput.value = '10000';
            }
            
            // Visual feedback
            presets.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

// Save search functionality
const saveSearchBtn = document.querySelector('.save-search-btn');
if (saveSearchBtn) {
    saveSearchBtn.addEventListener('click', function() {
        alert('検索条件を保存しました！');
    });
}

// Product card hover effects (additional enhancement)
document.querySelectorAll('.product-card').forEach(card => {
    card.addEventListener('click', function() {
        // Navigate to product detail page
        console.log('商品詳細ページへ移動');
    });
});
