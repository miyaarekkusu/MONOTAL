// MyPage JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initFollowToggleButtons();
    initBlockToggleButtons();
});

/**
 * Initialize follow toggle buttons on follow list page
 */
function initFollowToggleButtons() {
    const btns = document.querySelectorAll('.follow-toggle-btn');

    btns.forEach(btn => {
        const label = btn.querySelector('.btn-label');

        btn.addEventListener('mouseenter', function() {
            if (this.dataset.following === 'true') {
                label.textContent = '解除する';
                this.classList.remove('border-zinc-300', 'bg-white', 'text-zinc-600');
                this.classList.add('border-red-300', 'bg-red-50', 'text-red-600');
            }
        });

        btn.addEventListener('mouseleave', function() {
            updateFollowUI(this, label);
        });

        btn.addEventListener('click', async function(e) {
            e.preventDefault();

            const userId = this.dataset.userId;
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
                    this.dataset.following = data.is_following ? 'true' : 'false';
                    updateFollowUI(this, label);

                    const followerCountEl = this.parentElement.querySelector('.follower-count');
                    if (followerCountEl) {
                        followerCountEl.textContent = 'フォロワー ' + data.follower_count;
                    }
                } else {
                    showAlert(data.error || 'エラーが発生しました');
                }
            } catch (error) {
                console.error('Follow toggle error:', error);
                showAlert('エラーが発生しました');
            } finally {
                this.disabled = false;
            }
        });
    });
}

function updateFollowUI(btn, label) {
    if (btn.dataset.following === 'true') {
        label.textContent = 'フォロー中';
        btn.classList.remove('border-pink-600', 'bg-pink-600', 'text-white', 'border-red-300', 'bg-red-50', 'text-red-600');
        btn.classList.add('border-zinc-300', 'bg-white', 'text-zinc-600');
    } else {
        label.textContent = 'フォローする';
        btn.classList.remove('border-zinc-300', 'bg-white', 'text-zinc-600', 'border-red-300', 'bg-red-50', 'text-red-600');
        btn.classList.add('border-pink-600', 'bg-pink-600', 'text-white');
    }
}

/**
 * Initialize block toggle buttons on block list page
 */
function initBlockToggleButtons() {
    const btns = document.querySelectorAll('.block-toggle-btn');

    btns.forEach(btn => {
        const label = btn.querySelector('.btn-label');

        btn.addEventListener('mouseenter', function() {
            if (this.dataset.blocked === 'true') {
                label.textContent = '解除する';
                this.classList.remove('border-red-300', 'bg-red-50', 'text-red-600');
                this.classList.add('border-zinc-300', 'bg-zinc-100', 'text-zinc-600');
            }
        });

        btn.addEventListener('mouseleave', function() {
            updateBlockUI(this, label);
        });

        btn.addEventListener('click', async function(e) {
            e.preventDefault();

            const userId = this.dataset.userId;
            const isBlocked = this.dataset.blocked === 'true';

            if (isBlocked) {
                if (!await showConfirm('このユーザーのブロックを解除しますか？')) return;
            } else {
                if (!await showConfirm('このユーザーを再ブロックしますか？')) return;
            }

            this.disabled = true;

            try {
                const csrfToken = getCookie('csrftoken');

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
                    updateBlockUI(this, label);
                } else {
                    showAlert(data.error || 'エラーが発生しました');
                }
            } catch (error) {
                console.error('Block toggle error:', error);
                showAlert('エラーが発生しました');
            } finally {
                this.disabled = false;
            }
        });
    });
}

function updateBlockUI(btn, label) {
    if (btn.dataset.blocked === 'true') {
        label.textContent = 'ブロック中';
        btn.classList.remove('border-zinc-300', 'bg-zinc-100', 'text-zinc-600', 'border-zinc-900', 'bg-zinc-900', 'text-white');
        btn.classList.add('border-red-300', 'bg-red-50', 'text-red-600');
    } else {
        label.textContent = 'ブロックする';
        btn.classList.remove('border-red-300', 'bg-red-50', 'text-red-600', 'border-zinc-300', 'bg-zinc-100', 'text-zinc-600');
        btn.classList.add('border-zinc-900', 'bg-zinc-900', 'text-white');
    }
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
