// ========== User Management Page (管理员专有) ==========
Router.register('users', async (container) => {
    const isAdmin = Auth.isAdmin();
    container.innerHTML = `
        <div class="page-users">
            ${!isAdmin ? '<div class="empty-state"><div class="empty-icon">&#128274;</div><p>仅管理员可访问用户管理</p></div>' : `
            <div class="card">
                <div class="card-header"><h3>用户列表</h3><button class="btn btn-primary" onclick="UserPage.showCreate()">+ 新增用户</button></div>
                <div class="card-body">
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>用户ID</th><th>用户名</th><th>真实姓名</th><th>所属部门</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
                            <tbody id="user-table-body"><tr><td colspan="7"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
                        </table>
                    </div>
                </div>
            </div>
            `}
        </div>
    `;
    if (!isAdmin) return;

    window.UserPage = {
        async load() {
            const tbody = document.getElementById('user-table-body');
            try {
                const deptBizId = Auth.isSchoolAdmin() ? '' : (Auth.getUser()?.dept_biz_id || '');
                const resp = await API.get(`/user/list?dept_biz_id=${deptBizId}`);
                if (resp.code !== 200) { tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`; return; }
                const list = resp.data.list || [];
                if (!list.length) { tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p>暂无用户</p></div></td></tr>'; return; }
                tbody.innerHTML = list.map(u => `<tr>
                    <td>${u.biz_id}</td><td>${u.username}</td><td>${u.real_name || '-'}</td>
                    <td>${u.dept_biz_id}</td><td>--</td>
                    <td>${u.user_status===1?'<span class="tag tag-success">正常</span>':'<span class="tag tag-danger">禁用</span>'}</td>
                    <td class="table-actions">
                        <button class="btn btn-outline btn-xs" onclick="UserPage.showEdit('${u.biz_id}')">编辑</button>
                        <button class="btn btn-outline btn-xs" onclick="UserPage.toggleStatus('${u.biz_id}', ${u.user_status||0})">${u.user_status===1?'禁用':'启用'}</button>
                    </td>
                </tr>`).join('');
            } catch (e) { tbody.innerHTML = '<tr><td colspan="7"><div class="empty-state"><p>加载失败</p></div></td></tr>'; }
        },

        showCreate() {
            Modal.show('新增用户', `
                <div class="form-row">
                    <div class="form-group"><label>用户名 <span class="required">*</span></label><input id="f-username"></div>
                    <div class="form-group"><label>密码 <span class="required">*</span></label><input id="f-password" type="password"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>真实姓名 <span class="required">*</span></label><input id="f-realname"></div>
                    <div class="form-group"><label>所属部门 <span class="required">*</span></label><input id="f-dept-id" placeholder="部门ID"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>角色 <span class="required">*</span></label><select id="f-role"><option value="">请选择</option><option value="school_admin">超级管理员</option><option value="dept_admin">学院管理员</option><option value="teacher">教师</option><option value="student">学生</option></select></div>
                    <div class="form-group"></div>
                </div>
            `, async () => {
                const data = {
                    username: $('#f-username').value, password: $('#f-password').value,
                    real_name: $('#f-realname').value, dept_biz_id: $('#f-dept-id').value,
                    role_code: $('#f-role').value
                };
                if (!data.username || !data.password || !data.real_name || !data.dept_biz_id || !data.role_code) {
                    Toast.error('请填写所有必填项'); return false;
                }
                const resp = await API.post('/user/create', data);
                if (resp.code === 200) { Toast.success('用户创建成功'); UserPage.load(); return true; }
                Toast.error(resp.msg); return false;
            });
        },

        showEdit(bizId) {
            Toast.warning('用户角色编辑功能需后端扩展 /user/assign-role 接口');
        },

        async toggleStatus(bizId, currentStatus) {
            Toast.warning('用户状态切换功能需后端扩展 /user/status 接口');
        }
    };

    UserPage.load();
});
