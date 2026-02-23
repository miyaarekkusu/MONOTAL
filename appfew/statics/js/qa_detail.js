/**
 * qa_detail.js — Q&A詳細ページ用
 */

/* ===== Utility ===== */
function getCsrfToken() {
    const c = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return c ? c.split('=')[1] : '';
}

function escapeHtml(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function showToast(msg, type) {
    const c = document.getElementById('toast-container');
    if (!c) return;
    const t = document.createElement('div');
    t.className = `community-toast ${type === 'error' ? 'community-toast-error' : 'community-toast-success'}`;
    t.textContent = msg;
    c.appendChild(t);
    requestAnimationFrame(() => t.classList.add('show'));
    setTimeout(() => {
        t.classList.remove('show');
        setTimeout(() => t.remove(), 300);
    }, 3000);
}

/* ===== Answer Modal ===== */
function openAnswerModal() {
    const modal = document.getElementById('qa-answer-modal');
    if (modal) {
        modal.classList.remove('hidden');
        document.getElementById('qa-answer-input').focus();
    }
}

function closeAnswerModal() {
    const modal = document.getElementById('qa-answer-modal');
    if (modal) modal.classList.add('hidden');
}

/* ===== Post Answer ===== */
async function postQAAnswer() {
    const input = document.getElementById('qa-answer-input');
    const content = input.value.trim();
    if (!content) return;

    const btn = document.getElementById('qa-answer-submit');
    btn.disabled = true;

    try {
        const res = await fetch(QA_POST_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ content }),
        });
        const data = await res.json();
        if (data.success) {
            input.value = '';
            closeAnswerModal();
            appendAnswer(data.answer);
            showToast('回答を投稿しました', 'success');
        } else {
            showToast(data.message || 'エラーが発生しました', 'error');
        }
    } catch {
        showToast('通信エラーが発生しました', 'error');
    } finally {
        btn.disabled = false;
    }
}

function appendAnswer(ans) {
    const list = document.getElementById('qa-answers-list');
    // Remove empty state
    const empty = document.getElementById('qa-no-answers');
    if (empty) empty.remove();

    const div = document.createElement('div');
    div.className = 'bg-white border border-zinc-200 rounded-2xl p-5';
    div.setAttribute('data-answer-id', ans.id);

    const avatarHtml = ans.author.avatar
        ? `<img src="${escapeHtml(ans.author.avatar)}" class="h-7 w-7 rounded-full object-cover" alt="">`
        : `<div class="h-7 w-7 rounded-full bg-zinc-200 flex items-center justify-center"><span class="iconify text-zinc-400" data-icon="lucide:user" data-width="12"></span></div>`;

    div.innerHTML = `
        <div class="flex items-center gap-2 mb-2">
            <a href="${escapeHtml(ans.author.profile_url)}" class="flex items-center gap-2 hover:opacity-80 transition-opacity">
                ${avatarHtml}
                <span class="text-sm font-semibold text-zinc-700">${escapeHtml(ans.author.name)}</span>
            </a>
            <span class="text-[10px] text-zinc-400">${escapeHtml(ans.created_at)}</span>
        </div>
        <div class="text-sm text-zinc-700 whitespace-pre-wrap leading-relaxed mb-3">${escapeHtml(ans.content)}</div>
        <div class="mt-3 ml-6 border-l-2 border-zinc-100 pl-4 space-y-3 hidden" id="replies-${ans.id}"></div>
    `;

    list.appendChild(div);
    if (typeof Iconify !== 'undefined') Iconify.scan(div);

    // Update count
    const countEl = document.getElementById('answer-count');
    if (countEl) {
        const current = parseInt(countEl.textContent) || 0;
        countEl.textContent = (current + 1) + '件';
    }
}

/* ===== Post Reply ===== */
async function postQAReply(questionId, parentAnswerId) {
    const input = document.getElementById('reply-input-' + parentAnswerId);
    const content = input.value.trim();
    if (!content) return;

    try {
        const res = await fetch(QA_POST_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify({ content, parent_answer_id: parentAnswerId }),
        });
        const data = await res.json();
        if (data.success) {
            input.value = '';
            document.getElementById('reply-form-' + parentAnswerId).classList.add('hidden');
            appendReply(parentAnswerId, data.answer);
            showToast('返信を投稿しました', 'success');
        } else {
            showToast(data.message || 'エラーが発生しました', 'error');
        }
    } catch {
        showToast('通信エラーが発生しました', 'error');
    }
}

function appendReply(parentId, reply) {
    const container = document.getElementById('replies-' + parentId);
    if (!container) return;
    container.classList.remove('hidden');

    const div = document.createElement('div');
    div.className = 'py-2';

    const avatarHtml = reply.author.avatar
        ? `<img src="${escapeHtml(reply.author.avatar)}" class="h-6 w-6 rounded-full object-cover" alt="">`
        : `<div class="h-6 w-6 rounded-full bg-zinc-200 flex items-center justify-center"><span class="iconify text-zinc-400" data-icon="lucide:user" data-width="10"></span></div>`;

    div.innerHTML = `
        <div class="flex items-center gap-2 mb-1">
            <a href="${escapeHtml(reply.author.profile_url)}" class="flex items-center gap-2 hover:opacity-80 transition-opacity">
                ${avatarHtml}
                <span class="text-xs font-semibold text-zinc-600">${escapeHtml(reply.author.name)}</span>
            </a>
            <span class="text-[10px] text-zinc-400">${escapeHtml(reply.created_at)}</span>
        </div>
        <div class="text-sm text-zinc-600 whitespace-pre-wrap">${escapeHtml(reply.content)}</div>
    `;

    container.appendChild(div);
    if (typeof Iconify !== 'undefined') Iconify.scan(div);
}

/* ===== Toggle Reply Form ===== */
function toggleReplyForm(answerId) {
    const form = document.getElementById('reply-form-' + answerId);
    form.classList.toggle('hidden');
    if (!form.classList.contains('hidden')) {
        document.getElementById('reply-input-' + answerId).focus();
    }
}

/* ===== Select Best Answer ===== */
async function selectBestAnswer(answerId) {
    if (!confirm('この回答をベストアンサーに選びますか？')) return;
    const url = QA_SELECT_BEST_BASE.replace('/0/', '/' + answerId + '/');
    try {
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        });
        const data = await res.json();
        if (data.success) {
            showToast('ベストアンサーを選択しました', 'success');
            location.reload();
        } else {
            showToast(data.message || 'エラーが発生しました', 'error');
        }
    } catch {
        showToast('通信エラーが発生しました', 'error');
    }
}

/* ===== Edit Question ===== */
function toggleQAEdit() {
    const display = document.getElementById('qa-display');
    const form = document.getElementById('qa-edit-form');
    const btn = document.getElementById('qa-edit-btn');

    if (form.classList.contains('hidden')) {
        display.classList.add('hidden');
        form.classList.remove('hidden');
        btn.classList.add('hidden');
        // カテゴリ選択肢を設定
        const sel = document.getElementById('qa-edit-category');
        if (sel.options.length <= 1 && typeof QA_CATEGORIES !== 'undefined') {
            QA_CATEGORIES.forEach(c => {
                const o = document.createElement('option');
                o.value = c.id;
                o.textContent = c.name;
                if (c.id === QA_CURRENT_CATEGORY_ID) o.selected = true;
                sel.appendChild(o);
            });
        }
    } else {
        display.classList.remove('hidden');
        form.classList.add('hidden');
        btn.classList.remove('hidden');
    }
}

async function submitQAEdit() {
    if (typeof QA_EDIT_URL === 'undefined') return;

    const title = document.getElementById('qa-edit-title').value.trim();
    const content = document.getElementById('qa-edit-content').value.trim();
    const category_id = document.getElementById('qa-edit-category').value;

    if (!title || !content) {
        showToast('タイトルと本文は必須です', 'error');
        return;
    }

    try {
        const res = await fetch(QA_EDIT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ title, content, category_id: category_id ? parseInt(category_id) : null }),
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('qa-title-display').textContent = title;
            document.getElementById('qa-content-display').textContent = content;
            toggleQAEdit();
            showToast('質問を更新しました', 'success');
        } else {
            showToast(data.message || 'エラーが発生しました', 'error');
        }
    } catch {
        showToast('通信エラーが発生しました', 'error');
    }
}
