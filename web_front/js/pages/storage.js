// ========== File Management Page (PERM0401) ==========
Router.register('storage', async (container) => {
    const user = Auth.getUser();
    container.innerHTML = `
        <div class="page-storage">
            <div class="card">
                <div class="card-header">
                    <h3>文件管理</h3>
                    <button class="btn btn-primary" onclick="StoragePage.showUpload()">+ 上传文件</button>
                </div>
                <div class="card-body">
                    <div class="toolbar">
                        <div class="search-box">
                            <input type="text" id="storage-asset-id" placeholder="输入资产ID查询关联文件...">
                            <button class="btn btn-outline" onclick="StoragePage.load()">查询</button>
                        </div>
                    </div>
                    <div class="table-wrapper">
                        <table>
                            <thead><tr>
                                <th>文件名</th><th>关联资产</th><th>文件大小</th><th>类型</th><th>上传时间</th><th>操作</th>
                            </tr></thead>
                            <tbody id="storage-table-body">
                                <tr><td colspan="6"><div class="empty-state"><p>请先输入资产ID查询该资产的附件</p></div></td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;

    window.StoragePage = {
        async load() {
            const assetId = document.getElementById('storage-asset-id').value.trim();
            if (!assetId) {
                document.getElementById('storage-table-body').innerHTML =
                    '<tr><td colspan="6"><div class="empty-state"><p>请先输入资产ID查询该资产的附件</p></div></td></tr>';
                return;
            }
            const tbody = document.getElementById('storage-table-body');
            tbody.innerHTML = '<tr><td colspan="6"><div class="loading"><div class="spinner"></div></div></td></tr>';
            try {
                const resp = await API.get(`/storage/list?asset_biz_id=${assetId}`);
                if (resp.code !== 200) {
                    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>${resp.msg}</p></div></td></tr>`;
                    return;
                }
                const list = resp.data.list || [];
                if (!list.length) {
                    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>该资产暂无附件</p></div></td></tr>`;
                    return;
                }
                const typeMap = { 1: '图片', 2: '文档', 3: '其他' };
                tbody.innerHTML = list.map(f => `
                    <tr>
                        <td><strong>${f.attach_name}</strong></td>
                        <td><code>${f.asset_biz_id}</code></td>
                        <td>${formatFileSize(f.file_size)}</td>
                        <td><span class="tag">${typeMap[f.attach_type] || '其他'}</span></td>
                        <td>${f.create_time || '-'}</td>
                        <td class="table-actions">
                            <button class="btn btn-outline btn-sm" onclick="StoragePage.downloadFile('${f.biz_id}','${f.attach_name}')">下载</button>
                            <button class="btn btn-outline btn-sm" style="color:#e74c3c;" onclick="StoragePage.deleteFile('${f.biz_id}','${f.attach_name}')">删除</button>
                        </td>
                    </tr>`).join('');
            } catch (e) {
                tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>加载失败：${e.message}</p></div></td></tr>`;
            }
        },

        showUpload() {
            const assetId = document.getElementById('storage-asset-id').value.trim();
            Modal.show('上传文件', `
                <div class="form-group">
                    <label>关联资产ID <span class="required">*</span></label>
                    <input id="f-upload-asset-id" placeholder="资产业务ID" value="${assetId}">
                </div>
                <div class="form-group">
                    <label>附件类型</label>
                    <select id="f-upload-type">
                        <option value="1">图片</option>
                        <option value="2" selected>文档</option>
                        <option value="3">其他</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>选择文件 <span class="required">*</span></label>
                    <input type="file" id="f-upload-file">
                </div>
            `, async () => {
                const assetBizId = document.getElementById('f-upload-asset-id').value.trim();
                const attachType = document.getElementById('f-upload-type').value;
                const fileInput = document.getElementById('f-upload-file');
                if (!assetBizId) { Toast.error('请输入资产ID'); return false; }
                if (!fileInput.files || !fileInput.files[0]) { Toast.error('请选择文件'); return false; }

                const formData = new FormData();
                formData.append('asset_biz_id', assetBizId);
                formData.append('attach_type', attachType);
                formData.append('file', fileInput.files[0]);

                try {
                    const resp = await API.upload('/storage/upload', formData);
                    if (resp.code === 200) {
                        Toast.success('上传成功');
                        document.getElementById('storage-asset-id').value = assetBizId;
                        StoragePage.load();
                        return true;
                    }
                    Toast.error(resp.msg);
                    return false;
                } catch (e) {
                    Toast.error('上传失败');
                    return false;
                }
            });
        },

        downloadFile(bizId, fileName) {
            const token = Auth.getToken();
            window.open(`${AppConfig.BASE_URL}/storage/download?attach_biz_id=${bizId}&token=${token}`, '_blank');
        },

        async deleteFile(bizId, fileName) {
            if (!confirm(`确定删除文件「${fileName}」吗？此操作不可撤销。`)) return;
            try {
                const resp = await API.del(`/storage/delete?attach_biz_id=${bizId}`);
                if (resp.code === 200) {
                    Toast.success('删除成功');
                    StoragePage.load();
                } else {
                    Toast.error(resp.msg);
                }
            } catch (e) {
                Toast.error('删除失败');
            }
        }
    };
});

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}
