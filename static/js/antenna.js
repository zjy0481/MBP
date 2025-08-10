document.addEventListener('DOMContentLoaded', function () {
    const terminalSelector = document.getElementById('terminal_selector');
    const confirmButton = document.getElementById('confirm_terminal');
    const mainContent = document.getElementById('main_content');
    
    let selectedSn = null;
    let selectedIp = null;
    let selectedPort = null;

    // 确认选择端站
    confirmButton.addEventListener('click', function() {
        const selectedOption = terminalSelector.options[terminalSelector.selectedIndex];
        selectedSn = selectedOption.value;
        
        if (selectedSn) {
            selectedIp = selectedOption.dataset.ip;
            selectedPort = selectedOption.dataset.port;
            mainContent.style.display = 'block';
            alert(`已选择端站: ${selectedSn}。现在将为您加载最新数据。`);
            fetchLatestReport(selectedSn);
        } else {
            alert('请先选择一个端站！');
        }
    });

    // 通过WebSocket获取最新上报数据
    function fetchLatestReport(sn) {
        if (!dataSocket || dataSocket.readyState !== WebSocket.OPEN) {
            alert('WebSocket尚未连接，请刷新页面后重试。');
            return;
        }
        const message = {
            'type': 'get_latest_report',
            'sn': sn
        };
        dataSocket.send(JSON.stringify(message));
    }

    // --- WebSocket消息处理 ---
    // 注意：这里的 onmessage 是对 base.html 中已有的 onmessage 的扩展
    const original_onmessage = dataSocket.onmessage;
    dataSocket.onmessage = function(e) {
        // 首先，执行base.html中原始的onmessage逻辑，以保证列表页刷新功能正常
        if(original_onmessage) {
            original_onmessage(e);
        }

        const data = JSON.parse(e.data);
        const message = data.message;

        // 如果是本页面需要的数据，则进行处理
        if (message.type === 'latest_report_data') {
            if (message.data) {
                updatePageData(message.data);
            } else {
                alert(`未能获取到SN为 ${message.sn} 的最新上报数据。可能该端站暂无数据。`);
            }
        } else if (message.type === 'control_response') {
            if (message.success) {
                alert(`操作成功！\n模块: ${message.module}\n返回数据: ${JSON.stringify(message.data)}`);
                // 如果是查询工作模式或设备状态，则更新页面
                if(message.module === 'query_work_mode' && message.data) {
                    document.getElementById('work_mode').value = message.data.workMode;
                    const modeText = message.data.workMode === 0 ? "自动模式" : "手动模式";
                    document.getElementById('work_mode_status').innerText = `当前模式: ${modeText}`;
                }
                if(message.module === 'query_device_status' && message.data) {
                    showDevicesStatus(message.data);
                }
            } else {
                 alert(`操作失败！\n模块: ${message.module}\n错误信息: ${message.error}`);
            }
        }
    };

    function updatePageData(report) {
        // 系统状态
        setSystemStatus(report.op_sub); // 假设op_sub代表系统状态

        // 无线网络状态
        setLinkStatus(report.op); // 假设op代表链接状态

        // MBP状态参数
        document.getElementById("bts_name").value = report.bts_name || "N/A";
        document.getElementById("bts_no").value = report.bts_number || "N/A";
        document.getElementById("bts_longitude").value = report.bts_long?.toFixed(3) || "N/A";
        document.getElementById("bts_latitude").value = report.bts_lat?.toFixed(3) || "N/A";
        document.getElementById("longitude").value = report.long?.toFixed(3) || "N/A";
        document.getElementById("latitude").value = report.lat?.toFixed(3) || "N/A";
        document.getElementById("theory_yaw").value = report.theory_yaw?.toFixed(2) || "N/A";
        document.getElementById("yaw").value = report.yaw?.toFixed(2) || "N/A";
        document.getElementById("pitch").value = report.pitch?.toFixed(2) || "N/A";
        document.getElementById("roll").value = report.roll?.toFixed(2) || "N/A";
        setYawLimit(report.yao_limit_state);
        document.getElementById("temperature").value = report.temp?.toFixed(2) || "N/A";
        document.getElementById("humidity").value = report.humi?.toFixed(2) || "N/A";
        // document.getElementById("dgps_err").value = "N/A"; // 暂无此字段
        // document.getElementById("dgps_start").value = "N/A"; // 暂无此字段
        
        // 网络速率
        showLinkspeed({
            upstream: report.upstream_rate || 0,
            downstream: report.downstream_rate || 0
        });

        // RSRP
        showNetworkState({
            plmn: report.plmn,
            standard: report.standard,
            cellid: report.cellid,
            pci: report.pci,
            rsrp: report.rsrp,
            rssi: report.rssi,
            sinr: report.sinr
        });
    }

    // --- 控制指令发送 ---
    function sendControlCommand(module, payload = {}) {
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
        dataSocket.send(JSON.stringify(message));
    }

    // 查询工作模式
    document.getElementById('query_work_mode').addEventListener('click', function() {
        sendControlCommand('query_work_mode');
    });

    // 设置工作模式
    document.getElementById('set_work_mode').addEventListener('click', function() {
        const workMode = document.getElementById('work_mode').value;
        sendControlCommand('set_work_mode', { workMode: parseInt(workMode, 10) });
    });
    
    // 手动控制
    document.getElementById('turn_up').addEventListener('click', () => onTurn(0x01, 0x00));
    document.getElementById('turn_down').addEventListener('click', () => onTurn(0x01, 0x01));
    document.getElementById('turn_left').addEventListener('click', () => onTurn(0x00, 0x01));
    document.getElementById('turn_right').addEventListener('click', () => onTurn(0x00, 0x00));

    function onTurn(axis, direct) {
        const turnAngle = parseFloat(document.getElementById('turn_angle').value);
        if(isNaN(turnAngle)){
            alert("请输入有效的旋转角度！");
            return;
        }
        sendControlCommand('turn_control', {
            axis: axis,
            direct: direct,
            angle: turnAngle
        });
    }

    // 查询设备状态
    document.getElementById('query_devices_status').addEventListener('click', function() {
        sendControlCommand('query_device_status');
    });

});

// --- 以下是从 antenna.js 移植并稍作修改的UI更新函数 ---

// 系统状态
function setSystemStatus(status){
    let statuslights = document.querySelectorAll("#antenna_status .statusLight");
    statuslights.forEach(light => light.style.backgroundColor = "lightgray");
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
    const linklights = document.querySelectorAll("#link_status .statusLight");
    linklights.forEach(light => light.style.backgroundColor = "lightgray");
    switch (status) {
        case 0: document.getElementById("dtu_unlink").style.backgroundColor = "red"; break;
        case 1: document.getElementById("dtu_state_dial").style.backgroundColor = "limegreen"; break;
        case 2: document.getElementById("dtu_state_normal").style.backgroundColor = "limegreen"; break;
    }
}

// 方位限位
function setYawLimit(state) {
    const nodeYawLimit = document.getElementById("yaw_limit");
    switch (state) {
        case 0: nodeYawLimit.value = "无接触"; break;
        case 1: nodeYawLimit.value = "左限位"; break;
        case 2: nodeYawLimit.value = "右限位"; break;
        default: nodeYawLimit.value = "N/A"; break;
    }
}

// 网络速率
function showLinkspeed(stream) {
    const nodeLinkspeed = document.getElementById("link_speed");
    nodeLinkspeed.innerHTML=`<h4> 上行：${stream.upstream || 0} Mbps&nbsp;&nbsp;下行：${stream.downstream || 0} Mbps</h4>`;
}

function showNetworkState(param) {
    const nodeDtuPlmn = document.getElementById("dtu_plmn");
    // 运营商转换
    switch (parseInt(param["plmn"],10)) {
        case 46000: case 46002: case 46004: case 46007: case 46008: case 46013:
            nodeDtuPlmn.value = "中国移动"; break;
        case 46001: case 46006: case 46009: case 46010:
            nodeDtuPlmn.value = "中国联通"; break;
        case 46003: case 46005: case 46011: case 46012:
            nodeDtuPlmn.value = "中国电信"; break;
        case 46015:
            nodeDtuPlmn.value = "中国广电"; break;
        default:
            nodeDtuPlmn.value = param.plmn ? "未知运营商" : "N/A"; break;
    }

    document.getElementById("dtu_standard").value = param.standard || 'N/A';
    document.getElementById("dtu_cellid").value = param.cellid || 'N/A';
    document.getElementById("dtu_pci").value = param.pci || 'N/A';
    document.getElementById("dtu_rsrp").value = param.rsrp || 'N/A';
    document.getElementById("dtu_rssi").value = param.rssi || 'N/A';
    document.getElementById("dtu_sinr").value = param.sinr || 'N/A';

    // rsrp图标与换算
    const nodeRsrp = document.getElementById("rsrp_value");
    const nodeRsrpMeter = document.getElementById("rsrp_meter");
    nodeRsrp.innerHTML = `<h1>${param.rsrp || '?'} dBm</h1>`;
    if (param.rsrp) {
        nodeRsrpMeter.value = param.rsrp + 150;
    } else {
        nodeRsrpMeter.value = 0;
    }
}

function setLight(id, status){
    const light = document.getElementById(id);
    if(light) {
        switch (status){
            case 0: light.style.backgroundColor="limegreen"; break;
            case 1: light.style.backgroundColor="red"; break;
            default: light.style.backgroundColor="lightgray";
        }
    }
}

// 设备状态
function showDevicesStatus(status){
    setLight("IMUState", status.IMUState);
    setLight("DGPSState", status.DGPSState);
    setLight("storageState", status.storageState);
    setLight("yawMotoState", status.yawMotoState);
    setLight("pitchMotoState", status.pitchMotoState);
    setLight("yawLimitState", status.yawLimitState);
    setLight("pitchLimitState", status.pitchLimitState);
}