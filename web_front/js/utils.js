// ========== Common UI Utilities ==========
// Modal
window.Modal = {
    show(title, bodyHtml, onConfirm) {
        // Remove existing modal
        const existing = document.querySelector('.modal-overlay');
        if (existing) existing.remove();

        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay show';
        overlay.innerHTML = `
            <div class="modal modal-lg">
                <div class="modal-header"><h3>${title}</h3><button class="modal-close">&times;</button></div>
                <div class="modal-body">${bodyHtml}</div>
                <div class="modal-footer">
                    <button class="btn btn-outline cancel-btn">取消</button>
                    <button class="btn btn-primary confirm-btn">确认</button>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);

        const close = () => overlay.remove();
        overlay.querySelector('.modal-close').onclick = close;
        overlay.querySelector('.cancel-btn').onclick = close;
        overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

        overlay.querySelector('.confirm-btn').onclick = async () => {
            const btn = overlay.querySelector('.confirm-btn');
            btn.disabled = true;
            btn.textContent = '处理中...';
            try {
                const result = await onConfirm();
                if (result !== false) close();
            } catch (e) {
                Toast.error(e.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '确认';
            }
        };
    }
};

// Toast
window.Toast = {
    show(msg, type = 'success') {
        const container = document.querySelector('.toast-container') || (() => {
            const el = document.createElement('div');
            el.className = 'toast-container';
            document.body.appendChild(el);
            return el;
        })();
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = msg;
        container.appendChild(toast);
        setTimeout(() => { toast.style.opacity = '0'; setTimeout(() => toast.remove(), 300); }, 3000);
    },
    success(msg) { this.show(msg, 'success'); },
    error(msg) { this.show(msg, 'error'); },
    warning(msg) { this.show(msg, 'warning'); }
};

// Shortcuts
function $(id) { return document.getElementById(String(id).replace(/^#/, '')); }
function $$(sel) { return document.querySelector(sel); }

// Status Tags
function statusTag(status) {
    const map = {
        'AUDITING': '<span class="tag tag-warning">审核中</span>',
        'BORROWING': '<span class="tag tag-info">使用中</span>',
        'RETURN': '<span class="tag tag-success">已归还</span>',
        'REJECT': '<span class="tag tag-danger">已驳回</span>',
        'WAITING': '<span class="tag tag-warning">待处理</span>',
        'REPAIRING': '<span class="tag tag-info">维修中</span>',
        'DONE': '<span class="tag tag-success">已完成</span>',
        'FINISHED': '<span class="tag tag-success">已完成</span>',
        'SCRAPPING': '<span class="tag tag-warning">报废中</span>',
        'SCRAPPED': '<span class="tag tag-success">已报废</span>'
    };
    return map[status] || `<span class="tag">${status}</span>`;
}
