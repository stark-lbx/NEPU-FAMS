// ========== Dashboard Page ==========
Router.register('dashboard', async (container) => {
    container.innerHTML = `
        <div class="page-dashboard">
            <div class="stats-row">
                <div class="stat-card"><div class="stat-icon blue">&#128188;</div><div><div class="stat-value" id="stat-total">-</div><div class="stat-label">资产总数</div></div></div>
                <div class="stat-card"><div class="stat-icon green">&#9989;</div><div><div class="stat-value" id="stat-normal">-</div><div class="stat-label">正常使用中</div></div></div>
                <div class="stat-card"><div class="stat-icon orange">&#128295;</div><div><div class="stat-value" id="stat-repair">-</div><div class="stat-label">报修中</div></div></div>
                <div class="stat-card"><div class="stat-icon purple">&#128203;</div><div><div class="stat-value" id="stat-flow">-</div><div class="stat-label">待审批</div></div></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                <div class="card">
                    <div class="card-header"><h3>最近入库资产</h3></div>
                    <div class="card-body" id="recent-assets"><div class="loading"><div class="spinner"></div></div></div>
                </div>
                <div class="card">
                    <div class="card-header"><h3>我的待办事项</h3></div>
                    <div class="card-body" id="my-todos"><div class="loading"><div class="spinner"></div></div></div>
                </div>
            </div>
        </div>
    `;

    const user = Auth.getUser();
    if (!user) return;

    // 非管理员显示权限未开启占位
    if (!Auth.isAdmin()) {
        document.getElementById('page-content').innerHTML = `
            <div class="page-dashboard">
                <div class="empty-state"><div class="empty-icon">&#128274;</div><p>仪表盘权限未开启，请联系管理员分配权限</p></div>
            </div>`;
        return;
    }

    // Load stats - 校级管理员查看全校、其他人按部门
    try {
        const deptParam = Auth.isSchoolAdmin() ? '' : `?dept_biz_id=${user.dept_biz_id}`;
        const resp = await API.get(`/asset/list${deptParam ? '?' + deptParam : ''}&page_size=100`);
        if (resp.code === 200) {
            const assets = resp.data.list || [];
            document.getElementById('stat-total').textContent = resp.data.total || 0;
            document.getElementById('stat-normal').textContent = assets.filter(a => a.current_status_code === 'normal').length;
            document.getElementById('stat-repair').textContent = assets.filter(a => a.current_status_code === 'repair').length;
        }
    } catch (e) { /* silent */ }

    // Load pending flows for admin - 校级查看全校，部门级别只看本部门
    let pendingCount = 0;
    try {
        const deptParam = Auth.isSchoolAdmin() ? 'scope=department_all' : `dept_biz_id=${user.dept_biz_id}`;
        const [borrowResp, repairResp, scrapResp] = await Promise.all([
            API.get(`/flow/borrow/list?${deptParam}`),
            API.get(`/flow/repair/list?${deptParam}`),
            API.get(`/flow/scrap/list?${deptParam}`)
        ]);
        pendingCount = [borrowResp, repairResp, scrapResp].reduce((sum, r) => {
            if (r.code === 200) return sum + (r.data.list || []).filter(i => i.borrow_status === 'APPLY' || i.order_status === 'AUDITING' || i.scrap_status === 'APPLY').length;
            return sum;
        }, 0);
        document.getElementById('stat-flow').textContent = pendingCount;
    } catch (e) { document.getElementById('stat-flow').textContent = '-'; }

    // Recent assets - 校级管理员查看全校范围
    try {
        const queryParts = [];
        if (!Auth.isSchoolAdmin()) {
            queryParts.push(`dept_biz_id=${user.dept_biz_id}`);
        }
        queryParts.push('page_size=5');
        const resp = await API.get(`/asset/list?${queryParts.join('&')}`);
        if (resp.code === 200) {
            const list = resp.data.list || [];
            document.getElementById('recent-assets').innerHTML = list.length ? `
                <table><thead><tr><th>资产ID</th><th>名称</th><th>价格</th><th>状态</th></tr></thead>
                <tbody>${list.map(a => `<tr><td><code>${a.biz_id}</code></td><td>${a.asset_name}</td><td>&yen;${a.asset_price}</td><td>${statusTag(a.current_status_code)}</td></tr>`).join('')}</tbody></table>
            ` : '<div class="empty-state"><p>暂无资产数据</p></div>';
        }
    } catch (e) {
        document.getElementById('recent-assets').innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
    }

    // My todos - 只有管理员才显示待审批事项
    if (Auth.isAdmin()) {
        try {
            const deptParam = Auth.isSchoolAdmin() ? 'scope=department_all' : `dept_biz_id=${user.dept_biz_id}`;
            const [borrowResp, repairResp, scrapResp] = await Promise.all([
                API.get(`/flow/borrow/list?${deptParam}`),
                API.get(`/flow/repair/list?${deptParam}`),
                API.get(`/flow/scrap/list?${deptParam}`)
            ]);
            let todos = [];
            if (borrowResp.code === 200) todos.push(...(borrowResp.data.list || []).map(i => ({...i, type: '领用'})));
            if (repairResp.code === 200) todos.push(...(repairResp.data.list || []).map(i => ({...i, type: '报修'})));
            if (scrapResp.code === 200) todos.push(...(scrapResp.data.list || []).map(i => ({...i, type: '报废'})));
            todos = todos.sort((a,b) => (b.borrow_status || b.order_status || b.scrap_status || '').localeCompare(a.borrow_status || a.order_status || a.scrap_status || '')).slice(0, 5);

            document.getElementById('my-todos').innerHTML = todos.length ? `
                <table><thead><tr><th>类型</th><th>资产ID</th><th>状态</th></tr></thead>
                <tbody>${todos.map(t => `<tr><td>${t.type}</td><td>${t.asset_biz_id}</td><td>${statusTag(t.borrow_status || t.order_status || t.scrap_status)}</td></tr>`).join('')}</tbody></table>
            ` : '<div class="empty-state"><p>暂无待办事项</p></div>';
        } catch (e) {
            document.getElementById('my-todos').innerHTML = '<div class="empty-state"><p>加载失败</p></div>';
        }
    } else {
        document.getElementById('my-todos').innerHTML = '<div class="empty-state"><p>暂无待办事项</p></div>';
    }
});

function statusTag(code) {
    const map = {
        // 资产状态
        'normal': '<span class="tag tag-success">正常</span>',
        'idle': '<span class="tag tag-success">空闲</span>',
        'repair': '<span class="tag tag-warning">维修中</span>',
        'scrapped': '<span class="tag tag-danger">已报废</span>',
        'borrowed': '<span class="tag tag-info">已领用</span>',
        'IDLE': '<span class="tag tag-success">空闲</span>',
        'SCRAP': '<span class="tag tag-danger">已报废</span>',
        // 领用流程
        'APPLY': '<span class="tag tag-warning">待审批</span>',
        'BORROWING': '<span class="tag tag-info">使用中</span>',
        'RETURN': '<span class="tag tag-success">已归还</span>',
        'REJECT': '<span class="tag tag-danger">已驳回</span>',
        // 报修流程
        'AUDITING': '<span class="tag tag-warning">待审批</span>',
        'APPROVED': '<span class="tag tag-info">已通过</span>',
        'ASSIGNED': '<span class="tag tag-info">已派单</span>',
        'REPAIRING': '<span class="tag tag-warning">维修中</span>',
        'COMPLETED': '<span class="tag tag-success">已完成</span>',
        'DONE': '<span class="tag tag-success">已完成</span>',
        'FINISHED': '<span class="tag tag-success">已完成</span>',
        // 报废流程
        'SCRAPPING': '<span class="tag tag-warning">报废中</span>',
        'SCRAPPED': '<span class="tag tag-success">已报废</span>',
        // 通用
        'pending': '<span class="tag tag-warning">待审批</span>',
        'audited': '<span class="tag tag-info">已审核</span>',
        'rejected': '<span class="tag tag-danger">已驳回</span>',
        'running': '<span class="tag tag-info">进行中</span>',
        'completed': '<span class="tag tag-success">已完成</span>',
        'returned': '<span class="tag tag-success">已归还</span>',
        'WAITING': '<span class="tag tag-warning">待处理</span>'
    };
    return map[code] || `<span class="tag tag-default">${code || '未知'}</span>`;
}
