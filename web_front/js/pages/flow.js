// ========== Flow Approval Page (审批管理 - 管理员专有) ==========
Router.register('flow', async (container) => {
    const user = Auth.getUser();
    const isAdmin = Auth.isAdmin();
    container.innerHTML = `
        <div class="page-flow">
            ${!isAdmin ? '<div class="empty-state"><div class="empty-icon">&#128274;</div><p>您没有审批权限，请联系管理员</p></div>' : `
            <div class="tabs">
                <div class="tab active" onclick="FlowPage.switchTab('pending')">待审批</div>
                <div class="tab" onclick="FlowPage.switchTab('all')">全部记录</div>
            </div>
            <div id="flow-tab-pending">
                <div class="card">
                    <div class="card-header"><h3>待审批事项</h3></div>
                    <div class="card-body" id="pending-flows"><div class="loading"><div class="spinner"></div></div></div>
                </div>
            </div>
            <div id="flow-tab-all" style="display:none;">
                <div class="card">
                    <div class="card-header"><h3>全部审批记录</h3></div>
                    <div class="card-body" id="all-flows"><div class="loading"><div class="spinner"></div></div></div>
                </div>
            </div>
            `}
        </div>
    `;

    if (!isAdmin) return;

    window.FlowPage = {
        currentTab: 'pending',
        expandedRows: {},

        switchTab(tab) {
            this.currentTab = tab;
            document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', (i===0 && tab==='pending') || (i===1 && tab==='all')));
            document.getElementById('flow-tab-pending').style.display = tab === 'pending' ? 'block' : 'none';
            document.getElementById('flow-tab-all').style.display = tab === 'all' ? 'block' : 'none';
            if (tab === 'pending') this.loadPending();
            else this.loadAll();
        },

        toggleRow(id) {
            this.expandedRows[id] = !this.expandedRows[id];
            if (this.currentTab === 'all') this.loadAll();
        },

        buildDetailHTML(item) {
            const ft = item.flowType;
            if (ft === 'borrow') {
                return `
                    <div style="font-size:13px;color:var(--gray-600);margin:8px 0;">
                        <div><strong>申请人：</strong>${item.user_name || item.borrow_user_biz_id}</div>
                        <div><strong>所属部门：</strong>${item.dept_name || '-'}</div>
                        <div><strong>资产名称：</strong>${item.asset_name || item.asset_biz_id} (${item.asset_type_code || '-'})</div>
                        <div><strong>领用时间：</strong>${item.borrow_start_time || '-'} ~ ${item.borrow_end_time || '-'}</div>
                        <div><strong>申请理由：</strong>${item.borrow_desc || '-'}</div>
                        <div><strong>提交时间：</strong>${item.create_time || '-'}</div>
                    </div>`;
            }
            if (ft === 'repair') {
                return `
                    <div style="font-size:13px;color:var(--gray-600);margin:8px 0;">
                        <div><strong>报修人：</strong>${item.user_name || item.report_user_biz_id}</div>
                        <div><strong>所属部门：</strong>${item.dept_name || '-'}</div>
                        <div><strong>资产名称：</strong>${item.asset_name || item.asset_biz_id} (${item.asset_type_code || '-'})</div>
                        <div><strong>故障描述：</strong>${item.fault_desc || '-'}</div>
                        <div><strong>维修费用：</strong>${item.repair_cost ? item.repair_cost + '元' : '-'}</div>
                        <div><strong>维修结果：</strong>${item.repair_result || '-'}</div>
                        <div><strong>报修时间：</strong>${item.report_time || item.create_time || '-'}</div>
                    </div>`;
            }
            if (ft === 'scrap') {
                return `
                    <div style="font-size:13px;color:var(--gray-600);margin:8px 0;">
                        <div><strong>申请人：</strong>${item.user_name || item.apply_user_biz_id}</div>
                        <div><strong>所属部门：</strong>${item.dept_name || '-'}</div>
                        <div><strong>资产名称：</strong>${item.asset_name || item.asset_biz_id} (${item.asset_type_code || '-'})</div>
                        <div><strong>报废理由：</strong>${item.scrap_reason || '-'}</div>
                        <div><strong>提交时间：</strong>${item.create_time || '-'}</div>
                    </div>`;
            }
            return '';
        },

        async loadPending() {
            const container = document.getElementById('pending-flows');
            const isSchool = Auth.isSchoolAdmin();
            const deptParam = isSchool ? '?scope=department_all' : `?dept_biz_id=${user.dept_biz_id}`;
            try {
                const [borrowResp, repairResp, scrapResp] = await Promise.all([
                    API.get(`/flow/borrow/list${deptParam}`),
                    API.get(`/flow/repair/list${deptParam}`),
                    API.get(`/flow/scrap/list${deptParam}`)
                ]);

                let items = [];
                if (borrowResp.code === 200) {
                    items.push(...(borrowResp.data.list || []).filter(i => i.borrow_status === 'APPLY').map(i => ({...i, flowType: 'borrow', label: '领用申请'})));
                }
                if (repairResp.code === 200) {
                    items.push(...(repairResp.data.list || []).filter(i => i.order_status === 'AUDITING').map(i => ({...i, flowType: 'repair', label: '报修工单'})));
                    // 校级管理员还需看到待派单的报修
                    if (isSchool) {
                        items.push(...(repairResp.data.list || []).filter(i => i.order_status === 'APPROVED').map(i => ({...i, flowType: 'repair', label: '报修工单', actionType: 'dispatch'})));
                    }
                }
                if (scrapResp.code === 200) {
                    items.push(...(scrapResp.data.list || []).filter(i => i.scrap_status === 'APPLY').map(i => ({...i, flowType: 'scrap', label: '报废申请'})));
                }

                if (!items.length) { container.innerHTML = '<div class="empty-state"><p>暂无待审批事项</p></div>'; return; }

                container.innerHTML = items.map(item => {
                    const fid = item.flow_biz_id || item.biz_id;
                    const isDispatch = item.actionType === 'dispatch';
                    return `
                    <div class="card pending-item" data-flow-id="${fid}" data-biz-id="${item.biz_id || ''}" style="margin-bottom:12px;border:1px solid var(--warning);border-left:4px solid var(--warning);">
                        <div class="card-body" style="padding:16px;">
                            <div style="display:flex;justify-content:space-between;align-items:flex-start;">
                                <div style="flex:1;">
                                    <div style="margin-bottom:8px;">
                                        <span class="tag tag-warning" style="margin-right:8px;">${item.label}</span>
                                        ${isDispatch ? '<span class="tag tag-info" style="margin-right:8px;">待派单</span>' : ''}
                                        <strong>${fid}</strong>
                                        <span style="margin-left:12px;color:var(--gray-500);font-size:13px;">${item.asset_name || item.asset_biz_id}</span>
                                    </div>
                                    ${this.buildDetailHTML(item)}
                                </div>
                                ${isDispatch ? `
                                <div class="audit-actions" style="display:flex;gap:6px;margin-left:16px;flex-shrink:0;">
                                    <button class="btn btn-primary btn-sm" onclick="FlowPage.showDispatchDialog('${item.biz_id}')">派单</button>
                                </div>` : `
                                <div class="audit-actions" style="display:flex;gap:6px;margin-left:16px;flex-shrink:0;">
                                    <button class="btn btn-success btn-sm" onclick="FlowPage.audit('${fid}', 'PASS', '${item.flowType}', this)">通过</button>
                                    <button class="btn btn-danger btn-sm" onclick="FlowPage.audit('${fid}', 'REJECT', '${item.flowType}', this)">驳回</button>
                                </div>`}
                            </div>
                        </div>
                    </div>`;
                }).join('');
            } catch (e) { container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>'; }
        },

        async loadAll() {
            const container = document.getElementById('all-flows');
            const isSchool = Auth.isSchoolAdmin();
            const deptParam = isSchool ? '?scope=department_all' : `?dept_biz_id=${user.dept_biz_id}`;
            try {
                const [borrowResp, repairResp, scrapResp] = await Promise.all([
                    API.get(`/flow/borrow/list${deptParam}`),
                    API.get(`/flow/repair/list${deptParam}`),
                    API.get(`/flow/scrap/list${deptParam}`)
                ]);
                let items = [];
                if (borrowResp.code === 200) items.push(...(borrowResp.data.list || []).map(i => ({...i, flowType: 'borrow', label: '领用'})));
                if (repairResp.code === 200) items.push(...(repairResp.data.list || []).map(i => ({...i, flowType: 'repair', label: '报修'})));
                if (scrapResp.code === 200) items.push(...(scrapResp.data.list || []).map(i => ({...i, flowType: 'scrap', label: '报废'})));
                if (!items.length) { container.innerHTML = '<div class="empty-state"><p>暂无记录</p></div>'; return; }

                container.innerHTML = items.map(item => {
                    const bizId = item.flow_biz_id || item.biz_id;
                    const isExpanded = this.expandedRows[bizId];
                    const status = item.borrow_status || item.order_status || item.scrap_status;
                    const isAuditing = status === 'AUDITING' || status === 'APPLY';

                    return `
                    <div class="card" style="margin-bottom:8px;border-left:3px solid var(--info);">
                        <div class="card-body" style="padding:12px 16px;cursor:pointer;" onclick="FlowPage.toggleRow('${bizId}')">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <div style="flex:1;">
                                    <span class="tag tag-info" style="margin-right:8px;">${item.label}</span>
                                    <strong>${bizId}</strong>
                                    <span style="margin-left:12px;color:var(--gray-500);font-size:13px;">${item.user_name || ''} - ${item.asset_name || item.asset_biz_id}</span>
                                </div>
                                <div style="display:flex;align-items:center;gap:10px;">
                                    ${statusTag(status)}
                                    ${isAuditing ? `
                                        <span class="audit-actions" style="display:flex;gap:4px;">
                                            <button class="btn btn-success btn-xs" onclick="event.stopPropagation();FlowPage.audit('${bizId}', 'PASS', '${item.flowType}', this)">通过</button>
                                            <button class="btn btn-danger btn-xs" onclick="event.stopPropagation();FlowPage.audit('${bizId}', 'REJECT', '${item.flowType}', this)">驳回</button>
                                        </span>
                                    ` : ''}
                                </div>
                            </div>
                        </div>
                        ${isExpanded ? `
                        <div style="padding:12px 16px;border-top:1px solid var(--gray-200);background:var(--gray-50);">
                            ${this.buildDetailHTML(item)}
                            <div id="progress-${bizId}" style="margin-top:8px;"><div class="loading" style="padding:8px;"><div class="spinner" style="width:16px;height:16px;"></div></div></div>
                        </div>` : ''}
                    </div>`;
                }).join('');

                for (const item of items) {
                    const bizId = item.flow_biz_id || item.biz_id;
                    if (this.expandedRows[bizId]) {
                        this.loadProgress(bizId, item.flowType);
                    }
                }
            } catch (e) { container.innerHTML = '<div class="empty-state"><p>加载失败</p></div>'; }
        },

        async loadProgress(bizId, flowType) {
            const el = document.getElementById(`progress-${bizId}`);
            if (!el) return;
            try {
                const resp = await API.get(`/flow/progress?flow_biz_id=${bizId}`);
                if (resp.code !== 200) { el.innerHTML = '<p style="font-size:13px;color:var(--gray-500);">暂无审批进度</p>'; return; }
                const data = resp.data;
                const steps = data.steps || [];
                if (!steps.length) { el.innerHTML = '<p style="font-size:13px;color:var(--gray-500);">等待审批中</p>'; return; }
                el.innerHTML = `
                    <div style="margin-top:8px;">
                        <strong style="font-size:13px;">审批进度：</strong>
                        ${steps.map(s => {
                            const icon = s.result === 'PASS' ? '&#9989;' : (s.result === 'REJECT' ? '&#10060;' : '&#9203;');
                            const color = s.result === 'PASS' ? 'var(--success)' : (s.result === 'REJECT' ? 'var(--danger)' : 'var(--warning)');
                            const label = s.result === 'PASS' ? '通过' : (s.result === 'REJECT' ? '驳回' : '待审');
                            return `<div style="margin:4px 0;font-size:13px;">
                                <span style="color:${color};margin-right:4px;">${icon}</span>
                                <span style="font-weight:500;">${s.step_name}</span>
                                <span style="margin:0 6px;color:var(--gray-400);">|</span>
                                <span>${s.auditor_user_name || s.auditor_user_biz_id || '-'}</span>
                                <span style="margin:0 6px;color:var(--gray-400);">|</span>
                                <span>${label}</span>
                                <span style="margin-left:8px;color:var(--gray-400);font-size:12px;">${s.audit_time || ''}</span>
                            </div>`;
                        }).join('')}
                        ${data.final_result && data.final_result !== 'WAIT' ? `
                            <div style="margin-top:6px;font-size:13px;font-weight:bold;color:${data.final_result === 'PASS' ? 'var(--success)' : 'var(--danger)'};">
                                终审结果：${data.final_result === 'PASS' ? '通过' : '驳回'}
                            </div>` : ''}
                    </div>`;
            } catch (e) { el.innerHTML = '<p style="font-size:13px;color:var(--gray-500);">加载进度失败</p>'; }
        },

        async audit(flowId, result, flowType, btn) {
            // 立即禁用按钮，防重复点击
            const actions = btn ? btn.closest('.audit-actions') : null;
            if (actions) {
                actions.querySelectorAll('button').forEach(b => {
                    b.disabled = true;
                    b.textContent = b.textContent.trim() === '通过' ? '通过中...' : '驳回中...';
                });
            }
            const isSchool = Auth.isSchoolAdmin();
            const endpoint = isSchool ? '/flow/audit/school' : '/flow/audit/dept';
            const resp = await API.post(endpoint, { flow_biz_id: flowId, result: result });
            if (resp.code === 200) {
                Toast.success(result === 'PASS' ? '已通过' : '已驳回');
                // 立即移除卡片
                const card = document.querySelector(`.pending-item[data-flow-id="${flowId}"]`);
                if (card) {
                    card.style.transition = 'opacity 0.3s';
                    card.style.opacity = '0';
                    setTimeout(() => {
                        card.remove();
                        const container = document.getElementById('pending-flows');
                        if (container && !container.querySelector('.pending-item')) {
                            container.innerHTML = '<div class="empty-state"><p>暂无待审批事项</p></div>';
                        }
                    }, 300);
                }
                // 后台刷新保持数据一致
                setTimeout(() => {
                    if (this.currentTab === 'pending') this.loadPending();
                    else this.loadAll();
                }, 500);
            } else {
                Toast.error(resp.msg);
                // 恢复按钮
                if (actions) {
                    actions.querySelectorAll('button').forEach(b => {
                        b.disabled = false;
                        b.textContent = ['通过', '驳回'][['PASS', 'REJECT'].indexOf(result)];
                    });
                }
            }
        },

        async showDispatchDialog(workorderBizId) {
            // 加载修理工列表
            const resp = await API.get('/flow/repair/workers');
            if (resp.code !== 200 || !resp.data.list || !resp.data.list.length) {
                Toast.error('暂无可用的修理工');
                return;
            }
            const workers = resp.data.list;
            const options = workers.map(w =>
                `<option value="${w.biz_id}">${w.real_name} (${w.dept_name || '-'})</option>`
            ).join('');

            const modal = document.createElement('div');
            modal.id = 'dispatch-modal';
            modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:9999;';
            modal.innerHTML = `
                <div class="card" style="width:420px;max-width:90vw;">
                    <div class="card-header"><h3>派单 - 选择修理工</h3></div>
                    <div class="card-body">
                        <div class="form-group">
                            <label>修理工</label>
                            <select id="dispatch-worker-select" class="form-control" style="width:100%;padding:8px;">${options}</select>
                        </div>
                        <div style="margin-top:16px;display:flex;gap:8px;justify-content:flex-end;">
                            <button class="btn btn-secondary" onclick="document.getElementById('dispatch-modal').remove()">取消</button>
                            <button class="btn btn-primary" onclick="FlowPage.doDispatch('${workorderBizId}')">确认派单</button>
                        </div>
                    </div>
                </div>`;
            document.body.appendChild(modal);
        },

        async doDispatch(workorderBizId) {
            const sel = document.getElementById('dispatch-worker-select');
            const repairUserBizId = sel.value;
            const btn = event.target;
            btn.disabled = true;
            btn.textContent = '派单中...';
            const resp = await API.post('/flow/repair/dispatch', { workorder_biz_id: workorderBizId, repair_user_biz_id: repairUserBizId });
            if (resp.code === 200) {
                Toast.success('派单成功');
                document.getElementById('dispatch-modal').remove();
                this.loadPending();
            } else {
                Toast.error(resp.msg || '派单失败');
                btn.disabled = false;
                btn.textContent = '确认派单';
            }
        }
    };

    FlowPage.loadPending();
});
