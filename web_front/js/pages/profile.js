// ========== Profile Management ==========
window.ProfilePage = {
    show() {
        const user = Auth.getUser();
        if (!user) return;
        
        const roles = Auth.getRoles();
        const roleNames = roles.map(r => {
            const map = { school_admin: '超级管理员', dept_admin: '学院管理员', teacher: '教师', student: '学生' };
            return map[r.role_code] || r.role_code;
        }).join(', ');
        
        Modal.show('个人信息', `
            <div class="form-group">
                <label>姓名</label>
                <input id="p-real-name" value="${user.real_name || ''}" placeholder="请输入真实姓名">
            </div>
            <div class="form-group">
                <label>用户名</label>
                <input id="p-username" value="${user.username || ''}" disabled>
                <div class="form-hint">用户名不可修改</div>
            </div>
            <div class="form-group">
                <label>角色</label>
                <input value="${roleNames}" disabled>
                <div class="form-hint">角色不可修改</div>
            </div>
            <div class="form-group">
                <label>手机号</label>
                <input id="p-phone" value="${user.phone || ''}" placeholder="请输入手机号">
            </div>
            <div class="form-group">
                <label>邮箱</label>
                <input id="p-email" value="${user.email || ''}" placeholder="请输入邮箱">
            </div>
            <div class="form-group">
                <label>所属部门</label>
                <input value="${user.dept_name || user.dept_biz_id || ''}" disabled>
                <div class="form-hint">部门不可修改</div>
            </div>
            <div class="form-group">
                <label>用户ID</label>
                <input value="${user.biz_id || ''}" disabled>
                <div class="form-hint">系统唯一标识</div>
            </div>
        `, async () => {
            const realName = $('#p-real-name').value.trim();
            const phone = $('#p-phone').value.trim();
            const email = $('#p-email').value.trim();
            
            if (!realName) {
                Toast.error('姓名不能为空');
                return false;
            }
            
            try {
                const resp = await API.post('/user/update', {
                    real_name: realName,
                    phone: phone || null,
                    email: email || null
                });
                
                if (resp.code === 200) {
                    // 更新本地存储
                    const updatedUser = { ...user, real_name: realName, phone, email };
                    localStorage.setItem(AppConfig.USER_KEY, JSON.stringify(updatedUser));
                    
                    // 更新侧边栏显示
                    document.getElementById('sidebar-avatar').textContent = (realName || user.username || 'U')[0].toUpperCase();
                    document.getElementById('sidebar-name').textContent = realName || user.username || '--';
                    
                    Toast.success('个人信息更新成功');
                    return true;
                } else {
                    Toast.error(resp.msg || '更新失败');
                    return false;
                }
            } catch (e) {
                Toast.error('网络错误: ' + e.message);
                return false;
            }
        });
    }
};