// ========== Borrow Management Page (资产领用管理) ==========
Router.register('borrow', async (container) => {
    const user = Auth.getUser();
    container.innerHTML = `
        <div class="page-borrow">
            <div class="tabs">
                <div class="tab active" onclick="BorrowPage.switchTab('apply')">领用申请</div>
                <div class="tab" onclick="BorrowPage.switchTab('list')">我的领用记录</div>
            </div>
            <div id="borrow-tab-apply">
                <div class="card">
                    <div class="card-header"><h3>提交领用申请</h3></div>
                    <div class="card-body">
                        <div class="form-row">
                            <div class="form-group"><label>资产ID <span class="required">*</span></label><input id="b-asset-id" placeholder="请输入资产ID（可从资产台账查看）"></div>
                            <div class="form-group"><label>领用开始时间 <span class="required">*</span></label><input id="b-start-time" type="datetime-local"></div>
                        </div>
                        <div class="form-row">
                            <div class="form-group"><label>预计归还时间</label><input id="b-end-time" type="datetime-local"></div>
                            <div class="form-group"></div>
                        </div>
                        <div class="form-group"><label>领用说明 <span class="required">*</span></label><textarea id="b-desc" rows="3" placeholder="请说明领用原因和用途..."></textarea></div>
                        <button class="btn btn-primary" onclick="BorrowPage.submit()">提交申请</button>
                    </div>
                </div>
                <div class="card" style="margin-top:20px;">
                    <div class="card-header"><h3>审批流程说明</h3></div>
                    <div class="card-body">
                        <div class="flow-steps">
                            <div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交申请</div><div class="step-line"></div></div>
                            <div class="flow-step pending"><div class="step-circle">2</div><div class="step-label">学院管理员初审</div><div class="step-line"></div></div>
                            <div class="flow-step pending"><div class="step-circle">3</div><div class="step-label">校级管理员复审</div><div class="step-line"></div></div>
                            <div class="flow-step pending"><div class="step-circle">4</div><div class="step-label">领用完成</div></div>
                        </div>
                        <p style="font-size:13px;color:var(--gray-500);margin-top:12px;">提交后由学院管理员进行初审，通过后由校级管理员进行复审，两级均通过后即可领用资产。</p>
                    </div>
                </div>
            </div>
            <div id="borrow-tab-list" style="display:none;">
                <div class="card">
                    <div class="card-header"><h3>我的领用记录</h3></div>
                    <div class="card-body">
                        <div id="borrow-list-container"><div class="loading"><div class="spinner"></div></div></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.BorrowPage = {
        currentTab: 'apply',
        expandedRows: {},

        init() {
            const assetCtx = sessionStorage.getItem('asset_context');
            if (assetCtx) {
                try {
                    const ctx = JSON.parse(assetCtx);
                    if (ctx.biz_id) {
                        const el = document.getElementById('b-asset-id');
                        if (el) el.value = ctx.biz_id;
                        sessionStorage.removeItem('asset_context');
                    }
                } catch(e) {}
            }
        },

        switchTab(tab) {
            this.currentTab = tab;
            document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', (i===0 && tab==='apply') || (i===1 && tab==='list')));
            document.getElementById('borrow-tab-apply').style.display = tab === 'apply' ? 'block' : 'none';
            document.getElementById('borrow-tab-list').style.display = tab === 'list' ? 'block' : 'none';
            if (tab === 'list') this.loadList();
        },

        async submit() {
            const assetId = $('#b-asset-id').value.trim();
            const startTime = $('#b-start-time').value;
            const endTime = $('#b-end-time').value;
            const desc = $('#b-desc').value.trim();

            if (!assetId || !startTime || !desc) { Toast.error('请填写所有必填项'); return; }

            const data = { asset_biz_id: assetId, borrow_start_time: startTime, borrow_desc: desc };
            if (endTime) data.borrow_end_time = endTime;

            const resp = await API.post('/flow/borrow', data);
            if (resp.code === 200) {
                Toast.success('领用申请已提交，等待审批');
                $('#b-asset-id').value = '';
                $('#b-start-time').value = '';
                $('#b-end-time').value = '';
                $('#b-desc').value = '';
            } else { Toast.error(resp.msg); }
        },

        async loadList() {
            const container = document.getElementById('borrow-list-container');
            try {
                const currentUser = Auth.getUser();
                const resp = await API.get('/flow/borrow/list?user_biz_id=' + currentUser.biz_id);
                if (resp.code !== 200) { container.innerHTML = `<div class="empty-state"><p>${resp.msg}</p></div>`; return; }
                const list = resp.data.list || [];
                // Filter by current user
                const myList = list.filter(b => b.borrow_user_biz_id === currentUser.biz_id);
                if (!myList.length) { container.innerHTML = '<div class="empty-state"><p>暂无领用记录</p></div>'; return; }

                container.innerHTML = myList.map((b, idx) => {
                    const isExpanded = this.expandedRows[b.biz_id];
                    const status = b.borrow_status;
                    const isReturned = status === 'RETURN' || !!b.actual_return_time;
                    const isBorrowing = status === 'BORROWING';

                    let returnLabel = '';
                    if (isReturned && b.actual_return_time && b.borrow_end_time) {
                        returnLabel = b.actual_return_time > b.borrow_end_time
                            ? '<span class="tag tag-danger">逾期归还</span>'
                            : '<span class="tag tag-success">正常归还</span>';
                    }

                    const actionBtn = isBorrowing
                        ? `<button class="btn btn-success btn-xs" onclick="BorrowPage.doReturn('${b.biz_id}')">归还</button>`
                        : '';

                    return `
                    <div class="borrow-item card" style="margin-bottom:10px;border-left:3px solid ${isReturned ? 'var(--success)' : (isBorrowing ? 'var(--info)' : 'var(--warning)')};">
                        <div class="card-body" style="padding:12px 16px;cursor:pointer;" onclick="BorrowPage.toggleRow('${b.biz_id}')">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div style="flex:1;">
                                    <strong>${b.asset_name || b.biz_id}</strong>
                                    <span style="margin:0 10px;color:var(--gray-500);">${b.borrow_desc || '-'}</span>
                                    <span style="color:var(--gray-400);font-size:12px;">${b.borrow_start_time || '-'} ~ ${b.borrow_end_time || '-'}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:8px;" onclick="event.stopPropagation()">
                                    ${statusTag(status)} ${returnLabel} ${actionBtn}
                                    <span style="color:var(--gray-400);">${isExpanded ? '▲' : '▼'}</span>
                                </div>
                            </div>
                        </div>
                        <div id="borrow-detail-${b.biz_id}" class="borrow-detail" style="display:${isExpanded ? 'block' : 'none'};padding:0 16px 16px;border-top:1px solid var(--gray-200);">
                            ${isExpanded ? '<div class="loading"><div class="spinner"></div></div>' : ''}
                        </div>
                    </div>`;
                }).join('');
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
            }
        },

        async toggleRow(bizId) {
            const detail = document.getElementById(`borrow-detail-${bizId}`);
            const isOpen = detail.style.display === 'block';

            if (isOpen) {
                detail.style.display = 'none';
                this.expandedRows[bizId] = false;
                return;
            }

            detail.style.display = 'block';
            detail.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            this.expandedRows[bizId] = true;

            // 找到该行数据中的 flow_biz_id
            const list = await this._getList();
            const item = list.find(b => b.biz_id === bizId);
            if (!item || !item.flow_biz_id) {
                detail.innerHTML = '<div class="empty-state"><p>暂无审批进度信息</p></div>';
                return;
            }

            try {
                const resp = await API.get(`/flow/progress?flow_biz_id=${item.flow_biz_id}`);
                if (resp.code !== 200) {
                    detail.innerHTML = `<div class="empty-state"><p>${resp.msg}</p></div>`;
                    return;
                }

                const data = resp.data;
                const steps = data.steps || [];
                const finalResult = data.final_result || '';

                detail.innerHTML = `
                    <div style="margin-top:12px;">
                        <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;">
                            <strong>资产编号：</strong>${item.asset_biz_id || '-'}
                        </div>
                        <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;">
                            <strong>领用说明：</strong>${item.borrow_desc || '-'}
                        </div>
                        ${item.actual_return_time ? `<div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>实际归还时间：</strong>${item.actual_return_time}</div>` : ''}
                        <div style="font-size:14px;font-weight:600;margin-bottom:10px;">审批进度</div>
                        ${BorrowPage._renderTimeline(steps, finalResult)}
                    </div>
                `;
            } catch (e) {
                detail.innerHTML = '<div class="empty-state"><p>加载进度失败</p></div>';
            }
        },

        _renderTimeline(steps, finalResult) {
            const resultLabel = { 'PASS': '已通过', 'REJECT': '已驳回', 'WAIT': '待审批' };
            if (!steps.length) {
                return `<div class="flow-steps" style="margin-top:8px;">
                    <div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交申请</div></div>
                    <div class="flow-step ${finalResult === 'PASS' ? 'active' : (finalResult === 'REJECT' ? 'rejected' : 'pending')}"><div class="step-circle">2</div><div class="step-label">等待审批</div></div>
                </div>`;
            }

            let html = '<div class="flow-steps" style="margin-top:8px;">';
            html += '<div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交申请</div><div class="step-line"></div></div>';

            steps.forEach((s, i) => {
                const isPass = s.result === 'PASS';
                const isReject = s.result === 'REJECT';
                const cls = isPass ? 'active' : (isReject ? 'rejected' : 'pending');
                html += `<div class="flow-step ${cls}">
                    <div class="step-circle">${i + 2}</div>
                    <div class="step-label">${s.step_name}<br><small>${isPass ? '通过' : (isReject ? '驳回' : '')} ${s.audit_time || ''}</small></div>
                    ${i < steps.length - 1 || finalResult === 'PASS' ? '<div class="step-line"></div>' : ''}
                </div>`;
            });

            if (finalResult === 'PASS') {
                html += `<div class="flow-step active"><div class="step-circle">${steps.length + 2}</div><div class="step-label">审批通过</div></div>`;
            } else if (finalResult === 'REJECT') {
                html += `<div class="flow-step rejected"><div class="step-circle">${steps.length + 2}</div><div class="step-label">已驳回</div></div>`;
            } else {
                html += `<div class="flow-step pending"><div class="step-circle">${steps.length + 2}</div><div class="step-label">等待中</div></div>`;
            }
            html += '</div>';
            return html;
        },

        async _getList() {
            const resp = await API.get('/flow/borrow/list');
            return resp.code === 200 ? (resp.data.list || []) : [];
        },

        async doReturn(borrowId) {
            if (!confirm('确认归还该资产？')) return;
            const resp = await API.post('/flow/return', { borrow_biz_id: borrowId });
            if (resp.code === 200) { Toast.success('归还成功'); this.loadList(); } else { Toast.error(resp.msg); }
        }
    };

    BorrowPage.init();
});

// CSS support for rejected step
if (!document.getElementById('borrow-timeline-css')) {
    const style = document.createElement('style');
    style.id = 'borrow-timeline-css';
    style.textContent = '.flow-step.rejected .step-circle{background:var(--danger);}.flow-step.rejected .step-label{color:var(--danger);}';
    document.head.appendChild(style);
}
