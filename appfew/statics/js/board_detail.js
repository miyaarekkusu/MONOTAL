/**
 * board_detail.js — 掲示板詳細ページ用
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

/* ===== Auto scroll to bottom ===== */
document.addEventListener('DOMContentLoaded', () => {
    const area = document.getElementById('board-messages-area');
    if (area) area.scrollTop = area.scrollHeight;
});

/* ===== Textarea auto resize ===== */
function boardAutoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

/* ===== Send Message ===== */
async function sendBoardMessage() {
    const input = document.getElementById('board-message-input');
    const fileInput = document.getElementById('board-file-input');
    const productId = document.getElementById('board-selected-product-id').value;
    const content = input.value.trim();
    const errEl = document.getElementById('board-post-error');
    errEl.classList.add('hidden');

    if (!content && !fileInput.files[0] && !productId) return;

    const btn = document.getElementById('board-send-btn');
    btn.disabled = true;

    const fd = new FormData();
    if (content) fd.append('message_content', content);
    if (fileInput.files[0]) fd.append('image', fileInput.files[0]);
    if (productId) fd.append('product_link_id', productId);

    try {
        const res = await fetch(POST_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: fd,
        });
        const data = await res.json();
        if (data.success) {
            appendMessage(data.msg);
            input.value = '';
            input.style.height = 'auto';
            clearBoardImage();
            clearBoardProduct();
        } else {
            const msg = data.errors ? Object.values(data.errors).join(', ') : (data.message || 'エラー');
            errEl.textContent = msg;
            errEl.classList.remove('hidden');
        }
    } catch {
        errEl.textContent = '通信エラーが発生しました';
        errEl.classList.remove('hidden');
    } finally {
        btn.disabled = false;
    }
}

function appendMessage(msg) {
    const area = document.getElementById('board-messages-area');
    // Remove empty state if exists
    const empty = area.querySelector('.text-center.text-zinc-400');
    if (empty && empty.querySelector('[data-icon="lucide:message-square"]')) empty.remove();

    const isMine = msg.is_mine;
    const div = document.createElement('div');
    div.className = `flex gap-3 ${isMine ? 'flex-row-reverse' : ''}`;
    div.setAttribute('data-msg-id', msg.id);

    let avatarHtml = '';
    if (msg.user.avatar) {
        avatarHtml = `<img src="${escapeHtml(msg.user.avatar)}" class="h-8 w-8 rounded-full object-cover" alt="">`;
    } else {
        avatarHtml = `<div class="h-8 w-8 rounded-full bg-zinc-200 flex items-center justify-center"><span class="iconify text-zinc-400" data-icon="lucide:user" data-width="14"></span></div>`;
    }

    let contentHtml = '';
    if (msg.image_url) {
        contentHtml += `<img src="${escapeHtml(msg.image_url)}" class="max-w-full max-h-60 rounded-xl mb-2 cursor-pointer" onclick="openBoardImageModal('${escapeHtml(msg.image_url)}')">`;
    }
    if (msg.product) {
        const pImg = msg.product.image ? `<img src="${escapeHtml(msg.product.image)}" class="h-10 w-10 rounded-lg object-cover" alt="">` : '';
        contentHtml += `<a href="${escapeHtml(msg.product.url)}" class="flex items-center gap-2 bg-white/80 border border-zinc-200 rounded-xl px-3 py-2 mb-2 hover:bg-zinc-50 transition-colors">
            ${pImg}<div class="min-w-0"><p class="text-xs font-semibold text-zinc-800 truncate">${escapeHtml(msg.product.name)}</p></div></a>`;
    }
    if (msg.content) {
        contentHtml += `<p class="whitespace-pre-wrap break-words">${escapeHtml(msg.content)}</p>`;
    }

    const deleteBtn = msg.delete_url
        ? `<button onclick="deleteBoardMessage(${msg.id}, '${escapeHtml(msg.delete_url)}')" class="text-zinc-300 hover:text-red-400 transition-colors"><span class="iconify" data-icon="lucide:trash-2" data-width="12"></span></button>`
        : '';

    div.innerHTML = `
        <a href="${escapeHtml(msg.user.profile_url)}" class="flex-shrink-0">${avatarHtml}</a>
        <div class="max-w-[70%]">
            <div class="flex items-center gap-2 mb-1 ${isMine ? 'justify-end' : ''}">
                <a href="${escapeHtml(msg.user.profile_url)}" class="text-xs font-semibold text-zinc-700 hover:text-pink-600 transition-colors">${escapeHtml(msg.user.name)}</a>
                <span class="text-[10px] text-zinc-400">${escapeHtml(msg.time)}</span>
                ${deleteBtn}
            </div>
            <div class="${isMine ? 'bubble-me' : 'bubble-other'} rounded-2xl px-4 py-2.5 text-sm">${contentHtml}</div>
        </div>`;

    area.appendChild(div);
    if (typeof Iconify !== 'undefined') Iconify.scan(div);
    area.scrollTop = area.scrollHeight;
}

/* ===== Delete Message ===== */
async function deleteBoardMessage(msgId, deleteUrl) {
    if (!confirm('このメッセージを削除しますか？')) return;
    try {
        const res = await fetch(deleteUrl, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken(), 'Content-Type': 'application/json' },
        });
        const data = await res.json();
        if (data.success) {
            const el = document.querySelector(`[data-msg-id="${msgId}"]`);
            if (el) el.remove();
            showToast('メッセージを削除しました', 'success');
        }
    } catch {
        showToast('削除に失敗しました', 'error');
    }
}

/* ===== Image ===== */
function previewBoardImage(input) {
    if (!input.files[0]) return;
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById('board-image-preview').src = e.target.result;
        document.getElementById('board-image-preview-wrap').classList.remove('hidden');
    };
    reader.readAsDataURL(input.files[0]);
}

function clearBoardImage() {
    document.getElementById('board-file-input').value = '';
    document.getElementById('board-image-preview-wrap').classList.add('hidden');
    document.getElementById('board-image-preview').src = '';
}

function openBoardImageModal(url) {
    const modal = document.getElementById('board-image-modal');
    document.getElementById('board-modal-img').src = url;
    modal.style.display = 'flex';
    modal.classList.remove('hidden');
}

function closeBoardImageModal() {
    const modal = document.getElementById('board-image-modal');
    modal.style.display = '';
    modal.classList.add('hidden');
}

/* ===== Product Picker ===== */
function toggleBoardProductPicker() {
    const picker = document.getElementById('board-product-picker');
    picker.classList.toggle('hidden');
}

function selectBoardProduct(id, name) {
    document.getElementById('board-selected-product-id').value = id;
    document.getElementById('board-product-name').textContent = name;
    document.getElementById('board-product-preview').classList.remove('hidden');
    document.getElementById('board-product-picker').classList.add('hidden');
}

function clearBoardProduct() {
    document.getElementById('board-selected-product-id').value = '';
    document.getElementById('board-product-preview').classList.add('hidden');
    document.getElementById('board-product-name').textContent = '';
}

