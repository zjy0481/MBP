// static/js/antenna.js

// 这个函数将由 base.html 在 WebSocket 连接成功后自动调用
function onSocketReady() {
    console.log("Antenna.js: WebSocket is ready. Initializing page logic.");

    // --- 变量定义 ---
    const terminalSelector = document.getElementById('terminal_selector');
    const confirmButton = document.getElementById('confirm_terminal');
    const mainContent = document.getElementById('main_content');
    
    let selectedSn = null;

    // --- 事件监听 ---
    // “确认选择”按钮的点击事件
    // (因为这个函数在 onSocketReady 内部，所以它被绑定时，WebSocket 必定是可用的)
    confirmButton.addEventListener('click', function() {
        const selectedOption = terminalSelector.options[terminalSelector.selectedIndex];
        if (!selectedOption || !selectedOption.value) {
            alert('请先选择一个端站！');
            return;
        }
        
        selectedSn = selectedOption.value;
        mainContent.style.display = 'block';

        // 重置工作模式状态为初始状态
        document.getElementById('work_mode').value = ""; // 选中占位符
        const workModeStatus = document.getElementById('work_mode_status');
        workModeStatus.innerText = '当前模式：暂无数据';
        workModeStatus.className = 'form-text mt-2'; // 恢复为灰色

        alert(`已选择端站: ${selectedSn}。现在将为您加载最新数据。`);
        
        // 调用发送函数
        fetchLatestReport(selectedSn);
    });

    // --- WebSocket消息处理 ---
    // 定义 antenna.html 专属的 WebSocket 消息处理器
    const antennaPageMessageHandler = function(message) {
        if (message.type === 'latest_report_data') {
            if (message.sn === selectedSn) {
                if (message.data) {
                    updatePageData(message.data);
                } else {
                    alert(`未能获取到SN为 ${message.sn} 的最新上报数据。可能该端站暂无数据。`);
                }
            }
        } else if (message.type === 'control_response') {
            if (message.success) {
                const responseData = message.data; // data 是端站返回的完整JSON
                alert(`操作成功！模块: ${message.module}`);
                
                // --- 将端站响应信息反映到前端 ---

                // 查询工作模式
                if (message.module === 'query_work_mode') {
                    // 检查响应是否符合协议
                    if (responseData && responseData.op === 'query_ans' && responseData.op_sub === 'work_pattern') {
                        const pattern = responseData.pattern; // "0" or "1"
                        const workModeSelect = document.getElementById('work_mode');
                        const workModeStatus = document.getElementById('work_mode_status');

                        workModeSelect.value = pattern; // 更新下拉框的选中值
                        const modeText = (pattern === '0') ? "自动模式" : "手动模式";
                        workModeStatus.innerText = `当前模式: ${modeText}`;
                        workModeStatus.className = 'mt-2 text-success'; // 移除旧class, 添加绿色class
                    } else {
                        // 如果响应格式不正确
                        const workModeStatus = document.getElementById('work_mode_status');
                        workModeStatus.innerText = '查询失败：端站响应格式错误';
                        workModeStatus.className = 'mt-2 text-danger'; // 设置为红色
                    }
                }
                // 设置工作模式
                else if (message.module === 'set_work_mode') {
                    if (responseData && responseData.op === 'antenna_control_ans' && responseData.op_sub === 'work_pattern') {
                        if (responseData.result === '1') {
                            alert('工作模式设置成功！');
                            sendControlCommand('query_work_mode');
                        } else {
                            alert('工作模式设置失败！端站返回错误。');
                        }
                    }
                }
                // 查询设备状态
                else if (message.module === 'query_device_status') {
                    if (responseData && responseData.op === 'query_ans' && responseData.op_sub === 'equipment_status') {
                        // 协议中 1=正常, 0=异常; 而 setLight 函数 0=正常, 1=异常，需要转换
                        const statusMap = {
                            IMUState: responseData.IMU_stat === '1' ? 0 : 1,
                            DGPSState: responseData.DGPS_stat === '1' ? 0 : 1,
                            storageState: responseData.storage_stat === '1' ? 0 : 1,
                            yawMotoState: responseData.yaw_moto_stat === '1' ? 0 : 1,
                            pitchMotoState: responseData.pitch_moto_stat === '1' ? 0 : 1,
                            yawLimitState: responseData.yaw_lim_stat === '1' ? 0 : 1,
                            pitchLimitState: responseData.pitch_lim_stat === '1' ? 0 : 1,
                        };
                        showDevicesStatus(statusMap);
                        alert('设备状态查询成功！');
                    }
                }
                // 手动控制天线旋转
                else if (message.module === 'turn_control') {
                    if (responseData && responseData.op === 'antenna_control_ans' && responseData.op_sub === 'rotate') {
                        if (responseData.result === '1') {
                            alert('天线转动操作成功！');
                        } else {
                            alert(`天线转动操作失败！\n原因: ${responseData.error || '未知'}`);
                        }
                    }
                }

            } else {
                alert(`操作失败！\n模块: ${message.module}\n错误信息: ${message.error}`);
            }
        }
    };

    // 将我们的专属处理器注册到 base.html 定义的全局列表中
    if (window.webSocketOnMessageHandlers) {
        window.webSocketOnMessageHandlers = [];
        window.webSocketOnMessageHandlers.push(antennaPageMessageHandler);
    }

    // --- 为所有控制按钮绑定事件 ---
    document.getElementById('query_work_mode').addEventListener('click', () => sendControlCommand('query_work_mode'));
    
    document.getElementById('set_work_mode').addEventListener('click', () => {
        const workMode = document.getElementById('work_mode').value;
        if (workMode === "") {
            alert("请先选择一个工作模式再进行设置！");
            return;
        }
        sendControlCommand('set_work_mode', { pattern: workMode });
    });
    
    document.getElementById('turn_up').addEventListener('click', () => onTurn(1, 0));
    document.getElementById('turn_down').addEventListener('click', () => onTurn(1, 1));
    document.getElementById('turn_left').addEventListener('click', () => onTurn(0, 1));
    document.getElementById('turn_right').addEventListener('click', () => onTurn(0, 0));

    document.getElementById('query_devices_status').addEventListener('click', () => sendControlCommand('query_device_status'));
}


// --- 以下函数不依赖于 WebSocket 的连接状态，可以放在 onSocketReady 外部 ---

function fetchLatestReport(sn) {
    // 此处调用时，可以确信 dataSocket 已经连接成功
    const message = {
        'type': 'get_latest_report',
        'sn': sn
    };
    window.dataSocket.send(JSON.stringify(message));
}

function sendControlCommand(module, payload = {}) {
    const selectedSn = document.getElementById('terminal_selector').value;
    const selectedOption = document.getElementById('terminal_selector').selectedOptions[0];
    const selectedIp = selectedOption.dataset.ip;
    const selectedPort = selectedOption.dataset.port;

    if (!selectedSn || !selectedIp || !selectedPort) {
        alert('错误：尚未选择端站或端站信息不完整！');
        return;
    }
    const message = {
        type: 'control_command',
        sn: selectedSn,
        ip: selectedIp,
        port: selectedPort,
        module: module,
        payload: payload
    };
    window.dataSocket.send(JSON.stringify(message));
}

function onTurn(axis, direct) {
    const turnAngle = parseFloat(document.getElementById('turn_angle').value);
    if(isNaN(turnAngle)){
        alert("请输入有效的旋转角度！");
        return;
    }
    const turnMode = document.getElementById('turn_mode').value;
    sendControlCommand('turn_control', { 
        mode: turnMode, 
        axis: axis, 
        direct: direct, 
        angle: turnAngle 
    });
}

function updatePageData(report) {
    // (这部分UI更新逻辑保持不变)
    setSystemStatus(parseInt(report.op_sub, 10));
    setLinkStatus(parseInt(report.op, 10));
    document.getElementById("bts_name").value = report.bts_name || "N/A";
    document.getElementById("bts_no").value = report.bts_number || "N/A";
    document.getElementById("bts_longitude").value = parseFloat(report.bts_long)?.toFixed(3) || "N/A";
    document.getElementById("bts_latitude").value = parseFloat(report.bts_lat)?.toFixed(3) || "N/A";
    document.getElementById("longitude").value = parseFloat(report.long)?.toFixed(3) || "N/A";
    document.getElementById("latitude").value = parseFloat(report.lat)?.toFixed(3) || "N/A";
    document.getElementById("theory_yaw").value = parseFloat(report.theory_yaw)?.toFixed(2) || "N/A";
    document.getElementById("yaw").value = parseFloat(report.yaw)?.toFixed(2) || "N/A";
    document.getElementById("pitch").value = parseFloat(report.pitch)?.toFixed(2) || "N/A";
    document.getElementById("roll").value = parseFloat(report.roll)?.toFixed(2) || "N/A";
    setYawLimit(parseInt(report.yao_limit_state, 10));
    document.getElementById("temperature").value = parseFloat(report.temp)?.toFixed(2) || "N/A";
    document.getElementById("humidity").value = parseFloat(report.humi)?.toFixed(2) || "N/A";
    showLinkspeed({ upstream: report.upstream_rate, downstream: report.downstream_rate });
    showNetworkState({
        plmn: report.plmn, standard: report.standard, cellid: report.cellid,
        pci: report.pci, rsrp: report.rsrp, rssi: report.rssi, sinr: report.sinr
    });
}

// --- 以下是独立的UI更新函数，它们不依赖 DOMContentLoaded ---

// 系统状态
function setSystemStatus(status) {
    let lights = document.querySelectorAll("#antenna_status .statusLight");
    lights.forEach(light => light.style.backgroundColor = "lightgray");
    switch (status) {
        case 0: document.getElementById("light_none").style.backgroundColor = "limegreen"; break;
        case 1: document.getElementById("light_init").style.backgroundColor = "limegreen"; break;
        case 2: document.getElementById("light_presearch").style.backgroundColor = "limegreen"; break;
        case 3: document.getElementById("light_track").style.backgroundColor = "limegreen"; break;
        case 4: document.getElementById("light_fault").style.backgroundColor = "red"; break;
    }
}

// 无限网络状态
function setLinkStatus(status) {
    let lights = document.querySelectorAll("#link_status .statusLight");
    lights.forEach(light => light.style.backgroundColor = "lightgray");
    switch (status) {
        case 0: document.getElementById("dtu_unlink").style.backgroundColor = "red"; break;
        case 1: document.getElementById("dtu_state_dial").style.backgroundColor = "limegreen"; break;
        case 2: document.getElementById("dtu_state_normal").style.backgroundColor = "limegreen"; break;
    }
}

// 方位限位
function setYawLimit(state) {
    const node = document.getElementById("yaw_limit");
    switch (state) {
        case 0: node.value = "无接触"; break;
        case 1: node.value = "左限位"; break;
        case 2: node.value = "右限位"; break;
        default: node.value = "N/A"; break;
    }
}

// 网络速率
function showLinkspeed(stream) {
    const node = document.getElementById("link_speed");
    node.innerHTML = `<h4> 上行：${stream.upstream || 0} Mbps&nbsp;&nbsp;下行：${stream.downstream || 0} Mbps</h4>`;
}

function showNetworkState(param) {
    const plmnNode = document.getElementById("dtu_plmn");
    // 运营商转换
    switch (parseInt(param["plmn"], 10)) {
        case 46000: case 46002: case 46004: case 46007: case 46008: case 46013: plmnNode.value = "中国移动"; break;
        case 46001: case 46006: case 46009: case 46010: plmnNode.value = "中国联通"; break;
        case 46003: case 46005: case 46011: case 46012: plmnNode.value = "中国电信"; break;
        case 46015: plmnNode.value = "中国广电"; break;
        default: plmnNode.value = param.plmn ? "未知运营商" : "N/A"; break;
    }
    document.getElementById("dtu_standard").value = param.standard || 'N/A';
    document.getElementById("dtu_cellid").value = param.cellid || 'N/A';
    document.getElementById("dtu_pci").value = param.pci || 'N/A';
    document.getElementById("dtu_rsrp").value = param.rsrp || 'N/A';
    document.getElementById("dtu_rssi").value = param.rssi || 'N/A';
    document.getElementById("dtu_sinr").value = param.sinr || 'N/A';

    // rsrp转换与换算
    const rsrpValue = document.getElementById("rsrp_value");
    const rsrpMeter = document.getElementById("rsrp_meter");
    rsrpValue.innerHTML = `<h1>${param.rsrp || '?'} dBm</h1>`;
    rsrpMeter.value = param.rsrp ? parseFloat(param.rsrp) + 150 : 0;
}

function setLight(id, status) {
    const light = document.getElementById(id);
    if (light) {
        switch (status) {
            case 0: light.style.backgroundColor = "limegreen"; break;
            case 1: light.style.backgroundColor = "red"; break;
            default: light.style.backgroundColor = "lightgray";
        }
    }
}

// 设备状态
function showDevicesStatus(status) {
    setLight("IMUState", status.IMUState);
    setLight("DGPSState", status.DGPSState);
    setLight("storageState", status.storageState);
    setLight("yawMotoState", status.yawMotoState);
    setLight("pitchMotoState", status.pitchMotoState);
    setLight("yawLimitState", status.yawLimitState);
    setLight("pitchLimitState", status.pitchLimitState);
}