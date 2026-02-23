// =============================================
// Community Page JavaScript
// =============================================

// --- State ---
const state = {
    // tabs
    activeTab: 'chat',  // 'chat' | 'qa'

    // group chat list
    chatSort: 'new',
    chatCategory: '',
    chatSearch: '',
    chatMine: '',
    chatPage: 1,
    chatHasNext: false,

    // group chat detail
    activeBoardId: null,
    activeBoardUrl: null,
    activeBoardJoinUrl: null,
    activeBoardLeaveUrl: null,
    activeBoardDeleteUrl: null,
    boardMembers: [],

    // qa list
    qaData: [],
    qaSearch: '',
    qaCategory: '',
    qaMine: '',
    qaStatus: '',
    pendingQAId: null,

    // qa detail
    activeQAId: null,

    // product modal
    productSearchTimer: null,
    productCategory: '',

    // reply
    replyTo: null,  // { id, userName, content, imageUrl }


    // message edit modal
    editingMsgId: null,
    editingMsgUrl: null,
};

// --- Utilities ---

function icon(name, size) {
    return `<span class="iconify" data-icon="${name}" data-width="${size || 18}"></span>`;
}

function escHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function refreshIcons() {
    if (window.Iconify?.scan) window.Iconify.scan();
}

function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
}

function commAutoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
}

// =============================================
// TABS
// =============================================

function switchTab(tab) {
    state.activeTab = tab;
    document.querySelectorAll('.comm-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.getElementById('panel-chat').classList.toggle('hidden', tab !== 'chat');
    document.getElementById('panel-qa').classList.toggle('hidden', tab !== 'qa');

    if (tab === 'chat' && document.getElementById('chat-cards').children.length === 0) {
        loadBoardList(true);
    }
    if (tab === 'qa') {
        loadQAList();
    }
}

// =============================================
// GROUP CHAT: LIST
// =============================================

function initCategorySelects() {
    const sel = document.getElementById('chat-category-select');
    if (sel && BOARD_CATEGORIES) {
        BOARD_CATEGORIES.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        });
    }
    const qaSel = document.getElementById('qa-category-select');
    if (qaSel && QA_CATEGORIES) {
        QA_CATEGORIES.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            qaSel.appendChild(opt);
        });
    }
}

async function loadBoardList(reset = false) {
    if (reset) {
        state.chatPage = 1;
        state.chatHasNext = false;
        document.getElementById('chat-cards').innerHTML =
            `<div class="flex justify-center py-12"><div class="h-6 w-6 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;
    }

    const params = new URLSearchParams({
        sort: state.chatSort,
        page: state.chatPage,
    });
    if (state.chatCategory) params.set('category', state.chatCategory);
    if (state.chatSearch)   params.set('q', state.chatSearch);
    if (state.chatMine)     params.set('mine', state.chatMine);

    try {
        const res = await fetch(`${BOARD_LIST_URL}?${params}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        state.chatHasNext = data.has_next;

        const container = document.getElementById('chat-cards');
        if (reset) container.innerHTML = '';

        if (data.boards.length === 0 && state.chatPage === 1) {
            container.innerHTML = `
                <div class="comm-empty">
                    <div class="comm-empty-icon">${icon('lucide:message-square', 28)}</div>
                    <p>グループがまだありません</p>
                </div>`;
        } else {
            data.boards.forEach(b => container.appendChild(buildGroupCard(b)));
        }

        const loadMore = document.getElementById('chat-load-more');
        if (loadMore) loadMore.classList.toggle('hidden', !data.has_next);

        refreshIcons();
    } catch (e) {
        document.getElementById('chat-cards').innerHTML =
            `<div class="comm-empty"><p class="text-red-400">読み込みエラーが発生しました</p></div>`;
    }
}

function loadMoreBoards() {
    if (!state.chatHasNext) return;
    state.chatPage++;
    loadBoardList(false);
}

function buildGroupCard(b) {
    const div = document.createElement('div');
    div.className = 'comm-group-card';
    div.onclick = () => { window.location.href = BOARD_DETAIL_URL_BASE.replace('/0/', `/${b.id}/`); };

    let memberBadge = '';
    if (b.user_is_creator) memberBadge = `<span class="comm-badge-creator">作成者</span>`;
    else if (b.user_is_member) memberBadge = `<span class="comm-badge-joined">参加中</span>`;

    let joinBtn = '';
    if (!b.user_is_creator && !b.user_is_member) {
        if (!IS_AUTHENTICATED) {
            joinBtn = `<a href="${escHtml(LOGIN_URL)}" class="comm-join-card-btn">参加する</a>`;
        } else {
            joinBtn = `<button class="comm-join-card-btn" data-join-card="${b.id}"
                               onclick="joinFromCard(event, ${b.id}, '${escHtml(b.join_url)}')">参加する</button>`;
        }
    }

    div.innerHTML = `
        <div class="comm-group-card-top">
            <div class="comm-group-card-icon">${icon('lucide:message-square', 20)}</div>
            <div class="comm-group-card-body">
                <div class="comm-group-card-title">${escHtml(b.name)}</div>
                ${b.description ? `<div class="comm-group-card-desc">${escHtml(b.description)}</div>` : ''}
            </div>
            ${memberBadge ? `<div class="flex-shrink-0">${memberBadge}</div>` : ''}
        </div>
        <div class="comm-group-card-footer">
            ${b.category ? `<span class="comm-category-badge">${escHtml(b.category)}</span>` : ''}
            <span class="comm-meta">${icon('lucide:users', 13)} ${b.member_count}人</span>
            <span class="comm-meta">${icon('lucide:calendar', 13)} ${escHtml(b.created_at)}</span>
            ${joinBtn}
        </div>`;
    return div;
}

async function joinFromCard(event, boardId, joinUrl) {
    event.stopPropagation();
    const btn = document.querySelector(`[data-join-card="${boardId}"]`);
    if (btn) btn.disabled = true;
    try {
        const res = await fetch(joinUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
            if (btn) {
                btn.replaceWith(Object.assign(document.createElement('span'), {
                    className: 'comm-badge-joined',
                    textContent: '参加中'
                }));
            }
            showToast('グループに参加しました', 'lucide:check-circle', 'text-green-500');
            window.location.href = BOARD_DETAIL_URL_BASE.replace('/0/', `/${boardId}/`);
        } else {
            showToast(data.message || '参加できませんでした', 'lucide:alert-circle', 'text-red-500');
            if (btn) btn.disabled = false;
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        if (btn) btn.disabled = false;
    }
}

// =============================================
// GROUP CHAT: DETAIL
// =============================================

function showChatListView() {
    document.getElementById('chat-list-view').classList.remove('hidden');
    document.getElementById('chat-detail-view').classList.add('hidden');
}

function showChatDetailView() {
    document.getElementById('chat-list-view').classList.add('hidden');
    document.getElementById('chat-detail-view').classList.remove('hidden');
}

function backToChatList() {
    state.activeBoardId = null;
    state.activeBoardUrl = null;
    showChatListView();
}

async function openChatDetail(boardId, boardUrl) {
    state.activeBoardId = boardId;
    state.activeBoardUrl = boardUrl;
    showChatDetailView();

    // ローディング
    document.getElementById('chat-messages-area').innerHTML =
        `<div style="display:flex;justify-content:center;padding:3rem"><div class="h-6 w-6 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;
    document.getElementById('chat-input-bar').classList.add('hidden');
    document.getElementById('chat-join-btn').classList.add('hidden');
    document.getElementById('chat-members-btn').classList.add('hidden');
    document.getElementById('chat-delete-btn').classList.add('hidden');

    try {
        const res = await fetch(boardUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const data = await res.json();

        // ヘッダー更新
        document.getElementById('chat-header-title').textContent = data.board.name;
        document.getElementById('chat-header-sub').textContent = data.board.category || 'グループチャット';
        document.getElementById('chat-header-icon').innerHTML = icon('lucide:message-square', 20);

        // メンバーボタン
        state.boardMembers = data.members || [];
        const membersBtn = document.getElementById('chat-members-btn');
        document.getElementById('chat-members-count').textContent = `${data.member_count}人`;
        membersBtn.classList.remove('hidden');

        // URL保存
        state.activeBoardJoinUrl   = data.join_url;
        state.activeBoardLeaveUrl  = data.leave_url;
        state.activeBoardDeleteUrl = data.delete_url || null;

        // 参加状態
        const inputBar  = document.getElementById('chat-input-bar');
        const joinBtn   = document.getElementById('chat-join-btn');
        const deleteBtn = document.getElementById('chat-delete-btn');
        if (data.is_member) {
            inputBar.classList.remove('hidden');
            document.getElementById('chat-product-btn').classList.remove('hidden');
            if (data.is_creator) {
                joinBtn.classList.add('hidden');
                if (data.delete_url) {
                    deleteBtn.onclick = () => deleteBoard(data.delete_url, data.board.name);
                    deleteBtn.classList.remove('hidden');
                }
            } else {
                joinBtn.className = 'comm-join-btn flex border border-red-200 text-red-600 bg-red-50 hover:bg-red-100';
                joinBtn.innerHTML = `${icon('lucide:log-out', 14)} 退会する`;
                joinBtn.onclick = () => leaveGroup(data.leave_url);
                joinBtn.classList.remove('hidden');
            }
        } else {
            inputBar.classList.add('hidden');
            joinBtn.className = 'comm-join-btn flex bg-pink-600 text-white border border-pink-600 hover:bg-pink-700';
            joinBtn.innerHTML = `${icon('lucide:user-plus', 14)} 参加する`;
            joinBtn.onclick = IS_AUTHENTICATED
                ? () => joinGroup(data.join_url)
                : () => { window.location.href = LOGIN_URL; };
            joinBtn.classList.remove('hidden');
        }

        renderMessages(data.messages);
        refreshIcons();
    } catch (e) {
        document.getElementById('chat-messages-area').innerHTML =
            `<div class="comm-empty"><p class="text-red-400">読み込みエラーが発生しました</p></div>`;
    }
}

function renderMessages(messages) {
    const area = document.getElementById('chat-messages-area');
    if (messages.length === 0) {
        area.innerHTML = `
            <div class="comm-empty" style="flex:1">
                <div class="comm-empty-icon">${icon('lucide:message-circle', 28)}</div>
                <p>まだメッセージがありません。最初の投稿をしてみましょう！</p>
            </div>`;
        return;
    }
    area.innerHTML = '';
    messages.forEach(m => area.appendChild(buildMsgEl(m)));
    area.scrollTop = area.scrollHeight;
    refreshIcons();
}

function buildMsgEl(msg) {
    const div = document.createElement('div');
    div.id = `msg-${msg.id}`;
    if (!msg.is_system) {
        div.dataset.userName    = msg.user.name;
        div.dataset.msgContent  = msg.content ? msg.content.slice(0, 80) : '';
        div.dataset.hasImage    = msg.image_url ? '1' : '';
        div.dataset.productName = msg.product ? msg.product.name : '';
    }

    // システムメッセージ
    if (msg.is_system) {
        div.className = 'comm-msg-system animate-fade-in';
        div.innerHTML = `<span>${escHtml(msg.system_text)}</span>`;
        return div;
    }

    const isMine = msg.is_mine;
    div.className = `flex ${isMine ? 'justify-end items-end gap-3' : 'items-end gap-3'} animate-fade-in`;

    const avatar = isMine
        ? (BOARD_CURRENT_USER.avatar
            ? `<a href="${escHtml(BOARD_CURRENT_USER.profile_url || '#')}" class="h-8 w-8 rounded-full flex-shrink-0 overflow-hidden bg-pink-100 flex items-center justify-center hover:opacity-80"><img src="${escHtml(BOARD_CURRENT_USER.avatar)}" class="h-full w-full object-cover" alt=""></a>`
            : `<div class="h-8 w-8 rounded-full flex-shrink-0 bg-pink-100 flex items-center justify-center">${icon('lucide:user', 16)}</div>`)
        : (msg.user.avatar
            ? `<a href="${escHtml(msg.user.profile_url || '#')}" class="h-8 w-8 rounded-full flex-shrink-0 overflow-hidden bg-zinc-200 flex items-center justify-center hover:opacity-80"><img src="${escHtml(msg.user.avatar)}" class="h-full w-full object-cover" alt=""></a>`
            : `<div class="h-8 w-8 rounded-full flex-shrink-0 bg-zinc-200 flex items-center justify-center">${icon('lucide:user', 16)}</div>`);

    // 返信引用
    const replyHtml = msg.reply
        ? `<div class="flex items-stretch gap-1.5 max-w-[65vw] sm:max-w-sm md:max-w-md lg:max-w-lg opacity-80 cursor-pointer" onclick="document.getElementById('msg-${msg.reply.id}')?.scrollIntoView({behavior:'smooth',block:'center'})">
               <div class="w-0.5 bg-pink-400 rounded-full flex-shrink-0"></div>
               <div class="flex-1 min-w-0 px-2 py-1 rounded-lg ${isMine ? 'bg-pink-700/40' : 'bg-zinc-100'} text-xs">
                   <p class="font-semibold ${isMine ? 'text-pink-200' : 'text-pink-500'} mb-0.5">${escHtml(msg.reply.user_name)}</p>
                   <p class="truncate ${isMine ? 'text-pink-100' : 'text-zinc-500'}">${msg.reply.content ? escHtml(msg.reply.content) : (msg.reply.image_url ? '🖼 画像' : (msg.reply.product_name ? `📦 ${escHtml(msg.reply.product_name)}` : 'メッセージ'))}</p>
               </div>
           </div>`
        : '';

    const textHtml = msg.content
        ? `<div id="msg-text-${msg.id}" data-raw="${escHtml(msg.content)}" class="px-4 py-3 text-sm leading-relaxed break-words max-w-[65vw] sm:max-w-sm md:max-w-md lg:max-w-lg ${isMine ? 'bg-pink-600 text-white bubble-me' : 'bg-white text-zinc-800 border border-zinc-200 bubble-other'}">${escHtml(msg.content).replace(/\n/g, '<br>')}</div>`
        : '';

    const imgHtml = msg.image_url
        ? `<div class="overflow-hidden rounded-xl cursor-pointer" onclick="openImgModal('${escHtml(msg.image_url)}')">
               <img src="${escHtml(msg.image_url)}" alt="" class="max-w-[22rem] max-h-80 object-cover rounded-xl hover:opacity-90 transition-opacity">
           </div>`
        : '';

    const productHtml = msg.product
        ? `<a href="${escHtml(msg.product.url)}" class="block border border-zinc-200 bg-white rounded-xl overflow-hidden hover:border-pink-300 hover:shadow-md transition-all w-52">
               <div class="h-36 bg-zinc-100 overflow-hidden flex items-center justify-center">
                   ${msg.product.image ? `<img src="${escHtml(msg.product.image)}" class="h-full w-full object-cover" alt="">` : icon('lucide:image', 28)}
               </div>
               <div class="p-3">
                   <p class="text-xs font-semibold text-zinc-800 leading-snug line-clamp-2">${escHtml(msg.product.name)}</p>
               </div>
           </a>`
        : '';

    const canEdit = isMine && msg.edit_url && msg.content && !msg.image_url && !msg.product;
    const editBtn = canEdit
        ? `<button onclick="startEditMessage(${msg.id}, '${escHtml(msg.edit_url)}')" class="text-zinc-300 hover:text-blue-400 transition-colors" title="編集">${icon('lucide:pencil', 18)}</button>`
        : '';

    const deleteBtn = (isMine && msg.delete_url)
        ? `<button onclick="deleteChatMessage(${msg.id}, '${escHtml(msg.delete_url)}')" class="text-zinc-300 hover:text-red-400 transition-colors" title="削除">${icon('lucide:trash-2', 18)}</button>`
        : '';

    const replyBtn = !msg.is_system && IS_AUTHENTICATED
        ? `<button onclick="startReply(${msg.id})" class="text-zinc-300 hover:text-pink-400 transition-colors" title="返信">${icon('lucide:reply', 18)}</button>`
        : '';

    const timeRow = `<div class="flex items-center gap-1.5 ${isMine ? 'flex-row-reverse' : ''}">
        <span class="text-[11px] text-zinc-400">${escHtml(msg.time)}</span>
        ${replyBtn}
        ${editBtn}
        ${deleteBtn}
    </div>`;

    const bubble = `<div class="flex flex-col gap-2 max-w-[70%] ${isMine ? 'items-end' : 'items-start'}">
        ${!isMine ? `<span class="text-xs text-zinc-400 ml-1">${escHtml(msg.user.name)}</span>` : ''}
        ${replyHtml}
        ${textHtml}${imgHtml}${productHtml}
        ${timeRow}
    </div>`;

    div.innerHTML = `${!isMine ? avatar : ''}${bubble}${isMine ? avatar : ''}`;
    return div;
}

function appendMessage(msg) {
    const area = document.getElementById('chat-messages-area');
    if (!area) return;
    // 空状態の要素を消す
    area.querySelector('.comm-empty')?.remove();
    const el = buildMsgEl(msg);
    area.appendChild(el);
    area.scrollTop = area.scrollHeight;
    refreshIcons();
}

// ---- Join / Leave ----

async function joinGroup(joinUrl) {
    const btn = document.getElementById('chat-join-btn');
    if (btn) btn.disabled = true;
    try {
        const res = await fetch(joinUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('chat-input-bar').classList.remove('hidden');
            document.getElementById('chat-product-btn').classList.remove('hidden');
            if (btn) {
                btn.className = 'comm-join-btn flex border border-red-200 text-red-600 bg-red-50 hover:bg-red-100';
                btn.innerHTML = `${icon('lucide:log-out', 14)} 退会する`;
                btn.onclick = () => leaveGroup(state.activeBoardLeaveUrl);
                btn.disabled = false;
            }
            const cntEl = document.getElementById('chat-members-count');
            if (cntEl) cntEl.textContent = `${(parseInt(cntEl.textContent) || 0) + 1}人`;
            showToast('グループに参加しました', 'lucide:check-circle', 'text-green-500');
            refreshIcons();
        } else {
            showToast(data.message || '参加できませんでした', 'lucide:alert-circle', 'text-red-500');
            if (btn) btn.disabled = false;
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        if (btn) btn.disabled = false;
    }
}

async function leaveGroup(leaveUrl) {
    if (!confirm('このグループから退会しますか？')) return;
    const btn = document.getElementById('chat-join-btn');
    if (btn) btn.disabled = true;
    try {
        const res = await fetch(leaveUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('chat-input-bar').classList.add('hidden');
            if (btn) {
                btn.className = 'comm-join-btn flex bg-pink-600 text-white border border-pink-600 hover:bg-pink-700';
                btn.innerHTML = `${icon('lucide:user-plus', 14)} 参加する`;
                btn.onclick = () => joinGroup(state.activeBoardJoinUrl);
                btn.disabled = false;
            }
            const cntEl = document.getElementById('chat-members-count');
            if (cntEl) cntEl.textContent = `${Math.max(0, (parseInt(cntEl.textContent) || 1) - 1)}人`;
            if (data.system_msg) appendMessage(data.system_msg);
            showToast('退会しました', 'lucide:log-out', 'text-zinc-500');
            refreshIcons();
        } else {
            showToast(data.message || '退会できませんでした', 'lucide:alert-circle', 'text-red-500');
            if (btn) btn.disabled = false;
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        if (btn) btn.disabled = false;
    }
}

async function deleteBoard(deleteUrl, boardName) {
    if (!confirm(`「${boardName}」を削除しますか？\nこの操作は取り消せません。参加中のメンバー全員に通知されます。`)) return;
    const btn = document.getElementById('chat-delete-btn');
    if (btn) btn.disabled = true;
    try {
        const res = await fetch(deleteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
            showToast('グループを削除しました', 'lucide:check-circle', 'text-green-500');
            backToChatList();
            loadBoardList(true);
        } else {
            showToast(data.message || '削除できませんでした', 'lucide:alert-circle', 'text-red-500');
            if (btn) btn.disabled = false;
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        if (btn) btn.disabled = false;
    }
}

// ---- Send Message ----

async function sendChatMessage() {
    if (!state.activeBoardUrl) return;
    clearPostError();

    const textarea  = document.getElementById('chat-message-input');
    const fileInput = document.getElementById('chat-file-input');
    const productId = document.getElementById('chat-selected-product-id').value;
    const content   = textarea.value.trim();
    const image     = fileInput.files[0];

    if (!content && !image && !productId) {
        showPostError('メッセージ、画像、または商品リンクを入力してください');
        return;
    }
    if (content.length > 2000) {
        showPostError('メッセージは2000文字以内で入力してください');
        return;
    }

    const sendBtn = document.getElementById('chat-send-btn');
    sendBtn.disabled = true;

    const formData = new FormData();
    formData.append('message_content', content);
    if (image) formData.append('image', image);
    if (productId) formData.append('product_link_id', productId);

    try {
        const res = await fetch(state.activeBoardUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' },
            body: formData,
        });
        const data = await res.json();
        if (data.success) {
            textarea.value = '';
            textarea.style.height = 'auto';
            clearChatImage();
            clearChatProduct();
            appendMessage(data.msg);
        } else {
            showPostError(data.errors ? Object.values(data.errors)[0] : (data.message || 'エラーが発生しました'));
        }
    } catch (e) {
        showPostError('通信エラーが発生しました');
    } finally {
        sendBtn.disabled = false;
    }
}

async function deleteChatMessage(id, url) {
    if (!confirm('このメッセージを削除しますか？')) return;
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById(`msg-${id}`)?.remove();
        } else {
            alert(data.message || '削除できませんでした');
        }
    } catch (e) {
        alert('通信エラーが発生しました');
    }
}

function startEditMessage(msgId, editUrl) {
    const textEl = document.getElementById(`msg-text-${msgId}`);
    if (!textEl) return;
    state.editingMsgId  = msgId;
    state.editingMsgUrl = editUrl;
    const ta    = document.getElementById('msg-edit-modal-ta');
    const errEl = document.getElementById('msg-edit-modal-error');
    ta.value = textEl.dataset.raw || '';
    errEl.classList.add('hidden');
    const modal = document.getElementById('msg-edit-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    refreshIcons();
    ta.focus();
}

function closeMsgEditModal() {
    const modal = document.getElementById('msg-edit-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    state.editingMsgId  = null;
    state.editingMsgUrl = null;
}

function closeMsgEditModalOutside(event) {
    if (event.target === document.getElementById('msg-edit-modal')) closeMsgEditModal();
}

async function saveEditMessageModal() {
    const ta     = document.getElementById('msg-edit-modal-ta');
    const errEl  = document.getElementById('msg-edit-modal-error');
    const content = ta.value.trim();
    if (!content) {
        errEl.textContent = '内容を入力してください';
        errEl.classList.remove('hidden');
        return;
    }
    const msgId   = state.editingMsgId;
    const editUrl = state.editingMsgUrl;
    if (!msgId || !editUrl) return;
    errEl.classList.add('hidden');
    try {
        const res = await fetch(editUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrf(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ content }),
        });
        const data = await res.json();
        if (data.success) {
            const textEl = document.getElementById(`msg-text-${msgId}`);
            if (textEl) {
                textEl.innerHTML = escHtml(data.content).replace(/\n/g, '<br>');
                textEl.dataset.raw = data.content;
            }
            closeMsgEditModal();
            showToast('メッセージを編集しました', 'lucide:check-circle', 'text-green-500');
        } else {
            errEl.textContent = data.message || 'エラーが発生しました';
            errEl.classList.remove('hidden');
        }
    } catch (e) {
        errEl.textContent = '通信エラーが発生しました';
        errEl.classList.remove('hidden');
    }
}

function updateChatClearBtn() {
    const hasFilter = !!state.chatSearch || !!state.chatCategory;
    document.getElementById('chat-clear-btn')?.classList.toggle('hidden', !hasFilter);
}
function updateQAClearBtn() {
    const hasFilter = !!state.qaSearch || !!state.qaCategory;
    document.getElementById('qa-clear-btn')?.classList.toggle('hidden', !hasFilter);
}
function setChatMine(val) {
    state.chatMine = val;
    document.querySelectorAll('.comm-mine-btns [data-mine]').forEach(btn => {
        if (btn.closest('#panel-chat'))
            btn.classList.toggle('active', btn.dataset.mine === val);
    });
    loadBoardList(true);
}

function setQAMine(val) {
    state.qaMine = val;
    document.querySelectorAll('.comm-mine-btns [data-mine]').forEach(btn => {
        if (btn.closest('#panel-qa'))
            btn.classList.toggle('active', btn.dataset.mine === val);
    });
    loadQAList();
}

function setQAStatus(val) {
    state.qaStatus = val;
    document.querySelectorAll('.comm-status-btns [data-status]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === val);
    });
    loadQAList();
}

function clearChatFilters() {
    document.getElementById('chat-search-input').value = '';
    document.getElementById('chat-category-select').value = '';
    state.chatSearch = '';
    state.chatCategory = '';
    updateChatClearBtn();
    loadBoardList(true);
}
function clearQAFilters() {
    document.getElementById('qa-search-input').value = '';
    document.getElementById('qa-category-select').value = '';
    state.qaSearch = '';
    state.qaCategory = '';
    updateQAClearBtn();
    renderQACards();
}

function showPostError(msg) {
    const el = document.getElementById('chat-post-error');
    if (el) { el.textContent = msg; el.classList.remove('hidden'); }
}
function clearPostError() {
    const el = document.getElementById('chat-post-error');
    if (el) { el.textContent = ''; el.classList.add('hidden'); }
}

// ---- Image Attachment ----

function previewChatImage(input) {
    if (!input.files?.[0]) return;
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById('chat-image-preview').src = e.target.result;
        document.getElementById('chat-image-preview-wrap').classList.remove('hidden');
    };
    reader.readAsDataURL(input.files[0]);
}

function clearChatImage() {
    const fi = document.getElementById('chat-file-input');
    if (fi) fi.value = '';
    document.getElementById('chat-image-preview-wrap').classList.add('hidden');
    document.getElementById('chat-image-preview').src = '';
}

// ---- Reply ----

function startReply(msgId) {
    const msgEl = document.getElementById(`msg-${msgId}`);
    if (!msgEl) return;
    const userName    = msgEl.dataset.userName    || '';
    const content     = msgEl.dataset.msgContent  || '';
    const hasImage    = msgEl.dataset.hasImage    === '1';
    const productName = msgEl.dataset.productName || '';
    state.replyTo = { id: msgId, userName, content };

    document.getElementById('reply-modal-user').textContent = userName;
    document.getElementById('reply-modal-text').textContent = content || (hasImage ? '🖼 画像' : (productName ? `📦 ${productName}` : 'メッセージ'));
    document.getElementById('reply-modal-ta').value = '';
    document.getElementById('reply-modal-error').classList.add('hidden');

    const modal = document.getElementById('reply-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    refreshIcons();
    setTimeout(() => document.getElementById('reply-modal-ta').focus(), 50);
}

function closeReplyModal() {
    const modal = document.getElementById('reply-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    state.replyTo = null;
}

function closeReplyModalOutside(event) {
    if (event.target === document.getElementById('reply-modal')) closeReplyModal();
}

async function sendReplyModal() {
    const ta      = document.getElementById('reply-modal-ta');
    const errEl   = document.getElementById('reply-modal-error');
    const content = ta.value.trim();
    if (!content) {
        errEl.textContent = '返信内容を入力してください';
        errEl.classList.remove('hidden');
        return;
    }
    if (!state.activeBoardUrl || !state.replyTo) return;
    errEl.classList.add('hidden');

    const formData = new FormData();
    formData.append('message_content', content);
    formData.append('reply_to_id', state.replyTo.id);

    try {
        const res = await fetch(state.activeBoardUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' },
            body: formData,
        });
        const data = await res.json();
        if (data.success) {
            closeReplyModal();
            appendMessage(data.msg);
        } else {
            errEl.textContent = data.message || (data.errors ? Object.values(data.errors)[0] : 'エラーが発生しました');
            errEl.classList.remove('hidden');
        }
    } catch (e) {
        errEl.textContent = '通信エラーが発生しました';
        errEl.classList.remove('hidden');
    }
}

// ---- Product Modal ----

function openProductModal() {
    const modal = document.getElementById('product-modal');
    if (!modal) return;
    document.getElementById('product-modal-search').value = '';

    // カテゴリselect初期化（初回のみ選択肢を追加）
    const catSel = document.getElementById('product-modal-category');
    if (catSel && catSel.options.length <= 1 && PRODUCT_CATEGORIES) {
        PRODUCT_CATEGORIES.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            catSel.appendChild(opt);
        });
    }
    if (catSel) catSel.value = '';
    state.productCategory = '';

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    searchProductModal('');
    refreshIcons();
}

function closeProductModal() {
    const modal = document.getElementById('product-modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
}

function closeProductModalOutside(e) {
    if (e.target === document.getElementById('product-modal')) closeProductModal();
}

function searchProductModal(q) {
    const catSel = document.getElementById('product-modal-category');
    state.productCategory = catSel ? catSel.value : '';
    clearTimeout(state.productSearchTimer);
    state.productSearchTimer = setTimeout(() => fetchProductModal(q), 250);
}

async function fetchProductModal(q) {
    const list = document.getElementById('product-modal-list');
    list.innerHTML = `<div class="flex justify-center py-6"><div class="h-5 w-5 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;
    try {
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (state.productCategory) params.set('category_id', state.productCategory);
        const res = await fetch(`${BOARD_USER_PRODUCTS_URL}${params.toString() ? '?' + params : ''}`, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.products.length === 0) {
            list.innerHTML = `<p class="text-sm text-zinc-400 text-center py-6">出品中の商品がありません</p>`;
            return;
        }
        list.innerHTML = '';
        data.products.forEach(p => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'flex items-center gap-3 w-full text-left p-3 border border-zinc-200 rounded-xl hover:border-pink-300 hover:bg-pink-50 transition-all';
            btn.onclick = () => selectProduct(p.id, p.name);
            btn.innerHTML = `
                <div class="h-12 w-12 rounded-lg bg-zinc-100 flex-shrink-0 overflow-hidden flex items-center justify-center">
                    ${p.image ? `<img src="${escHtml(p.image)}" class="h-full w-full object-cover" alt="">` : icon('lucide:image', 18)}
                </div>
                <div class="min-w-0 flex-1">
                    <p class="text-sm font-semibold text-zinc-800 truncate">${escHtml(p.name)}</p>
                    ${p.owner ? `<p class="text-xs text-zinc-400 truncate">${escHtml(p.owner)}</p>` : ''}
                </div>`;
            list.appendChild(btn);
        });
        refreshIcons();
    } catch (e) {
        list.innerHTML = `<p class="text-sm text-red-400 text-center py-6">読み込みエラー</p>`;
    }
}

function selectProduct(id, name) {
    document.getElementById('chat-selected-product-id').value = id;
    document.getElementById('chat-product-name').textContent = name;
    document.getElementById('chat-product-preview').classList.remove('hidden');
    closeProductModal();
}

function clearChatProduct() {
    document.getElementById('chat-selected-product-id').value = '';
    document.getElementById('chat-product-preview').classList.add('hidden');
}

// ---- Members Modal ----

function openMembersModal() {
    const modal = document.getElementById('members-modal');
    const list  = document.getElementById('members-modal-list');
    const cnt   = document.getElementById('members-modal-count');
    if (!modal || !list) return;

    const members = state.boardMembers;
    if (cnt) cnt.textContent = `${members.length}人`;

    list.innerHTML = members.length === 0
        ? `<p class="text-center text-xs text-zinc-400 py-6">まだメンバーがいません</p>`
        : members.map(m => `
            <a href="${escHtml(m.profile_url || '#')}" class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-zinc-50 transition-colors">
                <div class="h-9 w-9 rounded-full flex-shrink-0 overflow-hidden bg-zinc-200 flex items-center justify-center">
                    ${m.avatar ? `<img src="${escHtml(m.avatar)}" class="h-full w-full object-cover" alt="">` : icon('lucide:user', 16)}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-semibold text-zinc-900 truncate">${escHtml(m.name)}</p>
                </div>
                ${m.is_creator ? `<span class="text-[10px] px-2 py-0.5 bg-pink-50 text-pink-600 rounded-full font-semibold">作成者</span>` : ''}
            </a>`).join('');

    modal.classList.remove('hidden');
    modal.classList.add('flex');
    refreshIcons();
}

function closeMembersModal() {
    const modal = document.getElementById('members-modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
}
function closeMembersModalOutside(e) {
    if (e.target === document.getElementById('members-modal')) closeMembersModal();
}

// ---- Board Create Modal ----

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
function closeBoardCreateModalOutside(e) {
    if (e.target === document.getElementById('board-create-modal')) closeBoardCreateModal();
}

async function submitBoardCreate() {
    const name        = document.getElementById('board-create-name').value.trim();
    const description = document.getElementById('board-create-description').value.trim();
    const categoryId  = document.getElementById('board-create-category').value;
    const errorEl     = document.getElementById('board-create-error');
    const submitBtn   = document.getElementById('board-create-submit');

    if (!name)        { errorEl.textContent = 'タイトルを入力してください'; errorEl.classList.remove('hidden'); return; }
    if (!categoryId)  { errorEl.textContent = 'カテゴリを選択してください'; errorEl.classList.remove('hidden'); return; }
    if (!description) { errorEl.textContent = '説明文を入力してください'; errorEl.classList.remove('hidden'); return; }
    errorEl.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const res = await fetch(BOARD_CREATE_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, category_id: categoryId }),
        });
        const data = await res.json();
        if (data.success) {
            window.location.href = BOARD_DETAIL_URL_BASE.replace('/0/', `/${data.board_id}/`);
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

// =============================================
// Q&A: LIST
// =============================================

async function loadQAList() {
    const container = document.getElementById('qa-cards');
    container.innerHTML = `<div class="flex justify-center py-12"><div class="h-6 w-6 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;
    try {
        const qaParams = new URLSearchParams();
        if (state.qaMine)   qaParams.set('mine', state.qaMine);
        if (state.qaStatus) qaParams.set('status', state.qaStatus);
        const qaQs = qaParams.toString();
        const qaUrl = qaQs ? QA_LIST_URL + '?' + qaQs : QA_LIST_URL;
        const res = await fetch(qaUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const data = await res.json();
        state.qaData = data.questions || [];
        renderQACards();
        if (state.pendingQAId) {
            const id = state.pendingQAId;
            state.pendingQAId = null;
            window.location.href = QA_DETAIL_URL_BASE.replace('/0/', `/${id}/`);
            return;
        }
    } catch (e) {
        container.innerHTML = `<div class="comm-empty"><p class="text-red-400">読み込みエラー</p></div>`;
    }
}

function renderQACards() {
    const container = document.getElementById('qa-cards');
    const searchLower = (state.qaSearch || '').toLowerCase();
    const catFilter   = state.qaCategory;

    let filtered = state.qaData.filter(q => {
        const matchSearch = !searchLower || q.title.toLowerCase().includes(searchLower);
        const matchCat    = !catFilter || String(q.category_id) === String(catFilter);
        return matchSearch && matchCat;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div class="comm-empty">
                <div class="comm-empty-icon">${icon('lucide:help-circle', 28)}</div>
                <p>質問はまだありません</p>
            </div>`;
        return;
    }

    container.innerHTML = '';
    filtered.forEach(q => container.appendChild(buildQACard(q)));
    refreshIcons();
}

// 受付中のみ期限バッジを返す（解決済み・期限切れはヘッダーのstatusBadgeで表示済み）
function deadlineBadge(q) {
    if (q.status_id !== 1) return '';
    if (!q.expires_at_raw) return `<span class="deadline-normal">${icon('lucide:clock', 11)} 受付中</span>`;
    const diff = new Date(q.expires_at_raw) - new Date();
    const hours = diff / (1000 * 60 * 60);
    if (hours < 0) return '';
    if (hours < 24) return `<span class="deadline-urgent">${icon('lucide:clock', 11)} あと${Math.ceil(hours)}時間</span>`;
    const days = Math.ceil(hours / 24);
    return `<span class="deadline-soon">${icon('lucide:clock', 11)} あと${days}日</span>`;
}

function buildQACard(q) {
    const div = document.createElement('div');
    div.className = 'comm-qa-card';
    div.onclick = () => { window.location.href = QA_DETAIL_URL_BASE.replace('/0/', `/${q.id}/`); };

    // ヘッダーにのみステータスを表示
    const statusBadge = q.status_id === 2
        ? `<span class="status-solved">${icon('lucide:check-circle', 12)} 解決済み</span>`
        : q.status_id === 3
            ? `<span class="status-expired">期限切れ</span>`
            : `<span class="status-open">受付中</span>`;

    const footerDeadline = deadlineBadge(q);

    div.innerHTML = `
        <div class="comm-qa-card-header">
            ${statusBadge}
            ${q.category ? `<span class="comm-category-badge">${escHtml(q.category)}</span>` : ''}
        </div>
        <div class="comm-qa-card-title">
            <span class="q-prefix">Q.</span>${escHtml(q.title)}
        </div>
        <div class="comm-qa-card-footer">
            ${footerDeadline}
            <span class="comm-meta">${icon('lucide:message-circle', 13)} ${q.answer_count}件の回答</span>
            <span class="comm-meta">${icon('lucide:calendar', 13)} ${escHtml(q.created_at)}</span>
        </div>`;
    return div;
}

// =============================================
// Q&A: DETAIL
// =============================================

function showQAListView() {
    document.getElementById('qa-list-view').classList.remove('hidden');
    document.getElementById('qa-detail-view').classList.add('hidden');
}

function showQADetailView() {
    document.getElementById('qa-list-view').classList.add('hidden');
    document.getElementById('qa-detail-view').classList.remove('hidden');
}

function backToQAList() {
    state.activeQAId = null;
    showQAListView();
}

async function openQADetail(qId) {
    state.activeQAId = qId;
    showQADetailView();

    document.getElementById('qa-detail-content').innerHTML =
        `<div style="flex:1;display:flex;justify-content:center;padding:3rem"><div class="h-6 w-6 rounded-full border-2 border-pink-500 border-t-transparent animate-spin"></div></div>`;

    const url = QA_DETAIL_URL_BASE.replace('/0/', `/${qId}/`);
    try {
        const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const data = await res.json();

        // ヘッダー更新
        const statusText = data.question.status_id === 2 ? '解決済み' : data.question.status_id === 3 ? '期限切れ' : '受付中';
        const statusClass = data.question.status_id === 2 ? 'bg-green-50 text-green-700 border-green-200' : data.question.status_id === 3 ? 'bg-zinc-100 text-zinc-500' : 'bg-orange-50 text-orange-700 border-orange-200';
        document.getElementById('qa-header-title').innerHTML =
            `Q&A <span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold border ${statusClass}">${statusText}</span>`;
        document.getElementById('qa-header-sub').textContent = data.question.category || 'Q&A';

        renderQADetail(data);
        refreshIcons();
    } catch (e) {
        document.getElementById('qa-detail-content').innerHTML =
            `<div class="comm-empty"><p class="text-red-400">読み込みエラーが発生しました</p></div>`;
    }
}

function renderQADetail(data) {
    const q       = data.question;
    const answers = data.answers || [];
    const postUrl = data.post_url;
    const isClosed = q.is_closed;
    const isOwner  = q.is_owner;

    const editUrl = q.edit_url || '';
    const editBtn = editUrl
        ? `<button onclick="toggleQAEdit()" id="qa-edit-btn" class="flex items-center gap-1.5 text-xs font-semibold text-zinc-500 hover:text-pink-500 border border-zinc-200 hover:border-pink-300 bg-white hover:bg-pink-50 px-3 py-1.5 rounded-lg transition-colors">${icon('lucide:pencil', 14)} 編集</button>`
        : '';
    const editForm = editUrl ? `
        <div id="qa-edit-form" class="hidden mt-3 pt-3 border-t border-zinc-100">
            <div class="mb-2">
                <label class="text-xs font-semibold text-zinc-500 mb-1 block">タイトル</label>
                <input id="qa-edit-title" type="text" maxlength="200" class="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-400">
            </div>
            <div class="mb-2">
                <label class="text-xs font-semibold text-zinc-500 mb-1 block">本文</label>
                <textarea id="qa-edit-content" rows="4" class="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 resize-none"></textarea>
            </div>
            <div id="qa-edit-error" class="hidden mb-2 text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2"></div>
            <div class="flex justify-end gap-2">
                <button onclick="toggleQAEdit()" class="text-xs text-zinc-400 hover:text-zinc-600 px-3 py-1.5 rounded-lg hover:bg-zinc-100">キャンセル</button>
                <button onclick="submitQAEdit('${escHtml(editUrl)}')" class="text-xs bg-pink-600 text-white px-4 py-1.5 rounded-lg hover:bg-pink-700 font-semibold">保存する</button>
            </div>
        </div>` : '';

    // 受付期限表示
    let deadlineHtml = '';
    if (q.status_id === 1 && q.expires_at) {
        const diff  = new Date(q.expires_at_raw || q.expires_at) - new Date();
        const hours = diff / (1000 * 60 * 60);
        let deadlineCls = 'deadline-normal', deadlineTxt = `受付期限: ${escHtml(q.expires_at)}`;
        if (hours < 0)   { deadlineCls = 'status-expired'; deadlineTxt = '受付期限切れ'; }
        else if (hours < 24) { deadlineCls = 'deadline-urgent'; deadlineTxt = `受付期限: ${escHtml(q.expires_at)}（あと${Math.ceil(hours)}時間）`; }
        else { deadlineCls = 'deadline-soon'; deadlineTxt = `受付期限: ${escHtml(q.expires_at)}（あと${Math.ceil(hours/24)}日）`; }
        deadlineHtml = `<span class="${deadlineCls}">${icon('lucide:clock', 12)} ${deadlineTxt}</span>`;
    }

    const noAnswerMsg = answers.length === 0
        ? (isOwner
            ? `<p class="text-sm text-zinc-400 text-center py-8">まだ回答がありません。回答をお待ちください。</p>`
            : `<p class="text-sm text-zinc-400 text-center py-8">まだ回答がありません。最初の回答を投稿しましょう！</p>`)
        : '';
    const answersHtml = noAnswerMsg || answers.map(a => buildAnswerHTML(a, postUrl, isClosed, isOwner)).join('');

    const answerForm = !isClosed && IS_AUTHENTICATED && !isOwner ? `
        <div class="comm-qa-answer-input">
            <div id="qa-answer-error" class="hidden mb-2 text-xs text-red-500 bg-red-50 border border-red-200 rounded-lg px-3 py-2"></div>
            <div class="flex gap-2 items-end">
                <textarea id="qa-answer-input" rows="1" placeholder="回答を入力..."
                          class="flex-1 px-4 py-2.5 border border-zinc-200 rounded-xl text-sm resize-none focus:outline-none focus:ring-2 focus:ring-pink-400 transition overflow-hidden"
                          oninput="commAutoResize(this)"></textarea>
                <button onclick="postQAAnswer('${escHtml(postUrl)}')" class="comm-send-btn">
                    ${icon('lucide:send', 18)}
                </button>
            </div>
        </div>` : '';

    const closedBanner = isClosed ? `
        <div class="flex-shrink-0 bg-zinc-50 border-t border-zinc-200 px-4 py-3 text-center text-xs text-zinc-400">
            ${q.status_id === 2 ? 'この質問は解決済みです' : 'この質問は受付を終了しました'}
        </div>` : '';

    document.getElementById('qa-detail-content').innerHTML = `
        <div class="comm-qa-scroll">
            <div class="comm-qa-inner">
                <div class="qa-question-card">
                    <div class="flex items-center gap-2 mb-3 flex-wrap">
                        ${q.author.avatar
                            ? `<img src="${escHtml(q.author.avatar)}" class="h-8 w-8 rounded-full object-cover border border-zinc-100" alt="">`
                            : `<div class="h-8 w-8 rounded-full bg-zinc-100 flex items-center justify-center">${icon('lucide:user', 16)}</div>`}
                        <a href="${escHtml(q.author.profile_url || '#')}" class="text-xs font-bold text-zinc-900 hover:underline">${escHtml(q.author.name)}</a>
                        <span class="text-[10px] text-zinc-400">• ${escHtml(q.created_at)}</span>
                        ${deadlineHtml}
                        <span class="ml-auto">${editBtn}</span>
                    </div>
                    <div id="qa-question-display">
                        <h1 class="text-lg font-bold text-zinc-900 mb-3 leading-snug">${escHtml(q.title)}</h1>
                        <p class="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap">${escHtml(q.content)}</p>
                    </div>
                    ${editForm}
                </div>
                <div class="flex items-center justify-between px-1 mb-4">
                    <h3 class="font-bold text-zinc-900 text-sm">回答 <span class="text-zinc-400 font-normal ml-1">${answers.length}件</span></h3>
                </div>
                <div id="qa-answers-list" class="space-y-4">${answersHtml}</div>
            </div>
        </div>
        ${answerForm}
        ${closedBanner}
    `;
    refreshIcons();
}

function buildAnswerHTML(a, postUrl, isClosed, isOwner) {
    const avatarHTML = a.author.avatar
        ? `<img src="${escHtml(a.author.avatar)}" class="h-9 w-9 rounded-full object-cover border border-zinc-100 flex-shrink-0" alt="">`
        : `<div class="h-9 w-9 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">${icon('lucide:user', 16)}</div>`;

    const repliesHTML = (a.replies || []).map(r => {
        const rAvatar = r.author.avatar
            ? `<img src="${escHtml(r.author.avatar)}" class="h-7 w-7 rounded-full object-cover border border-zinc-100 flex-shrink-0" alt="">`
            : `<div class="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">${icon('lucide:user', 14)}</div>`;
        return `
        <div class="flex gap-2 pl-2 border-l-2 border-zinc-100">
            ${rAvatar}
            <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 mb-1">
                    <a href="${escHtml(r.author.profile_url || '#')}" class="text-xs font-semibold text-zinc-800 hover:underline">${escHtml(r.author.name)}</a>
                    <span class="text-[10px] text-zinc-400">${escHtml(r.created_at)}</span>
                </div>
                <p class="text-sm text-zinc-700 whitespace-pre-wrap break-words">${escHtml(r.content)}</p>
            </div>
        </div>`;
    }).join('');

    const baBtn = a.can_select_best
        ? `<button onclick="selectBestAnswer(${a.id}, '${escHtml(postUrl.replace('answer/', ''))}answers/${a.id}/best/')"
                   class="qa-best-btn flex items-center gap-1 text-[10px] px-2 py-0.5 border border-zinc-300 text-zinc-500 rounded-full hover:bg-amber-50 hover:border-amber-300 hover:text-amber-600 transition-colors">
               ${icon('lucide:star', 12)} ベストアンサーを選択
           </button>` : '';

    const replyBtn = !isClosed && IS_AUTHENTICATED && !isOwner
        ? `<button onclick="toggleReplyForm(${a.id})" class="qa-reply-btn text-[10px] text-zinc-400 hover:text-pink-500 transition-colors flex items-center gap-1">
               ${icon('lucide:corner-down-right', 12)} 返信する
           </button>` : '';

    const replyForm = !isClosed && IS_AUTHENTICATED && !isOwner ? `
        <div id="reply-form-${a.id}" class="qa-reply-form hidden mt-3 pl-2 border-l-2 border-pink-200">
            <textarea id="reply-input-${a.id}" rows="2" placeholder="返信を入力..."
                      class="w-full border border-zinc-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pink-400 resize-none"></textarea>
            <div class="flex justify-end gap-2 mt-1">
                <button onclick="toggleReplyForm(${a.id})" class="text-xs text-zinc-400 hover:text-zinc-600 px-3 py-1">キャンセル</button>
                <button onclick="postQAReply(${a.id}, '${escHtml(postUrl)}')" class="text-xs bg-pink-600 text-white px-3 py-1 rounded-lg hover:bg-pink-700">送信</button>
            </div>
        </div>` : '';

    return `
    <div id="qa-answer-${a.id}" class="qa-answer-card${a.is_best_answer ? ' best-answer' : ''} animate-fade-in">
        ${a.is_best_answer ? `<div class="qa-answer-best-label">${icon('lucide:check-circle', 14)} ベストアンサー</div>` : ''}
        <div class="qa-answer-body">
            <div class="flex items-start gap-3 mb-3">
                ${avatarHTML}
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-0.5">
                        <a href="${escHtml(a.author.profile_url || '#')}" class="text-sm font-bold text-zinc-900 hover:underline">${escHtml(a.author.name)}</a>
                        <span class="text-[10px] text-zinc-400">${escHtml(a.created_at)}</span>
                    </div>
                    <p class="text-sm text-zinc-700 leading-relaxed whitespace-pre-wrap break-words">${escHtml(a.content)}</p>
                </div>
            </div>
            ${repliesHTML ? `<div class="flex flex-col gap-3 mt-3">${repliesHTML}</div>` : ''}
            ${replyForm}
            <div class="flex items-center gap-3 mt-3">${baBtn}${replyBtn}</div>
        </div>
    </div>`;
}

// ---- Q&A: Post Answer / Reply ----

async function postQAAnswer(postUrl) {
    const textarea = document.getElementById('qa-answer-input');
    const errorEl  = document.getElementById('qa-answer-error');
    if (!textarea) return;
    const content = textarea.value.trim();
    if (!content) { if (errorEl) { errorEl.textContent = '回答内容を入力してください'; errorEl.classList.remove('hidden'); } return; }
    if (errorEl) errorEl.classList.add('hidden');
    try {
        const res = await fetch(postUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ content }),
        });
        const data = await res.json();
        if (data.success) {
            textarea.value = '';
            textarea.style.height = 'auto';
            const list = document.getElementById('qa-answers-list');
            if (list) {
                list.querySelector('p.text-center')?.remove();
                const div = document.createElement('div');
                div.innerHTML = buildAnswerHTML(data.answer, postUrl, false, false);
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
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, parent_answer_id: parentAnswerId }),
        });
        const data = await res.json();
        if (data.success) {
            textarea.value = '';
            document.getElementById(`reply-form-${parentAnswerId}`)?.classList.add('hidden');
            const answerCard = document.getElementById(`qa-answer-${parentAnswerId}`);
            if (answerCard) {
                const replyHTML = `
                <div class="flex gap-2 pl-2 border-l-2 border-zinc-100">
                    <div class="h-7 w-7 rounded-full bg-zinc-100 flex items-center justify-center flex-shrink-0">${icon('lucide:user', 14)}</div>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <a href="${escHtml(data.answer.author.profile_url || '#')}" class="text-xs font-semibold text-zinc-800 hover:underline">${escHtml(data.answer.author.name)}</a>
                            <span class="text-[10px] text-zinc-400">${escHtml(data.answer.created_at)}</span>
                        </div>
                        <p class="text-sm text-zinc-700 whitespace-pre-wrap break-words">${escHtml(data.answer.content)}</p>
                    </div>
                </div>`;
                const repliesContainer = answerCard.querySelector('.flex.flex-col.gap-3');
                const actionsDiv = answerCard.querySelector('.flex.items-center.gap-3.mt-3');
                if (repliesContainer) {
                    repliesContainer.insertAdjacentHTML('beforeend', replyHTML);
                } else if (actionsDiv) {
                    actionsDiv.insertAdjacentHTML('beforebegin', `<div class="flex flex-col gap-3 mt-3">${replyHTML}</div>`);
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
    document.getElementById(`reply-form-${answerId}`)?.classList.toggle('hidden');
}

// ---- Q&A: Edit ----

function toggleQAEdit() {
    const display = document.getElementById('qa-question-display');
    const form    = document.getElementById('qa-edit-form');
    const btn     = document.getElementById('qa-edit-btn');
    if (!display || !form) return;
    const isEditing = !form.classList.contains('hidden');
    if (!isEditing) {
        const titleInput   = document.getElementById('qa-edit-title');
        const contentInput = document.getElementById('qa-edit-content');
        if (titleInput)   titleInput.value   = display.querySelector('h1').textContent;
        if (contentInput) contentInput.value = display.querySelector('p').textContent;
        document.getElementById('qa-edit-error')?.classList.add('hidden');
    }
    display.classList.toggle('hidden', !isEditing);
    form.classList.toggle('hidden', isEditing);
    if (btn) btn.classList.toggle('hidden', !isEditing);
}

async function submitQAEdit(editUrl) {
    const titleInput   = document.getElementById('qa-edit-title');
    const contentInput = document.getElementById('qa-edit-content');
    const errorEl      = document.getElementById('qa-edit-error');
    if (!titleInput || !contentInput) return;
    const title   = titleInput.value.trim();
    const content = contentInput.value.trim();
    if (!title)   { errorEl.textContent = 'タイトルを入力してください'; errorEl.classList.remove('hidden'); return; }
    if (!content) { errorEl.textContent = '本文を入力してください'; errorEl.classList.remove('hidden'); return; }
    errorEl.classList.add('hidden');
    try {
        const res = await fetch(editUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content }),
        });
        const data = await res.json();
        if (data.success) {
            const display = document.getElementById('qa-question-display');
            if (display) {
                display.querySelector('h1').textContent = data.title;
                display.querySelector('p').textContent  = data.content;
            }
            const qaItem = state.qaData.find(q => q.id === state.activeQAId);
            if (qaItem) qaItem.title = data.title;
            toggleQAEdit();
            showToast('質問を更新しました', 'lucide:check-circle', 'text-green-500');
        } else {
            errorEl.textContent = data.message || 'エラーが発生しました';
            errorEl.classList.remove('hidden');
        }
    } catch (e) {
        errorEl.textContent = '通信エラーが発生しました';
        errorEl.classList.remove('hidden');
    }
}

// ---- Q&A: Best Answer ----

async function selectBestAnswer(answerId, selectUrl) {
    if (!confirm('この回答をベストアンサーに選びますか？')) return;
    try {
        const res = await fetch(selectUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.success) {
            document.querySelectorAll('.qa-answer-card').forEach(card => {
                card.classList.remove('best-answer');
                card.querySelector('.qa-answer-best-label')?.remove();
            });
            const answerCard = document.getElementById(`qa-answer-${answerId}`);
            if (answerCard) {
                answerCard.classList.add('best-answer');
                const label = document.createElement('div');
                label.className = 'qa-answer-best-label';
                label.innerHTML = `${icon('lucide:check-circle', 14)} ベストアンサー`;
                answerCard.insertBefore(label, answerCard.firstChild);
            }
            document.querySelectorAll('.qa-best-btn').forEach(btn => btn.remove());
            document.querySelectorAll('.qa-reply-btn').forEach(btn => btn.remove());
            document.querySelectorAll('.qa-reply-form').forEach(f => f.classList.add('hidden'));

            const answerFormEl = document.getElementById('qa-answer-form') || document.querySelector('.comm-qa-answer-input');
            if (answerFormEl) {
                const banner = document.createElement('div');
                banner.className = 'flex-shrink-0 bg-zinc-50 border-t border-zinc-200 px-4 py-3 text-center text-xs text-zinc-400';
                banner.textContent = 'この質問は解決済みです';
                answerFormEl.replaceWith(banner);
            }

            const headerTitle = document.getElementById('qa-header-title');
            if (headerTitle) {
                headerTitle.innerHTML = `Q&A <span class="ml-2 px-2 py-0.5 rounded text-[10px] font-bold border bg-green-50 text-green-700 border-green-200">解決済み</span>`;
            }

            const qaItem = state.qaData.find(q => q.id === state.activeQAId);
            if (qaItem) qaItem.status_id = 2;

            showToast('ベストアンサーを選択しました', 'lucide:check-circle', 'text-green-500');
            refreshIcons();
        } else {
            showToast(data.message || 'エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
        }
    } catch (e) {
        showToast('通信エラーが発生しました', 'lucide:alert-circle', 'text-red-500');
    }
}

// ---- Q&A: Create Modal ----

function openQACreateModal() {
    const modal = document.getElementById('qa-create-modal');
    if (!modal) return;
    const sel = document.getElementById('qa-create-category');
    if (sel && QA_CATEGORIES) {
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
    refreshIcons();
}
function closeQACreateModal() {
    const modal = document.getElementById('qa-create-modal');
    if (modal) { modal.classList.add('hidden'); modal.classList.remove('flex'); }
}
function closeQACreateModalOutside(e) {
    if (e.target === document.getElementById('qa-create-modal')) closeQACreateModal();
}

async function submitQAQuestion() {
    const title      = document.getElementById('qa-create-title').value.trim();
    const content    = document.getElementById('qa-create-content').value.trim();
    const categoryId = document.getElementById('qa-create-category').value;
    const errorEl    = document.getElementById('qa-create-error');
    const submitBtn  = document.getElementById('qa-create-submit');

    if (!title)   { errorEl.textContent = 'タイトルを入力してください'; errorEl.classList.remove('hidden'); return; }
    if (!content) { errorEl.textContent = '本文を入力してください'; errorEl.classList.remove('hidden'); return; }
    errorEl.classList.add('hidden');
    if (submitBtn) submitBtn.disabled = true;

    try {
        const res = await fetch(QA_CREATE_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrf(), 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content, category_id: categoryId || null }),
        });
        const data = await res.json();
        if (data.success) {
            window.location.href = QA_DETAIL_URL_BASE.replace('/0/', `/${data.question_id}/`);
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

// =============================================
// Image Modal
// =============================================

function openImgModal(src) {
    const modal = document.getElementById('img-modal');
    document.getElementById('img-modal-src').src = src;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}
function closeImgModal() {
    const modal = document.getElementById('img-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// =============================================
// Toast
// =============================================

function showToast(message, toastIcon, colorClass) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = 'bg-white border border-zinc-200 shadow-xl rounded-xl p-4 flex items-center gap-3 animate-slide-in min-w-[280px] pointer-events-auto';
    toast.innerHTML = `
        <div class="h-8 w-8 bg-zinc-50 rounded-full flex items-center justify-center flex-shrink-0 ${colorClass}">
            ${icon(toastIcon, 18)}
        </div>
        <p class="text-sm font-semibold text-zinc-900">${escHtml(message)}</p>`;
    container.appendChild(toast);
    refreshIcons();
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// =============================================
// INIT
// =============================================

document.addEventListener('DOMContentLoaded', () => {

    // カテゴリプルダウン初期化
    initCategorySelects();

    // グループチャット: 検索・カテゴリ・ソート
    const chatSearch = document.getElementById('chat-search-input');
    if (chatSearch) {
        let timer;
        chatSearch.addEventListener('input', e => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                state.chatSearch = e.target.value.trim();
                updateChatClearBtn();
                loadBoardList(true);
            }, 300);
        });
    }
    const chatCat = document.getElementById('chat-category-select');
    if (chatCat) {
        chatCat.addEventListener('change', e => {
            state.chatCategory = e.target.value;
            updateChatClearBtn();
            loadBoardList(true);
        });
    }
    document.querySelectorAll('.comm-sort-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.comm-sort-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.chatSort = btn.dataset.sort;
            loadBoardList(true);
        });
    });

    // Q&A: 検索・カテゴリ
    const qaSearch = document.getElementById('qa-search-input');
    if (qaSearch) {
        let timer;
        qaSearch.addEventListener('input', e => {
            clearTimeout(timer);
            timer = setTimeout(() => {
                state.qaSearch = e.target.value.trim();
                updateQAClearBtn();
                renderQACards();
            }, 250);
        });
    }
    const qaCat = document.getElementById('qa-category-select');
    if (qaCat) {
        qaCat.addEventListener('change', e => {
            state.qaCategory = e.target.value;
            updateQAClearBtn();
            renderQACards();
        });
    }

    // チャット入力: Enter送信
    const chatInput = document.getElementById('chat-message-input');
    if (chatInput) {
        chatInput.addEventListener('keydown', e => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        });
    }

    // 初期タブ処理（URLで決定済み）
    const params = new URLSearchParams(window.location.search);
    const qaParam    = params.get('qa');
    const boardParam = params.get('board');
    const initialTab = (typeof INITIAL_TAB !== 'undefined') ? INITIAL_TAB : 'chat';

    state.activeTab = initialTab;

    if (initialTab === 'qa') {
        if (qaParam) {
            const qId = parseInt(qaParam, 10);
            if (!isNaN(qId)) {
                window.location.href = QA_DETAIL_URL_BASE.replace('/0/', `/${qId}/`);
                return;
            }
        }
        loadQAList();
    } else if (boardParam) {
        const bId = parseInt(boardParam, 10);
        if (!isNaN(bId)) {
            window.location.href = BOARD_DETAIL_URL_BASE.replace('/0/', `/${bId}/`);
            return;
        } else {
            loadBoardList(true);
        }
    } else {
        loadBoardList(true);
    }
});
