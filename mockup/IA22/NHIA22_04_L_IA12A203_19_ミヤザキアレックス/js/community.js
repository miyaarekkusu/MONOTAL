// コミュニティページ JavaScript

document.addEventListener('DOMContentLoaded', function () {
    // DOM要素の取得
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const chatMessages = document.getElementById('chatMessages');
    const categoryItems = document.querySelectorAll('.category-item');
    const chatTitle = document.querySelector('.chat-title');
    const chatSubtitle = document.querySelector('.chat-subtitle');

    // 初期化
    init();

    function init() {
        // イベントリスナーの設定
        setupEventListeners();

        // 初期スクロール位置を最下部に設定
        scrollToBottom();
    }

    function setupEventListeners() {
        // チャット送信イベント
        chatForm.addEventListener('submit', handleChatSubmit);

        // テキストエリアの自動リサイズ
        messageInput.addEventListener('input', handleTextareaResize);

        // Enterキーでの送信（Shift+Enterで改行）
        messageInput.addEventListener('keydown', handleKeyDown);

        // カテゴリー切り替えイベント
        categoryItems.forEach(item => {
            item.addEventListener('click', () => handleCategoryChange(item));
        });
    }

    // チャット送信処理
    function handleChatSubmit(e) {
        e.preventDefault();

        const message = messageInput.value.trim();
        if (message) {
            addMessage(message, true);
            messageInput.value = '';
            resetTextareaHeight();
        }
    }

    // テキストエリアの自動リサイズ処理
    function handleTextareaResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
    }

    // テキストエリアの高さをリセット
    function resetTextareaHeight() {
        messageInput.style.height = 'auto';
    }

    // キーボードイベント処理
    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    }

    // カテゴリー変更処理
    function handleCategoryChange(selectedItem) {
        // アクティブ状態の更新
        categoryItems.forEach(item => item.classList.remove('active'));
        selectedItem.classList.add('active');

        // チャットヘッダーの更新
        const categoryName = selectedItem.querySelector('.category-name').textContent;
        const categoryDesc = selectedItem.querySelector('.category-desc').textContent;

        updateChatHeader(categoryName, categoryDesc);

        // チャット履歴をクリア（新しいカテゴリーなので）
        clearChatMessages();

        // サンプルメッセージを追加
        loadSampleMessages(selectedItem.dataset.category);
    }

    // チャットヘッダーの更新
    function updateChatHeader(categoryName, categoryDesc) {
        chatTitle.textContent = categoryName;
        chatSubtitle.textContent = categoryDesc + 'についての情報交換';
    }

    // チャットメッセージをクリア
    function clearChatMessages() {
        chatMessages.innerHTML = '';
    }

    // メッセージ追加処理
    function addMessage(text, isMyMessage = false) {
        const messageDiv = createMessageElement(text, isMyMessage);
        chatMessages.appendChild(messageDiv);
        scrollToBottom();

        // 自分のメッセージの場合、自動返信をシミュレート
        if (isMyMessage) {
            setTimeout(() => {
                simulateReply();
            }, 1000 + Math.random() * 2000);
        }
    }

    // メッセージ要素の作成
    function createMessageElement(text, isMyMessage) {
        const messageDiv = document.createElement('div');
        messageDiv.className = isMyMessage ? 'message my-message' : 'message';

        const timeString = getTimeString();
        const userName = isMyMessage ? 'あなた' : getRandomUserName();
        const avatar = isMyMessage ? 'あ' : getRandomAvatar();

        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-header">
                    <span class="message-user">${userName}</span>
                    <span class="message-time">${timeString}</span>
                </div>
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
        `;

        return messageDiv;
    }

    // 自動返信のシミュレーション
    function simulateReply() {
        const replies = [
            "参考になりました！ありがとうございます。",
            "私も同じような体験をしました。",
            "詳しい情報をありがとうございます。",
            "それは良いですね！今度試してみます。",