// ========== API Layer ==========
const API = {
    getToken() {
        return localStorage.getItem(AppConfig.TOKEN_KEY);
    },

    async request(method, path, data = null, isFormData = false) {
        const url = AppConfig.API_BASE + path;
        const headers = {};
        const token = this.getToken();
        if (token) headers['Authorization'] = 'Bearer ' + token;

        const opts = { method, headers };

        if (data && !isFormData) {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(data);
        } else if (data && isFormData) {
            opts.body = data;
        }

        try {
            const resp = await fetch(url, opts);
            const json = await resp.json();
            if (json.code === 401) {
                Auth.logout();
                throw new Error('登录已过期，请重新登录');
            }
            return json;
        } catch (e) {
            if (e.message.includes('登录已过期')) {
                window.location.href = 'index.html';
            }
            throw e;
        }
    },

    get(path) { return this.request('GET', path); },
    post(path, data) { return this.request('POST', path, data); },
    del(path) { return this.request('DELETE', path); },
    upload(path, formData) { return this.request('POST', path, formData, true); }
};
