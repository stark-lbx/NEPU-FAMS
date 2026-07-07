// ========== Authentication ==========
const Auth = {
    isLoggedIn() {
        return !!localStorage.getItem(AppConfig.TOKEN_KEY);
    },

    getUser() {
        const raw = localStorage.getItem(AppConfig.USER_KEY);
        return raw ? JSON.parse(raw) : null;
    },

    getRoles() {
        const raw = localStorage.getItem(AppConfig.ROLES_KEY);
        return raw ? JSON.parse(raw) : [];
    },

    hasRole(roleCode) {
        return this.getRoles().some(r => r.role_code === roleCode);
    },

    isSchoolAdmin() {
        return this.hasRole('school_admin');
    },

    isDeptAdmin() {
        return this.hasRole('dept_admin');
    },

    isAdmin() {
        return this.isSchoolAdmin() || this.isDeptAdmin();
    },

    /** 加载用户权限并缓存到 localStorage */
    async loadPermissions() {
        try {
            const resp = await API.get('/user/permissions');
            if (resp.code === 200 && resp.data.perm_ids) {
                localStorage.setItem(AppConfig.PERMS_KEY, JSON.stringify(resp.data.perm_ids));
                Permission.load(resp.data.perm_ids);
                return resp.data.perm_ids;
            }
        } catch (e) { /* non-critical */ }
        return [];
    },

    async login(username, password) {
        const resp = await API.post('/user/login', { username, password });
        if (resp.code === 200) {
            localStorage.setItem(AppConfig.TOKEN_KEY, resp.data.token);
            localStorage.setItem(AppConfig.USER_KEY, JSON.stringify(resp.data.user));
            // Fetch roles after login
            try {
                const rolesResp = await API.get('/user/roles');
                if (rolesResp.code === 200) {
                    localStorage.setItem(AppConfig.ROLES_KEY, JSON.stringify(rolesResp.data));
                }
            } catch (e) { /* non-critical */ }
            // Load permissions
            await this.loadPermissions();
        }
        return resp;
    },

    logout() {
        localStorage.removeItem(AppConfig.TOKEN_KEY);
        localStorage.removeItem(AppConfig.USER_KEY);
        localStorage.removeItem(AppConfig.ROLES_KEY);
        localStorage.removeItem(AppConfig.PERMS_KEY);
        window.location.href = 'index.html';
    },

    checkAuth() {
        if (!this.isLoggedIn()) {
            window.location.href = 'index.html';
            return false;
        }
        return true;
    }
};
