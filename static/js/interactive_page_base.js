// static/js/interactive_page_base.js

document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('terminal-sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar-btn');
    const searchInput = document.getElementById('terminal-search-input');
    const terminalListItems = document.querySelectorAll('#terminal-list .list-group-item');
    
    const contentPlaceholder = document.getElementById('content-placeholder');
    const mainContent = document.getElementById('main_content');

    // 1. 侧边栏收起/展开
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });

    // 2. 搜索过滤
    searchInput.addEventListener('input', function() {
        const filter = this.value.toUpperCase();
        terminalListItems.forEach(item => {
            const text = item.textContent || item.innerText;
            if (text.toUpperCase().indexOf(filter) > -1) {
                item.style.display = "";
            } else {
                item.style.display = "none";
            }
        });
    });

    // 3. 点击选择端站
    terminalListItems.forEach(item => {
        item.addEventListener('click', function() {
            // 移除其他项的 'active' 状态
            terminalListItems.forEach(li => li.classList.remove('active'));
            // 为当前项添加 'active' 状态
            this.classList.add('active');

            // 隐藏提示，显示主内容区
            contentPlaceholder.style.display = 'none';
            mainContent.style.display = 'block';

            const terminalData = {
                sn: this.dataset.sn,
                ip: this.dataset.ip,
                port: this.dataset.port,
                shipName: this.dataset.shipName,
                mmsi: this.dataset.mmsi
            }
            document.getElementById('selected_ship_name').innerText = terminalData.shipName;
            document.getElementById('selected_mmsi').innerText = terminalData.mmsi;
            document.getElementById('selected_sn').innerText = terminalData.sn;
            document.getElementById('selected_ip').innerText = terminalData.ip;
            document.getElementById('selected_port').innerText = terminalData.port;
            
            const lastReportDate = this.dataset.lastReportDate;
            const lastReportTime = this.dataset.lastReportTime;
            const lastReportEl = document.getElementById('selected_last_report');
            if (lastReportEl) {
                if (lastReportDate && lastReportTime) {
                    lastReportEl.innerText = `${lastReportDate} ${lastReportTime}`;
                } else {
                    lastReportEl.innerText = '暂无上报数据';
                }
            }
            const event = new CustomEvent('terminalSelected', { detail: terminalData });
            document.dispatchEvent(event);
        });
    });
});