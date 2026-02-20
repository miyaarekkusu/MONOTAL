// --- Community Page JavaScript ---

// --- Data Store ---
const MOCK_USER = {
    name: '自分',
    avatar: document.getElementById('community-data')?.dataset.userAvatar || ''
};

const QUESTIONS = []; // 互換性のため残す（未使用）
let QA_DATA = []; // サーバーから取得した質問リスト
// App State
const appState = {
    activeTab: 'boards',
    activeQAId: null,
    searchQuery: '',
    activeBoardId: null,
    activeBoardUrl: null,
    activeBoardJoinUrl: null,
    activeBoardLeaveUrl: null,
    boardUserProducts: [],
    boardMembers: [],
    pendingQAId: null,
};

// --- Helper: create icon span ---
function icon(name, size) {
    return `<span class="iconify" data-icon="${name}" data-width="${size || 20}"></span>`;
}

// --- Utility ---
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Force Iconify to scan new dynamic elements
function refreshIcons() {
    if (window.Iconify && typeof window.Iconify.scan === 'function') {
        window.Iconify.scan();
    }
}

// --- Core Functions ---

function handleSearchInput(value) {
    appState.searchQuery = value.toLowerCase();
    renderSidebar();
}

function switchTab(tab) {
    appState.activeTab = tab;
    if (tab === 'qa') {
        appState.activeQAId = null;
    }
    document.querySelectorAll('[data-community-tab]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.communityTab === tab);
    });

    const boardContent = document.getElementById('board-list-content');
    const sidebarList = document.getElementById('sidebar-list');
    const qaHeader = document.getElementById('qa-sidebar-header');

    if (tab === 'boards') {
        if (boardContent) boardContent.classList.remove('hidden');
        if (sidebarList) sidebarList.classList.add('hidden');
        if (qaHeader) qaHeader.classList.add('hidden');
        resetContentArea();
        resetHeaderDefault();
        renderSidebar();
    } else {
        if (boardContent) boardContent.classList.add('hidden');
        if (sidebarList) sidebarList.classList.remove('hidden');
        if (tab === 'qa') {
            if (qaHeader) qaHeader.classList.remove('hidden');
            resetContentArea();
            resetHeaderForQA();
            loadQAList();
        } else {
            if (qaHeader) qaHeader.classList.add('hidden');
            resetContentArea();
            resetHeaderDefault();
            renderSidebar();
        }
    }
}

function resetContentArea() {
    const container = document.getElementById('content-area');
    container.innerHTML = `
        <div class="community-empty-state">
            <div class="h-16 w-16 bg-zinc-100 rounded-full flex items-center justify-center mb-4">
                ${icon('lucide:layout-list', 32)}
            </div>
            <p class="text-sm font-medium">掲示板を選択してください</p>
        </div>`;
    // 投稿バーを非表示に
    const postBar = document.getElementById('board-post-bar');
    if (postBar) postBar.classList.add('hidden');
    // アクティブ掲示板をリセット
    appState.activeBoardId = null;
    appState.activeBoardUrl = null;
    // サイドバーのアクティブ状態をリセット
    document.querySelectorAll('[data-board-id]').forEach(el => el.classList.remove('bg-pink-50'));
    refreshIcons();
}

function resetHeaderDefault() {
    document.getElementById('header-icon').className = 'h-10 w-10 rounded-xl bg-zinc-100 text-zinc-400 flex items-center justify-center flex-shrink-0';
    document.getElementById('header-icon').innerHTML = icon('lucide:layout-list', 24);
    document.getElementById('header-title').innerHTML = '掲示板';
    document.getElementById('header-tag').innerText = '左のリストから掲示板を選択';
    const membersEl = document.getElementById('header-members');
    if (membersEl) { membersEl.innerText = ''; membersEl.classList.add('hidden'); }
    const btn = document.getElementById('join-btn');
    btn.classList.add('hidden');
    btn.classList.remove('flex');
    btn.disabled = false;
    btn.onclick = null;
    const membersBtn = document.getElementById('members-btn');
    if (membersBtn) { membersBtn.classList.add('hidden'); membersBtn.classList.remove('flex'); }
    appState.boardMembers = [];
    refreshIcons();
}

function resetHeaderForQA() {
    document.getElementById('header-icon').className = 'h-10 w-10 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center flex-shrink-0 border border-pink-100';
    document.getElementById('header-icon').innerHTML = icon('solar:question-circle-bold', 24);
    document.getElementById('header-title').innerHTML = 'Q&A';
    document.getElementById('header-tag').innerText = '質問を選択';
    const membersEl = document.getElementById('header-members');
    if (membersEl) { membersEl.innerText = ''; membersEl.classList.add('hidden'); }
    const btn = document.getElementById('join-btn');
    btn.classList.add('hidden');
    btn.classList.remove('flex');
    refreshIcons();
}

function toggleMobileView(showContent) {
    const sidebar = document.getElementById('community-sidebar');
    const mainView = document.getElementById('community-main');
    const backBtn = document.getElementById('mobile-back');
    if (window.innerWidth < 768) {
        if (showContent) {
            sidebar.style.transform = 'translateX(-100%)';
            mainView.style.transform = 'translateX(0)';
            if (backBtn) backBtn.classList.remove('hidden');
        } else {
            sidebar.style.transform = 'translateX(0)';
            mainView.style.transform = 'translateX(100%)';
            if (backBtn) backBtn.classList.add('hidden');
        }
    }
}

// --- Sidebar Rendering ---

function renderSidebar() {
    const list = document.getElementById('sidebar-list');
    list.innerHTML = '';

    if (appState.activeTab === 'boards') {
        return;
    }

    if (appState.activeTab === 'qa') {
        renderQAList(list);
        refreshIcons();
        return;
    }

}

// --- Q&A: Load List ---

async function loadQAList() {
    const list = document.getElementById('sidebar-list');
    if (!list) return;
    list.innerHTML = `<div class="flex justify-center py-8"><div class="h-6 w-6 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;
    try {
        const res = await fetch(QA_LIST_URL, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const data = await res.json();
        QA_DATA = data.questions || [];
        renderQAList(list);
        if (appState.pendingQAId) {
            const pendingId = appState.pendingQAId;
            appState.pendingQAId = null;
            selectQA(pendingId);
        }
    } catch (e) {
        list.innerHTML = `<p class="text-xs text-red-400 text-center py-8">読み込みエラー</p>`;
    }
}

// --- Q&A Sidebar ---

function renderQAList(list) {
    const filtered = QA_DATA.filter(q => q.title.toLowerCase().includes(appState.searchQuery));

    if (filtered.length === 0) {
        list.innerHTML = `
            <div class="flex flex-col items-center justify-center py-16 text-zinc-400">
                <div class="h-14 w-14 bg-zinc-100 rounded-full flex items-center justify-center mb-3">
                    ${icon('solar:question-circle-linear', 28)}
                </div>
                <p class="text-sm font-medium text-zinc-500 mb-1">質問はまだありません</p>
                <p class="text-xs text-zinc-400">最初の質問を投稿してみましょう</p>
            </div>
        `;
        return;
    }

    list.innerHTML = '';
    filtered.forEach(q => {
        const isActive = appState.activeQAId === q.id;
        const statusId = q.status_id;
        const statusClass = statusId === 2 ? 'status-badge-solved' : statusId === 3 ? 'status-badge-expired' : 'status-badge-open';
        const statusText = statusId === 2 ? '解決済' : statusId === 3 ? '期限切れ' : '受付中';

        const item = document.createElement('div');
        item.className = `p-3 cursor-pointer transition-all flex flex-col gap-2 border-b border-zinc-100 ${isActive ? 'bg-pink-50' : 'hover:bg-zinc-50'}`;
        item.onclick = () => selectQA(q.id);
        item.innerHTML = `
            <div class="flex justify-between items-start gap-2">
                <div class="flex items-center gap-2 flex-wrap">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-full ${statusClass}">${statusText}</span>
                    ${q.category ? `<span class="text-[10px] text-zinc-500">${escapeHtml(q.category)}</span>` : ''}
                </div>
                <span class="text-[10px] text-zinc-400 flex-shrink-0">${escapeHtml(q.created_at)}</span>
            </div>
            <h3 class="text-sm font-bold text-zinc-900 line-clamp-2 leading-snug">
                <span class="text-pink-500 mr-1">Q.</span>${escapeHtml(q.title)}
            </h3>
            <span class="text-[10px] text-zinc-400">${q.answer_count}件の回答</span>
        `;
        list.appendChild(item);
    });
}

// --- Toast ---

function showToast(message, toastIcon, colorClass) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'bg-white border border-zinc-200 shadow-xl rounded-xl p-4 flex items-center gap-3 animate-slide-in min-w-[280px] pointer-events-auto';
    toast.innerHTML = `
        <div class="h-8 w-8 bg-zinc-50 rounded-full flex items-center justify-center flex-shrink-0 ${colorClass}">
            ${icon(toastIcon, 18)}
        </div>
        <p class="text-sm font-semibold text-zinc-900">${escapeHtml(message)}</p>
    `;
    container.appendChild(toast);
    refreshIcons();
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// --- Q&A Detail ---

function selectQA(qId) {
    appState.activeQAId = qId;
    toggleMobileView(true);
    renderSidebar();
    loadQADetail(qId);
}

async function loadQADetail(qId) {
    const container = document.getElementById('content-area');
    container.innerHTML = `<div class="community-empty-state"><div class="h-8 w-8 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;
    const postBar = document.getElementById('board-post-bar');
    if (postBar) postBar.classList.add('hidden');
    const joinBtn = document.getElementById('join-btn');
    if (joinBtn) { joinBtn.classList.add('hidden'); joinBtn.classList.remove('flex'); }

    const url = QA_DETAIL_URL_BASE.replace('/0/', `/${qId}/`);
    try {
        const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const data = await res.json();
        updateHeaderForQA(data.question);
        renderQADetail(data);
    } catch (e) {
        container.innerHTML = `<div class="community-empty-state"><p class="text-sm text-red-500">読み込みエラーが発生しました</p></div>`;
    }
}

function updateHeaderForQA(q) {
    const statusId = q.status_id;
    const statusClass = statusId === 2
        ? 'bg-green-50 text-green-700 border-green-200'
        : statusId === 3
            ? 'bg-zinc-100 text-zinc-500 border-zinc-200'
            : 'bg-orange-50 text-orange-700 border-orange-200';
    const statusText = statusId === 2 ? '解決済み' : statusId === 3 ? '期限切れ終了' : '回答募集中';

    document.getElementById('header-icon').className = 'h-10 w-10 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center flex-shrink-0 border border-pink-100';
    document.getElementById('header-icon').innerHTML = icon('solar:question-circle-bold', 24);
    document.getElementById('header-title').innerHTML = `Q&A <span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold border ${statusClass}">${statusText}</span>`;
    document.getElementById('header-tag').innerText = q.category ? q.category : 'Q&A';
    const membersEl = document.getElementById('header-members');
    if (membersEl) { membersEl.innerText = ''; membersEl.classList.add('hidden'); }
    const btn = document.getElementById('join-btn');
    if (btn) { btn.classList.add('hidden'); btn.classList.remove('flex'); }
    const membersBtn = document.getElementById('members-btn');
    if (membersBtn) { membersBtn.classList.add('hidden'); membersBtn.classList.remove('flex'); }
    refreshIcons();
}

function buildAnswerHTML(a, postUrl, isClosed, isOwner) {
    const avatarHTML = a.author.avatar
        ? `<img src="${a.author.avatar}" alt="${escapeHtml(a.author.name)}" class="h-9 w-9 rounded-full object-cover border border-zinc-100 flex-shrink-0">`
        : `<div class="h-9 w-9 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">${icon('lucide:user', 16)}</div>`;

    const repliesHTML = (a.replies || []).map(r => {
        const rAvatar = r.author.avatar
            ? `<img src="${r.author.avatar}" alt="${escapeHtml(r.author.name)}" class="h-7 w-7 rounded-full object-cover border border-zinc-100 flex-shrink-0">`
            : `<div class="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">${icon('lucide:user', 14)}</div>`;
        return `
        <div class="flex gap-2 pl-2 border-l-2 border-zinc-100">
            ${rAvatar}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <a href="${r.author.profile_url || '#'}" class="text-xs font-semibold text-zinc-800 hover:underline">${escapeHtml(r.author.name)}</a>
                    <span class="text-[10px] text-zinc-400">${escapeHtml(r.created_at)}</span>
                </div>
                <p class="text-sm text-zinc-700 whitespace-pre-wrap break-words">${escapeHtml(r.content)}</p>
            </div>
        </div>`;
    }).join('');

    const baBtn = a.can_select_best
        ? `<button onclick="selectBestAnswer(${a.id}, '${postUrl.replace('answer/', '')}answers/${a.id}/best/')"
                   class="qa-best-btn flex items-center gap-1 text-[10px] px-2 py-0.5 border border-zinc-300 text-zinc-500 rounded-full hover:bg-amber-50 hover:border-amber-300 hover:text-amber-600 transition-colors">
               ${icon('solar:star-linear', 12)} ベストアンサーを選択
           </button>`
        : '';

    const replyBtn = !isClosed && IS_AUTHENTICATED && !isOwner
        ? `<button onclick="toggleReplyForm(${a.id})"
                   class="qa-reply-btn text-[10px] text-zinc-400 hover:text-pink-500 transition-colors flex items-center gap-1">
               ${icon('lucide:corner-down-right', 12)} 返信する
           </button>`
        : '';

    const replyForm = !isClosed && IS_AUTHENTICATED && !isOwner ? `
        <div id="reply-form-${a.id}" class="qa-reply-form hidden mt-3 pl-2 border-l-2 border-pink-200">
            <textarea id="reply-input-${a.id}" rows="2" placeholder="返信を入力..."
                      class="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 resize-none"></textarea>
            <div class="flex justify-end gap-2 mt-1">
                <button onclick="toggleReplyForm(${a.id})" class="text-xs text-zinc-400 hover:text-zinc-600 px-3 py-1">キャンセル</button>
                <button onclick="postQAReply(${a.id}, '${postUrl}')"
                        class="text-xs bg-pink-600 text-white px-3 py-1 rounded-lg hover:bg-pink-700 transition-colors">送信</button>
            </div>
        </div>` : '';

    return `
    <div id="qa-answer-${a.id}" class="qa-answer-card${a.is_best_answer ? ' best-answer' : ''} animate-fade-in">
        ${a.is_best_answer ? `<div class="qa-answer-best-label">${icon('solar:check-circle-bold', 14)}ベストアンサー</div>` : ''}
        <div class="qa-answer-body">
            <div class="flex items-start gap-3 mb-3">
                ${avatarHTML}
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-0.5">
                        <a href="${a.author.profile_url || '#'}" class="text-sm font-bold text-zinc-900 hover:underline">${escapeHtml(a.author.name)}</a>
                        <span class="text-[10px] text-zinc-400">${escapeHtml(a.created_at)}</span>
                    </div>
                    <p class="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap break-words">${escapeHtml(a.content)}</p>
                </div>
            </div>
            ${repliesHTML ? `<div class="flex flex-col gap-3 mt-3">${repliesHTML}</div>` : ''}
            ${replyForm}
            <div class="flex items-center gap-3 mt-3">
                ${baBtn}
                ${replyBtn}
            </div>
        </div>
    </div>`;
}

function renderQADetail(data) {
    const container = document.getElementById('content-area');
    const q = data.question;
    const answers = data.answers || [];
    const postUrl = data.post_url;
    const isClosed = q.is_closed;

    const isOwner = q.is_owner;
    const answersHTML = answers.length === 0
        ? `<p class="text-sm text-zinc-400 text-center py-8">まだ回答がありません。最初の回答を投稿しましょう！</p>`
        : answers.map(a => buildAnswerHTML(a, postUrl, isClosed, isOwner)).join('');

    const answerForm = !isClosed && IS_AUTHENTICATED && !isOwner ? `
        <div id="qa-answer-form" class="flex-shrink-0 bg-white border-t border-zinc-200 px-4 py-3">
            <div id="qa-answer-error" class="hidden mb-2 text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2"></div>
            <div class="flex gap-2 items-end">
                <textarea id="qa-answer-input" rows="1" placeholder="回答を入力..."
                          class="flex-1 px-4 py-2.5 border border-zinc-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-pink-400 transition overflow-hidden"
                          oninput="boardAutoResize(this)"></textarea>
                <button onclick="postQAAnswer('${postUrl}')"
                        class="p-2.5 bg-pink-600 hover:bg-pink-700 text-white rounded-xl transition-colors flex-shrink-0">
                    ${icon('lucide:send', 18)}
                </button>
            </div>
        </div>` : '';

    const closedBanner = isClosed ? `
        <div class="flex-shrink-0 bg-zinc-50 border-t border-zinc-200 px-4 py-3 text-center text-xs text-zinc-400">
            ${q.status_id === 2 ? 'この質問は解決済みです' : 'この質問は受付を終了しました'}
        </div>` : '';

    const editUrl = q.edit_url || '';
    const editBtn = editUrl
        ? `<button onclick="toggleQAEdit()" id="qa-edit-btn"
                   class="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-pink-500 transition-colors">
               ${icon('lucide:pencil', 12)} 編集
           </button>`
        : '';
    const editForm = editUrl ? `
        <div id="qa-edit-form" class="hidden mt-3 pt-3 border-t border-zinc-100">
            <div class="mb-2">
                <label class="text-xs font-semibold text-zinc-500 mb-1 block">タイトル</label>
                <input id="qa-edit-title" type="text" maxlength="200"
                       class="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm font-bold focus:outline-none focus:ring-2 focus:ring-pink-400">
            </div>
            <div class="mb-2">
                <label class="text-xs font-semibold text-zinc-500 mb-1 block">本文</label>
                <textarea id="qa-edit-content" rows="4"
                          class="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 resize-none"></textarea>
            </div>
            <div id="qa-edit-error" class="hidden mb-2 text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2"></div>
            <div class="flex justify-end gap-2">
                <button onclick="toggleQAEdit()"
                        class="text-xs text-zinc-400 hover:text-zinc-600 px-3 py-1.5 rounded-lg hover:bg-zinc-100 transition-colors">
                    キャンセル
                </button>
                <button onclick="submitQAEdit('${editUrl}')"
                        class="text-xs bg-pink-600 text-white px-4 py-1.5 rounded-lg hover:bg-pink-700 transition-colors font-semibold">
                    保存する
                </button>
            </div>
        </div>` : '';

    container.innerHTML = `
        <div id="board-messages-area" class="flex-1 overflow-y-auto p-4 space-y-4">
            <div class="qa-question-card">
                <div class="flex items-center gap-2 mb-3">
                    ${q.author.avatar
                        ? `<img src="${q.author.avatar}" alt="${escapeHtml(q.author.name)}" class="h-8 w-8 rounded-full object-cover border border-zinc-100">`
                        : `<div class="h-8 w-8 rounded-full bg-zinc-100 flex items-center justify-center">${icon('lucide:user', 16)}</div>`}
                    <a href="${q.author.profile_url || '#'}" class="text-xs font-bold text-zinc-900 hover:underline">${escapeHtml(q.author.name)}</a>
                    <span class="text-[10px] text-zinc-400">• ${escapeHtml(q.created_at)}</span>
                    <span class="text-[10px] text-zinc-400 ml-auto">期限: ${escapeHtml(q.expires_at)}</span>
                    ${editBtn}
                </div>
                <div id="qa-question-display">
                    <h1 class="text-lg font-bold text-zinc-900 mb-3 leading-snug">${escapeHtml(q.title)}</h1>
                    <p class="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap">${escapeHtml(q.content)}</p>
                </div>
                ${editForm}
            </div>
            <div class="flex items-center justify-between px-1">
                <h3 class="font-bold text-zinc-900 text-sm">回答 <span class="text-zinc-400 font-normal ml-1">${answers.length}件</span></h3>
            </div>
            <div id="qa-answers-list" class="space-y-4">${answersHTML}</div>
        </div>
        ${answerForm}
        ${closedBanner}
    `;
    refreshIcons();
}

// --- Q&A: Post Answer / Reply ---

async function postQAAnswer(postUrl) {
    const textarea = document.getElementById('qa-answer-input');
    const errorEl = document.getElementById('qa-answer-error');
    if (!textarea) return;
    const content = textarea.value.trim();
    if (!content) {
        if (errorEl) { errorEl.textContent = '回答内容を入力してください'; errorEl.classList.remove('hidden'); }
        return;
    }
    if (errorEl) errorEl.classList.add('hidden');
    try {
        const res = await fetch(postUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });
        const data = await res.json();
        if (data.success) {
            textarea.value = '';
            textarea.style.height = 'auto';
            const list = document.getElementById('qa-answers-list');
            if (list) {
                const isClosed = false;
                list.querySelector('p.text-center')?.remove();
                const div = document.createElement('div');
                div.innerHTML = buildAnswerHTML(data.answer, postUrl, isClosed, false);
                list.appendChild(div.firstElementChild);
                refreshIcons();
            }
        } else {
            if (errorEl) { errorEl.textContent = data.message || 'エラーが発生しました'; errorEl.classList.remove('hidden'); }
        }
    } catch (e) {
        if (errorEl) { errorEl.textContent = '通信エラーが発生しました'; errorEl.classList.remove('hidden'); }
    }
}

async function postQAReply(parentAnswerId, postUrl) {
    const textarea = document.getElementById(`reply-input-${parentAnswerId}`);
    if (!textarea) return;
    const content = textarea.value.trim();
    if (!content) return;
    try {
        const res = await fetch(postUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, parent_answer_id: parentAnswerId }),
        });
        const data = await res.json();
        if (data.success) {
            textarea.value = '';
            document.getElementById(`reply-form-${parentAnswerId}`)?.classList.add('hidden');
            const answerCard = document.getElementById(`qa-answer-${parentAnswerId}`);
            if (answerCard) {
                const repliesContainer = answerCard.querySelector('.flex.flex-col.gap-3');
                const replyHTML = `
                <div class="flex gap-2 pl-2 border-l-2 border-zinc-100">
                    <div class="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">${icon('lucide:user', 14)}</div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <a href="${data.answer.author.profile_url || '#'}" class="text-xs font-semibold text-zinc-800 hover:underline">${escapeHtml(data.answer.author.name)}</a>
                            <span class="text-[10px] text-zinc-400">${escapeHtml(data.answer.created_at)}</span>
                        </div>
                        <p class="text-sm text-zinc-700 whitespace-pre-wrap break-words">${escapeHtml(data.answer.content)}</p>
                    </div>
                </div>`;
                if (repliesContainer) {
                    repliesContainer.insertAdjacentHTML('beforeend', replyHTML);
                } else {
                    const actionsDiv = answerCard.querySelector('.flex.items-center.gap-3.mt-3');
                    if (actionsDiv) actionsDiv.insertAdjacentHTML('beforebegin', `<div class="flex flex-col gap-3 mt-3">${replyHTML}</div>`);
                }
                refreshIcons();
            }
        } else {
            showToast(data.message || 'エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
    }
}

function toggleReplyForm(answerId) {
    const form = document.getElementById(`reply-form-${answerId}`);
    if (form) form.classList.toggle('hidden');
}

// --- Q&A: Edit Question ---

function toggleQAEdit() {
    const display = document.getElementById('qa-question-display');
    const form = document.getElementById('qa-edit-form');
    const btn = document.getElementById('qa-edit-btn');
    if (!display || !form) return;

    const isEditing = !form.classList.contains('hidden');
    if (!isEditing) {
        // 編集モードへ：現在の表示内容をフォームに同期
        const titleInput = document.getElementById('qa-edit-title');
        const contentInput = document.getElementById('qa-edit-content');
        if (titleInput) titleInput.value = display.querySelector('h1').textContent;
        if (contentInput) contentInput.value = display.querySelector('p').textContent;
        document.getElementById('qa-edit-error')?.classList.add('hidden');
    }
    display.classList.toggle('hidden', !isEditing);
    form.classList.toggle('hidden', isEditing);
    if (btn) btn.classList.toggle('hidden', !isEditing);
}

async function submitQAEdit(editUrl) {
    const titleInput = document.getElementById('qa-edit-title');
    const contentInput = document.getElementById('qa-edit-content');
    const errorEl = document.getElementById('qa-edit-error');
    if (!titleInput || !contentInput) return;

    const title = titleInput.value.trim();
    const content = contentInput.value.trim();

    if (!title) { errorEl.textContent = 'タイトルを入力してください'; errorEl.classList.remove('hidden'); return; }
    if (!content) { errorEl.textContent = '本文を入力してください'; errorEl.classList.remove('hidden'); return; }
    errorEl.classList.add('hidden');

    try {
        const res = await fetch(editUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content }),
        });
        const data = await res.json();
        if (data.success) {
            // 表示を更新
            const display = document.getElementById('qa-question-display');
            if (display) {
                display.querySelector('h1').textContent = data.title;
                display.querySelector('p').textContent = data.content;
            }
            // QA_DATA のタイトルを更新してサイドバーを再描画
            const qaItem = QA_DATA.find(q => q.id === appState.activeQAId);
            if (qaItem) qaItem.title = data.title;
            renderSidebar();
            toggleQAEdit();
            showToast('質問を更新しました', 'solar:check-circle-bold', 'text-green-500');
        } else {
            errorEl.textContent = data.message || 'エラーが発生しました';
            errorEl.classList.remove('hidden');
        }
    } catch (e) {
        errorEl.textContent = '通信エラーが発生しました';
        errorEl.classList.remove('hidden');
    }
}

async function selectBestAnswer(answerId, selectUrl) {
    if (!confirm('この回答をベストアンサーに選びますか？')) return;
    try {
        const res = await fetch(selectUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
        });
        const data = await res.json();
        if (data.success) {
            // 1. 全回答カードからbest-answerクラスとラベルを除去
            document.querySelectorAll('.qa-answer-card').forEach(card => {
                card.classList.remove('best-answer');
                card.querySelector('.qa-answer-best-label')?.remove();
            });

            // 2. 選択した回答カードにbest-answerを付与してラベルを先頭に挿入
            const answerCard = document.getElementById(`qa-answer-${answerId}`);
            if (answerCard) {
                answerCard.classList.add('best-answer');
                const label = document.createElement('div');
                label.className = 'qa-answer-best-label';
                label.innerHTML = `${icon('solar:check-circle-bold', 14)}ベストアンサー`;
                answerCard.insertBefore(label, answerCard.firstChild);
            }

            // 3. 「ベストアンサーを選択」ボタンをすべて削除
            document.querySelectorAll('.qa-best-btn').forEach(btn => btn.remove());

            // 4. 返信ボタン・フォームをすべて非表示
            document.querySelectorAll('.qa-reply-btn').forEach(btn => btn.remove());
            document.querySelectorAll('.qa-reply-form').forEach(form => form.classList.add('hidden'));

            // 5. 回答フォームを「解決済み」バナーに差し替え
            const answerFormEl = document.getElementById('qa-answer-form');
            if (answerFormEl) {
                const banner = document.createElement('div');
                banner.className = 'flex-shrink-0 bg-zinc-50 border-t border-zinc-200 px-4 py-3 text-center text-xs text-zinc-400';
                banner.textContent = 'この質問は解決済みです';
                answerFormEl.replaceWith(banner);
            }

            // 6. ヘッダーのステータスバッジを「解決済み」に更新
            const headerTitle = document.getElementById('header-title');
            if (headerTitle) {
                headerTitle.innerHTML = `Q&A <span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold border bg-green-50 text-green-700 border-green-200">解決済み</span>`;
            }

            // 7. QA_DATAを更新してサイドバーを再描画
            const qaItem = QA_DATA.find(q => q.id === appState.activeQAId);
            if (qaItem) qaItem.status_id = 2;
            renderSidebar();

            showToast('ベストアンサーを選択しました', 'solar:check-circle-bold', 'text-green-500');
            refreshIcons();
        } else {
            showToast(data.message || 'エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
    }
}

// --- Q&A: Create Modal ---

function openQACreateModal() {
    const modal = document.getElementById('qa-create-modal');
    if (!modal) return;
    // カテゴリをセット
    const sel = document.getElementById('qa-create-category');
    if (sel && typeof QA_CATEGORIES !== 'undefined') {
        sel.innerHTML = '<option value="">カテゴリなし</option>';
        QA_CATEGORIES.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        });
    }
    document.getElementById('qa-create-error')?.classList.add('hidden');
    document.getElementById('qa-create-title').value = '';
    document.getElementById('qa-create-content').value = '';
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeQACreateModal() {
    const modal = document.getElementById('qa-create-modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
}

function closeQACreateModalOutside(event) {
    if (event.target === document.getElementById('qa-create-modal')) closeQACreateModal();
}

async function submitQAQuestion() {
    const title = document.getElementById('qa-create-title').value.trim();
    const content = document.getElementById('qa-create-content').value.trim();
    const categoryId = document.getElementById('qa-create-category').value;
    const errorEl = document.getElementById('qa-create-error');
    const submitBtn = document.getElementById('qa-create-submit');

    if (!title) { errorEl.textContent = 'タイトルを入力してください'; errorEl.classList.remove('hidden'); return; }
    if (!content) { errorEl.textContent = '本文を入力してください'; errorEl.classList.remove('hidden'); return; }
    errorEl.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const res = await fetch(QA_CREATE_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content, category_id: categoryId || null }),
        });
        const data = await res.json();
        if (data.success) {
            closeQACreateModal();
            showToast('質問を投稿しました', 'solar:check-circle-bold', 'text-green-500');
            await loadQAList();
            renderSidebar();
            selectQA(data.question_id);
        } else {
            const msg = data.errors ? Object.values(data.errors)[0] : (data.message || 'エラーが発生しました');
            errorEl.textContent = msg;
            errorEl.classList.remove('hidden');
        }
    } catch (e) {
        errorEl.textContent = '通信エラーが発生しました';
        errorEl.classList.remove('hidden');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

// --- Board: Load & Render ---

async function loadBoard(boardId, boardUrl) {
    appState.activeBoardId = boardId;
    appState.activeBoardUrl = boardUrl;

    // サイドバーのアクティブ状態を更新
    document.querySelectorAll('[data-board-id]').forEach(el => {
        el.classList.toggle('bg-pink-50', String(el.dataset.boardId) === String(boardId));
    });

    // ローディング表示
    const container = document.getElementById('content-area');
    container.innerHTML = `
        <div class="community-empty-state">
            <div class="h-8 w-8 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div>
        </div>`;

    try {
        const response = await fetch(boardUrl, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        if (!response.ok) throw new Error('Network error');
        const data = await response.json();

        // ヘッダー更新
        document.getElementById('header-icon').className = 'h-10 w-10 rounded-xl bg-pink-50 text-pink-600 flex items-center justify-center flex-shrink-0';
        document.getElementById('header-icon').innerHTML = icon('lucide:message-square', 22);
        document.getElementById('header-title').innerHTML = escapeHtml(data.board.name || '掲示板');
        document.getElementById('header-tag').innerText = data.board.category || '掲示板';
        const membersEl = document.getElementById('header-members');
        if (membersEl) { membersEl.innerText = ''; membersEl.classList.add('hidden'); }

        // メンバーボタン更新
        appState.boardMembers = data.members || [];
        const membersBtn = document.getElementById('members-btn');
        const membersBtnCount = document.getElementById('members-btn-count');
        if (membersBtn && membersBtnCount) {
            membersBtnCount.textContent = `${data.member_count || 0}人`;
            membersBtn.classList.remove('hidden');
            membersBtn.classList.add('flex');
        }

        document.getElementById('join-btn').classList.add('hidden');
        refreshIcons();

        // メッセージ描画
        renderBoardMessages(data.messages);

        // 商品リスト保存 & ピッカー更新
        appState.boardUserProducts = data.user_products || [];
        updateBoardProductPicker();

        // URLをappStateに保存
        appState.activeBoardJoinUrl = data.join_url;
        appState.activeBoardLeaveUrl = data.leave_url;

        // 参加状態に応じて投稿バー・参加ボタンを制御
        const postBar = document.getElementById('board-post-bar');
        const joinBtn = document.getElementById('join-btn');
        if (data.is_member) {
            // 参加済み → 投稿バー表示
            if (postBar) {
                postBar.classList.remove('hidden');
                const productBtn = document.getElementById('board-product-btn');
                if (productBtn) productBtn.classList.remove('hidden');
            }
            if (joinBtn) {
                if (data.is_creator) {
                    // 作成者 → ボタン非表示
                    joinBtn.classList.add('hidden');
                    joinBtn.classList.remove('flex');
                } else {
                    // 参加中（作成者以外）→ 「退会する」ボタン表示
                    joinBtn.className = 'flex px-4 py-1.5 rounded-full text-xs font-bold transition-all items-center gap-1.5 border border-red-200 text-red-600 bg-red-50 hover:bg-red-100';
                    joinBtn.innerHTML = `${icon('lucide:log-out', 14)} 退会する`;
                    joinBtn.disabled = false;
                    joinBtn.onclick = () => leaveBoard(data.leave_url);
                    refreshIcons();
                }
            }
        } else {
            // 未参加 → 投稿バー非表示、参加ボタン表示
            if (postBar) postBar.classList.add('hidden');
            if (joinBtn) {
                joinBtn.className = 'flex px-4 py-1.5 rounded-full text-xs font-bold transition-all items-center gap-1.5 border bg-pink-600 text-white border-pink-600 hover:bg-pink-700';
                joinBtn.innerHTML = `${icon('lucide:user-plus', 14)} 参加する`;
                joinBtn.disabled = false;
                joinBtn.onclick = () => joinBoard(data.join_url);
                refreshIcons();
            }
        }

        // モバイル: メイン表示
        toggleMobileView(true);
    } catch (e) {
        container.innerHTML = `
            <div class="community-empty-state">
                <p class="text-sm text-red-500">読み込みエラーが発生しました</p>
            </div>`;
    }
}

function renderBoardMessages(messages) {
    const container = document.getElementById('content-area');
    const msgsHtml = messages.length === 0
        ? `<div id="board-empty-state" class="flex flex-col items-center justify-center py-16 text-zinc-400">
               <div class="h-14 w-14 bg-zinc-100 rounded-full flex items-center justify-center mb-3">
                   ${icon('lucide:message-circle', 28)}
               </div>
               <p class="text-sm">まだメッセージがありません。最初の投稿をしてみましょう！</p>
           </div>`
        : messages.map(m => buildBoardMessageHtml(m)).join('');

    container.innerHTML = `
        <div id="board-messages-area" class="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-50/50">
            ${msgsHtml}
        </div>`;

    // 最下部にスクロール
    const area = document.getElementById('board-messages-area');
    if (area) area.scrollTop = area.scrollHeight;

    refreshIcons();
}

function buildBoardMessageHtml(msg) {
    const isMine = msg.is_mine;
    const id = msg.id;

    // アバター（他人）
    const otherAvatar = !isMine
        ? `<a href="${msg.user.profile_url || '#'}" class="h-8 w-8 rounded-full flex-shrink-0 overflow-hidden bg-zinc-200 flex items-center justify-center hover:opacity-80 transition-opacity">
               ${msg.user.avatar
                   ? `<img src="${msg.user.avatar}" alt="${escapeHtml(msg.user.name)}" class="h-full w-full object-cover">`
                   : icon('lucide:user', 16)}
           </a>`
        : '';

    // アバター（自分）
    const myAvatar = isMine
        ? `<a href="${(typeof BOARD_CURRENT_USER !== 'undefined' && BOARD_CURRENT_USER.profile_url) || '#'}" class="h-8 w-8 rounded-full flex-shrink-0 overflow-hidden bg-pink-100 flex items-center justify-center hover:opacity-80 transition-opacity">
               ${(typeof BOARD_CURRENT_USER !== 'undefined' && BOARD_CURRENT_USER.avatar)
                   ? `<img src="${BOARD_CURRENT_USER.avatar}" alt="${escapeHtml(BOARD_CURRENT_USER.name)}" class="h-full w-full object-cover">`
                   : icon('lucide:user', 16)}
           </a>`
        : '';

    // テキスト
    const textHtml = msg.content
        ? `<div class="px-4 py-2.5 text-sm leading-relaxed break-words ${isMine ? 'bg-pink-600 text-white bubble-me' : 'bg-white text-zinc-800 border border-zinc-200 bubble-other'}">
               ${escapeHtml(msg.content).replace(/\n/g, '<br>')}
           </div>`
        : '';

    // 画像
    const imgHtml = msg.image_url
        ? `<div class="overflow-hidden rounded-xl cursor-pointer" onclick="openBoardImageModal('${msg.image_url}')">
               <img src="${msg.image_url}" alt="添付画像" class="max-w-xs max-h-64 object-cover hover:opacity-90 transition-opacity rounded-xl">
           </div>`
        : '';

    // 商品リンク
    const productHtml = msg.product
        ? `<a href="${msg.product.url}" class="block border border-zinc-200 bg-white rounded-xl overflow-hidden hover:border-pink-300 hover:shadow-sm transition-all max-w-xs">
               <div class="flex items-center gap-3 p-3">
                   <div class="h-12 w-12 rounded-lg bg-zinc-100 flex items-center justify-center flex-shrink-0 overflow-hidden">
                       ${msg.product.image
                           ? `<img src="${msg.product.image}" alt="${escapeHtml(msg.product.name)}" class="h-full w-full object-cover">`
                           : icon('lucide:image', 20)}
                   </div>
                   <p class="text-xs font-semibold text-zinc-800 truncate">${escapeHtml(msg.product.name)}</p>
               </div>
           </a>`
        : '';

    // 削除ボタン
    const deleteBtn = (isMine && msg.delete_url)
        ? `<button onclick="deleteBoardMessage(${id}, '${msg.delete_url}')" class="text-xs text-zinc-300 hover:text-red-400 transition-colors">
               ${icon('lucide:trash-2', 13)}
           </button>`
        : '';

    const timestampHtml = `<div class="flex items-center gap-2 ${isMine ? 'flex-row-reverse' : ''}">
        <span class="text-xs text-zinc-400">${escapeHtml(msg.time)}</span>
        ${deleteBtn}
    </div>`;

    const bubble = `<div class="max-w-[75%] ${isMine ? 'items-end' : 'items-start'} flex flex-col gap-1">
        ${!isMine ? `<span class="text-xs text-zinc-400 ml-1">${escapeHtml(msg.user.name)}</span>` : ''}
        ${textHtml}${imgHtml}${productHtml}
        ${timestampHtml}
    </div>`;

    return `<div id="board-msg-${id}" class="flex ${isMine ? 'justify-end items-end gap-3' : 'items-end gap-3'} animate-fade-in">
        ${otherAvatar}${bubble}${myAvatar}
    </div>`;
}

function appendBoardMessage(msg) {
    const area = document.getElementById('board-messages-area');
    if (!area) return;
    // 空状態を削除
    const empty = document.getElementById('board-empty-state');
    if (empty) empty.remove();
    // メッセージ追加
    const div = document.createElement('div');
    div.innerHTML = buildBoardMessageHtml(msg);
    area.appendChild(div.firstElementChild);
    area.scrollTop = area.scrollHeight;
    refreshIcons();
}

// --- Board: Send Message ---

function getCsrfToken() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
}

function boardAutoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

function showBoardPostError(msg) {
    const el = document.getElementById('board-post-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}

function clearBoardPostError() {
    const el = document.getElementById('board-post-error');
    if (el) { el.textContent = ''; el.classList.add('hidden'); }
}

async function sendBoardMessage() {
    if (!appState.activeBoardUrl) return;
    clearBoardPostError();

    const textarea = document.getElementById('board-message-input');
    const fileInput = document.getElementById('board-file-input');
    const productId = document.getElementById('board-selected-product-id').value;
    const content = textarea.value.trim();
    const image = fileInput.files[0];

    if (!content && !image && !productId) {
        showBoardPostError('メッセージ、画像、または商品リンクのいずれかを入力してください');
        return;
    }
    if (content.length > 2000) {
        showBoardPostError('メッセージは2000文字以内で入力してください');
        return;
    }

    const sendBtn = document.getElementById('board-send-btn');
    sendBtn.disabled = true;

    const formData = new FormData();
    formData.append('message_content', content);
    if (image) formData.append('image', image);
    if (productId) formData.append('product_link_id', productId);

    try {
        const response = await fetch(appState.activeBoardUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData,
        });
        const data = await response.json();
        if (data.success) {
            textarea.value = '';
            textarea.style.height = 'auto';
            clearBoardImage();
            clearBoardProduct();
            appendBoardMessage(data.msg);
        } else if (data.errors) {
            showBoardPostError(Object.values(data.errors)[0]);
        } else {
            showBoardPostError(data.message || 'エラーが発生しました');
        }
    } catch (err) {
        showBoardPostError('通信エラーが発生しました');
    } finally {
        sendBtn.disabled = false;
    }
}

async function deleteBoardMessage(id, url) {
    if (!confirm('このメッセージを削除しますか？')) return;
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (data.success) {
            const el = document.getElementById('board-msg-' + id);
            if (el) el.remove();
        } else {
            alert(data.message || '削除できませんでした');
        }
    } catch (err) {
        alert('通信エラーが発生しました');
    }
}

// --- Board: Image Attachment ---

function previewBoardImage(input) {
    if (!input.files || !input.files[0]) return;
    const reader = new FileReader();
    reader.onload = function (e) {
        document.getElementById('board-image-preview').src = e.target.result;
        document.getElementById('board-image-preview-wrap').classList.remove('hidden');
    };
    reader.readAsDataURL(input.files[0]);
}

function clearBoardImage() {
    const fi = document.getElementById('board-file-input');
    if (fi) fi.value = '';
    const wrap = document.getElementById('board-image-preview-wrap');
    if (wrap) wrap.classList.add('hidden');
    const img = document.getElementById('board-image-preview');
    if (img) img.src = '';
}

// --- Board: Product Attachment ---

function updateBoardProductPicker() {
    const list = document.getElementById('board-product-list');
    if (!list) return;
    list.innerHTML = '';
    if (appState.boardUserProducts.length === 0) {
        list.innerHTML = `<p class="text-xs text-zinc-400 py-2">出品中の商品がありません</p>`;
        return;
    }
    appState.boardUserProducts.forEach(p => {
        const el = document.createElement('button');
        el.type = 'button';
        el.className = 'flex-shrink-0 border border-zinc-200 bg-white rounded-xl p-2 hover:border-pink-300 transition-all text-left w-32';
        el.onclick = () => selectBoardProduct(p.id, p.name);
        el.innerHTML = `
            <div class="h-16 w-full rounded-lg bg-zinc-100 flex items-center justify-center mb-1.5 overflow-hidden">
                ${p.image
                    ? `<img src="${p.image}" alt="${escapeHtml(p.name)}" class="h-full w-full object-cover">`
                    : icon('lucide:image', 20)}
            </div>
            <p class="text-[11px] font-semibold text-zinc-800 truncate">${escapeHtml(p.name)}</p>
        `;
        list.appendChild(el);
    });
}

function toggleBoardProductPicker() {
    const picker = document.getElementById('board-product-picker');
    if (picker) picker.classList.toggle('hidden');
}

function selectBoardProduct(id, name) {
    document.getElementById('board-selected-product-id').value = id;
    document.getElementById('board-product-name').textContent = name;
    document.getElementById('board-product-preview').classList.remove('hidden');
    const picker = document.getElementById('board-product-picker');
    if (picker) picker.classList.add('hidden');
}

function clearBoardProduct() {
    document.getElementById('board-selected-product-id').value = '';
    document.getElementById('board-product-preview').classList.add('hidden');
}

async function joinBoard(joinUrl) {
    const joinBtn = document.getElementById('join-btn');
    if (joinBtn) joinBtn.disabled = true;
    try {
        const response = await fetch(joinUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (data.success) {
            // 参加成功 → 参加ボタンを「退会する」ボタンに変更
            if (joinBtn) {
                joinBtn.className = 'flex px-4 py-1.5 rounded-full text-xs font-bold transition-all items-center gap-1.5 border border-red-200 text-red-600 bg-red-50 hover:bg-red-100';
                joinBtn.innerHTML = `${icon('lucide:log-out', 14)} 退会する`;
                joinBtn.disabled = false;
                joinBtn.onclick = () => leaveBoard(appState.activeBoardLeaveUrl);
                refreshIcons();
            }
            const postBar = document.getElementById('board-post-bar');
            if (postBar) {
                postBar.classList.remove('hidden');
                const productBtn = document.getElementById('board-product-btn');
                if (productBtn) productBtn.classList.remove('hidden');
            }
            // メンバーボタンのカウントを+1
            const membersBtnCount = document.getElementById('members-btn-count');
            if (membersBtnCount) {
                const cur = parseInt(membersBtnCount.textContent) || 0;
                membersBtnCount.textContent = `${cur + 1}人`;
            }
            // サイドバーの参加ボタンを「参加中」バッジに切り替え
            updateSidebarMemberStatus(appState.activeBoardId, 'joined');
            showToast('掲示板に参加しました', 'lucide:check-circle', 'text-green-500');
        } else {
            showToast(data.message || '参加できませんでした', 'lucide:alert-circle', 'text-red-500');
            if (joinBtn) joinBtn.disabled = false;
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        if (joinBtn) joinBtn.disabled = false;
    }
}

async function leaveBoard(leaveUrl) {
    if (!confirm('この掲示板の参加をキャンセルしますか？')) return;
    const joinBtn = document.getElementById('join-btn');
    if (joinBtn) joinBtn.disabled = true;
    try {
        const response = await fetch(leaveUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (data.success) {
            // 退会成功 → 「参加する」ボタンに戻す、投稿バー非表示
            if (joinBtn) {
                joinBtn.className = 'flex px-4 py-1.5 rounded-full text-xs font-bold transition-all items-center gap-1.5 border bg-pink-600 text-white border-pink-600 hover:bg-pink-700';
                joinBtn.innerHTML = `${icon('lucide:user-plus', 14)} 参加する`;
                joinBtn.disabled = false;
                joinBtn.onclick = () => joinBoard(appState.activeBoardJoinUrl);
                refreshIcons();
            }
            const postBar = document.getElementById('board-post-bar');
            if (postBar) postBar.classList.add('hidden');
            // メンバー数を-1
            const membersBtnCount = document.getElementById('members-btn-count');
            if (membersBtnCount) {
                const cur = parseInt(membersBtnCount.textContent) || 0;
                membersBtnCount.textContent = `${Math.max(0, cur - 1)}人`;
            }
            updateSidebarMemberStatus(appState.activeBoardId, 'left');
            showToast('参加をキャンセルしました', 'lucide:log-out', 'text-zinc-500');
        } else {
            showToast(data.message || '退会できませんでした', 'lucide:alert-circle', 'text-red-500');
            if (joinBtn) joinBtn.disabled = false;
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        if (joinBtn) joinBtn.disabled = false;
    }
}

// --- Members Modal ---

function openMembersModal() {
    const modal = document.getElementById('members-modal');
    const list = document.getElementById('members-modal-list');
    const countEl = document.getElementById('members-modal-count');
    if (!modal || !list) return;

    const members = appState.boardMembers;
    if (countEl) countEl.textContent = `${members.length}人`;

    list.innerHTML = members.length === 0
        ? `<p class="text-center text-xs text-zinc-400 py-6">まだメンバーがいません</p>`
        : members.map(m => `
            <a href="${m.profile_url || '#'}" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-zinc-50 transition-colors">
                <div class="h-9 w-9 rounded-full flex-shrink-0 overflow-hidden bg-zinc-200 flex items-center justify-center">
                    ${m.avatar
                        ? `<img src="${m.avatar}" alt="${escapeHtml(m.name)}" class="h-full w-full object-cover">`
                        : icon('lucide:user', 16)}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-zinc-900 truncate">${escapeHtml(m.name)}</p>
                </div>
                ${m.is_creator ? `<span class="text-[10px] px-2 py-0.5 bg-pink-50 text-pink-600 rounded-full font-semibold flex-shrink-0">作成者</span>` : ''}
            </a>`).join('');

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    refreshIcons();
}

function closeMembersModal() {
    const modal = document.getElementById('members-modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
}

function closeMembersModalOutside(event) {
    if (event.target === document.getElementById('members-modal')) closeMembersModal();
}

// --- Board: Create Modal ---

function openBoardCreateModal() {
    const modal = document.getElementById('board-create-modal');
    if (!modal) return;
    document.getElementById('board-create-error')?.classList.add('hidden');
    document.getElementById('board-create-name').value = '';
    document.getElementById('board-create-description').value = '';
    document.getElementById('board-create-category').value = '';
    document.getElementById('board-create-name-counter').textContent = '0 / 100';
    document.getElementById('board-create-desc-counter').textContent = '0 / 1000';
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeBoardCreateModal() {
    const modal = document.getElementById('board-create-modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
}

function closeBoardCreateModalOutside(event) {
    if (event.target === document.getElementById('board-create-modal')) closeBoardCreateModal();
}

async function submitBoardCreate() {
    const name = document.getElementById('board-create-name').value.trim();
    const description = document.getElementById('board-create-description').value.trim();
    const categoryId = document.getElementById('board-create-category').value;
    const errorEl = document.getElementById('board-create-error');
    const submitBtn = document.getElementById('board-create-submit');

    if (!name) { errorEl.textContent = 'タイトルを入力してください'; errorEl.classList.remove('hidden'); return; }
    if (!categoryId) { errorEl.textContent = 'カテゴリを選択してください'; errorEl.classList.remove('hidden'); return; }
    if (!description) { errorEl.textContent = '説明文を入力してください'; errorEl.classList.remove('hidden'); return; }
    errorEl.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const res = await fetch(BOARD_CREATE_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, category_id: categoryId }),
        });
        const data = await res.json();
        if (data.success) {
            closeBoardCreateModal();
            showToast('掲示板を作成しました', 'lucide:check-circle', 'text-green-500');
            prependBoardToSidebar(data);
            switchTab('boards');
            loadBoard(data.board_id, data.board_url);
        } else {
            const msg = data.errors ? Object.values(data.errors)[0] : (data.message || 'エラーが発生しました');
            errorEl.textContent = msg;
            errorEl.classList.remove('hidden');
        }
    } catch (e) {
        errorEl.textContent = '通信エラーが発生しました';
        errorEl.classList.remove('hidden');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
    }
}

function prependBoardToSidebar(data) {
    const sidebarItems = document.getElementById('sidebar-board-items');
    if (!sidebarItems) return;

    // 空状態を削除
    const empty = sidebarItems.querySelector('.py-10');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.setAttribute('data-board-id', data.board_id);
    div.setAttribute('data-board-url', data.board_url);
    div.setAttribute('data-join-url', data.join_url);
    div.setAttribute('data-leave-url', data.leave_url);
    div.className = 'flex flex-col gap-1.5 px-4 py-3 hover:bg-zinc-50 transition-colors cursor-pointer';
    div.onclick = () => loadBoard(data.board_id, data.board_url);
    div.innerHTML = `
        <div class="flex items-center gap-2">
            ${data.board_category_name ? `<span class="text-[10px] px-1.5 py-0.5 bg-pink-50 text-pink-600 rounded-md font-semibold flex-shrink-0">${escapeHtml(data.board_category_name)}</span>` : ''}
            <span class="text-sm font-semibold text-zinc-900 truncate flex-1">${escapeHtml(data.board_name)}</span>
            <span class="text-[10px] px-1.5 py-0.5 bg-zinc-100 text-zinc-500 rounded-md font-semibold flex-shrink-0">作成者</span>
        </div>
        <div class="flex items-center justify-between">
            <span class="text-[11px] text-zinc-400 flex items-center gap-1">
                <span class="iconify" data-icon="lucide:users" data-width="11"></span>1人
            </span>
        </div>
    `;
    sidebarItems.insertBefore(div, sidebarItems.firstChild);
    refreshIcons();
}

// --- Sidebar Join ---

async function joinBoardFromSidebar(event, boardId, joinUrl) {
    event.stopPropagation();
    const btn = document.querySelector(`[data-join-btn="${boardId}"]`);
    if (btn) btn.disabled = true;
    try {
        const response = await fetch(joinUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
        });
        const data = await response.json();
        if (data.success) {
            updateSidebarMemberStatus(boardId, 'joined');
            // 現在表示中の掲示板なら投稿バー表示・ヘッダーボタンを「退会する」に更新
            if (String(appState.activeBoardId) === String(boardId)) {
                const postBar = document.getElementById('board-post-bar');
                if (postBar) {
                    postBar.classList.remove('hidden');
                    const productBtn = document.getElementById('board-product-btn');
                    if (productBtn) productBtn.classList.remove('hidden');
                }
                const joinBtn = document.getElementById('join-btn');
                if (joinBtn) {
                    joinBtn.className = 'flex px-4 py-1.5 rounded-full text-xs font-bold transition-all items-center gap-1.5 border border-red-200 text-red-600 bg-red-50 hover:bg-red-100';
                    joinBtn.innerHTML = `${icon('lucide:log-out', 14)} 退会する`;
                    joinBtn.disabled = false;
                    joinBtn.onclick = () => leaveBoard(appState.activeBoardLeaveUrl);
                    refreshIcons();
                }
                const membersBtnCount = document.getElementById('members-btn-count');
                if (membersBtnCount) {
                    const cur = parseInt(membersBtnCount.textContent) || 0;
                    membersBtnCount.textContent = `${cur + 1}人`;
                }
            }
            showToast('掲示板に参加しました', 'lucide:check-circle', 'text-green-500');
        } else {
            if (btn) btn.disabled = false;
            showToast(data.message || '参加できませんでした', 'lucide:alert-circle', 'text-red-500');
        }
    } catch (e) {
        if (btn) btn.disabled = false;
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
    }
}


function updateSidebarMemberStatus(boardId, status) {
    const boardItem = document.querySelector(`[data-board-id="${boardId}"]`);
    if (!boardItem) return;
    const titleRow = boardItem.querySelector('.flex.items-center.gap-2');
    const bottomRow = boardItem.querySelector('.flex.items-center.justify-between');

    if (status === 'joined') {
        // 「参加する」ボタンを削除
        const joinBtn = boardItem.querySelector(`[data-join-btn="${boardId}"]`);
        if (joinBtn) joinBtn.remove();
        // タイトル行に「参加中」バッジを追加
        if (titleRow && !titleRow.querySelector(`[data-leave-btn="${boardId}"]`)) {
            const badge = document.createElement('span');
            badge.className = 'text-[10px] px-1.5 py-0.5 bg-emerald-50 text-emerald-600 rounded-md font-semibold flex-shrink-0';
            badge.textContent = '参加中';
            badge.setAttribute('data-leave-btn', boardId);
            titleRow.appendChild(badge);
        }
    } else if (status === 'left') {
        // 「参加中」バッジを削除
        const badge = boardItem.querySelector(`[data-leave-btn="${boardId}"]`);
        if (badge) badge.remove();
        // ボトム行に「参加する」ボタンを追加
        if (bottomRow) {
            const joinUrl = boardItem.dataset.joinUrl;
            const btn = document.createElement('button');
            btn.className = 'text-[10px] px-2 py-0.5 bg-pink-600 text-white rounded-full font-semibold hover:bg-pink-700 transition-colors';
            btn.textContent = '参加する';
            btn.setAttribute('data-join-btn', boardId);
            if (joinUrl) {
                btn.onclick = (e) => joinBoardFromSidebar(e, boardId, joinUrl);
            }
            bottomRow.appendChild(btn);
        }
    }
}

function openBoardImageModal(src) {
    const modal = document.getElementById('board-image-modal');
    document.getElementById('board-modal-img').src = src;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeBoardImageModal() {
    const modal = document.getElementById('board-image-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// --- Image Modal ---

function openImageModal(src) {
    const modal = document.getElementById('image-modal');
    document.getElementById('modal-img').src = src;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeImageModal() {
    const modal = document.getElementById('image-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// --- Initialize ---

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('community-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => handleSearchInput(e.target.value));
    }

    document.querySelectorAll('[data-community-tab]').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.communityTab));
    });

    const backBtn = document.getElementById('mobile-back');
    if (backBtn) {
        backBtn.addEventListener('click', () => toggleMobileView(false));
    }

    // 掲示板メッセージ入力: Enterで送信、Shift+Enterで改行
    const boardInput = document.getElementById('board-message-input');
    if (boardInput) {
        boardInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendBoardMessage();
            }
        });
    }

    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    const qaParam = urlParams.get('qa');
    const boardParam = urlParams.get('board');

    if (tabParam === 'qa') {
        // 通知リンクなどからQ&Aタブを直接開く
        switchTab('qa');
        if (qaParam) {
            const qaId = parseInt(qaParam, 10);
            if (!isNaN(qaId)) appState.pendingQAId = qaId;
        }
    } else {
        switchTab('boards');
        // URLパラメータ ?board=<id> があれば自動ロード
        if (boardParam && typeof BOARD_DETAIL_URL_BASE !== 'undefined') {
            const boardId = parseInt(boardParam, 10);
            if (!isNaN(boardId)) {
                const sidebarItem = document.querySelector(`[data-board-id="${boardId}"]`);
                const boardUrl = sidebarItem
                    ? sidebarItem.dataset.boardUrl
                    : BOARD_DETAIL_URL_BASE.replace('/0/', `/${boardId}/`);
                loadBoard(boardId, boardUrl);
            }
        }
    }
});
