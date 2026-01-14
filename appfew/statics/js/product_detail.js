// Product Detail Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Image gallery functionality
    initImageGallery();

    // Rental period selection and calculation
    initRentalPeriodSelector();

    // Like button functionality
    initLikeButton();

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

    thumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener('click', function() {
            // Remove active class from all thumbnails
            thumbnails.forEach(t => {
                t.classList.remove('ring-2', 'ring-pink-600', 'ring-offset-2');
                t.classList.add('bg-zinc-100', 'border', 'border-zinc-200');
            });

            // Add active class to clicked thumbnail
            this.classList.remove('bg-zinc-100', 'border', 'border-zinc-200');
            this.classList.add('ring-2', 'ring-pink-600', 'ring-offset-2');

            // Update main image
            const newImageSrc = this.querySelector('img').src;
            if (newImageSrc) {
                mainImage.src = newImageSrc;
            }
        });
    });
}

/**
 * Initialize rental period selector with buttons
 */
function initRentalPeriodSelector() {
    const periodBtns = document.querySelectorAll('.period-select-btn');
    const startDateInput = document.getElementById('startDate');
    const returnDateText = document.getElementById('returnDateText');
    const rentalDaysDisplay = document.getElementById('rentalDays');
    const totalPriceValue = document.getElementById('totalPriceValue');
    const dailyRate = parseInt(document.getElementById('dailyRate')?.dataset.rate || '0');

    let selectedDays = null;

    // Set today as default start date
    const today = new Date();
    startDateInput.value = formatDateForInput(today);
    startDateInput.min = formatDateForInput(today); // Prevent past dates

    // Period button selection
    periodBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            periodBtns.forEach(b => {
                b.classList.remove('bg-pink-600', 'text-white', 'border-pink-600');
                b.classList.add('bg-white', 'text-zinc-700', 'border-zinc-200');
            });

            // Add active class to selected button
            this.classList.remove('bg-white', 'text-zinc-700', 'border-zinc-200');
            this.classList.add('bg-pink-600', 'text-white', 'border-pink-600');

            // Store selected days
            selectedDays = parseInt(this.dataset.days);

            // Calculate return date
            calculateReturnDate();
        });
    });

    // Start date change
    startDateInput.addEventListener('change', function() {
        if (selectedDays) {
            calculateReturnDate();
        }
    });

    function calculateReturnDate() {
        if (!selectedDays || !startDateInput.value) {
            returnDateText.textContent = '期間を選択してください';
            rentalDaysDisplay.textContent = '--';
            totalPriceValue.textContent = dailyRate.toLocaleString();
            return;
        }

        const startDate = new Date(startDateInput.value);
        const returnDate = new Date(startDate);
        returnDate.setDate(returnDate.getDate() + selectedDays);

        // Update return date display
        returnDateText.textContent = formatDateForDisplay(returnDate);

        // Update rental days display
        rentalDaysDisplay.textContent = `${selectedDays}日間`;

        // Update total price
        const totalPrice = dailyRate * selectedDays;
        totalPriceValue.textContent = totalPrice.toLocaleString();
    }

    function formatDateForInput(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    function formatDateForDisplay(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}/${month}/${day}`;
    }
}

/**
 * Initialize like/favorite button
 */
function initLikeButton() {
    const likeBtn = document.getElementById('likeBtn');

    if (!likeBtn) return;

    likeBtn.addEventListener('click', function(e) {
        e.preventDefault();

        const icon = this.querySelector('.iconify');
        const count = this.querySelector('.like-count');

        if (icon.classList.contains('text-zinc-400')) {
            // Like
            icon.classList.remove('text-zinc-400');
            icon.classList.add('text-pink-600');
            icon.setAttribute('data-icon', 'lucide:heart-filled');

            if (count) {
                const currentCount = parseInt(count.textContent);
                count.textContent = currentCount + 1;
            }
        } else {
            // Unlike
            icon.classList.remove('text-pink-600');
            icon.classList.add('text-zinc-400');
            icon.setAttribute('data-icon', 'lucide:heart');

            if (count) {
                const currentCount = parseInt(count.textContent);
                count.textContent = Math.max(0, currentCount - 1);
            }
        }
    });
}

/**
 * Initialize comment section
 */
function initCommentSection() {
    const commentInput = document.getElementById('commentInput');
    const commentBtn = document.getElementById('commentBtn');

    if (!commentInput || !commentBtn) return;

    // Enable/disable comment button based on input
    commentInput.addEventListener('input', function() {
        if (this.value.trim().length > 0) {
            commentBtn.classList.remove('bg-zinc-300', 'text-zinc-500', 'cursor-not-allowed');
            commentBtn.classList.add('bg-pink-600', 'text-white', 'hover:bg-pink-700', 'cursor-pointer');
            commentBtn.disabled = false;
        } else {
            commentBtn.classList.add('bg-zinc-300', 'text-zinc-500', 'cursor-not-allowed');
            commentBtn.classList.remove('bg-pink-600', 'text-white', 'hover:bg-pink-700', 'cursor-pointer');
            commentBtn.disabled = true;
        }
    });

    // Submit comment (placeholder - would need backend integration)
    commentBtn.addEventListener('click', function(e) {
        e.preventDefault();

        if (commentInput.value.trim().length > 0) {
            // Here you would send the comment to the backend
            console.log('Comment submitted:', commentInput.value);

            // Clear input
            commentInput.value = '';
            commentInput.dispatchEvent(new Event('input'));

            // Show success message (placeholder)
            alert('コメントを送信しました');
        }
    });
}
