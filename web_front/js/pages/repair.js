// ========== Repair Management Page (资产报修管理) ==========
Router.register('repair', async (container) => {
    container.innerHTML = `
        <div class="page-repair">
            <div class="tabs">
                <div class="tab active" onclick="RepairPage.switchTab('apply')">提交报修</div>
                <div class="tab" onclick="RepairPage.switchTab('list')">我的报修记录</div>
            </div>
            <div id="repair-tab-apply">
                <div class="card">
                    <div class="card-header"><h3>提交报修工单</h3></div>
                    <div class="card-body">
                        <div class="form-group"><label>资产ID <span class="required">*</span></label><input id="r-asset-id" placeholder="请输入资产ID（可从资产台账查看）"></div>
                        <div class="form-group"><label>故障描述 <span class="required">*</span></label><textarea id="r-fault" rows="4" placeholder="请详细描述故障现象..."></textarea></div>
                        <button class="btn btn-primary" onclick="RepairPage.submit()">提交报修</button>
                    </div>
                </div>
            </div>
            <div id="repair-tab-list" style="display:none;">
                <div class="card">
                    <div class="card-header"><h3>我的报修记录</h3></div>
                    <div class="card-body">
                        <div id="repair-list-container"><div class="loading"><div class="spinner"></div></div></div>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.RepairPage = {
        currentTab: 'apply',
        expandedRows: {},

        init() {
            const assetCtx = sessionStorage.getItem('asset_context');
            if (assetCtx) {
                try {
                    const ctx = JSON.parse(assetCtx);
                    if (ctx.biz_id) {
                        const el = document.getElementById('r-asset-id');
                        if (el) el.value = ctx.biz_id;
                        sessionStorage.removeItem('asset_context');
                    }
                } catch(e) {}
            }
        },

        switchTab(tab) {
            this.currentTab = tab;
            document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', (i===0 && tab==='apply') || (i===1 && tab==='list')));
            document.getElementById('repair-tab-apply').style.display = tab === 'apply' ? 'block' : 'none';
            document.getElementById('repair-tab-list').style.display = tab === 'list' ? 'block' : 'none';
            if (tab === 'list') this.loadList();
        },

        async submit() {
            const assetId = $('#r-asset-id').value.trim();
            const fault = $('#r-fault').value.trim();
            if (!assetId || !fault) { Toast.error('请填写所有必填项'); return; }
            const resp = await API.post('/flow/repair', { asset_biz_id: assetId, fault_desc: fault });
            if (resp.code === 200) { Toast.success('报修工单已提交'); $('#r-asset-id').value=''; $('#r-fault').value=''; }
            else { Toast.error(resp.msg); }
        },

        async loadList() {
            const container = document.getElementById('repair-list-container');
            try {
                const currentUser = Auth.getUser();
                const resp = await API.get('/flow/repair/list');
                if (resp.code !== 200) { container.innerHTML = `<div class="empty-state"><p>${resp.msg}</p></div>`; return; }
                const list = resp.data.list || [];
                const myList = list.filter(r => r.report_user_biz_id === currentUser.biz_id);
                if (!myList.length) { container.innerHTML = '<div class="empty-state"><p>暂无报修记录</p></div>'; return; }

                container.innerHTML = myList.map((r, idx) => {
                    const isExpanded = this.expandedRows[r.biz_id];
                    const isFinished = r.order_status === 'DONE' || r.order_status === 'FINISHED' || !!r.finish_time;
                    const color = isFinished ? 'var(--success)' : (r.order_status === 'REPAIRING' ? 'var(--info)' : 'var(--warning)');

                    return `
                    <div class="card" style="margin-bottom:10px;border-left:3px solid ${color};">
                        <div class="card-body" style="padding:12px 16px;cursor:pointer;" onclick="RepairPage.toggleRow('${r.biz_id}')">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div style="flex:1;">
                                    <strong>${r.asset_name || r.biz_id}</strong>
                                    <span style="margin:0 10px;color:var(--gray-500);">${r.fault_desc || '-'}</span>
                                    <span style="color:var(--gray-400);font-size:12px;">${r.report_time || '-'}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:8px;" onclick="event.stopPropagation()">
                                    ${statusTag(r.order_status)}
                                    ${isFinished ? '<span class="tag tag-success">已完成</span>' : ''}
                                    <span style="color:var(--gray-400);">${isExpanded ? '▲' : '▼'}</span>
                                </div>
                            </div>
                        </div>
                        <div id="repair-detail-${r.biz_id}" style="display:${isExpanded ? 'block' : 'none'};padding:0 16px 16px;border-top:1px solid var(--gray-200);">
                            ${isExpanded ? '<div class="loading"><div class="spinner"></div></div>' : ''}
                        </div>
                    </div>`;
                }).join('');
            } catch (e) {
                container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
            }
        },

        async toggleRow(bizId) {
            const detail = document.getElementById(`repair-detail-${bizId}`);
            const isOpen = detail.style.display === 'block';

            if (isOpen) { detail.style.display = 'none'; this.expandedRows[bizId] = false; return; }

            detail.style.display = 'block';
            detail.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            this.expandedRows[bizId] = true;

            const list = await this._getList();
            const item = list.find(r => r.biz_id === bizId);
            if (!item) { detail.innerHTML = '<div class="empty-state"><p>未找到记录</p></div>'; return; }

            // 渲染详情（不依赖 flow 进度，直接展示已有信息）
            let detailHtml = `
                <div style="margin-top:12px;">
                    <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>故障描述：</strong>${item.fault_desc || '-'}</div>
                    <div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>报修时间：</strong>${item.report_time || '-'}</div>`;

            if (item.repair_user_biz_id) detailHtml += `<div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>维修人员ID：</strong>${item.repair_user_biz_id}</div>`;
            if (item.repair_cost) detailHtml += `<div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>维修费用：</strong>${item.repair_cost}</div>`;
            if (item.repair_result) detailHtml += `<div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>维修结果：</strong>${item.repair_result}</div>`;
            if (item.finish_time) detailHtml += `<div style="font-size:13px;color:var(--gray-600);margin-bottom:8px;"><strong>完成时间：</strong>${item.finish_time}</div>`;

            // 如果有 flow，加载审批进度
            if (item.flow_biz_id) {
                try {
                    const resp = await API.get(`/flow/progress?flow_biz_id=${item.flow_biz_id}`);
                    if (resp.code === 200) {
                        const steps = resp.data.steps || [];
                        const finalResult = resp.data.final_result || '';
                        detailHtml += `<div style="font-size:14px;font-weight:600;margin:14px 0 8px;">审批进度</div>`;
                        detailHtml += RepairPage._renderTimeline(steps, finalResult);
                    }
                } catch (e) { /* ignore progress loading failure */ }
            }

            detailHtml += '</div>';
            detail.innerHTML = detailHtml;
        },

        _renderTimeline(steps, finalResult) {
            const resultLabel = { 'PASS': '已通过', 'REJECT': '已驳回', 'WAIT': '待审批' };
            if (!steps.length) {
                return `<div class="flow-steps" style="margin-top:8px;">
                    <div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交报修</div></div>
                    <div class="flow-step ${finalResult === 'PASS' ? 'active' : (finalResult === 'REJECT' ? 'rejected' : 'pending')}"><div class="step-circle">2</div><div class="step-label">等待审批</div></div>
                </div>`;
            }

            let html = '<div class="flow-steps" style="margin-top:8px;">';
            html += '<div class="flow-step active"><div class="step-circle">1</div><div class="step-label">提交报修</div><div class="step-line"></div></div>';

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

            if (finalResult === 'PASS') html += `<div class="flow-step active"><div class="step-circle">${steps.length + 2}</div><div class="step-label">审批通过</div></div>`;
            else if (finalResult === 'REJECT') html += `<div class="flow-step rejected"><div class="step-circle">${steps.length + 2}</div><div class="step-label">已驳回</div></div>`;
            else html += `<div class="flow-step pending"><div class="step-circle">${steps.length + 2}</div><div class="step-label">等待中</div></div>`;
            html += '</div>';
            return html;
        },

        async _getList() {
            const resp = await API.get('/flow/repair/list');
            return resp.code === 200 ? (resp.data.list || []) : [];
        }
    };

    RepairPage.init();
});
