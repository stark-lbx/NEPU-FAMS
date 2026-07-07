// ========== Department Management Page (管理员专有) ==========
Router.register('dept', async (container) => {
    const isAdmin = Auth.isAdmin();
    container.innerHTML = `
        <div class="page-dept">
            ${!isAdmin ? '<div class="empty-state"><div class="empty-icon">&#128274;</div><p>仅管理员可访问部门管理</p></div>' : `
            <div style="display:grid;grid-template-columns:280px 1fr;gap:20px;">
                <div class="card">
                    <div class="card-header"><h3>组织机构</h3></div>
                    <div class="card-body" id="dept-tree"><div class="loading"><div class="spinner"></div></div></div>
                </div>
                <div class="card" id="dept-detail-card">
                    <div class="card-header"><h3>部门详情</h3></div>
                    <div class="card-body">
                        <div class="form-group"><label>新增子部门</label><div style="display:flex;gap:8px;"><input id="d-new-dept-name" placeholder="新部门名称"><button class="btn btn-primary btn-sm" onclick="DeptPage.addDept()">添加</button></div></div>
                    </div>
                </div>
            </div>
            `}
        </div>
    `;
    if (!isAdmin) return;

    window.DeptPage = {
        selectedDeptId: null,
        deptData: [],

        async load() {
            const treeContainer = document.getElementById('dept-tree');
            try {
                const deptParam = Auth.isSchoolAdmin() ? '?scope=department_all' : '';
                const resp = await API.get(`/dept/tree${deptParam}`);
                if (resp.code !== 200) { treeContainer.innerHTML = `<div class="empty-state"><p>${resp.msg}</p></div>`; return; }
                // Backend returns flat list or tree directly in data
                const raw = resp.data;
                this.deptData = Array.isArray(raw) ? raw : (raw.tree || raw.list || []);
                treeContainer.innerHTML = this.renderTree(this.deptData);
                // Bind click
                treeContainer.querySelectorAll('.tree-node').forEach(el => {
                    el.addEventListener('click', () => {
                        treeContainer.querySelectorAll('.tree-node').forEach(n => n.classList.remove('selected'));
                        el.classList.add('selected');
                        this.selectedDeptId = el.dataset.id;
                        this.showDetail();
                    });
                });
                this.deptTree = treeContainer;
            } catch (e) { treeContainer.innerHTML = '<div class="empty-state"><p>加载失败</p></div>'; }
        },

        renderTree(nodes, depth = 0) {
            return nodes.map(n => `
                <div class="tree-node" data-id="${n.biz_id}" style="padding-left:${8 + depth * 16}px;">
                    ${n.children && n.children.length ? '&#128193;' : '&#128196;'} ${n.dept_name}
                </div>
                ${n.children && n.children.length ? `<div class="tree-children">${this.renderTree(n.children, depth + 1)}</div>` : ''}
            `).join('');
        },

        showDetail() {
            const card = document.getElementById('dept-detail-card');
            const dept = this.findDept(this.selectedDeptId);
            if (!dept) return;
            card.innerHTML = `
                <div class="card-header"><h3>${dept.dept_name}</h3></div>
                <div class="card-body">
                    <div class="detail-grid">
                        <div class="detail-item"><span class="detail-label">部门ID</span><span class="detail-value">${dept.biz_id}</span></div>
                        <div class="detail-item"><span class="detail-label">部门名称</span><span class="detail-value">${dept.dept_name}</span></div>
                        <div class="detail-item"><span class="detail-label">上级ID</span><span class="detail-value">${dept.parent_biz_id || '无（根节点）'}</span></div>
                    </div>
                    <div style="margin-top:20px;">
                        <div class="form-group"><label>新增子部门</label>
                            <div style="display:flex;gap:8px;">
                                <input id="d-new-dept-name" placeholder="新部门名称">
                                <button class="btn btn-primary btn-sm" onclick="DeptPage.addDept()">添加</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        findDept(id, nodes = null) {
            const search = nodes || this.deptData;
            for (const n of search) {
                if (n.biz_id === id) return n;
                if (n.children) { const found = this.findDept(id, n.children); if (found) return found; }
            }
            return null;
        },

        async addDept() {
            const name = $('#d-new-dept-name')?.value?.trim();
            if (!name) { Toast.error('请输入部门名称'); return; }
            const resp = await API.post('/dept/create', {
                dept_name: name, parent_biz_id: this.selectedDeptId
            });
            if (resp.code === 200) { Toast.success('部门创建成功'); this.load(); }
            else { Toast.error(resp.msg); }
        }
    };

    DeptPage.load();
});
