// stationimport.js

// 全局变量
let ws = null;
let currentTerminalSN = null;

// 初始化函数
function init() {
    console.log("StationImport.js: Initializing page...");
    
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
        console.log('StationImport: WebSocket connection established successfully.');
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
        console.error('StationImport: WebSocket connection closed!');
        // 尝试重连
        setTimeout(initWebSocket, 5000);
    };

    // 错误事件
    ws.onerror = function(e) {
        console.error('StationImport: WebSocket error:', e);
    };
}

// 绑定事件监听器
function bindEventListeners() {
    // 基站全选
    document.getElementById('selectAllBts').addEventListener('click', selectAllBts);
    // 基站全不选
    document.getElementById('selectNoneBts').addEventListener('click', selectNoneBts);
    // 基站主复选框
    document.getElementById('btsMasterCheckbox').addEventListener('change', toggleAllBts);
    // 端站主复选框已移除，不再需要此事件监听
    // document.getElementById('terminalMasterCheckbox').addEventListener('change', toggleAllTerminals);
    // 更新基站信息按钮
    document.getElementById('updateBtsInfoBtn').addEventListener('click', updateBtsInfo);
    // 按地区选择基站
    document.querySelectorAll('.region-select-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            const region = this.getAttribute('data-region');
            selectBtsByRegion(region);
        });
    });
    // 端站单选框点击事件，用于记录当前选中的端站
    document.querySelectorAll('.terminal-radio').forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                currentTerminalSN = this.getAttribute('data-sn');
                console.log('当前选中端站:', currentTerminalSN);
            }
        });
    });
}

// 处理WebSocket消息
function handleWebSocketMessage(message) {
    console.log("StationImport: Received message:", message);
    if (message.type === 'control_response' && message.module === 'station_import') {
        // console.log('handleWebSocketMessage: 基站导入响应:', message.data);
        handleStationImportResponse(message);
        
    }
}

// 全选基站
function selectAllBts() {
    document.querySelectorAll('.bts-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
    updateMasterCheckboxState('btsMasterCheckbox', '.bts-checkbox');
}

// 全不选基站
function selectNoneBts() {
    document.querySelectorAll('.bts-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    updateMasterCheckboxState('btsMasterCheckbox', '.bts-checkbox');
}

// 按地区选择基站
function selectBtsByRegion(region) {
    document.querySelectorAll('.bts-checkbox').forEach(checkbox => {
        checkbox.checked = checkbox.getAttribute('data-region') === region;
    });
    updateMasterCheckboxState('btsMasterCheckbox', '.bts-checkbox');
}

// 切换所有基站选择状态
function toggleAllBts() {
    const isChecked = document.getElementById('btsMasterCheckbox').checked;
    document.querySelectorAll('.bts-checkbox').forEach(checkbox => {
        checkbox.checked = isChecked;
    });
}

// 切换所有端站选择状态 - 不再需要，因为已改为单选框
// function toggleAllTerminals() {
//     const isChecked = document.getElementById('terminalMasterCheckbox').checked;
//     document.querySelectorAll('.terminal-checkbox').forEach(checkbox => {
//         checkbox.checked = isChecked;
//     });
// }

// 更新主复选框状态
function updateMasterCheckboxState(masterId, checkboxClass) {
    const checkboxes = document.querySelectorAll(checkboxClass);
    const checkedBoxes = document.querySelectorAll(`${checkboxClass}:checked`);
    const masterCheckbox = document.getElementById(masterId);
    
    masterCheckbox.checked = checkboxes.length > 0 && checkboxes.length === checkedBoxes.length;
    masterCheckbox.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < checkboxes.length;
}

// 获取选中的基站
function getSelectedBts() {
    const selectedBts = [];
    document.querySelectorAll('.bts-checkbox:checked').forEach(checkbox => {
        const btsId = checkbox.getAttribute('data-bts-id');
        // 查找对应的行获取基站信息
        const row = checkbox.closest('tr');
        const cells = row.querySelectorAll('td');
        
        selectedBts.push({
            bts_id: btsId,
            bts_name: cells[2].textContent.trim(),
            region_code: cells[3].textContent.trim() !== '-' ? cells[3].textContent.trim() : '',
            // 经度和纬度信息已从表格中移除
        });
    });
    console.log('选中的基站:', selectedBts);
    return selectedBts;
}

// 获取选中的端站
function getSelectedTerminal() {
    let selectedTerminals = null;
    const checkedRadio = document.querySelector('.terminal-radio:checked');
    
    if (checkedRadio) {
        // 获取端站的SN、IP和端口信息
        currentTerminalSN = checkedRadio.getAttribute('data-sn');   // 再次更新currentTerminalSN，确保该全局变量与所选端站同步
        const sn = checkedRadio.getAttribute('data-sn');
        const ip_address = checkedRadio.getAttribute('data-ip_address');
        const port_number = checkedRadio.getAttribute('data-port_number');

        // console.log(`端站信息 - SN: ${sn}, IP: ${ip_address || ''}, Port: ${port_number || ''}`);
        
        selectedTerminals = {
            sn: sn,
            ip_address: ip_address || '',
            port_number: port_number || ''
        };
    }
    return selectedTerminals;
}

// 更新基站信息
function updateBtsInfo() {
    const selectedBts = getSelectedBts();
    const selectedTerminals = getSelectedTerminal();
    
    if (selectedBts.length === 0) {
        warningMessage('请至少选择一个基站');
        return;
    }
    
    if (!selectedTerminals) {
        warningMessage('请选择一个端站');
        return;
    }
    
    // 发送消息给选中的端站（现在只有一个）
    sendMessageToTerminals(selectedTerminals, selectedBts);
    
    infoMessage(`正在向端站sn: ${selectedTerminals.sn}发送基站信息...`);
}

// 向端站发送消息
function sendMessageToTerminals(terminal, stationList) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        errorMessage('WebSocket连接未建立，无法发送消息');
        return;
    }

    if (currentTerminalSN !== terminal.sn) {
        errorMessage(`currentTerminalSN与选中的端站SN不匹配: ${currentTerminalSN} !== ${terminal.sn}`);
        return;
    }
    
    // 为选中的端站发送消息
    const terminalSN = currentTerminalSN;
    const terminalIP = terminal.ip_address;
    const terminalPort = terminal.port_number;
    
    // 按照协议文档构造消息
    const payload = {
        sn: terminalSN, // 消息的sn字段与端站匹配
        op: "update",
        op_sub: "base_station_import",
        station_list: stationList // 直接使用原始对象，避免双重JSON序列化
    };
    
    console.log(`发送基站导入消息给端站 ${terminalSN}:`, payload);
    console.log(`端站信息 - SN: ${terminalSN}, IP: ${terminalIP}, Port: ${terminalPort}`);

    // 构造最终消息对象
    const message = {
        type: 'control_command',
        sn: terminalSN,
        ip: terminalIP,
        port: terminalPort,
        module: 'station_import', // 设置默认模块名称
        payload: payload
    };

    // 发送消息
    ws.send(JSON.stringify(message));
    
    // 为避免消息发送过快，可以添加一个小延迟
    // if (index < terminal.length - 1) {
    //     setTimeout(() => {}, 100);
    // }
}

// 处理基站导入响应
function handleStationImportResponse(message) {
    console.log("收到基站导入响应:", message);
    
    // 情况1: 通信级别的错误
    if (message.success === false) {
        const errorMsg = `更新sn: ${currentTerminalSN}的基站信息失败，失败原因：${message.error || "操作失败：通信错误"}`;
        errorMessage(errorMsg);
        return;
    }
    
    // 检查是否有data字段
    if (!message.data) {
        console.error("响应格式不正确，缺少data字段:", message);
        errorMessage("响应格式错误：缺少必要数据");
        return;
    }
    
    const data = message.data;
    
    // 情况2: 端站级别的错误
    if (data.result === 1) {
        const errorMsg = `更新sn: ${data.sn}的基站信息失败，失败原因：${data.error || '未知错误'}`;
        errorMessage(errorMsg);
        return;
    }
    
    // 情况3: 更新成功
    if (data.result === 0) {
        const successMessage = `成功更新了sn: ${data.sn}的基站信息`;
        infoMessage(successMessage);
    }
}

// 移除了消息队列系统，改用base.html中提供的全局函数

// 移除了消息队列系统相关函数，改用base.html中提供的全局函数

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);