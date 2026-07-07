// ========== Asset Category Management Page (PERM0202) ==========
Router.register('categories', async (container) => {
    container.innerHTML = `
        <div class="page-categories">
            <div class="card">
                <div class="card-header">
                    <h3>资产分类管理</h3>
                    <button class="btn btn-primary" onclick="CatPage.showCreate()">+ 新增分类</button>
                </div>
                <div class="card-body">
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>分类编码</th><th>分类名称</th><th>排序</th><th>操作</th></tr></thead>
                            <tbody id="cat-table-body"><tr><td colspan="4"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.CatPage = {
        async load() {
            const tbody = document.getElementById('cat-table-body');
            try {
                const resp = await API.get('/dict/list?dict_type=asset_type');
                if (resp.code !== 200) {
                    tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`;
                    return;
                }
                const list = resp.data.list || [];
                if (!list.length) {
                    tbody.innerHTML = '<tr><td colspan="4"><div class="empty-state"><p>暂无分类数据</p></div></td></tr>';
                    return;
                }
                tbody.innerHTML = list.map(c => `
                    <tr>
                        <td><code>${c.dict_code}</code></td>
                        <td><strong>${c.dict_name}</strong></td>
                        <td>${c.sort || 0}</td>
                        <td class="table-actions">
                            <button class="btn btn-outline btn-sm" onclick="CatPage.showEdit('${c.biz_id}','${c.dict_code}','${c.dict_name}',${c.sort||0})">编辑</button>
                            <button class="btn btn-outline btn-sm" style="color:#e74c3c;" onclick="CatPage.deleteCat('${c.biz_id}','${c.dict_name}')">删除</button>
                        </td>
                    </tr>`).join('');
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><p>加载失败：${e.message}</p></div></td></tr>`;
            }
        },

        showCreate() {
            Modal.show('新增资产分类', `
                <div class="form-row">
                    <div class="form-group"><label>分类编码 <span class="required">*</span></label><input id="f-cat-code" placeholder="如 computer"></div>
                    <div class="form-group"><label>分类名称 <span class="required">*</span></label><input id="f-cat-name" placeholder="如 电脑设备"></div>
                </div>
                <div class="form-group"><label>排序</label><input id="f-cat-sort" type="number" value="0"></div>
            `, async () => {
                const dict_code = document.getElementById('f-cat-code').value.trim();
                const dict_name = document.getElementById('f-cat-name').value.trim();
                const sort = parseInt(document.getElementById('f-cat-sort').value) || 0;
                if (!dict_code || !dict_name) { Toast.error('请填写编码和名称'); return false; }
                try {
                    const resp = await API.post('/dict/create', {
                        dict_type: 'asset_type',
                        dict_code: dict_code,
                        dict_name: dict_name,
                        sort: sort
                    });
                    if (resp.code === 200) {
                        Toast.success('分类创建成功');
                        CatPage.load();
                        return true;
                    }
                    Toast.error(resp.msg);
                    return false;
                } catch (e) {
                    Toast.error('创建失败');
                    return false;
                }
            });
        },

        showEdit(bizId, dictCode, dictName, sort) {
            Modal.show('编辑资产分类', `
                <div class="form-group"><label>分类编码</label><input id="f-edit-cat-code" value="${dictCode}"></div>
                <div class="form-group"><label>分类名称 <span class="required">*</span></label><input id="f-edit-cat-name" value="${dictName}"></div>
                <div class="form-group"><label>排序</label><input id="f-edit-cat-sort" type="number" value="${sort}"></div>
            `, async () => {
                const data = {
                    biz_id: bizId,
                    dict_code: document.getElementById('f-edit-cat-code').value.trim(),
                    dict_name: document.getElementById('f-edit-cat-name').value.trim(),
                    sort: parseInt(document.getElementById('f-edit-cat-sort').value) || 0
                };
                if (!data.dict_name) { Toast.error('名称不能为空'); return false; }
                try {
                    const resp = await API.post('/dict/update', data);
                    if (resp.code === 200) { Toast.success('更新成功'); CatPage.load(); return true; }
                    Toast.error(resp.msg); return false;
                } catch (e) { Toast.error('更新失败'); return false; }
            });
        },

        async deleteCat(bizId, name) {
            if (!confirm(`确定删除分类「${name}」吗？`)) return;
            try {
                const resp = await API.del(`/dict/delete?biz_id=${bizId}`);
                if (resp.code === 200) { Toast.success('删除成功'); CatPage.load(); }
                else { Toast.error(resp.msg); }
            } catch (e) { Toast.error('删除失败'); }
        }
    };

    CatPage.load();
});
