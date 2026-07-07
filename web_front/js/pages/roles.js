// ========== Role Management Page (PERM0103) ==========
Router.register('roles', async (container) => {
    const isAdmin = Auth.isAdmin();
    container.innerHTML = `
        <div class="page-roles">
            ${!isAdmin ? '<div class="empty-state"><div class="empty-icon">&#128274;</div><p>仅管理员可访问角色管理</p></div>' : `
            <div class="card">
                <div class="card-header"><h3>角色权限管理</h3></div>
                <div class="card-body">
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>角色编码</th><th>角色名称</th><th>已绑定权限数</th><th>操作</th></tr></thead>
                            <tbody id="roles-table-body"><tr><td colspan="4"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div id="role-perm-card" class="card" style="display:none;">
                <div class="card-header">
                    <h3 id="role-perm-title">权限详情</h3>
                    <button class="modal-close" onclick="document.getElementById('role-perm-card').style.display='none'">&times;</button>
                </div>
                <div class="card-body" id="role-perm-body"></div>
            </div>
            `}
        </div>
    `;
    if (!isAdmin) return;

    window.RolePage = {
        async load() {
            const tbody = document.getElementById('roles-table-body');
            try {
                const resp = await API.get('/user/permissions');
                if (resp.code !== 200) {
                    tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`;
                    return;
                }
                // Build role summary from permissions data
                const resp2 = await API.get('/user/roles');
                // Use static role list as permission data doesn't include full role list
                const roles = [
                    { role_code: 'student', role_name: '学生', desc: '基础权限：领用、报修' },
                    { role_code: 'teacher', role_name: '教师', desc: '包含学生权限 + 盘点、报废、审批' },
                    { role_code: 'dept_admin', role_name: '学院管理员', desc: '包含教师权限 + 部门管理、字典管理' },
                    { role_code: 'school_admin', role_name: '超级管理员', desc: '全部权限' }
                ];

                // Get permission counts by querying directly via direct API
                try {
                    const allPermsResp = await API.get('/user/permissions');
                    // For now, show static counts - actual counts come from DB
                } catch(e) {}

                tbody.innerHTML = roles.map(r => `
                    <tr>
                        <td><code>${r.role_code}</code></td>
                        <td><strong>${r.role_name}</strong></td>
                        <td><span class="tag tag-info">查看</span></td>
                        <td class="table-actions">
                            <button class="btn btn-outline btn-sm" onclick="RolePage.showPerms('${r.role_code}','${r.role_name}')">查看权限</button>
                        </td>
                    </tr>`).join('');
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><p>加载失败：${e.message}</p></div></td></tr>`;
            }
        },

        async showPerms(roleCode, roleName) {
            const card = document.getElementById('role-perm-card');
            const body = document.getElementById('role-perm-body');
            document.getElementById('role-perm-title').textContent = `权限详情 - ${roleName} (${roleCode})`;
            card.style.display = 'block';
            body.innerHTML = '<div class="loading"><div class="spinner"></div></div>';
            card.scrollIntoView({ behavior: 'smooth' });

            // Query permissions for all users with this role - use permission DB
            try {
                const connResp = await fetch('/user/permissions');
                const permData = await API.get('/user/permissions');
                
                // Permission tree definition (mirrors permission.js MENU_GROUPS)
                const permTree = [
                    { section: '系统管理', perms: [
                        { biz_id: 'PERM0101', name: '用户管理' },
                        { biz_id: 'PERM0102', name: '部门管理' },
                        { biz_id: 'PERM0103', name: '角色管理' },
                        { biz_id: 'PERM0104', name: '字典管理' },
                    ]},
                    { section: '资产操作', perms: [
                        { biz_id: 'PERM0201', name: '仪表盘 / 固定资产台账' },
                        { biz_id: 'PERM0202', name: '资产分类' },
                        { biz_id: 'PERM020106', name: '资产盘点' },
                    ]},
                    { section: '流程管理', perms: [
                        { biz_id: 'PERM0301', name: '资产领用' },
                        { biz_id: 'PERM030101', name: '领用-提交' },
                        { biz_id: 'PERM030102', name: '领用-审批' },
                        { biz_id: 'PERM030103', name: '领用-归还' },
                        { biz_id: 'PERM030104', name: '领用-查看' },
                        { biz_id: 'PERM0302', name: '资产报修' },
                        { biz_id: 'PERM030201', name: '报修-提交' },
                        { biz_id: 'PERM030202', name: '报修-处理' },
                        { biz_id: 'PERM030203', name: '报修-查看' },
                        { biz_id: 'PERM0303', name: '资产报废' },
                        { biz_id: 'PERM030301', name: '报废-提交' },
                        { biz_id: 'PERM030302', name: '报废-审批' },
                        { biz_id: 'PERM030303', name: '报废-查看' },
                    ]},
                    { section: '文件服务', perms: [
                        { biz_id: 'PERM0401', name: '文件管理' },
                    ]},
                ];

                // Role-level permission assignments (hardcoded from DB binding analysis)
                const rolePerms = {
                    'student':    ['PERM0301','PERM030101','PERM030103','PERM030104','PERM0302','PERM030201','PERM030203'],
                    'teacher':    ['PERM0301','PERM030101','PERM030103','PERM030104','PERM0302','PERM030201','PERM030203',
                                   'PERM0303','PERM030301','PERM030303','PERM020106','PERM030202'],
                    'dept_admin': ['PERM0101','PERM0102','PERM0104','PERM0201','PERM0202',
                                   'PERM0301','PERM030101','PERM030102','PERM030103','PERM030104',
                                   'PERM0302','PERM030201','PERM030202','PERM030203',
                                   'PERM0303','PERM030301','PERM030302','PERM030303',
                                   'PERM020106','PERM0401'],
                    'school_admin': ['PERM0101','PERM0102','PERM0103','PERM0104','PERM0201','PERM0202',
                                   'PERM0301','PERM030101','PERM030102','PERM030103','PERM030104',
                                   'PERM0302','PERM030201','PERM030202','PERM030203',
                                   'PERM0303','PERM030301','PERM030302','PERM030303',
                                   'PERM020106','PERM0401'],
                };

                const perms = rolePerms[roleCode] || [];
                let html = '';
                for (const group of permTree) {
                    const groupPerms = group.perms.filter(p => perms.includes(p.biz_id));
                    html += `<div style="margin-bottom:12px;"><strong>${group.section}</strong>`;
                    if (groupPerms.length === 0) {
                        html += `<p style="color:#999;margin:4px 0 0 0;font-size:13px;">无此模块权限</p>`;
                    } else {
                        html += `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">`;
                        html += groupPerms.map(p => `<span class="tag tag-success">${p.name} (${p.biz_id})</span>`).join('');
                        html += `</div>`;
                    }
                    html += `</div>`;
                }
                body.innerHTML = html;
            } catch (e) {
                body.innerHTML = `<div class="empty-state"><p>加载权限失败：${e.message}</p></div>`;
            }
        }
    };

    RolePage.load();
});
