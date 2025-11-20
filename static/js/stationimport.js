// stationimport.js

// 全局变量
let ws = null;
let currentTerminalSN = null;
let messageQueue = []; // 消息队列
let maxVisibleMessages = 3; // 最大可见消息数量
let successResponses = []; // 短时间内的成功响应集合
let successResponseTimer = null; // 成功响应合并定时器
const successMergeTimeout = 3000; // 成功响应合并超时时间（毫秒）

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
    // 端站主复选框
    document.getElementById('terminalMasterCheckbox').addEventListener('change', toggleAllTerminals);
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
    // 端站复选框点击事件，用于记录当前选中的端站
    document.querySelectorAll('.terminal-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
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

// 切换所有端站选择状态
function toggleAllTerminals() {
    const isChecked = document.getElementById('terminalMasterCheckbox').checked;
    document.querySelectorAll('.terminal-checkbox').forEach(checkbox => {
        checkbox.checked = isChecked;
    });
}

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
function getSelectedTerminals() {
    const selectedTerminals = [];
    document.querySelectorAll('.terminal-checkbox:checked').forEach(checkbox => {
        // 获取端站的SN、IP和端口信息
        const sn = checkbox.getAttribute('data-sn');
        const ip_address = checkbox.getAttribute('data-ip_address');
        const port_number = checkbox.getAttribute('data-port_number');

        // console.log(`端站信息 - SN: ${sn}, IP: ${ip_address || ''}, Port: ${port_number || ''}`);
        
        selectedTerminals.push({
            sn: sn,
            ip_address: ip_address || '',
            port_number: port_number || ''
        });
    });
    return selectedTerminals;
}

// 更新基站信息
function updateBtsInfo() {
    const selectedBts = getSelectedBts();
    const selectedTerminals = getSelectedTerminals();
    
    if (selectedBts.length === 0) {
        showResultMessage('请至少选择一个基站', 'alert-warning');
        return;
    }
    
    if (selectedTerminals.length === 0) {
        showResultMessage('请至少选择一个端站', 'alert-warning');
        return;
    }
    
    // 发送消息给每个选中的端站
    sendMessageToTerminals(selectedTerminals, selectedBts);
    
    showResultMessage(`正在向 ${selectedTerminals.length} 个端站发送基站信息...`, 'alert-info');
}

// 向端站发送消息
function sendMessageToTerminals(terminals, stationList) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        showResultMessage('WebSocket连接未建立，无法发送消息', 'alert-danger');
        return;
    }
    
    // 为每个选中的端站单独发送消息
    terminals.forEach((terminal, index) => {
        const terminalSN = terminal.sn;
        const terminalIP = terminal.ip_address;
        const terminalPort = terminal.port_number;
        
        // 按照协议文档构造消息
        const payload = {
            sn: terminalSN, // 每个消息的sn字段与对应端站匹配
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
        if (index < terminals.length - 1) {
            setTimeout(() => {}, 100);
        }
    });
}

// 处理基站导入响应
function handleStationImportResponse(message) {
    console.log("收到基站导入响应:", message);
    
    // 情况1: 通信级别的错误
    if (message.success === false) {
        const errorMessage = message.error || "操作失败：通信错误";
        addMessageToQueue(errorMessage, 'alert-danger');
        return;
    }
    
    // 检查是否有data字段
    if (!message.data) {
        console.error("响应格式不正确，缺少data字段:", message);
        addMessageToQueue("响应格式错误：缺少必要数据", 'alert-danger');
        return;
    }
    
    const data = message.data;
    
    // 情况2: 端站级别的错误
    if (data.result === 1) {
        const errorMessage = `更新sn: ${data.sn}的基站信息失败，失败原因：${data.error || '未知错误'}`;
        addMessageToQueue(errorMessage, 'alert-danger');
        return;
    }
    
    // 情况3: 更新成功
    if (data.result === 0) {
        // 添加到成功响应集合
        successResponses.push(data.sn);
        
        // 清除之前的定时器
        if (successResponseTimer) {
            clearTimeout(successResponseTimer);
        }
        
        // 更新成功消息并重置定时器
        updateSuccessMessage();
        
        // 设置新的定时器，用于清空成功响应集合
        successResponseTimer = setTimeout(() => {
            successResponses = [];
            successResponseTimer = null;
        }, successMergeTimeout);
    }
}

// 添加消息到队列
function addMessageToQueue(message, alertClass) {
    // 创建消息对象
    const messageObj = {
        content: message,
        type: alertClass,
        id: Date.now(), // 唯一ID用于标识
        element: null   // 将在显示时设置为DOM元素引用
    };
    
    // 添加到队列
    messageQueue.push(messageObj);
    
    // 尝试显示消息
    displayMessageFromQueue();
}

// 更新成功消息
function updateSuccessMessage() {
    // 查找已存在的成功消息
    const existingSuccessMessageIndex = messageQueue.findIndex(
        msg => msg.type === 'alert-success' && msg.content.includes('成功更新了')
    );
    
    if (existingSuccessMessageIndex >= 0) {
        // 更新现有成功消息的内容
        const messageObj = messageQueue[existingSuccessMessageIndex];
        const snList = successResponses.map(sn => `sn: ${sn}`).join('，');
        messageObj.content = `成功更新了${snList}的基站信息`;
        
        // 如果消息已经显示，更新DOM
        if (messageObj.element) {
            messageObj.element.textContent = messageObj.content;
            
            // 重置自动隐藏时间
            resetMessageTimeout(messageObj);
        }
    } else {
        // 创建新的成功消息
        addMessageToQueue(`成功更新了sn: ${successResponses[successResponses.length - 1]}的基站信息`, 'alert-success');
    }
}

// 从队列显示消息
function displayMessageFromQueue() {
    const messagesContainer = document.getElementById('operationResult');
    if (!messagesContainer) return;
    
    // 确保messagesContainer有正确的样式
    if (!messagesContainer.classList.contains('messages-container')) {
        messagesContainer.classList.add('messages-container');
        messagesContainer.style.position = 'relative';
        messagesContainer.style.display = 'block';
        messagesContainer.style.padding = '0';
        messagesContainer.style.margin = '10px 0';
    }
    
    // 获取当前可见的消息数量
    const visibleMessages = messagesContainer.querySelectorAll('.message-item').length;
    
    // 如果队列中有消息且可见消息数量少于最大限制，显示下一条
    if (messageQueue.length > 0 && visibleMessages < maxVisibleMessages) {
        const messageObj = messageQueue[0];
        
        // 创建消息元素
        const messageElement = document.createElement('div');
        messageElement.className = `alert ${messageObj.type} message-item`;
        messageElement.textContent = messageObj.content;
        messageElement.dataset.messageId = messageObj.id;
        messageElement.style.margin = '5px 0';
        messageElement.style.padding = '10px';
        messageElement.style.borderRadius = '4px';
        messageElement.style.transition = 'all 0.3s ease';
        messageElement.style.opacity = '0';
        messageElement.style.transform = 'translateY(10px)';
        
        // 将消息元素引用保存到消息对象
        messageObj.element = messageElement;
        
        // 添加到容器
        messagesContainer.appendChild(messageElement);
        
        // 触发动画显示
        setTimeout(() => {
            messageElement.style.opacity = '1';
            messageElement.style.transform = 'translateY(0)';
        }, 10);
        
        // 为所有消息设置自动隐藏定时器
        resetMessageTimeout(messageObj);
        
        // 从队列中移除已显示的消息
        messageQueue.shift();
        
        // 递归检查是否还有消息可以显示
        setTimeout(() => displayMessageFromQueue(), 50);
    }
}

// 重置消息的自动隐藏定时器
function resetMessageTimeout(messageObj) {
    // 清除现有的定时器
    if (messageObj.timeoutId) {
        clearTimeout(messageObj.timeoutId);
    }
    
    // 设置新的定时器
    messageObj.timeoutId = setTimeout(() => {
        if (messageObj.element) {
            // 触发淡出动画
            messageObj.element.style.opacity = '0';
            messageObj.element.style.transform = 'translateY(-10px)';
            
            // 动画结束后移除元素
            setTimeout(() => {
                if (messageObj.element && messageObj.element.parentNode) {
                    messageObj.element.parentNode.removeChild(messageObj.element);
                    messageObj.element = null;
                    
                    // 检查是否需要显示队列中的下一条消息
                    displayMessageFromQueue();
                }
            }, 300);
        }
    }, 5000); // 5秒后隐藏
}

// 显示结果消息（更新为使用消息队列系统）
function showResultMessage(message, alertClass) {
    addMessageToQueue(message, alertClass);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);