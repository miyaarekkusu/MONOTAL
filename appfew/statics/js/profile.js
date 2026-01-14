// Profile Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Follow button functionality
    initFollowButton();

    // Share button functionality
    initShareButton();

    // Load more button
    initLoadMoreButton();
});

/**
 * Initialize follow button
 */
function initFollowButton() {
    const followBtn = document.querySelector('button[data-action="follow"]');

    if (!followBtn) return;

    followBtn.addEventListener('click', function(e) {
        e.preventDefault();

        const icon = this.querySelector('.iconify');
        const text = this.querySelector('span:not(.iconify)');

        // Toggle follow state (placeholder - would need backend integration)
        if (this.classList.contains('following')) {
            // Unfollow
            this.classList.remove('following', 'bg-zinc-100', 'text-zinc-900');
            this.classList.add('bg-zinc-900', 'text-white');
            icon.setAttribute('data-icon', 'lucide:user-plus');
            if (text) text.textContent = 'フォローする';
        } else {
            // Follow
            this.classList.add('following', 'bg-zinc-100', 'text-zinc-900');
            this.classList.remove('bg-zinc-900', 'text-white');
            icon.setAttribute('data-icon', 'lucide:user-check');
            if (text) text.textContent = 'フォロー中';
        }
    });
}

/**
 * Initialize share button
 */
function initShareButton() {
    const shareBtn = document.querySelector('button[data-action="share"]');

    if (!shareBtn) return;

    shareBtn.addEventListener('click', function(e) {
        e.preventDefault();

        // Check if Web Share API is supported
        if (navigator.share) {
            navigator.share({
                title: document.title,
                url: window.location.href
            }).catch(err => {
                console.log('Share canceled or failed:', err);
            });
        } else {
            // Fallback: copy to clipboard
            navigator.clipboard.writeText(window.location.href).then(() => {
                alert('URLをコピーしました');
            });
        }
    });
}

/**
 * Initialize load more button
 */
function initLoadMoreButton() {
    const loadMoreBtn = document.querySelector('button[data-action="load-more"]');

    if (!loadMoreBtn) return;

    loadMoreBtn.addEventListener('click', function(e) {
        e.preventDefault();

        // Placeholder for loading more products
        // Would need to implement pagination or infinite scroll
        console.log('Load more products');

        // Show loading state
        const originalText = this.innerHTML;
        this.innerHTML = '<span class="iconify animate-spin" data-icon="lucide:loader-2" data-width="16"></span> 読み込み中...';
        this.disabled = true;

        // Simulate loading (would be replaced with actual API call)
        setTimeout(() => {
            this.innerHTML = originalText;
            this.disabled = false;
        }, 1000);
    });
}
