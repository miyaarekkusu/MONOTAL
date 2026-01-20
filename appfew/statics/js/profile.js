// Profile Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    initTabs();

    // Follow button functionality
    initFollowButton();

    // Share button functionality
    initShareButton();

    // Load more button
    initLoadMoreButton();
});

/**
 * Initialize tab switching
 */
function initTabs() {
    const tabs = document.querySelectorAll('.profile-tab');
    const tabContents = document.querySelectorAll('.tab-content');

    if (tabs.length === 0) return;

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const targetTab = this.dataset.tab;

            // Update tab states
            tabs.forEach(t => {
                t.classList.remove('active');
                // Hide indicator
                const indicator = t.querySelector('.tab-indicator');
                if (indicator) {
                    indicator.style.opacity = '0';
                }
            });

            // Activate clicked tab
            this.classList.add('active');
            const activeIndicator = this.querySelector('.tab-indicator');
            if (activeIndicator) {
                activeIndicator.style.opacity = '1';
            }

            // Update content visibility
            tabContents.forEach(content => {
                content.classList.add('hidden');
            });

            const targetContent = document.getElementById(`${targetTab}-tab`);
            if (targetContent) {
                targetContent.classList.remove('hidden');
            }
        });
    });
}

/**
 * Initialize follow button
 */
function initFollowButton() {
    const followBtn = document.getElementById('follow-btn');

    if (!followBtn) return;

    followBtn.addEventListener('click', async function(e) {
        e.preventDefault();

        const userId = this.dataset.userId;
        const isFollowing = this.dataset.following === 'true';
        const icon = document.getElementById('follow-icon');
        const text = document.getElementById('follow-text');
        const followerCountEl = document.getElementById('follower-count');

        // Disable button during request
        this.disabled = true;

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                              document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                              getCookie('csrftoken');

            const response = await fetch(`/monotal/user/${userId}/follow/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                // Update button state
                this.dataset.following = data.is_following ? 'true' : 'false';

                if (data.is_following) {
                    // Now following
                    this.classList.remove('bg-pink-600', 'text-white', 'hover:bg-pink-700');
                    this.classList.add('bg-zinc-100', 'text-zinc-700', 'border', 'border-zinc-300', 'hover:bg-red-50', 'hover:text-red-600', 'hover:border-red-200');
                    icon.setAttribute('data-icon', 'lucide:user-check');
                    text.textContent = 'フォロー中';
                } else {
                    // Unfollowed
                    this.classList.remove('bg-zinc-100', 'text-zinc-700', 'border', 'border-zinc-300', 'hover:bg-red-50', 'hover:text-red-600', 'hover:border-red-200');
                    this.classList.add('bg-pink-600', 'text-white', 'hover:bg-pink-700');
                    icon.setAttribute('data-icon', 'lucide:user-plus');
                    text.textContent = 'フォローする';
                }

                // Update follower count
                if (followerCountEl) {
                    followerCountEl.textContent = data.follower_count;
                }
            } else {
                alert(data.error || 'エラーが発生しました');
            }
        } catch (error) {
            console.error('Follow error:', error);
            alert('エラーが発生しました');
        } finally {
            this.disabled = false;
        }
    });
}

/**
 * Get cookie value by name
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
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
