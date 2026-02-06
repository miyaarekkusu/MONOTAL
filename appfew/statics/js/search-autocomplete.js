/**
 * 検索オートコンプリート機能
 * ヘッダーの検索バーでキーワード入力時に候補を表示
 */

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('header-search-input');
    const autocompleteDropdown = document.getElementById('autocomplete-dropdown');
    const searchForm = document.getElementById('header-search-form');

    if (!searchInput || !autocompleteDropdown) return;

    let debounceTimer;
    let currentFocus = -1;
    let suggestions = [];

    // 入力時のイベント
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();

        // デバウンス処理（300ms）
        clearTimeout(debounceTimer);

        if (query.length < 2) {
            hideDropdown();
            return;
        }

        debounceTimer = setTimeout(() => {
            fetchSuggestions(query);
        }, 300);
    });

    // キーボードナビゲーション
    searchInput.addEventListener('keydown', function(e) {
        const items = autocompleteDropdown.querySelectorAll('.autocomplete-item');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            currentFocus++;
            if (currentFocus >= items.length) currentFocus = 0;
            setActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            currentFocus--;
            if (currentFocus < 0) currentFocus = items.length - 1;
            setActive(items);
        } else if (e.key === 'Enter') {
            if (currentFocus > -1 && items[currentFocus]) {
                e.preventDefault();
                items[currentFocus].click();
            }
        } else if (e.key === 'Escape') {
            hideDropdown();
        }
    });

    // フォーカスアウト時にドロップダウンを閉じる
    document.addEventListener('click', function(e) {
        if (!searchForm.contains(e.target)) {
            hideDropdown();
        }
    });

    // 候補を取得
    async function fetchSuggestions(query) {
        try {
            const response = await fetch(`/monotal/search/autocomplete/?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            if (data.success && data.suggestions.length > 0) {
                suggestions = data.suggestions;
                renderSuggestions(data.suggestions);
                showDropdown();
            } else {
                hideDropdown();
            }
        } catch (error) {
            console.error('Autocomplete error:', error);
            hideDropdown();
        }
    }

    // 候補を表示
    function renderSuggestions(items) {
        autocompleteDropdown.innerHTML = items.map((item, index) => {
            const icon = item.icon || 'lucide:search';
            const typeLabel = item.type === 'category' ? 'カテゴリ' : '商品';
            const typeClass = item.type === 'category' ? 'bg-purple-50 text-purple-700' : 'bg-blue-50 text-blue-700';

            return `
                <div class="autocomplete-item flex items-center gap-3 px-4 py-3 hover:bg-zinc-50 cursor-pointer transition-colors border-b border-zinc-100 last:border-b-0"
                     data-index="${index}"
                     data-value="${escapeHtml(item.value)}"
                     data-type="${item.type}"
                     data-id="${item.category_id || item.product_id || ''}">
                    <span class="iconify text-zinc-400" data-icon="${icon}" data-width="18" data-height="18"></span>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-medium text-zinc-900 truncate">${escapeHtml(item.text)}</p>
                    </div>
                    <span class="text-[10px] font-semibold px-2 py-1 rounded ${typeClass}">${typeLabel}</span>
                </div>
            `;
        }).join('');

        // クリックイベントを追加
        autocompleteDropdown.querySelectorAll('.autocomplete-item').forEach((item, index) => {
            item.addEventListener('click', function() {
                selectSuggestion(index);
            });

            item.addEventListener('mouseenter', function() {
                currentFocus = index;
                setActive(autocompleteDropdown.querySelectorAll('.autocomplete-item'));
            });
        });
    }

    // 候補を選択
    function selectSuggestion(index) {
        const suggestion = suggestions[index];
        if (!suggestion) return;

        searchInput.value = suggestion.value;

        // カテゴリーの場合はカテゴリーセレクトも更新
        if (suggestion.type === 'category' && suggestion.category_id) {
            const categorySelect = document.querySelector('select[name="category"]');
            if (categorySelect) {
                categorySelect.value = suggestion.category_id;
            }
        }

        hideDropdown();
        searchForm.submit();
    }

    // アクティブな候補をハイライト
    function setActive(items) {
        items.forEach((item, index) => {
            if (index === currentFocus) {
                item.classList.add('bg-zinc-50');
            } else {
                item.classList.remove('bg-zinc-50');
            }
        });
    }

    // ドロップダウンを表示
    function showDropdown() {
        autocompleteDropdown.classList.remove('hidden');
    }

    // ドロップダウンを非表示
    function hideDropdown() {
        autocompleteDropdown.classList.add('hidden');
        currentFocus = -1;
    }

    // HTMLエスケープ
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
