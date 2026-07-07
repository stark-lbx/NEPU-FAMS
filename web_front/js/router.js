// ========== Simple Hash Router (权限守卫版) ==========
const Router = {
    routes: {},
    currentPage: null,

    register(path, handler) {
        this.routes[path] = handler;
    },

    navigate(path) {
        window.location.hash = '#' + path;
    },

    getCurrentPath() {
        return window.location.hash.replace('#', '') || 'dashboard';
    },

    async handle() {
        const path = this.getCurrentPath();

        // 权限守卫：检查用户是否有此页面的权限
        const perms = Permission.getPerms();
        if (perms.length > 0) {
            const pagePermMap = {
                users:       'PERM0101',
                dept:        'PERM0102',
                roles:       'PERM0103',
                dict:        'PERM0104',
                dashboard:   'PERM0201',
                assets:      'PERM0201',
                categories:  'PERM0202',
                check:       'PERM020106',
                borrow:      'PERM0301',
                repair:      'PERM0302',
                scrap:       'PERM0303',
                flow:        'PERM030102',  // 借用审批；fallback: PERM030202(报修审批) PERM030302(报废审批)
                storage:     'PERM0401',
            };
            const requiredPerm = pagePermMap[path];
            let allowed = !requiredPerm || Permission.hasPerm(requiredPerm);
            // 审批管理特殊处理：任一审批按钮权限均可
            if (!allowed && path === 'flow') {
                allowed = Permission.hasPerm('PERM030202') || Permission.hasPerm('PERM030302');
            }
            if (!allowed) {
                console.warn('[Router] 无权限访问页面:', path);
                if (path === this.currentPage) return;
                // 回退到默认页
                const fallback = Permission.hasPerm('PERM0201') ? 'dashboard' :
                                 Permission.hasPerm('PERM0302') ? 'repair' : null;
                if (fallback && fallback !== path) {
                    window.location.hash = '#' + fallback;
                }
                return;
            }
        }

        if (this.currentPage === path) return;
        this.currentPage = path;

        const handler = this.routes[path];
        const container = document.getElementById('page-content');
        if (!container) return;

        // Update nav active
        document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
        const navItem = document.querySelector(`[data-page="${path}"]`);
        if (navItem) navItem.classList.add('active');

        if (handler) {
            container.innerHTML = '<div class="loading"><div class="spinner"></div>加载中...</div>';
            try {
                await handler(container);
            } catch (e) {
                container.innerHTML = `<div class="empty-state"><div class="empty-icon">&#9888;</div><p>页面加载失败：${e.message}</p></div>`;
            }
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-icon">&#128269;</div><p>页面未找到</p></div>';
        }
    },

    init() {
        window.addEventListener('hashchange', () => this.handle());
        // Initial load
        if (!window.location.hash) {
            window.location.hash = '#dashboard';
        } else {
            this.handle();
        }
    }
};
