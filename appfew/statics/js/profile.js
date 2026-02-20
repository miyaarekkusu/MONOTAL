// Profile Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab switching functionality
    initTabs();

    // Follow button functionality
    initFollowButton();

    // Listing notification bell
    initListingNotificationButton();

    // More menu (three-dot menu)
    initMoreMenu();

    // Block button functionality
    initBlockButton();

    // Report button functionality
    initReportButton();

    // Share button functionality
    initShareButton();

    // Load more button
    initLoadMoreButton();

    // Review sort functionality
    initReviewSort();

    // Product filter & sort functionality
    initProductFilter();

    // URLハッシュによるタブ自動選択
    if (window.location.hash === '#reviews') {
        const reviewsTab = document.querySelector('.profile-tab[data-tab="reviews"]');
        if (reviewsTab) reviewsTab.click();
    }
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
                showAlert(data.error || 'エラーが発生しました');
            }
        } catch (error) {
            console.error('Follow error:', error);
            showAlert('エラーが発生しました');
        } finally {
            this.disabled = false;
        }
    });
}

/**
 * Initialize listing notification bell button
 */
function initListingNotificationButton() {
    const btn = document.getElementById('listing-notify-btn');
    if (!btn) return;

    btn.addEventListener('click', async function(e) {
        e.preventDefault();

        const userId = this.dataset.userId;
        const icon = document.getElementById('listing-notify-icon');

        this.disabled = true;

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                              document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                              getCookie('csrftoken');

            const response = await fetch(`/monotal/user/${userId}/listing-notification/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.dataset.subscribed = data.is_subscribed ? 'true' : 'false';

                if (data.is_subscribed) {
                    this.classList.remove('border-zinc-300', 'bg-white', 'text-zinc-400', 'hover:bg-zinc-50');
                    this.classList.add('border-pink-300', 'bg-pink-50', 'text-pink-600', 'hover:bg-pink-100');
                    icon.setAttribute('data-icon', 'lucide:bell-ring');
                } else {
                    this.classList.remove('border-pink-300', 'bg-pink-50', 'text-pink-600', 'hover:bg-pink-100');
                    this.classList.add('border-zinc-300', 'bg-white', 'text-zinc-400', 'hover:bg-zinc-50');
                    icon.setAttribute('data-icon', 'lucide:bell');
                }
            } else {
                showAlert(data.error || 'エラーが発生しました');
            }
        } catch (error) {
            console.error('Listing notification error:', error);
            showAlert('エラーが発生しました');
        } finally {
            this.disabled = false;
        }
    });
}

/**
 * Initialize more menu (three-dot menu)
 */
function initMoreMenu() {
    const menuBtn = document.getElementById('more-menu-btn');
    const dropdown = document.getElementById('more-menu-dropdown');

    if (!menuBtn || !dropdown) return;

    menuBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdown.classList.toggle('hidden');
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!menuBtn.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
}

/**
 * Initialize block button
 */
function initBlockButton() {
    const blockBtn = document.getElementById('block-btn');

    if (!blockBtn) return;

    blockBtn.addEventListener('click', async function(e) {
        e.preventDefault();

        const userId = this.dataset.userId;
        const isBlocked = this.dataset.blocked === 'true';
        const icon = document.getElementById('block-icon');
        const text = document.getElementById('block-text');
        const followBtn = document.getElementById('follow-btn');
        const listingNotifyBtn = document.getElementById('listing-notify-btn');
        const followerCountEl = document.getElementById('follower-count');
        const dropdown = document.getElementById('more-menu-dropdown');
        const blockNotice = document.getElementById('block-notice');

        // Confirm action
        const confirmMsg = isBlocked
            ? 'このユーザーのブロックを解除しますか？'
            : 'このユーザーをブロックしますか？\nブロックすると、お互いのフォローが解除されます。';
        if (!await showConfirm(confirmMsg)) return;

        // Disable button during request
        this.disabled = true;

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                              document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                              getCookie('csrftoken');

            const response = await fetch(`/monotal/user/${userId}/block/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                this.dataset.blocked = data.is_blocked ? 'true' : 'false';

                if (data.is_blocked) {
                    // Blocked: hide follow button, show notice, update menu text
                    icon.setAttribute('data-icon', 'lucide:user-check');
                    text.textContent = 'ブロック解除';
                    if (followBtn) followBtn.style.display = 'none';
                    if (listingNotifyBtn) listingNotifyBtn.style.display = 'none';
                    if (blockNotice) blockNotice.style.display = 'flex';
                } else {
                    // Unblocked: show follow button, hide notice, update menu text
                    icon.setAttribute('data-icon', 'lucide:ban');
                    text.textContent = 'ブロックする';
                    if (blockNotice) blockNotice.style.display = 'none';
                    if (listingNotifyBtn) {
                        listingNotifyBtn.style.display = 'flex';
                        // Reset to unsubscribed state
                        listingNotifyBtn.dataset.subscribed = 'false';
                        listingNotifyBtn.classList.remove('border-pink-300', 'bg-pink-50', 'text-pink-600', 'hover:bg-pink-100');
                        listingNotifyBtn.classList.add('border-zinc-300', 'bg-white', 'text-zinc-400', 'hover:bg-zinc-50');
                        const notifyIcon = document.getElementById('listing-notify-icon');
                        if (notifyIcon) notifyIcon.setAttribute('data-icon', 'lucide:bell');
                    }
                    if (followBtn) {
                        followBtn.style.display = 'flex';
                        // Reset follow button to "not following" state
                        followBtn.dataset.following = 'false';
                        followBtn.classList.remove('bg-zinc-100', 'text-zinc-700', 'border', 'border-zinc-300', 'hover:bg-red-50', 'hover:text-red-600', 'hover:border-red-200');
                        followBtn.classList.add('bg-pink-600', 'text-white', 'hover:bg-pink-700');
                        const followIcon = document.getElementById('follow-icon');
                        const followText = document.getElementById('follow-text');
                        if (followIcon) followIcon.setAttribute('data-icon', 'lucide:user-plus');
                        if (followText) followText.textContent = 'フォローする';
                    }
                }

                // Update follower count
                if (followerCountEl) {
                    followerCountEl.textContent = data.follower_count;
                }

                // Close dropdown
                if (dropdown) dropdown.classList.add('hidden');
            } else {
                showAlert(data.error || 'エラーが発生しました');
            }
        } catch (error) {
            console.error('Block error:', error);
            showAlert('エラーが発生しました');
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
                showAlert('URLをコピーしました');
            });
        }
    });
}

/**
 * Initialize review sort select
 */
function initReviewSort() {
    const sortSelect = document.getElementById('review-sort-select');
    if (!sortSelect) return;

    sortSelect.addEventListener('change', function() {
        const url = new URL(window.location.href);
        url.searchParams.set('sort', this.value);
        url.hash = 'reviews';
        window.location.href = url.toString();
    });
}

/**
 * Initialize product filter & sort selects
 */
function initProductFilter() {
    const statusSelect = document.getElementById('product-status-select');
    const sortSelect = document.getElementById('product-sort-select');

    function applyProductFilter() {
        const url = new URL(window.location.href);
        if (statusSelect) {
            if (statusSelect.value === 'all') {
                url.searchParams.delete('status');
            } else {
                url.searchParams.set('status', statusSelect.value);
            }
        }
        if (sortSelect) {
            if (sortSelect.value === '-register_datetime') {
                url.searchParams.delete('product_sort');
            } else {
                url.searchParams.set('product_sort', sortSelect.value);
            }
        }
        window.location.href = url.toString();
    }

    if (statusSelect) statusSelect.addEventListener('change', applyProductFilter);
    if (sortSelect) sortSelect.addEventListener('change', applyProductFilter);
}

/**
 * Initialize report button and modal
 */
function initReportButton() {
    const reportBtn = document.getElementById('report-btn');
    const reportModal = document.getElementById('report-modal');
    const reportForm = document.getElementById('report-form');
    const reportCloseBtn = document.getElementById('report-modal-close');
    const reportCancelBtn = document.getElementById('report-cancel-btn');
    const reportReason = document.getElementById('report-reason');
    const reportDetail = document.getElementById('report-detail');
    const reportDetailCount = document.getElementById('report-detail-count');
    const reportSubmitBtn = document.getElementById('report-submit-btn');

    if (!reportBtn || !reportModal) return;

    // Open modal
    reportBtn.addEventListener('click', function(e) {
        e.preventDefault();
        // Close dropdown menu
        const dropdown = document.getElementById('more-menu-dropdown');
        if (dropdown) dropdown.classList.add('hidden');
        // Show modal
        reportModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    });

    // Close modal functions
    function closeReportModal() {
        reportModal.classList.add('hidden');
        document.body.style.overflow = '';
        // Reset form
        if (reportForm) reportForm.reset();
        if (reportDetailCount) reportDetailCount.textContent = '0';
        if (reportSubmitBtn) reportSubmitBtn.disabled = true;
    }

    if (reportCloseBtn) reportCloseBtn.addEventListener('click', closeReportModal);
    if (reportCancelBtn) reportCancelBtn.addEventListener('click', closeReportModal);

    // Close on overlay click
    reportModal.addEventListener('click', function(e) {
        if (e.target === reportModal) closeReportModal();
    });

    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && !reportModal.classList.contains('hidden')) {
            closeReportModal();
        }
    });

    // Enable/disable submit button based on reason selection
    if (reportReason) {
        reportReason.addEventListener('change', function() {
            if (reportSubmitBtn) reportSubmitBtn.disabled = !this.value;
        });
    }

    // Character count for detail textarea
    if (reportDetail && reportDetailCount) {
        reportDetail.addEventListener('input', function() {
            reportDetailCount.textContent = this.value.length;
        });
    }

    // Submit report
    if (reportForm) {
        reportForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const userId = reportBtn.dataset.userId;
            const reasonId = reportReason ? reportReason.value : '';
            const detail = reportDetail ? reportDetail.value : '';

            if (!reasonId) {
                showAlert('通報理由を選択してください');
                return;
            }

            if (reportSubmitBtn) reportSubmitBtn.disabled = true;

            try {
                const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                                  document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                                  getCookie('csrftoken');

                const response = await fetch(`/monotal/user/${userId}/report/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: JSON.stringify({
                        report_reason_id: parseInt(reasonId),
                        report_detail: detail
                    })
                });

                const data = await response.json();

                if (data.success) {
                    closeReportModal();
                    await showAlert('通報を受け付けました。ご報告ありがとうございます。');
                } else {
                    showAlert(data.error || 'エラーが発生しました');
                    if (reportSubmitBtn) reportSubmitBtn.disabled = !reasonId;
                }
            } catch (error) {
                console.error('Report error:', error);
                showAlert('エラーが発生しました');
                if (reportSubmitBtn) reportSubmitBtn.disabled = !reasonId;
            }
        });
    }
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
