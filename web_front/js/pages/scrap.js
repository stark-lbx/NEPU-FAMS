// ========== Scrap Management Page (资产报废) ==========
Router.register('scrap', async (container) => {
    container.innerHTML = `
        <div class="page-scrap">
            <div class="tabs">
                <div class="tab active" onclick="ScrapPage.switchTab('apply')">报废申请</div>
                <div class="tab" onclick="ScrapPage.switchTab('list')">我的报废记录</div>
            </div>
            <div id="scrap-tab-apply">
                <div class="card">
                    <div class="card-header"><h3>提交报废申请</h3></div>
                    <div class="card-body">
                        <div class="form-group"><label>资产ID <span class="required">*</span></label><input id="s-asset-id" placeholder="请输入需要报废的资产ID"></div>
                        <div class="form-group"><label>报废原因 <span class="required">*</span></label><textarea id="s-reason" rows="4" placeholder="请说明报废原因，如：设备老化无法修复、技术淘汰等..."></textarea></div>
                        <button class="btn btn-danger" onclick="ScrapPage.submit()">提交申请</button>
                    </div>
                </div>
                <div class="card" style="margin-top:20px;">
                    <div class="card-header"><h3>审批流程说明</h3></div>
                    <div class="card-body">
                        <div class="flow-steps">
                            <div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交申请</div><div class="step-line"></div></div>
                            <div class="flow-step pending"><div class="step-circle">2</div><div class="step-label">学院管理员初审</div><div class="step-line"></div></div>
                            <div class="flow-step pending"><div class="step-circle">3</div><div class="step-label">校级管理员复审</div><div class="step-line"></div></div>
                            <div class="flow-step pending"><div class="step-circle">4</div><div class="step-label">报废完成</div></div>
                        </div>
                    </div>
                </div>
            </div>
            <div id="scrap-tab-list" style="display:none;">
                <div class="card">
                    <div class="card-header"><h3>我的报废记录</h3></div>
                    <div class="card-body" id="scrap-list-container">
                        <div class="loading"><div class="spinner"></div></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.ScrapPage = {
        currentTab: 'apply',
        expandedRows: {},

        init() {
            const assetCtx = sessionStorage.getItem('asset_context');
            if (assetCtx) {
                try {
                    const ctx = JSON.parse(assetCtx);
                    if (ctx.biz_id) {
                        const el = document.getElementById('s-asset-id');
                        if (el) el.value = ctx.biz_id;
                        sessionStorage.removeItem('asset_context');
                    }
                } catch(e) {}
            }
        },

        switchTab(tab) {
            this.currentTab = tab;
            document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', (i===0 && tab==='apply') || (i===1 && tab==='list')));
            document.getElementById('scrap-tab-apply').style.display = tab === 'apply' ? 'block' : 'none';
            document.getElementById('scrap-tab-list').style.display = tab === 'list' ? 'block' : 'none';
            if (tab === 'list') this.loadList();
        },

        async submit() {
            const assetId = $('#s-asset-id').value.trim();
            const reason = $('#s-reason').value.trim();
            if (!assetId || !reason) { Toast.error('请填写资产ID和报废原因'); return; }
            const resp = await API.post('/flow/scrap', { asset_biz_id: assetId, scrap_reason: reason });
            if (resp.code === 200) { Toast.success('报废申请已提交'); $('#s-asset-id').value=''; $('#s-reason').value=''; }
            else { Toast.error(resp.msg); }
        },

        async loadList() {
            const container = document.getElementById('scrap-list-container');
            try {
                const currentUser = Auth.getUser();
                const resp = await API.get('/flow/scrap/list');
                if (resp.code !== 200) { container.innerHTML = `<div class="empty-state"><p>${resp.msg}</p></div>`; return; }
                const list = resp.data.list || [];
                const myList = list.filter(s => s.apply_user_biz_id === currentUser.biz_id);
                if (!myList.length) { container.innerHTML = '<div class="empty-state"><p>暂无报废记录</p></div>'; return; }

                container.innerHTML = myList.map((s) => {
                    const isExpanded = this.expandedRows[s.biz_id];
                    const isApproved = s.scrap_status === 'SCRAPPED';
                    const isRejected = s.scrap_status === 'REJECT';
                    const color = isApproved ? 'var(--success)' : (isRejected ? 'var(--danger)' : 'var(--warning)');

                    return `
                    <div class="card" style="margin-bottom:10px;border-left:3px solid ${color};">
                        <div class="card-body" style="padding:12px 16px;cursor:pointer;" onclick="ScrapPage.toggleRow('${s.biz_id}')">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div style="flex:1;">
                                    <strong>${s.asset_name || s.biz_id}</strong>
                                    <span style="margin:0 10px;color:var(--gray-500);">${s.scrap_reason || '-'}</span>
                                    <span style="color:var(--gray-400);font-size:12px;">${s.create_time || '-'}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:8px;" onclick="event.stopPropagation()">
                                    ${statusTag(s.scrap_status)}
                                    <span style="color:var(--gray-400);">${isExpanded ? '▲' : '▼'}</span>
                                </div>
                            </div>
                        </div>
                        <div id="scrap-detail-${s.biz_id}" style="display:${isExpanded ? 'block' : 'none'};padding:0 16px 16px;border-top:1px solid var(--gray-200);">
                            ${isExpanded ? '<div class="loading"><div class="spinner"></div></div>' : ''}
                        </div>
                    </div>`;
                }).join('');
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
            }
        },

        async toggleRow(bizId) {
            const detail = document.getElementById(`scrap-detail-${bizId}`);
            const isOpen = detail.style.display === 'block';

            if (isOpen) { detail.style.display = 'none'; this.expandedRows[bizId] = false; return; }

            detail.style.display = 'block';
            detail.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            this.expandedRows[bizId] = true;

            const list = await this._getList();
            const item = list.find(s => s.biz_id === bizId);
            if (!item) { detail.innerHTML = '<div class="empty-state"><p>未找到记录</p></div>'; return; }

            let detailHtml = `
                <div style="margin-top:12px;">
                    <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>申请ID：</strong>${item.biz_id || '-'}</div>
                    <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>资产ID：</strong>${item.asset_biz_id || '-'}</div>
                    <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>报废原因：</strong>${item.scrap_reason || '-'}</div>
                    <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>申请时间：</strong>${item.create_time || '-'}</div>`;

            if (item.flow_biz_id) {
                try {
                    const resp = await API.get(`/flow/progress?flow_biz_id=${item.flow_biz_id}`);
                    if (resp.code === 200) {
                        const steps = resp.data.steps || [];
                        const finalResult = resp.data.final_result || '';
                        detailHtml += `<div style="font-size:14px;font-weight:600;margin:14px 0 8px;">审批进度</div>`;
                        detailHtml += ScrapPage._renderTimeline(steps, finalResult);
                    }
                } catch (e) { /* ignore progress loading failure */ }
            }

            detailHtml += '</div>';
            detail.innerHTML = detailHtml;
        },

        _renderTimeline(steps, finalResult) {
            if (!steps.length) {
                return `<div class="flow-steps" style="margin-top:8px;">
                    <div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交报废申请</div></div>
                    <div class="flow-step ${finalResult === 'PASS' ? 'active' : (finalResult === 'REJECT' ? 'rejected' : 'pending')}"><div class="step-circle">2</div><div class="step-label">等待审批</div></div>
                </div>`;
            }

            let html = '<div class="flow-steps" style="margin-top:8px;">';
            html += '<div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交报废申请</div><div class="step-line"></div></div>';

            steps.forEach((s, i) => {
                const isPass = s.result === 'PASS';
                const isReject = s.result === 'REJECT';
                const cls = isPass ? 'active' : (isReject ? 'rejected' : 'pending');
                const auditor = s.auditor_user_name ? `<br><small style="color:var(--gray-500);">${s.auditor_user_name}</small>` : '';
                html += `<div class="flow-step ${cls}">
                    <div class="step-circle">${i + 2}</div>
                    <div class="step-label">${s.step_name}${auditor}<br><small>${isPass ? '通过' : (isReject ? '驳回' : '')} ${s.audit_time || ''}</small></div>
                    ${i < steps.length - 1 || finalResult === 'PASS' ? '<div class="step-line"></div>' : ''}
                </div>`;
            });

            if (finalResult === 'PASS') html += `<div class="flow-step active"><div class="step-circle">${steps.length + 2}</div><div class="step-label">报废完成</div></div>`;
            else if (finalResult === 'REJECT') html += `<div class="flow-step rejected"><div class="step-circle">${steps.length + 2}</div><div class="step-label">已驳回</div></div>`;
            else html += `<div class="flow-step pending"><div class="step-circle">${steps.length + 2}</div><div class="step-label">等待中</div></div>`;
            html += '</div>';
            return html;
        },

        async _getList() {
            const currentUser = Auth.getUser();
            const resp = await API.get('/flow/scrap/list');
            if (resp.code !== 200) return [];
            return (resp.data.list || []).filter(s => s.apply_user_biz_id === currentUser.biz_id);
        }
    };

    ScrapPage.init();
});

// CSS support for rejected step
if (!document.getElementById('scrap-timeline-css')) {
    const style = document.createElement('style');
    style.id = 'scrap-timeline-css';
    style.textContent = '.flow-step.rejected .step-circle{background:var(--danger);}.flow-step.rejected .step-label{color:var(--danger);}';
    document.head.appendChild(style);
}
