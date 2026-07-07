// ========== Check/Inventory Page (多人协同盘点 - 重点2) ==========
Router.register('check', async (container) => {
    const user = Auth.getUser();
    container.innerHTML = `
        <div class="page-check">
            <div class="tabs">
                <div class="tab active" onclick="CheckPage.switchTab('tasks')">盘点任务</div>
                <div class="tab" onclick="CheckPage.switchTab('submit')">提交盘点</div>
            </div>
            <div id="check-tab-tasks">
                <div class="card">
                    <div class="card-header">
                        <h3>盘点任务列表</h3>
                        ${Auth.isAdmin() ? '<button class="btn btn-primary" onclick="CheckPage.showCreateTask()">+ 创建盘点任务</button>' : ''}
                    </div>
                    <div class="card-body">
                        <div class="table-wrapper">
                            <table>
                                <thead><tr><th>任务ID</th><th>任务名称</th><th>目标部门</th><th>开始时间</th><th>结束时间</th><th>状态</th><th>操作</th></tr></thead>
                                <tbody id="task-list-body"><tr><td colspan="7"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div id="check-tab-submit" style="display:none;">
                <div class="card">
                    <div class="card-header"><h3>提交盘点明细</h3></div>
                    <div class="card-body">
                        <div class="form-row">
                            <div class="form-group"><label>盘点任务ID <span class="required">*</span></label><input id="c-task-id" placeholder="从盘点任务列表复制"></div>
                            <div class="form-group"><label>资产ID <span class="required">*</span></label><input id="c-asset-id" placeholder="从资产台账复制"></div>
                        </div>
                        <div class="form-row">
                            <div class="form-group"><label>是否存在 <span class="required">*</span></label>
                                <select id="c-exist"><option value="1">是 - 资产存在</option><option value="0">否 - 资产缺失</option></select>
                            </div>
                            <div class="form-group"><label>实际存放地点</label><input id="c-location" placeholder="如与登记不一致请填写"></div>
                        </div>
                        <div class="form-group"><label>盘点备注</label><textarea id="c-remark" rows="2" placeholder="补充说明..."></textarea></div>
                        <button class="btn btn-primary" onclick="CheckPage.submitDetail()">提交盘点结果</button>
                    </div>
                </div>
                <div class="card" style="margin-top:20px;">
                    <div class="card-header"><h3>盘点明细列表</h3></div>
                    <div class="card-body">
                        <div class="toolbar">
                            <div class="form-group" style="margin:0;display:flex;align-items:center;gap:10px;">
                                <label style="margin:0;white-space:nowrap;">任务ID：</label>
                                <input id="c-detail-task-id" placeholder="输入任务ID查询明细" style="width:280px;">
                                <button class="btn btn-outline btn-sm" onclick="CheckPage.loadDetails()">查询</button>
                            </div>
                        </div>
                        <div class="table-wrapper">
                            <table>
                                <thead><tr><th>资产ID</th><th>盘点人</th><th>是否存在</th><th>实际地点</th><th>备注</th><th>时间</th></tr></thead>
                                <tbody id="detail-list-body"><tr><td colspan="6"><div class="empty-state"><p>请输入任务ID查询</p></div></td></tr></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.CheckPage = {
        currentTab: 'tasks',

        switchTab(tab) {
            this.currentTab = tab;
            document.querySelectorAll('.tab').forEach((t, i) => t.classList.toggle('active', (i===0 && tab==='tasks') || (i===1 && tab==='submit')));
            document.getElementById('check-tab-tasks').style.display = tab === 'tasks' ? 'block' : 'none';
            document.getElementById('check-tab-submit').style.display = tab === 'submit' ? 'block' : 'none';
            if (tab === 'tasks') this.loadTasks();
        },

        async loadTasks() {
            const tbody = document.getElementById('task-list-body');
            try {
                const resp = await API.get(`/check/task/list?dept_biz_id=${user.dept_biz_id}`);
                if (resp.code !== 200) { tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`; return; }
                const list = resp.data.list || [];
                if (!list.length) { tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p>暂无盘点任务</p></div></td></tr>'; return; }
                tbody.innerHTML = list.map(t => `
                    <tr>
                        <td>${t.biz_id}</td><td>${t.task_name}</td><td>${t.target_dept_biz_id}</td>
                        <td>${t.start_time || '-'}</td><td>${t.end_time || '-'}</td>
                        <td>${statusTag(t.task_status)}</td>
                        <td class="table-actions">
                            <button class="btn btn-outline btn-sm" onclick="CheckPage.switchTab('submit');$('#c-task-id').value='${t.biz_id}';">去盘点</button>
                        </td>
                    </tr>`).join('');
            } catch (e) { tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>加载失败</p></div></td></tr>`; }
        },

        showCreateTask() {
            Modal.show('创建盘点任务', `
                <div class="form-group"><label>任务名称 <span class="required">*</span></label><input id="f-task-name" placeholder="如 2024年Q4计算机学院资产盘点"></div>
                <div class="form-row">
                    <div class="form-group"><label>开始时间 <span class="required">*</span></label><input id="f-start-time" type="datetime-local"></div>
                    <div class="form-group"><label>结束时间 <span class="required">*</span></label><input id="f-end-time" type="datetime-local"></div>
                </div>
            `, async () => {
                const data = {
                    task_name: $('#f-task-name').value, target_dept_biz_id: user.dept_biz_id,
                    start_time: $('#f-start-time').value, end_time: $('#f-end-time').value
                };
                if (!data.task_name || !data.start_time || !data.end_time) { Toast.error('请填写所有必填项'); return false; }
                const resp = await API.post('/check/task/create', data);
                if (resp.code === 200) { Toast.success('盘点任务创建成功'); CheckPage.loadTasks(); return true; }
                Toast.error(resp.msg); return false;
            });
        },

        async submitDetail() {
            const taskId = $('#c-task-id').value.trim();
            const assetId = $('#c-asset-id').value.trim();
            const exist = parseInt($('#c-exist').value);
            if (!taskId || !assetId) { Toast.error('请填写任务ID和资产ID'); return; }
            const data = { task_biz_id: taskId, asset_biz_id: assetId, actual_exist: exist };
            const loc = $('#c-location').value.trim(); if (loc) data.real_location = loc;
            const remark = $('#c-remark').value.trim(); if (remark) data.check_remark = remark;

            const resp = await API.post('/check/detail/submit', data);
            if (resp.code === 200) { Toast.success('盘点结果已提交'); $('#c-asset-id').value=''; $('#c-location').value=''; $('#c-remark').value=''; this.loadDetails(); }
            else { Toast.error(resp.msg); }
        },

        async loadDetails() {
            const taskId = $('#c-detail-task-id').value.trim();
            const tbody = document.getElementById('detail-list-body');
            if (!taskId) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p>请输入任务ID查询</p></div></td></tr>'; return; }
            tbody.innerHTML = '<tr><td colspan="6"><div class="loading"><div class="spinner"></div></div></td></tr>';
            try {
                const resp = await API.get(`/check/detail/list?task_biz_id=${taskId}`);
                if (resp.code !== 200) { tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`; return; }
                const list = resp.data.list || [];
                if (!list.length) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p>暂无盘点记录</p></div></td></tr>'; return; }
                tbody.innerHTML = list.map(d => `<tr>
                    <td>${d.asset_biz_id}</td><td>${d.check_user_biz_id}</td>
                    <td>${d.actual_exist === 1 ? '<span class="tag tag-success">存在</span>' : '<span class="tag tag-danger">缺失</span>'}</td>
                    <td>${d.real_location || '-'}</td><td>${d.check_remark || '-'}</td><td>${d.check_time || '-'}</td>
                </tr>`).join('');
            } catch (e) { tbody.innerHTML = '<tr><td colspan="6"><div class="empty-state"><p>加载失败</p></div></td></tr>'; }
        }
    };

    CheckPage.loadTasks();
});
