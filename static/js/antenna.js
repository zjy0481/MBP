// static/js/antenna.js

// 全局变量
var ws = null;
let selectedSn = null;

// 初始化函数
function init() {
    console.log("Antenna.js: Initializing page...");
    
    // 初始化WebSocket连接
    initWebSocket();
    
    // 绑定事件监听器
    bindEventListeners();
}

// 初始化WebSocket连接
function initWebSocket() {
    // 创建WebSocket连接
    ws = new WebSocket(
        'ws://' + window.location.host + '/ws/data/'
    );

    // 连接打开事件
    ws.onopen = function(e) {
        console.log('Antenna: WebSocket connection established successfully.');
        
        // WebSocket连接建立后，尝试从全局状态获取已保存的端站选择
        // 这样可以确保在WebSocket连接建立后再发送请求
        const savedTerminal = getCurrentTerminal();
        if (savedTerminal && savedTerminal.sn) {
            console.log("Antenna: WebSocket连接后从全局状态获取到端站选择:", savedTerminal);
            selectedSn = savedTerminal.sn;
            
            // 查找并设置对应的端站项为活动状态
            const terminalItems = document.querySelectorAll('#terminal-list .list-group-item');
            terminalItems.forEach(item => {
                if (item.dataset.sn === savedTerminal.sn) {
                    item.classList.add('active');
                }
            });
            
            // 发起数据请求
            fetchLatestReport(selectedSn);
        }
    };

    // 接收消息事件
    ws.onmessage = function(e) {
        try {
            const data = JSON.parse(e.data);
            if (data.message) {
                handleWebSocketMessage(data.message);
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    };

    // 连接关闭事件
    ws.onclose = function(e) {
        console.error('Antenna: WebSocket connection closed!');
        // 尝试重连
        setTimeout(initWebSocket, 5000);
    };

    // 错误事件
    ws.onerror = function(e) {
        console.error('Antenna: WebSocket error:', e);
    };
}

// 绑定事件监听器
function bindEventListeners() {
    // 监听端站选择事件
    document.addEventListener('terminalSelected', function(e) {
        const detail = e.detail;
        console.log("Antenna page received selection:", detail);

        selectedSn = detail.sn;

        // 重置UI状态
        cleanPageData();
        
        // 发起数据请求
        fetchLatestReport(selectedSn);
    });

    // 监听全局端站状态变化
    if (window.globalTerminalState) {
        window.globalTerminalState.subscribe(function(terminal) {
            if (terminal && terminal.sn) {
                console.log("Antenna page received global terminal change:", terminal);
                selectedSn = terminal.sn;
                
                // 查找并设置对应的端站项为活动状态
                const terminalItems = document.querySelectorAll('#terminal-list .list-group-item');
                terminalItems.forEach(item => {
                    if (item.dataset.sn === terminal.sn) {
                        item.classList.add('active');
                    } else {
                        item.classList.remove('active');
                    }
                });
                
                // 重置UI状态
                cleanPageData();
                
                // 发起数据请求
                fetchLatestReport(selectedSn);
            }
        });
    }

    // 初始化时尝试从全局状态获取已保存的端站选择
    // 注意：这个逻辑现在移到了ws.onopen事件处理器中，确保WebSocket连接建立后再执行
    // const savedTerminal = getCurrentTerminal();
    // if (savedTerminal && savedTerminal.sn) {
    //     console.log("Antenna: 初始化时从全局状态获取到端站选择:", savedTerminal);
    //     selectedSn = savedTerminal.sn;
    //     
    //     // 查找并设置对应的端站项为活动状态
    //     const terminalItems = document.querySelectorAll('#terminal-list .list-group-item');
    //     terminalItems.forEach(item => {
    //         if (item.dataset.sn === savedTerminal.sn) {
    //             item.classList.add('active');
    //         }
    //     });
    //     
    //     // 发起数据请求
    //     fetchLatestReport(selectedSn);
    // }

    // 为所有控制按钮绑定事件
    document.getElementById('query_devices_status').addEventListener('click', () => sendControlCommand('query_device_status'));
}

// 处理WebSocket消息
function handleWebSocketMessage(message) {
    console.log(message.type);
    if (message.type === 'latest_report_data') {
        const report = message.data;
        
        // 实时更新逻辑
        if (report && report.sn === selectedSn) {
            console.log(`收到当前选中端站 [${selectedSn}] 的实时数据，正在更新页面...`);
            cleanPageData();
            updatePageData(report);
        } 
        // 手动查询后没有数据的处理逻辑
        else if (!report && message.sn === selectedSn) {
            document.getElementById('selected_last_report').innerText = '暂无上报数据';
            console.warn(`未能获取到SN为 ${message.sn} 的最新上报数据。`);
            cleanPageData();
        }
        
    } else if (message.type === 'control_response') {
        if (message.success) {
            const responseData = message.data; // data 是端站返回的完整JSON
            console.log(`成功收到来自端站的响应，模块: ${message.module}`);
            
            // 查询设备状态，现在antenna只需要这一功能
            if (message.module === 'query_device_status') {
                if (responseData && responseData.op === 'query_ans' && responseData.op_sub === 'equipment_status') {
                    // 协议中 0=正常, 1=异常; setLight 函数 0=正常, 1=异常
                    const statusMap = {
                        IMUState: responseData.IMU_stat === 0 ? 0 : 1,
                        DGPSState: responseData.DGPS_stat === 0 ? 0 : 1,
                        storageState: responseData.storage_stat === 0 ? 0 : 1,
                        yawMotoState: responseData.yaw_moto_stat === 0 ? 0 : 1,
                        pitchMotoState: responseData.pitch_moto_stat === 0 ? 0 : 1,
                        yawLimitState: responseData.yaw_lim_stat === 0 ? 0 : 1,
                        pitchLimitState: responseData.pitch_lim_stat === 0 ? 0 : 1,
                        RTCState: responseData.RTC_stat === 0 ? 0 : 1,
                    };
                    showDevicesStatus(statusMap);
                    infoMessage('设备状态查询成功！');
                }
            }
        } else {
            errorMessage(`操作失败！\n模块: ${message.module}\n错误信息: ${message.error}`);
        }
    }
}

// --- 以下函数不依赖于 WebSocket 的连接状态，可以放在 initWebSocket 外部 ---

function fetchLatestReport(sn) {
    // 此处调用时，可以确信 WebSocket 已经连接成功
    const message = {
        'type': 'get_latest_report',
        'sn': sn
    };
    ws.send(JSON.stringify(message));
}

function sendControlCommand(module, payload = {}) {
    const activeItem = document.querySelector('#terminal-list .list-group-item.active');
    if (!activeItem) {
        console.error('错误：没有选择任何端站！');
        return;
    }
    const sn = activeItem.dataset.sn;
    const ip = activeItem.dataset.ip;
    const port = activeItem.dataset.port;

    const message = {
        type: 'control_command', sn, ip, port, module, payload
    };
    ws.send(JSON.stringify(message));
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

function cleanPageData() {
    // 将所有栏目设为空
    setSystemStatus(-1);
    setLinkStatus(-1);
    document.getElementById("bts_name").value = "";
    document.getElementById("bts_no").value =  "";
    document.getElementById("bts_longitude").value = "";
    document.getElementById("bts_latitude").value = "";
    document.getElementById("longitude").value = "";
    document.getElementById("latitude").value = "";
    document.getElementById("theory_yaw").value = "";
    document.getElementById("yaw").value = "";
    document.getElementById("pitch").value = "";
    document.getElementById("roll").value = "";
    setYawLimit(-1);
    document.getElementById("temperature").value = "";
    document.getElementById("humidity").value = "";
    showLinkspeed({ upstream: '', downstream: '' });
    showNetworkState({
        plmn: 0, standard: '', cellid: '',
        pci: '', rsrp: -1, rssi: '', sinr: ''
    });
    setLight("IMUState", -1);
    setLight("DGPSState", -1);
    setLight("storageState", -1);
    setLight("yawMotoState", -1);
    setLight("pitchMotoState", -1);
    setLight("yawLimitState", -1);
    setLight("pitchLimitState", -1);
    setLight("RTCState", -1);
    // console.log("清理页面完成");
}

function updatePageData(report) {
    console.log("report如下", report);
    
    // 检查数据是否过期（超过7天）
    // todo 后续可以将判断数据是否过旧的阈值加入config
    if (report.report_date) {
        const reportDate = new Date(report.report_date + 'T00:00:00+08:00'); // 东八区时间
        const now = new Date();
        const chinaNow = new Date(now.getTime() + (8 * 60 * 60 * 1000)); // 转换为东八区时间
        
        // 计算7天前的日期
        const sevenDaysAgo = new Date(chinaNow.getTime() - (7 * 24 * 60 * 60 * 1000));
        
        // 如果数据超过7天，显示红色时间并停止更新
        if (reportDate < sevenDaysAgo) {
            const reportTime = report.report_time ? `${report.report_date} ${report.report_time}` : report.report_date;
            const lastReportNode = document.getElementById('selected_last_report');
            lastReportNode.innerHTML = `<span style="color: red; font-weight: bold;">⚠ ${reportTime} (数据过旧，不做显示)</span>`;
            console.log(`数据过期：${reportTime}，超过7天，停止页面更新`);
            return; // 不进行后续页面更新
        }
    }
    
    // 数据未过期，正常显示时间并更新页面
    if (report.report_date && report.report_time) {
        const lastReportNode = document.getElementById('selected_last_report');
        lastReportNode.innerHTML = `${report.report_date} ${report.report_time}`;
    }
    
    // console.log("系统状态、无线网络状态:",report.system_stat,", ",report.wireless_network_stat);
    let system_state = parseInt(report.system_stat, 10);
    let wireless_network_state = parseInt(report.wireless_network_stat, 10);
    setSystemStatus(system_state);
    setLinkStatus(wireless_network_state);
    // console.log("转换后的系统状态、无线网络状态:",report.system_stat,", ",report.wireless_network_stat);
    document.getElementById("bts_name").value = report.bts_name || "";
    document.getElementById("bts_no").value = report.bts_number || "";
    document.getElementById("bts_longitude").value = parseFloat(report.bts_long)?.toFixed(3) || "";
    document.getElementById("bts_latitude").value = parseFloat(report.bts_lat)?.toFixed(3) || "";
    document.getElementById("longitude").value = parseFloat(report.long)?.toFixed(3) || "";
    document.getElementById("latitude").value = parseFloat(report.lat)?.toFixed(3) || "";
    document.getElementById("theory_yaw").value = parseFloat(report.theory_yaw)?.toFixed(2) || "";
    document.getElementById("yaw").value = parseFloat(report.yaw)?.toFixed(2) || "";
    document.getElementById("pitch").value = parseFloat(report.pitch)?.toFixed(2) || "";
    document.getElementById("roll").value = parseFloat(report.roll)?.toFixed(2) || "";
    setYawLimit(parseInt(report.yao_limit_state, 10));
    document.getElementById("temperature").value = parseFloat(report.temp)?.toFixed(2) || "";
    document.getElementById("humidity").value = parseFloat(report.humi)?.toFixed(2) || "";
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
    // 清除所有状态类
    lights.forEach(light => {
        light.classList.remove('active', 'error', 'warning', 'info');
    });
    
    switch (status) {
        case 0: document.getElementById("light_none").classList.add('warning'); break;
        case 1: document.getElementById("light_init").classList.add('info'); break;
        case 2: document.getElementById("light_presearch").classList.add('info'); break;
        case 3: document.getElementById("light_track").classList.add('active'); break;
        case 4: document.getElementById("light_fault").classList.add('error'); break;
        default: 
    }
}

// 无限网络状态
function setLinkStatus(status) {
    let lights = document.querySelectorAll("#link_status .statusLight");
    // 清除所有状态类
    lights.forEach(light => {
        light.classList.remove('active', 'error', 'warning', 'info');
    });
    
    switch (status) {
        case 0: document.getElementById("dtu_unlink").classList.add('error'); break;
        case 1: document.getElementById("dtu_state_dial").classList.add('active'); break;
        case 2: document.getElementById("dtu_state_normal").classList.add('active'); break;
        default: 
    }
}

// 方位限位
function setYawLimit(state) {
    const node = document.getElementById("yaw_limit");
    switch (state) {
        case 0: node.value = "无接触"; break;
        case 1: node.value = "左限位"; break;
        case 2: node.value = "右限位"; break;
        default: node.value = ""; break;
    }
}

// 网络速率
function formatBandwidth(bps) {
    if (!bps || bps <= 0) {
        return '0 bps';
    }
    
    // 单位转换
    if (bps < 1000) {
        // 小于1000 bps，直接显示
        return `${bps} bps`;
    } else if (bps < 1000 * 1000) {
        // 小于1000 Kbps，转换为Kbps
        const kbps = bps / 1000;
        return `${kbps.toFixed(kbps < 10 ? 2 : 1)} Kbps`;
    } else {
        // 大于等于1000 Kbps，转换为Mbps
        const mbps = bps / (1000 * 1000);
        return `${mbps.toFixed(mbps < 10 ? 2 : 1)} Mbps`;
    }
}

function showLinkspeed(stream) {
    const node = document.getElementById("link_speed");
    const upstream = formatBandwidth(stream.upstream);
    const downstream = formatBandwidth(stream.downstream);
    node.innerHTML = `<h4> 上行：${upstream}&nbsp;&nbsp;下行：${downstream}</h4>`;
}

function showNetworkState(param) {
    const plmnNode = document.getElementById("dtu_plmn");
    // 运营商转换
    switch (parseInt(param["plmn"], 10)) {
        case 46000: case 46002: case 46004: case 46007: case 46008: case 46013: plmnNode.value = "中国移动"; break;
        case 46001: case 46006: case 46009: case 46010: plmnNode.value = "中国联通"; break;
        case 46003: case 46005: case 46011: case 46012: plmnNode.value = "中国电信"; break;
        case 46015: plmnNode.value = "中国广电"; break;
        default: plmnNode.value = param.plmn ? "未知运营商" : ""; break;
    }
    document.getElementById("dtu_standard").value = param.standard || '';
    document.getElementById("dtu_cellid").value = param.cellid || '';
    document.getElementById("dtu_pci").value = param.pci || '';
    document.getElementById("dtu_rsrp").value = param.rsrp == -1 ? '' : param.rsrp || '';
    document.getElementById("dtu_rssi").value = param.rssi || '';
    document.getElementById("dtu_sinr").value = param.sinr || '';

    // rsrp转换与换算
    if (param.rsrp){
        const rsrpValue = document.getElementById("rsrp_value");
        const rsrpMeter = document.getElementById("rsrp_meter");
        rsrpValue.innerHTML = `<h1>${param.rsrp == -1 ? '?' : param.rsrp || '?'} dBm</h1>`;
        rsrpMeter.value = param.rsrp == -1 ? 0 : parseFloat(param.rsrp) + 150 || 0;
    }
}

function setLight(id, status) {
    const light = document.getElementById(id);
    if (light) {
        // 清除所有状态类
        light.classList.remove('active', 'error', 'warning', 'info');
        
        switch (status) {
            case 0: light.classList.add('active'); break;
            case 1: light.classList.add('error'); break;
            case 2: light.classList.add('warning'); break;
            case 3: light.classList.add('info'); break;
            default: // 保持默认状态
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
    setLight("RTCState", status.RTCState);
}

// 页面初始化
init();