// MyPage JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initUnfollowButtons();
});

/**
 * Initialize unfollow buttons on follow list page
 */
function initUnfollowButtons() {
    const unfollowBtns = document.querySelectorAll('.follow-unfollow-btn');

    unfollowBtns.forEach(btn => {
        btn.addEventListener('click', async function(e) {
            e.preventDefault();

            const userId = this.dataset.userId;
            const userCard = this.closest('.flex');

            // Disable button during request
            this.disabled = true;

            try {
                const csrfToken = getCookie('csrftoken');

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
                    if (!data.is_following) {
                        // User was unfollowed - remove from list with animation
                        userCard.style.transition = 'opacity 0.3s, transform 0.3s';
                        userCard.style.opacity = '0';
                        userCard.style.transform = 'translateX(20px)';

                        setTimeout(() => {
                            userCard.remove();

                            // Update count in header
                            const countBadge = document.querySelector('.text-xs.font-medium.text-zinc-500.bg-zinc-100');
                            if (countBadge) {
                                const currentCount = parseInt(countBadge.textContent.match(/\d+/)[0]);
                                countBadge.textContent = `${currentCount - 1}人をフォロー中`;
                            }

                            // Check if list is now empty
                            const userList = document.querySelector('.divide-y');
                            if (userList && userList.children.length === 0) {
                                userList.innerHTML = `
                                    <div class="p-8 text-center text-zinc-400">
                                        <span class="iconify mx-auto mb-4" data-icon="lucide:users" data-width="48"></span>
                                        <p class="text-sm">フォローしているユーザーがいません</p>
                                        <a href="/monotal/shop/" class="mt-4 inline-flex items-center gap-2 text-pink-600 hover:text-pink-700 text-sm font-medium">
                                            商品を探す
                                            <span class="iconify" data-icon="lucide:arrow-right" data-width="16"></span>
                                        </a>
                                    </div>
                                `;
                            }
                        }, 300);
                    }
                } else {
                    alert(data.error || 'エラーが発生しました');
                    this.disabled = false;
                }
            } catch (error) {
                console.error('Unfollow error:', error);
                alert('エラーが発生しました');
                this.disabled = false;
            }
        });
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
