// ========== Permission System (前端权限控制) ==========
//
// 与 sys_permission 表对齐，通过 /user/permissions 接口获取用户权限列表
//
// 核心方法：
//   Permission.load(permIds)     - 注入权限ID列表
//   Permission.hasPerm(bizId)    - 检查是否拥有某权限
//   Permission.getSidebar()      - 生成侧边栏菜单 HTML

window.Permission = (() => {
    let _perms = [];

    // ========== 侧边栏定义 ==========
    // 结构严格对应 sys_permission 表：4个顶级菜单 + 子菜单
    const MENU_GROUPS = [
        {
            section: "系统管理",
            perm_id: "PERM0001",
            items: [
                { perm_id: "PERM0101", page: "users",       icon: "&#128101;", label: "用户管理" },
                { perm_id: "PERM0102", page: "dept",        icon: "&#127970;", label: "部门管理" },
                { perm_id: "PERM0103", page: "roles",       icon: "&#128273;", label: "角色管理" },
                { perm_id: "PERM0104", page: "dict",        icon: "&#128218;", label: "字典管理" },
            ]
        },
        {
            section: "资产操作",
            perm_id: "PERM0002",
            items: [
                { perm_id: "PERM0201", page: "dashboard",   icon: "&#127968;", label: "仪表盘" },
                { perm_id: "PERM0201", page: "assets",      icon: "&#128230;", label: "固定资产台账" },
                { perm_id: "PERM0202", page: "categories",  icon: "&#128451;", label: "资产分类" },
                { perm_id: "PERM020106",page: "check",       icon: "&#128203;", label: "资产盘点" },
            ]
        },
        {
            section: "流程管理",
            perm_id: "PERM0003",
            items: [
                { perm_id: "PERM0301", page: "borrow",      icon: "&#128196;", label: "资产领用" },
                { perm_id: "PERM0302", page: "repair",      icon: "&#128295;", label: "资产报修" },
                { perm_id: "PERM0303", page: "scrap",       icon: "&#128465;", label: "资产报废" },
                { perm_id: "PERM030102",page: "flow",        icon: "&#9989;",  label: "审批管理",
                  // 审批管理特殊判断：有任意审批按钮权限即视为可访问
                  alt_perms: ["PERM030202", "PERM030302"] },
            ]
        },
        {
            section: "文件服务",
            perm_id: "PERM0004",
            items: [
                { perm_id: "PERM0401", page: "storage",     icon: "&#128194;", label: "文件管理" },
            ]
        },
    ];

    // ========== 公共方法 ==========
    function load(permIds) {
        _perms = permIds || [];
    }

    function hasPerm(permBizId) {
        if (_perms.includes(permBizId)) return true;
        // 父级检查：拥有子权限即拥有父菜单
        return _perms.some(p => p.startsWith(permBizId) && p.length > permBizId.length);
    }

    function hasAnyPerm(permList) {
        return permList.some(p => hasPerm(p));
    }

    // 生成侧边栏 HTML（过滤无权限菜单）
    function getSidebar() {
        if (_perms.length === 0) return "";

        let html = "";
        for (const group of MENU_GROUPS) {
            // 检查顶级菜单权限
            if (!hasPerm(group.perm_id) && !group.items.some(it => hasPerm(it.perm_id))) continue;

            const visibleItems = group.items.filter(item => {
                if (item.alt_perms) {
                    return hasPerm(item.perm_id) || hasAnyPerm(item.alt_perms);
                }
                return hasPerm(item.perm_id);
            });

            if (visibleItems.length === 0) continue;

            html += `<div class="nav-section">\n`;
            html += `    <div class="nav-section-title">${group.section}</div>\n`;
            for (const item of visibleItems) {
                html += `    <a class="nav-item" data-page="${item.page}" href="#${item.page}" onclick="Router.navigate('${item.page}')">\n`;
                html += `        <span class="nav-icon">${item.icon}</span>\n`;
                html += `        <span>${item.label}</span>\n`;
                html += `    </a>\n`;
            }
            html += `</div>\n`;
        }
        return html;
    }

    function getPerms() { return [..._perms]; }

    return { load, hasPerm, hasAnyPerm, getSidebar, getPerms };
})();
