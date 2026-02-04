// Product Detail Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Image gallery functionality
    initImageGallery();

    // Rental plan selector
    initRentalPlanSelector();

    // Bookmark button functionality
    initBookmarkButton();

    // Comment functionality
    initCommentSection();
});

/**
 * Initialize image gallery thumbnail switching
 */
function initImageGallery() {
    const mainImage = document.getElementById('mainProductImage');
    const thumbnails = document.querySelectorAll('.thumbnail-btn');

    if (!mainImage || !thumbnails.length) return;

    thumbnails.forEach((thumbnail) => {
        thumbnail.addEventListener('click', function() {
            // Remove active class from all thumbnails
            thumbnails.forEach(t => t.classList.remove('active'));

            // Add active class to clicked thumbnail
            this.classList.add('active');

            // Update main image
            const newImageUrl = this.dataset.imageUrl;
            if (newImageUrl) {
                mainImage.src = newImageUrl;
            }
        });
    });
}

/**
 * Initialize rental plan selector
 */
function initRentalPlanSelector() {
    const planBtns = document.querySelectorAll('.rental-plan-btn');
    const rentalDaysDisplay = document.getElementById('rentalDays');
    const totalPriceValue = document.getElementById('totalPriceValue');
    const mobilePriceValue = document.getElementById('mobilePriceValue');
    const mobileDaysValue = document.getElementById('mobileDaysValue');

    let selectedDays = null;
    let selectedPrice = null;

    // Initialize with first plan if exists
    if (planBtns.length > 0) {
        const firstBtn = planBtns[0];
        selectedDays = parseInt(firstBtn.dataset.days);
        selectedPrice = parseInt(firstBtn.dataset.price);
        updateDisplay();
    }

    // Plan button selection
    planBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            planBtns.forEach(b => b.classList.remove('active'));

            // Add active class to selected button
            this.classList.add('active');

            // Store selected values
            selectedDays = parseInt(this.dataset.days);
            selectedPrice = parseInt(this.dataset.price);

            // Update display
            updateDisplay();
        });
    });

    function updateDisplay() {
        if (!selectedDays || !selectedPrice) {
            if (rentalDaysDisplay) rentalDaysDisplay.textContent = '--';
            if (totalPriceValue) totalPriceValue.textContent = '0';
            if (mobilePriceValue) mobilePriceValue.textContent = '¥0';
            if (mobileDaysValue) mobileDaysValue.textContent = '';
            return;
        }

        // Update rental days display
        if (rentalDaysDisplay) {
            rentalDaysDisplay.textContent = `${selectedDays}日間`;
        }

        // Update total price (using the plan price directly)
        if (totalPriceValue) {
            totalPriceValue.textContent = selectedPrice.toLocaleString();
        }

        // Update mobile display
        if (mobilePriceValue) {
            mobilePriceValue.textContent = `¥${selectedPrice.toLocaleString()}`;
        }
        if (mobileDaysValue) {
            mobileDaysValue.textContent = `（${selectedDays}日）`;
        }
    }
}

/**
 * Initialize bookmark button
 */
function initBookmarkButton() {
    const bookmarkBtn = document.getElementById('bookmarkBtn');

    if (!bookmarkBtn) return;

    // Get initial state from data attribute
    let isBookmarked = bookmarkBtn.dataset.bookmarked === 'true';
    const productId = bookmarkBtn.dataset.productId;

    // Set initial visual state
    updateBookmarkVisual(isBookmarked);

    bookmarkBtn.addEventListener('click', async function(e) {
        e.preventDefault();

        // Disable button during request
        this.disabled = true;

        try {
            const response = await fetch(`/monotal/product/${productId}/bookmark/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            });

            const data = await response.json();

            if (data.success) {
                isBookmarked = data.is_bookmarked;
                updateBookmarkVisual(isBookmarked);

                // Update count
                const countEl = document.getElementById('bookmarkCount');
                if (countEl) {
                    countEl.textContent = data.bookmark_count;
                }
            } else {
                // Show error message
                if (response.status === 401) {
                    alert('ブックマークするにはログインが必要です');
                } else {
                    alert(data.error || 'エラーが発生しました');
                }
            }
        } catch (error) {
            console.error('Bookmark error:', error);
            alert('通信エラーが発生しました');
        } finally {
            this.disabled = false;
        }
    });

    function updateBookmarkVisual(bookmarked) {
        const icon = bookmarkBtn.querySelector('.iconify');

        if (bookmarked) {
            bookmarkBtn.classList.add('liked');
            icon.style.fill = '#db2777';
            icon.style.color = '#db2777';
        } else {
            bookmarkBtn.classList.remove('liked');
            icon.style.fill = 'none';
            icon.style.color = '';
        }
    }
}

/**
 * Get CSRF token from cookie
 */
function getCSRFToken() {
    const name = 'csrftoken';
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
 * Initialize comment section
 */
function initCommentSection() {
    const commentsSection = document.querySelector('.comments-section');
    const commentInput = document.getElementById('commentInput');
    const commentBtn = document.getElementById('commentBtn');
    const commentList = document.getElementById('commentList');
    const commentLoading = document.getElementById('commentLoading');
    const commentCount = document.getElementById('commentCount');
    const commentCountMobile = document.getElementById('commentCountMobile');
    const mobileCommentBtn = document.getElementById('mobileCommentBtn');

    if (!commentsSection) return;

    const productId = commentsSection.dataset.productId;
    if (!productId) return;

    // 出品者かどうかを取得
    const isSeller = commentsSection.dataset.isSeller === 'true';

    // Load comments on page load
    loadComments();

    // Enable/disable comment button based on input
    if (commentInput && commentBtn) {
        commentInput.addEventListener('input', function() {
            commentBtn.disabled = this.value.trim().length === 0;
        });

        // Submit comment
        commentBtn.addEventListener('click', async function(e) {
            e.preventDefault();
            await submitComment();
        });

        // Enter key to submit (Shift+Enter for new line)
        commentInput.addEventListener('keydown', async function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                if (this.value.trim().length > 0) {
                    await submitComment();
                }
            }
        });
    }

    // Mobile comment button - scroll to comment section
    if (mobileCommentBtn) {
        mobileCommentBtn.addEventListener('click', function() {
            commentsSection.scrollIntoView({ behavior: 'smooth' });
            if (commentInput) {
                setTimeout(() => commentInput.focus(), 500);
            }
        });
    }

    // 削除ボタンのイベント委譲（出品者のみ）
    if (isSeller && commentList) {
        commentList.addEventListener('click', async function(e) {
            const deleteBtn = e.target.closest('.comment-delete-btn');
            if (!deleteBtn) return;

            const messageId = deleteBtn.dataset.messageId;
            if (!messageId) return;

            if (!confirm('このコメントを削除しますか？')) return;

            await deleteComment(messageId);
        });
    }

    async function deleteComment(messageId) {
        try {
            const response = await fetch(`/monotal/product/${productId}/messages/${messageId}/delete/`, {
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (data.success) {
                // コメントをDOMから削除
                const commentItem = commentList.querySelector(`.comment-item[data-message-id="${messageId}"]`);
                if (commentItem) {
                    commentItem.remove();
                }

                // コメント数を更新
                updateCommentCount(data.remaining_count);

                // コメントがなくなった場合
                if (data.remaining_count === 0) {
                    commentList.innerHTML = '<div class="comment-empty">まだコメントはありません</div>';
                }
            } else {
                alert(data.error || 'コメントの削除に失敗しました');
            }
        } catch (error) {
            console.error('Delete comment error:', error);
            alert('通信エラーが発生しました');
        }
    }

    async function loadComments() {
        try {
            const response = await fetch(`/monotal/product/${productId}/messages/`, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            const data = await response.json();

            if (commentLoading) {
                commentLoading.style.display = 'none';
            }

            if (data.success) {
                renderComments(data.messages);
                updateCommentCount(data.total_count);
            }
        } catch (error) {
            console.error('Load comments error:', error);
            if (commentLoading) {
                commentLoading.innerHTML = '<span class="comment-empty">コメントを読み込めませんでした</span>';
            }
        }
    }

    async function submitComment() {
        const content = commentInput.value.trim();
        if (!content) return;

        commentBtn.disabled = true;
        commentBtn.textContent = '送信中...';

        try {
            const response = await fetch(`/monotal/product/${productId}/messages/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCSRFToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: content })
            });

            const data = await response.json();

            if (data.success) {
                // Clear input
                commentInput.value = '';
                commentInput.dispatchEvent(new Event('input'));

                // Add new comment to list
                appendComment(data.message);

                // Update count
                const currentCount = parseInt(commentCount?.textContent || '0');
                updateCommentCount(currentCount + 1);
            } else {
                if (response.status === 401) {
                    alert('コメントするにはログインが必要です');
                } else {
                    alert(data.error || 'エラーが発生しました');
                }
            }
        } catch (error) {
            console.error('Submit comment error:', error);
            alert('通信エラーが発生しました');
        } finally {
            commentBtn.disabled = commentInput.value.trim().length === 0;
            commentBtn.textContent = 'コメントする';
        }
    }

    function renderComments(messages) {
        if (!commentList) return;

        if (messages.length === 0) {
            commentList.innerHTML = '<div class="comment-empty">まだコメントはありません</div>';
            return;
        }

        commentList.innerHTML = messages.map(msg => createCommentHTML(msg)).join('');
    }

    function appendComment(message) {
        if (!commentList) return;

        // Remove empty message if exists
        const emptyMsg = commentList.querySelector('.comment-empty');
        if (emptyMsg) {
            emptyMsg.remove();
        }

        commentList.insertAdjacentHTML('beforeend', createCommentHTML(message));

        // Scroll to new comment
        const newComment = commentList.lastElementChild;
        if (newComment) {
            newComment.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    function createCommentHTML(msg) {
        const avatarHTML = msg.user_image
            ? `<img src="${msg.user_image}" alt="${escapeHtml(msg.user_name)}">`
            : `<span class="iconify" data-icon="lucide:user" data-width="18"></span>`;

        const ownerBadge = msg.is_owner
            ? '<span class="comment-owner-badge">出品者</span>'
            : '';

        // 出品者のみ削除ボタンを表示
        const deleteBtn = isSeller
            ? `<button type="button" class="comment-delete-btn" data-message-id="${msg.message_id}" title="コメントを削除">
                   <span class="iconify" data-icon="lucide:trash-2" data-width="14"></span>
               </button>`
            : '';

        return `
            <div class="comment-item" data-message-id="${msg.message_id}">
                <div class="comment-avatar">
                    ${avatarHTML}
                </div>
                <div class="comment-body">
                    <div class="comment-header">
                        <span class="comment-author">${escapeHtml(msg.user_name)}</span>
                        ${ownerBadge}
                        <span class="comment-time">${msg.created_at}</span>
                        ${deleteBtn}
                    </div>
                    <div class="comment-content">${escapeHtml(msg.content)}</div>
                </div>
            </div>
        `;
    }

    function updateCommentCount(count) {
        if (commentCount) {
            commentCount.textContent = count;
        }
        if (commentCountMobile) {
            commentCountMobile.textContent = count;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
