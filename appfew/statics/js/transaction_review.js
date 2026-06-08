/**
 * 取引レビュー画面 JavaScript
 */

const ReviewPage = {
    selectedScore: 0,
    ratingLabels: {
        1: '不満',
        2: 'やや不満',
        3: '普通',
        4: '良い',
        5: 'とても良い'
    },

    init() {
        this.initStarRating();
        this.initCharCount();
        this.initForm();
    },

    /**
     * 星評価の初期化
     */
    initStarRating() {
        const stars = document.querySelectorAll('.star-btn');

        stars.forEach(star => {
            star.addEventListener('click', () => {
                this.selectedScore = parseInt(star.dataset.value);
                document.getElementById('reviewScore').value = this.selectedScore;
                this.updateStars();
                this.updateSubmitBtn();
            });

            star.addEventListener('mouseenter', () => {
                const hoverValue = parseInt(star.dataset.value);
                this.highlightStars(hoverValue);
            });

            star.addEventListener('mouseleave', () => {
                this.updateStars();
            });
        });
    },

    /**
     * 星のハイライト表示（ホバー時）
     */
    highlightStars(value) {
        const stars = document.querySelectorAll('.star-btn');
        const label = document.getElementById('ratingLabel');

        stars.forEach(star => {
            const starValue = parseInt(star.dataset.value);
            star.classList.toggle('hover', starValue <= value);
            star.classList.remove('active');
        });

        label.textContent = this.ratingLabels[value] || '';
    },

    /**
     * 星の選択状態を更新
     */
    updateStars() {
        const stars = document.querySelectorAll('.star-btn');
        const label = document.getElementById('ratingLabel');

        stars.forEach(star => {
            const starValue = parseInt(star.dataset.value);
            star.classList.remove('hover');
            star.classList.toggle('active', starValue <= this.selectedScore);
        });

        label.textContent = this.selectedScore > 0 ? this.ratingLabels[this.selectedScore] : '';
    },

    /**
     * 文字数カウント
     */
    initCharCount() {
        const textarea = document.getElementById('reviewContent');
        const counter = document.getElementById('charCount');

        if (!textarea || !counter) return;

        textarea.addEventListener('input', () => {
            counter.textContent = textarea.value.length;
        });
    },

    /**
     * 送信ボタンの状態を更新
     */
    updateSubmitBtn() {
        const btn = document.getElementById('submitBtn');
        btn.disabled = this.selectedScore === 0;
    },

    /**
     * フォーム送信
     */
    initForm() {
        const form = document.getElementById('reviewForm');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (this.selectedScore === 0) {
                await showAlert('評価を選択してください');
                return;
            }

            if (!await showConfirm('この評価を送信しますか？\n送信後は変更できません。')) return;

            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="iconify animate-spin" data-icon="lucide:loader-2" data-width="18"></span> 送信中...';

            try {
                const response = await fetch(`/monotal/transaction/${RENTAL_HISTORY_ID}/review/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': CSRF_TOKEN,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        review_score: this.selectedScore,
                        review_content: document.getElementById('reviewContent').value
                    })
                });

                const data = await response.json();

                if (data.success) {
                    await showAlert(data.message);
                    window.location.href = `/monotal/transaction/${RENTAL_HISTORY_ID}/`;
                } else {
                    showAlert(data.message || '評価の送信に失敗しました');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<span class="iconify" data-icon="lucide:send" data-width="18"></span> 評価を送信する';
                }
            } catch (error) {
                console.error('評価の送信に失敗しました:', error);
                showAlert('評価の送信に失敗しました');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span class="iconify" data-icon="lucide:send" data-width="18"></span> 評価を送信する';
            }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    ReviewPage.init();
});
