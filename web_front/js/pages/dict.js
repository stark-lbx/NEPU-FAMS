// ========== Dictionary Management Page (管理员专有) ==========
Router.register('dict', async (container) => {
    const isAdmin = Auth.isAdmin();
    container.innerHTML = `
        <div class="page-dict">
            ${!isAdmin ? '<div class="empty-state"><div class="empty-icon">&#128274;</div><p>仅管理员可访问数据字典</p></div>' : `
            <div class="card">
                <div class="card-header"><h3>数据字典</h3></div>
                <div class="card-body">
                    <div class="toolbar">
                        <select id="dict-type-filter" onchange="DictPage.load()">
                            <option value="">全部类型</option>
                        </select>
                        <button class="btn btn-outline" onclick="DictPage.load()">刷新</button>
                    </div>
                    <div class="table-wrapper">
                        <table>
                            <thead><tr><th>字典类型</th><th>编码</th><th>名称</th><th>排序</th><th>状态</th></tr></thead>
                            <tbody id="dict-table-body"><tr><td colspan="5"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
                        </table>
                    </div>
                </div>
            </div>
            `}
        </div>
    `;
    if (!isAdmin) return;

    window.DictPage = {
        // Store dict types fetched from backend
        _dictTypes: [],

        async loadTypes() {
            try {
                const resp = await API.get('/dict/types');
                if (resp.code === 200 && resp.data) {
                    this._dictTypes = resp.data;
                    const select = document.getElementById('dict-type-filter');
                    resp.data.forEach(t => {
                        const option = document.createElement('option');
                        option.value = t;
                        option.textContent = t;
                        select.appendChild(option);
                    });
                }
            } catch (e) { /* types loading failure not critical */ }
        },

        async load() {
            const dictType = document.getElementById('dict-type-filter').value;
            const tbody = document.getElementById('dict-table-body');
            try {
                // If no type selected, show all types (fetch per type and merge)
                if (!dictType) {
                    tbody.innerHTML = '<tr><td colspan="5"><div class="loading"><div class="spinner"></div></div></td></tr>';
                    let allList = [];
                    for (const t of this._dictTypes) {
                        try {
                            const resp = await API.get(`/dict/list?dict_type=${t}`);
                            if (resp.code === 200 && resp.data.list) {
                                allList = allList.concat(resp.data.list);
                            }
                        } catch (e) { /* skip failed type */ }
                    }
                    if (!allList.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>暂无数据</p></div></td></tr>'; return; }
                    tbody.innerHTML = allList.map(d => `<tr>
                        <td>${d.dict_type || '-'}</td><td>${d.dict_code}</td><td>${d.dict_name}</td>
                        <td>${d.sort || '-'}</td>
                        <td>${d.status===1?'<span class="tag tag-success">启用</span>':'<span class="tag tag-danger">禁用</span>'}</td>
                    </tr>`).join('');
                    return;
                }
                let url = `/dict/list?dict_type=${dictType}`;
                const resp = await API.get(url);
                if (resp.code !== 200) { tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`; return; }
                const list = resp.data.list || [];
                if (!list.length) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>暂无数据</p></div></td></tr>'; return; }
                tbody.innerHTML = list.map(d => `<tr>
                    <td>${d.dict_type || dictType}</td><td>${d.dict_code}</td><td>${d.dict_name}</td>
                    <td>${d.sort || '-'}</td>
                    <td>${d.status===1?'<span class="tag tag-success">启用</span>':'<span class="tag tag-danger">禁用</span>'}</td>
                </tr>`).join('');
            } catch (e) { tbody.innerHTML = '<tr><td colspan="5"><div class="empty-state"><p>加载失败</p></div></td></tr>'; }
        }
    };
    await DictPage.loadTypes();
    DictPage.load();
});
