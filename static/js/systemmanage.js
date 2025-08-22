// static/js/systemmanage.js

// 这个函数将由 base.html 在 WebSocket 连接成功后自动调用
function onSocketReady() {
    console.log("SystemManage.js: WebSocket is ready. Initializing page logic.");

    // --- 事件监听 ---
    document.addEventListener('terminalSelected', function(e) {
        const detail = e.detail;
        console.log("SystemManage page received selection:", detail);
        
        // 切换端站时，重置所有状态
        resetAllStatus();
    });

    // --- WebSocket 消息处理器 ---
    const systemManagePageMessageHandler = function(message) {
        if (message.type !== 'control_response') return;

        if (message.success) {
            const responseData = message.data;
            const module = message.module;
            
            if (responseData.hasOwnProperty('result')) {    // 处理端站响应级别的失败
                if (responseData.result === '1') {
                    alert(`操作 ${module} 成功！`);
                } else {
                    let errorMessage = `操作 ${module} 失败。`;
                    if (responseData.error) {
                        errorMessage += `\n错误信息: ${responseData.error}`;
                    }
                    alert(errorMessage);
                }
            } else {
                alert(`操作成功！模块: ${module}`);

                // 根据模块处理响应
            switch (message.module) {
                case 'query_work_mode':
                    handleWorkModeResponse(responseData);
                    break;
                case 'query_rtc':
                    handleRtcResponse(responseData);
                    break;
                case 'query_report_config':
                    handleReportConfigResponse(responseData);
                    break;
                case 'query_version':
                    handleVersionResponse(responseData);
                    break;
                // 设置类和复位类操作成功后只提示，不做UI更新
                case 'set_work_mode':
                case 'adu_soft_rst':
                case 'adu_task_rst':
                case 'set_rtc':
                case 'set_report_config':
                    break;
            }
            }

        } else {
            // 这部分逻辑处理WebSocket通信级别的失败（如超时），保持不变
            alert(`操作失败！\n模块: ${message.module}\n错误信息: ${message.error}`);
        }
    };

    // 注册消息处理器
    if (window.webSocketOnMessageHandlers) {
        window.webSocketOnMessageHandlers = [];
        window.webSocketOnMessageHandlers.push(systemManagePageMessageHandler);
    }

    // --- UI 更新与辅助函数 ---
    function setStatus(elementId, text, isSuccess) {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerText = text;
            el.className = isSuccess ? 'form-text mt-2 text-success' : 'form-text mt-2 text-danger';
        }
    }
    
    function resetAllStatus() {
        // 重置工作模式
        document.getElementById('work_mode').value = "";
        setStatus('work_mode_status', '当前模式：暂无数据', false);
        // 重置RTC
        document.getElementById('datetime_rtc').value = new Date().toISOString().slice(0, 16);
        setStatus('rtc_status', '端站当前RTC时间：暂无数据', false);
        // 重置上报参数
        document.getElementById('report_ip').value = '';
        document.getElementById('report_port').value = '';
        document.getElementById('report_mode').value = '';
        document.getElementById('report_interval').value = '';
        setStatus('report_ip_status', '端站当前IP地址：暂无数据', false);
        setStatus('report_port_status', '端站当前端口号：暂无数据', false);
        setStatus('report_mode_status', '端站当前上报方式：暂无数据', false);
        setStatus('report_interval_status', '端站当前上报时间间隔：暂无数据', false);
        // 重置版本信息
        ['model', 'hw', 'adu', 'acu', 'stru'].forEach(v => document.getElementById(`version_${v}`).value = '');
    }

    // --- 响应处理器 ---
    function handleWorkModeResponse(data) {
        if (data && data.op === 'query_ans' && data.op_sub === 'work_pattern') {
            const pattern = data.pattern;
            document.getElementById('work_mode').value = pattern;
            const modeText = (pattern === '0') ? "自动模式" : "手动模式";
            setStatus('work_mode_status', `当前模式: ${modeText}`, true);
        } else {
            setStatus('work_mode_status', '查询失败：端站响应格式错误', false);
        }
    }

    function handleRtcResponse(data) {
        if (data && data.op === 'query_ans' && data.op_sub === 'RTC') {
            setStatus('rtc_status', `端站当前RTC时间：${data.date} ${data.time}`, true);
        } else {
            setStatus('rtc_status', '查询失败：端站响应格式错误', false);
        }
    }

    function handleReportConfigResponse(data) {
        if (data && data.op === 'query_ans' && data.op_sub === 'report_config') {
            document.getElementById('report_ip').value = data.ip || '';
            document.getElementById('report_port').value = data.port || '';
            document.getElementById('report_mode').value = data.mode || '';
            document.getElementById('report_interval').value = data.interval || '';
            const modeMap = {'0': '不上报', '1': '通过CPE上报', '2': '通过NB上报'};
            setStatus('report_ip_status', `端站当前IP地址：${data.ip || 'N/A'}`, true);
            setStatus('report_port_status', `端站当前端口号：${data.port || 'N/A'}`, true);
            setStatus('report_mode_status', `端站当前上报方式：${modeMap[data.mode] || '未知'}`, true);
            setStatus('report_interval_status', `端站当前上报时间间隔：${data.interval || 'N/A'}秒`, true);
        } else {
            setStatus('report_ip_status', '查询失败：端站响应格式错误', false);
        }
    }
    
    function handleVersionResponse(data) {
        if (data && data.op === 'query_ans' && data.op_sub === 'version') {
            document.getElementById('version_model').value = data.model || '';
            document.getElementById('version_hw').value = data.hw_version || '';
            document.getElementById('version_adu').value = data.ADU_version || '';
            document.getElementById('version_acu').value = data.ACU_version || '';
            document.getElementById('version_stru').value = data.stru_version || '';
        }
    }

    function setupUpgradeHandlers(type) { // type can be 'adu' or 'acu'
        const uploadBtn = document.getElementById(`${type}_upload`);
        const upgradeBtn = document.getElementById(`${type}_upgrade`);
        const fileInput = document.getElementById(`${type}_file`);

        // 上传按钮事件
        uploadBtn.addEventListener('click', () => {
            const file = fileInput.files[0];
            if (!file) {
                alert('请先选择一个文件！');
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                // e.target.result 的格式是 "data:;base64,xxxxxx"，我们只需要逗号后面的部分
                const fileContent = e.target.result.split(',')[1];
                sendControlCommand(`upload_${type}_file`, {
                    content: fileContent,
                    file_name: file.name
                });
                alert('文件上传指令已发送，请等待设备响应...');
            };
            reader.onerror = () => {
                alert('读取文件时发生错误！');
            };
            reader.readAsDataURL(file); // 将文件读取为 Base64 编码的字符串
        });

        // 升级按钮事件
        upgradeBtn.addEventListener('click', () => {
            const file = fileInput.files[0];
            if (!file) {
                alert('请先选择一个文件！');
                return;
            }
            sendControlCommand(`update_${type}`, {
                file_name: file.name
            });
            alert('软件升级指令已发送，请等待设备响应，升级所需时间可能较久，请您耐心等待...');
        });
    }

    // --- 事件绑定 ---
    function sendControlCommand(module, payload = {}) {
        const activeItem = document.querySelector('#terminal-list .list-group-item.active');
        if (!activeItem) {
            alert('错误：没有选择任何端站！');
            return;
        }
        const sn = activeItem.dataset.sn;
        const ip = activeItem.dataset.ip;
        const port = activeItem.dataset.port;

        const message = {
            type: 'control_command', sn, ip, port, module, payload
        };
        window.dataSocket.send(JSON.stringify(message));
    }
    
    // 工作模式
    document.getElementById('query_work_mode').addEventListener('click', () => sendControlCommand('query_work_mode'));
    document.getElementById('set_work_mode').addEventListener('click', () => {
        const pattern = document.getElementById('work_mode').value;
        if (pattern === "") { alert("请先选择一个工作模式！"); return; }
        sendControlCommand('set_work_mode', { pattern });
    });

    // 系统复位
    document.getElementById('adu_task_rst').addEventListener('click', () => sendControlCommand('adu_task_rst'));
    document.getElementById('adu_soft_rst').addEventListener('click', () => sendControlCommand('adu_soft_rst'));

    // RTC
    document.getElementById('query_rtc').addEventListener('click', () => sendControlCommand('query_rtc'));
    document.getElementById('set_rtc').addEventListener('click', () => {
        const dateTime = document.getElementById('datetime_rtc').value;
        if (!dateTime) { alert("请选择日期和时间！"); return; }
        const [date, time] = dateTime.split('T');
        sendControlCommand('set_rtc', { date, time });
    });

    // 上报参数
    document.getElementById('query_report_config').addEventListener('click', () => sendControlCommand('query_report_config'));
    document.getElementById('set_report_config').addEventListener('click', () => {
        const ip = document.getElementById('report_ip').value;
        const port = document.getElementById('report_port').value;
        const mode = document.getElementById('report_mode').value;
        const interval = document.getElementById('report_interval').value;
        if (mode === "") { alert("请至少选择一种上报方式！"); return; }
        sendControlCommand('set_report_config', { ip, port, mode, interval });
    });
    
    // 版本查询
    document.getElementById('query_version').addEventListener('click', () => sendControlCommand('query_version'));

    // 升级版本 为 ADU 和 ACU 分别设置事件处理器
    setupUpgradeHandlers('adu');
    setupUpgradeHandlers('acu');
    
    // 初始化页面
    resetAllStatus();
}