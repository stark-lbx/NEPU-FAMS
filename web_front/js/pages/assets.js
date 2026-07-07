// ========== Asset Management Page (固定资产台账管理) ==========
Router.register('assets', async (container) => {
    const user = Auth.getUser();
    container.innerHTML = `
        <div class="page-assets">
            <div class="card">
                <div class="card-header">
                    <h3>固定资产台账</h3>
                    <div>
                        <button class="btn btn-primary" onclick="AssetPage.showCreate()">+ 新增资产</button>
                        <button class="btn btn-outline" onclick="AssetPage.exportData()" style="margin-left:8px;">导出Excel</button>
                    </div>
                </div>
                <div class="card-body">
                    <div class="toolbar">
                        <select id="asset-status-filter" onchange="AssetPage.load()">
                            <option value="">全部状态</option>
                            <option value="normal">正常</option>
                            <option value="borrowed">已领用</option>
                            <option value="repair">维修中</option>
                            <option value="scrapped">已报废</option>
                        </select>
                        <select id="asset-type-filter" onchange="AssetPage.load()">
                            <option value="">全部类型</option>
                        </select>
                        <div class="search-box"><input type="text" id="asset-search" placeholder="搜索资产编号/名称..." onkeyup="if(event.key==='Enter')AssetPage.load()"></div>
                        <button class="btn btn-outline" onclick="AssetPage.load()">查询</button>
                    </div>
                    <div class="table-wrapper">
                        <table>
                            <thead><tr>
                                <th>资产ID(biz_id)</th><th>名称</th><th>类型</th><th>价格(元)</th><th>存放地点</th><th>状态</th><th>操作</th>
                            </tr></thead>
                            <tbody id="asset-table-body"><tr><td colspan="7"><div class="loading"><div class="spinner"></div></div></td></tr></tbody>
                        </table>
                    </div>
                    <div id="asset-pagination" class="pagination"></div>
                </div>
            </div>
            <div id="asset-detail-card" class="card" style="display:none;"></div>
        </div>
    `;

    // Load dict types
    try {
        const resp = await API.get('/dict/list?dict_type=asset_type');
        if (resp.code === 200) {
            const sel = document.getElementById('asset-type-filter');
            resp.data.list.forEach(d => { const o = document.createElement('option'); o.value = d.dict_code; o.textContent = d.dict_name; sel.appendChild(o); });
        }
    } catch (e) { /* silent */ }

    window.AssetPage = {
        page: 1,
        deptId: Auth.isSchoolAdmin() ? '' : user.dept_biz_id,

        async load() {
            const status = document.getElementById('asset-status-filter').value;
            const type = document.getElementById('asset-type-filter').value;
            const search = document.getElementById('asset-search').value.trim();

            let params = `page=${this.page}&page_size=${AppConfig.PAGE_SIZE}`;
            if (this.deptId) params += `&dept_biz_id=${this.deptId}`;
            if (status) params += `&status_code=${status}`;
            const tbody = document.getElementById('asset-table-body');
            tbody.innerHTML = '<tr><td colspan="8"><div class="loading"><div class="spinner"></div></div></td></tr>';

            try {
                const resp = await API.get(`/asset/list?${params}`);
                if (resp.code !== 200) { tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`; return; }
                const list = resp.data.list || [];
                if (!list.length) { tbody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><p>暂无资产数据</p></div></td></tr>'; this.renderPagination(0); return; }

                // Client-side type/search filtering
                let filtered = list;
                if (type) filtered = filtered.filter(a => a.asset_type_code === type);
                if (search) filtered = filtered.filter(a => a.asset_code.includes(search) || a.asset_name.includes(search));

                tbody.innerHTML = filtered.map(a => `
                    <tr>
                        <td><code>${a.biz_id}</code></td>
                        <td><a href="javascript:void(0)" onclick="AssetPage.showDetail('${a.biz_id}')">${a.asset_name}</a></td>
                        <td>${a.asset_type_code || '-'}</td>
                        <td>&yen;${Number(a.asset_price || 0).toLocaleString()}</td>
                        <td>${a.store_location || '-'}</td>
                        <td>${statusTag(a.current_status_code)}</td>
                        <td class="table-actions">
                            <button class="btn btn-outline btn-sm" onclick="AssetPage.showDetail('${a.biz_id}')">详情</button>
                            <button class="btn btn-outline btn-sm" onclick="AssetPage.showStatusEdit('${a.biz_id}','${a.current_status_code}')">状态</button>
                            ${a.current_status_code === 'normal' ? `
                            <button class="btn btn-primary btn-sm" onclick="AssetPage.goBorrow('${a.biz_id}')">领用</button>
                            <button class="btn btn-warning btn-sm" onclick="AssetPage.goRepair('${a.biz_id}')">报修</button>
                            <button class="btn btn-danger btn-sm" onclick="AssetPage.goScrap('${a.biz_id}')">报废</button>
                            ` : ''}
                        </td>
                    </tr>`).join('');
                this.renderPagination(resp.data.total);
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>加载失败：${e.message}</p></div></td></tr>`;
            }
        },

        renderPagination(total) {
            const totalPages = Math.ceil(total / AppConfig.PAGE_SIZE);
            const pg = document.getElementById('asset-pagination');
            if (totalPages <= 1) { pg.innerHTML = ''; return; }
            let html = `<button ${this.page===1?'disabled':''} onclick="AssetPage.goPage(${this.page-1})">上一页</button>`;
            for (let i = 1; i <= totalPages; i++) {
                html += `<button class="${i===this.page?'active':''}" onclick="AssetPage.goPage(${i})">${i}</button>`;
            }
            html += `<button ${this.page===totalPages?'disabled':''} onclick="AssetPage.goPage(${this.page+1})">下一页</button>`;
            html += `<span class="page-info">共 ${total} 条</span>`;
            pg.innerHTML = html;
        },

        goPage(p) { this.page = p; this.load(); window.scrollTo(0,0); },

        showCreate() {
            Modal.show('新增资产', `
                <div class="form-row">
                    <div class="form-group"><label>资产编号 <span class="required">*</span></label><input id="f-asset-code" placeholder="如 ZC-2024-001"></div>
                    <div class="form-group"><label>资产名称 <span class="required">*</span></label><input id="f-asset-name" placeholder="如 联想ThinkPad X1"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>资产类型 <span class="required">*</span></label><select id="f-asset-type"><option value="">请选择</option></select></div>
                    <div class="form-group"><label>购置时间 <span class="required">*</span></label><input id="f-buy-time" type="date"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>资产价格(元) <span class="required">*</span></label><input id="f-price" type="number" step="0.01" placeholder="0.00"></div>
                    <div class="form-group"><label>存放地点 <span class="required">*</span></label><input id="f-location" placeholder="如 计算机楼301"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>规格型号</label><input id="f-spec" placeholder="如 X1 Carbon Gen11"></div>
                    <div class="form-group"><label>供应商</label><input id="f-supplier" placeholder="供应商名称"></div>
                </div>
                <div class="form-group"><label>备注</label><textarea id="f-remark" rows="2"></textarea></div>
            `, async () => {
                const data = {
                    asset_code: $('#f-asset-code').value, asset_name: $('#f-asset-name').value,
                    asset_type_code: $('#f-asset-type').value, buy_time: $('#f-buy-time').value,
                    asset_price: parseFloat($('#f-price').value), store_location: $('#f-location').value,
                    dept_biz_id: user.dept_biz_id, current_status_code: 'normal',
                    spec: $('#f-spec').value, supplier: $('#f-supplier').value, remark: $('#f-remark').value
                };
                if (!data.asset_code || !data.asset_name || !data.asset_type_code || !data.buy_time || !data.asset_price || !data.store_location) {
                    Toast.error('请填写所有必填项'); return false;
                }
                const resp = await API.post('/asset/create', data);
                if (resp.code === 200) { Toast.success('资产录入成功'); AssetPage.load(); return true; }
                Toast.error(resp.msg); return false;
            });

            // Load types for form
            API.get('/dict/list?dict_type=asset_type').then(r => {
                if (r.code === 200) {
                    const sel = document.getElementById('f-asset-type');
                    r.data.list.forEach(d => { const o = document.createElement('option'); o.value = d.dict_code; o.textContent = d.dict_name; sel.appendChild(o); });
                }
            });
        },

        async showDetail(bizId) {
            const card = document.getElementById('asset-detail-card');
            card.style.display = 'block';
            card.innerHTML = '<div class="card-body"><div class="loading"><div class="spinner"></div></div></div>';
            card.scrollIntoView({ behavior: 'smooth' });
            try {
                const resp = await API.get(`/asset/detail?biz_id=${bizId}`);
                if (resp.code !== 200) { card.innerHTML = `<div class="card-body"><div class="empty-state"><p>${resp.msg}</p></div></div>`; return; }
                const a = resp.data;
                card.innerHTML = `
                    <div class="card-header"><h3>资产详情 - ${a.asset_name}</h3><button class="modal-close" onclick="document.getElementById('asset-detail-card').style.display='none'">&times;</button></div>
                    <div class="card-body">
                        <div class="detail-grid">
                            <div class="detail-item"><span class="detail-label">资产ID</span><span class="detail-value"><code>${a.biz_id}</code></span></div>
                            <div class="detail-item"><span class="detail-label">资产名称</span><span class="detail-value">${a.asset_name}</span></div>
                            <div class="detail-item"><span class="detail-label">资产类型</span><span class="detail-value">${a.asset_type_code}</span></div>
                            <div class="detail-item"><span class="detail-label">购置时间</span><span class="detail-value">${a.buy_time}</span></div>
                            <div class="detail-item"><span class="detail-label">价格</span><span class="detail-value">&yen;${Number(a.asset_price).toLocaleString()}</span></div>
                            <div class="detail-item"><span class="detail-label">存放地点</span><span class="detail-value">${a.store_location}</span></div>
                            <div class="detail-item"><span class="detail-label">当前状态</span><span class="detail-value">${statusTag(a.current_status_code)}</span></div>
                            <div class="detail-item"><span class="detail-label">规格型号</span><span class="detail-value">${a.spec || '-'}</span></div>
                            <div class="detail-item"><span class="detail-label">供应商</span><span class="detail-value">${a.supplier || '-'}</span></div>
                            <div class="detail-item"><span class="detail-label">备注</span><span class="detail-value">${a.remark || '-'}</span></div>
                            <div class="detail-item"><span class="detail-label">创建时间</span><span class="detail-value">${a.create_time || '-'}</span></div>
                        </div>
                        <div style="margin-top:16px;display:flex;gap:8px;">
                            <button class="btn btn-primary btn-sm" onclick="AssetPage.goBorrow('${a.biz_id}')">领用申请</button>
                            <button class="btn btn-warning btn-sm" onclick="AssetPage.goRepair('${a.biz_id}')">报修</button>
                            <button class="btn btn-danger btn-sm" onclick="AssetPage.goScrap('${a.biz_id}')">报废申请</button>
                        </div>
                    </div>
                `;
            } catch (e) { card.innerHTML = `<div class="card-body"><div class="empty-state"><p>加载失败：${e.message}</p></div></div>`; }
        },

        showStatusEdit(bizId, currentStatus) {
            Modal.show('更新资产状态', `
                <div class="form-group"><label>资产ID</label><input value="${bizId}" disabled></div>
                <div class="form-group"><label>当前状态</label><input value="${currentStatus}" disabled></div>
                <div class="form-group"><label>新状态 <span class="required">*</span></label>
                    <select id="f-new-status">
                        <option value="normal">正常</option>
                        <option value="borrowed">已领用</option>
                        <option value="repair">维修中</option>
                        <option value="scrapped">已报废</option>
                    </select>
                </div>
                <div class="form-group"><label>操作说明 <span class="required">*</span></label><textarea id="f-oper-desc" rows="2"></textarea></div>
            `, async () => {
                const resp = await API.post('/asset/status', {
                    asset_biz_id: bizId, new_status_code: $('#f-new-status').value, oper_desc: $('#f-oper-desc').value
                });
                if (resp.code === 200) { Toast.success('状态更新成功'); AssetPage.load(); return true; }
                Toast.error(resp.msg); return false;
            });
        },

        goBorrow(bizId) {
            sessionStorage.setItem('asset_context', JSON.stringify({ biz_id: bizId }));
            Router.navigate('/borrow');
        },

        goRepair(bizId) {
            sessionStorage.setItem('asset_context', JSON.stringify({ biz_id: bizId }));
            Router.navigate('/repair');
        },

        goScrap(bizId) {
            sessionStorage.setItem('asset_context', JSON.stringify({ biz_id: bizId }));
            Router.navigate('/scrap');
        },

        exportData() {
            Toast.warning('导出功能需要后端支持，请使用浏览器的打印功能或手动复制表格数据');
        }
    };

    AssetPage.load();
});

// Utility
function $(sel) { return document.querySelector(sel); }
