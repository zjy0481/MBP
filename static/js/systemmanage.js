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
                if (responseData.result === '0') {
                    infoMessage(`操作 ${module} 成功！`);
                } else {
                    let errorMsg = `操作 ${module} 失败。`;
                    if (responseData.error) {
                        errorMsg += `\n错误信息: ${responseData.error}`;
                    }
                    errorMessage(errorMsg);
                }
            } else {
                infoMessage(`操作成功！模块: ${module}`);   //! 可能要修改？

                // 根据模块处理响应
            switch (message.module) {
                // case 'query_work_mode':
                //     handleWorkModeResponse(responseData);
                //     break;
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
                // case 'set_work_mode': break;
                case 'adu_rst': break;
                case 'set_rtc': break;
                case 'set_report_config': break;
                case 'upload_update_file': break;
                case 'software_update': break;
                default: break;
            }
            }

        } else {
            // 这部分逻辑处理WebSocket通信级别的失败（如超时），保持不变
            errorMessage(`操作失败！\n模块: ${message.module}\n错误信息: ${message.error}`);
        }
    };

    // 注册消息处理器
    if (window.webSocketOnMessageHandlers) {
        window.webSocketOnMessageHandlers = [];
        window.webSocketOnMessageHandlers.push(systemManagePageMessageHandler);
    }

    // --- UI 更新与辅助函数 ---
    function setStatus(elementId, text, mode) {
        const el = document.getElementById(elementId);
        if (el) {
            el.innerText = text;
            // 根据mode值设置不同的CSS类
            switch(mode) {
                case 0:
                    el.className = 'form-text mt-2';
                    break;
                case 1:
                    el.className = 'form-text mt-2 text-success';
                    break;
                case 2:
                    el.className = 'form-text mt-2 text-danger';
                    break;
                default:
                    el.className = 'form-text mt-2';
            }
        }
    }
    
    function setInputValue(elementId, value) {
        const el = document.getElementById(elementId);
        if (el) {
            // 根据元素类型处理不同的表单控件
            switch(el.tagName.toLowerCase()) {
                case 'input':
                    // 日期时间选择器需要特殊处理格式
                    if (el.type === 'datetime-local') {
                        // 确保value是有效的ISO格式（YYYY-MM-DDTHH:MM）
                        if (value && value.includes(' ')) {
                            // 如果是"YYYY-MM-DD HH:MM"格式，转换为"YYYY-MM-DDTHH:MM"
                            value = value.replace(' ', 'T');
                        }
                    }
                    el.value = value;
                    break;
                case 'select':
                    // 选择框需要确保value存在于选项中
                    if (value !== '' && Array.from(el.options).some(opt => opt.value === value)) {
                        el.value = value;
                    } else {
                        // 如果值不存在或为空，选择第一个选项
                        el.selectedIndex = 0;
                    }
                    break;
                default:
                    // 其他输入元素直接设置value
                    el.value = value;
            }
        }
    }
    
    function resetAllStatus() {
        // // 重置工作模式
        // document.getElementById('work_mode').value = "";
        // setStatus('work_mode_status', '当前模式：暂无数据', 0);
        // 重置RTC
        // 获取东八区(UTC+8)的当前时间
        const now = new Date();
        // 创建东八区时间对象（UTC时间加8小时）
        const beijingTime = new Date(now.getTime() + 8 * 60 * 60 * 1000);
        // 转换为ISO格式并截取到分钟部分
        const beijingTimeISO = beijingTime.toISOString().slice(0, 16);
        setInputValue('datetime_rtc', beijingTimeISO);
        setStatus('rtc_status', '端站当前RTC时间：暂无数据', 0);
        // 重置上报参数
        setInputValue('report_ip','暂无数据');
        setInputValue('report_port','暂无数据');
        setInputValue('report_mode','');
        setInputValue('report_interval','');
        setStatus('report_ip_status', '端站当前IP地址：暂无数据', 0);
        setStatus('report_port_status', '端站当前端口号：暂无数据', 0);
        setStatus('report_mode_status', '端站当前上报方式：暂无数据', 0);
        setStatus('report_interval_status', '端站当前上报时间间隔：暂无数据', 0);
        // 重置版本信息
        ['model', 'hw', 'adu', 'acu', 'stru'].forEach(v => document.getElementById(`version_${v}`).value = '');
    }

    // --- 响应处理器 ---
    // function handleWorkModeResponse(data) {
    //     if (data && data.op === 'query_ans' && data.op_sub === 'work_pattern') {
    //         const pattern = data.pattern;
    //         document.getElementById('work_mode').value = pattern;
    //         const modeText = (pattern === '0') ? "自动模式" : "手动模式";
    //         setStatus('work_mode_status', `当前模式: ${modeText}`, true);
    //     } else {
    //         setStatus('work_mode_status', '查询失败：端站响应格式错误', false);
    //     }
    // }

    function handleRtcResponse(data) {
        if (data && data.op === 'query_ans' && data.op_sub === 'RTC') {
            // 更新日期时间选择器
            const datetimeValue = `${data.date} ${data.time}`;
            setInputValue('datetime_rtc', datetimeValue);
            setStatus('rtc_status', `端站当前RTC时间：${datetimeValue}`, 1);
        } else {
            setStatus('rtc_status', '查询失败：端站响应格式错误', 2);
        }
    }

    function handleReportConfigResponse(data) {
        if (data && data.op === 'query_ans' && data.op_sub === 'report_config') {
            // 使用setInputValue函数更新表单控件
            setInputValue('report_ip', data.ip || '');
            setInputValue('report_port', data.port || '');
            setInputValue('report_mode', data.mode || '');
            setInputValue('report_RTC', data.RTC || '');
            setInputValue('report_interval', data.interval || '');
            const modeMap = {'0': '不上报', '1': '通过CPE上报', '2': '通过NB上报'};
            const RTCMap = {'0': '上报RTC时间', '1': '不上报RTC时间'};
            setStatus('report_ip_status', `端站当前IP地址：${data.ip || 'N/A'}`, 1);
            setStatus('report_port_status', `端站当前端口号：${data.port || 'N/A'}`, 1);
            setStatus('report_mode_status', `端站当前上报方式：${modeMap[data.mode] || '未知'}`, 1);
            setStatus('report_mode_status', `端站当前是否上报RTC：${RTCMap[data.RTC] || '未知'}`, 1);
            setStatus('report_interval_status', `端站当前上报时间间隔：${data.interval || 'N/A'}秒`, 1);
        } else {
            setStatus('report_ip_status', '查询失败：端站响应格式错误', 2);
            setStatus('report_port_status', '查询失败：端站响应格式错误', 2);
            setStatus('report_mode_status', '查询失败：端站响应格式错误', 2);
            setStatus('report_mode_status', '查询失败：端站响应格式错误', 2);
            setStatus('report_interval_status', '查询失败：端站响应格式错误', 2);

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
        const update_type = (type === 'adu') ? "0" : "1";

        // 上传按钮事件
        uploadBtn.addEventListener('click', () => {
            const file = fileInput.files[0];
            if (!file) {
                warningMessage('请先选择一个文件！');
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                // e.target.result 的格式是 "data:;base64,xxxxxx"，我们只需要逗号后面的部分
                const fileContent = e.target.result.split(',')[1];
                sendControlCommand('upload_update_file', {
                    update_type: update_type,
                    content: fileContent,
                    file_name: file.name
                });
                console.log('文件上传指令已发送，请等待设备响应...');
            };
            reader.onerror = () => {
                errorMessage('读取文件时发生错误！');
            };
            reader.readAsDataURL(file); // 将文件读取为 Base64 编码的字符串
        });

        // 升级按钮事件
        upgradeBtn.addEventListener('click', () => {
            const file = fileInput.files[0];
            if (!file) {
                warningMessage('请先选择一个文件！');
                return;
            }
            sendControlCommand('software_update', {
                update_type: update_type,
                file_name: file.name
            });
            console.log('软件升级指令已发送，请等待设备响应，升级所需时间可能较久，请您耐心等待...');
        });
    }

    // --- 事件绑定 ---
    function sendControlCommand(module, payload = {}) {
        const activeItem = document.querySelector('#terminal-list .list-group-item.active');
        if (!activeItem) {
            console.error('错误：activeItem为空！');
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
    // document.getElementById('query_work_mode').addEventListener('click', () => sendControlCommand('query_work_mode'));
    // document.getElementById('set_work_mode').addEventListener('click', () => {
    //     const pattern = document.getElementById('work_mode').value;
    //     if (pattern === "") { alert("请先选择一个工作模式！"); return; }
    //     sendControlCommand('set_work_mode', { pattern });
    // });

    // 系统复位
    document.getElementById('adu_task_rst').addEventListener('click', () => {
        const rst_type = 0;
        sendControlCommand('adu_rst', {rst_type});
    });
    document.getElementById('adu_soft_rst').addEventListener('click', () => {
        const rst_type = 1;
        sendControlCommand('adu_rst', {rst_type});
    });

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