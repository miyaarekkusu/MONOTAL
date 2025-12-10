document.addEventListener('DOMContentLoaded', function () {
    const planSelectBtns = document.querySelectorAll('.plan-select-btn');
    const selectedPlanInfo = document.getElementById('selectedPlanInfo');
    const selectedPlanName = document.getElementById('selectedPlanName');
    const selectedPlanPrice = document.getElementById('selectedPlanPrice');
    const applyBtn = document.getElementById('applyBtn');
    const faqQuestions = document.querySelectorAll('.faq-question');

    let selectedPlan = null;

    // プラン情報の定義
    const planData = {
        basic: {
            name: 'ベーシックプラン',
            price: 'レンタル料金の5%（最低100円）',
            description: '〜30,000円の商品対象'
        },
        standard: {
            name: 'スタンダードプラン',
            price: 'レンタル料金の8%（最低200円）',
            description: '〜100,000円の商品対象'
        },
        premium: {
            name: 'プレミアムプラン',
            price: 'レンタル料金の12%（最低500円）',
            description: 'すべての商品対象'
        }
    };

    // プラン選択ボタンのイベント処理
    planSelectBtns.forEach(btn => {
        btn.addEventListener('click', function () {
            const planType = this.getAttribute('data-plan');

            // 他のボタンの選択状態をリセット
            planSelectBtns.forEach(b => {
                b.classList.remove('selected');
                b.textContent = 'このプランを選択';
            });

            // 選択されたボタンの状態を更新
            this.classList.add('selected');
            this.textContent = '選択済み';

            // 選択されたプラン情報を更新
            selectedPlan = planType;
            updateSelectedPlanInfo(planType);

            // 申し込みボタンを有効化
            applyBtn.disabled = false;
        });
    });

    // 選択されたプラン情報を表示する関数
    function updateSelectedPlanInfo(planType) {
        const plan = planData[planType];
        if (plan) {
            selectedPlanName.textContent = plan.name;
            selectedPlanPrice.textContent = plan.price;
            selectedPlanInfo.style.display = 'block';

            // スムーズにスクロール
            selectedPlanInfo.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        }
    }

    // FAQ のアコーディオン機能
    faqQuestions.forEach(question => {
        question.addEventListener('click', function () {
            const faqId = this.getAttribute('data-faq');
            const answer = document.getElementById(`faq-${faqId}`);
            const isOpen = answer.classList.contains('open');

            // 他のFAQを閉じる
            document.querySelectorAll('.faq-answer').forEach(ans => {
                ans.classList.remove('open');
            });
            document.querySelectorAll('.faq-question').forEach(q => {
                q.classList.remove('active');
            });

            // クリックされたFAQの状態を切り替え
            if (!isOpen) {
                answer.classList.add('open');
                this.classList.add('active');
            }
        });
    });

    // 申し込みボタンのクリック処理
    applyBtn.addEventListener('click', function () {
        if (selectedPlan) {
            const plan = planData[selectedPlan];

            // 確認ダイアログ
            const confirmMessage = `${plan.name}（${plan.price}）に申し込みますか？\n\n申し込み後、レンタル料金と合わせて保険料が請求されます。`;

            if (confirm(confirmMessage)) {
                // 実際のAPI呼び出しを行う場合
                submitInsuranceApplication(selectedPlan);
            }
        }
    });

    // 保険申し込みの送信処理
    function submitInsuranceApplication(planType) {
        // ローディング状態にする
        applyBtn.disabled = true;
        applyBtn.textContent = '申し込み中...';

        // 申し込みデータを準備
        const applicationData = {
            planType: planType,
            planName: planData[planType].name,
            planPrice: planData[planType].price,
            timestamp: new Date().toISOString()
        };

        // 実際のAPI送信をシミュレート
        setTimeout(() => {
            // 成功時の処理
            alert(`${planData[planType].name}への申し込みが完了しました。\n\n保険証券は登録メールアドレスに送付いたします。`);

            // ボタンの状態をリセット
            applyBtn.textContent = '申し込み完了';
            applyBtn.style.backgroundColor = '#28a745';

            console.log('保険申し込みデータ:', applicationData);

            // 実際のAPI送信処理（コメントアウト状態）
            /*
            fetch('/api/insurance/apply', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(applicationData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(`${planData[planType].name}への申し込みが完了しました。\n\n保険証券は登録メールアドレスに送付いたします。`);
                    applyBtn.textContent = '申し込み完了';
                    applyBtn.style.backgroundColor = '#28a745';
                } else {
                    throw new Error(data.message || '申し込みに失敗しました');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('申し込み処理中にエラーが発生しました。もう一度お試しください。');
                applyBtn.disabled = false;
                applyBtn.textContent = '保険に申し込む';
            });
            */
        }, 2000);
    }

    // プラン比較のための視覚的効果
    function addPlanHoverEffects() {
        const planCards = document.querySelectorAll('.plan-card');

        planCards.forEach(card => {
            card.addEventListener('mouseenter', function () {
                // 他のカードを少し薄くする
                planCards.forEach(otherCard => {
                    if (otherCard !== this) {
                        otherCard.style.opacity = '0.7';
                    }
                });
            });

            card.addEventListener('mouseleave', function () {
                // 全てのカードの透明度を元に戻す
                planCards.forEach(otherCard => {
                    otherCard.style.opacity = '1';
                });
            });
        });
    }

    // スムーススクロール機能
    function addSmoothScrolling() {
        const links = document.querySelectorAll('a[href^="#"]');

        links.forEach(link => {
            link.addEventListener('click', function (e) {
                e.preventDefault();
                const targetId = this.getAttribute('href').substring(1);
                const targetElement = document.getElementById(targetId);

                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    // プラン料金計算機能（将来的な拡張用）
    function calculateInsuranceFee(rentalPrice, planType) {
        const rates = {
            basic: 0.05,
            standard: 0.08,
            premium: 0.12
        };

        const minimums = {
            basic: 100,
            standard: 200,
            premium: 500
        };

        const calculatedFee = rentalPrice * rates[planType];
        return Math.max(calculatedFee, minimums[planType]);
    }

    // ページ読み込み時の初期化処理
    function initializePage() {
        // プランホバー効果を追加
        addPlanHoverEffects();

        // スムーススクロールを追加
        addSmoothScrolling();

        // おすすめプランをハイライト
        const recommendedCard = document.querySelector('.plan-card.recommended');
        if (recommendedCard) {
            setTimeout(() => {
                recommendedCard.style.animation = 'pulse 2s ease-in-out';
            }, 1000);
        }
    }

    // 初期化を実行
    initializePage();
});