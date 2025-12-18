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
    
    // 端站选择下拉菜单和搜索功能
    const terminalSearch = document.getElementById('terminalSearch');
    const selectedTerminalText = document.getElementById('selectedTerminalText');
    
    // 端站搜索功能
    terminalSearch.addEventListener('input', function() {
        const filter = this.value.toLowerCase();
        // 每次搜索时重新获取选项列表，确保获取最新的DOM结构
        const terminalOptions = document.querySelectorAll('.terminal-option');
        
        terminalOptions.forEach(option => {
            const text = option.textContent.toLowerCase();
            if (text.includes(filter)) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    });
    
    // 端站选择事件 - 使用事件委托来处理动态生成的选项
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('terminal-option')) {
            e.preventDefault();
            
            // 获取选择的端站信息
            currentTerminalSN = e.target.getAttribute('data-sn');
            const shipName = e.target.getAttribute('data-ship-name');
            
            // 更新按钮显示的文本
            selectedTerminalText.textContent = `${shipName} - ${currentTerminalSN}`;
            
            console.log('当前选中端站:', currentTerminalSN);
            // 可以在这里添加加载端站当前基站列表的逻辑
        }
    });
    
    // 查询按钮事件
    document.getElementById('queryBtsBtn').addEventListener('click', queryBtsInfo);
    
    // 新增行按钮事件
    document.getElementById('addBaseStationRow').addEventListener('click', addBaseStationRow);
    
    // 将所选添加到列表按钮事件
    document.getElementById('addToTerminalListBtn').addEventListener('click', addSelectedToTerminalList);
    
    // 使用所选覆盖列表按钮事件
    document.getElementById('overwriteTerminalListBtn').addEventListener('click', overwriteTerminalList);
    
    // 初始化编辑功能
    initCellEditing();
}

// 处理WebSocket消息
function handleWebSocketMessage(message) {
    console.log("StationImport: Received message:", message);
    if (message.type === 'control_response' && message.module === 'station_import') {
        // console.log('handleWebSocketMessage: 基站导入响应:', message.data);
        handleStationImportResponse(message);
        
    }
    else if (message.type === 'control_response' && message.module === 'query_station') {
        // console.log('handleWebSocketMessage: 查询基站信息响应:', message.data);
        handleQueryResponse(message);
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
            coverage_distance: cells[4].textContent.trim() !== '-' ? cells[4].textContent.trim() : '',
            longitude: cells[5].textContent.trim() !== '-' ? cells[5].textContent.trim() : '',
            latitude: cells[6].textContent.trim() !== '-' ? cells[6].textContent.trim() : ''
        });
    });
    console.log('选中的基站:', selectedBts);
    return selectedBts;
}

// 获取选中的端站
function getSelectedTerminal() {
    let selectedTerminal = null;
    
    if (currentTerminalSN) {
        // 查找对应的端站选项
        const selectedOption = document.querySelector(`.terminal-option[data-sn="${currentTerminalSN}"]`);
        
        if (selectedOption) {
            const ip_address = selectedOption.getAttribute('data-ip');
            const port_number = selectedOption.getAttribute('data-port');

            selectedTerminal = {
                sn: currentTerminalSN,
                ip_address: ip_address || '',
                port_number: port_number || ''
            };
        }
    }
    return selectedTerminal;
}

// 新增行功能
function addBaseStationRow() {
    const tbody = document.getElementById('terminalBtsTableBody');
    const newRow = document.createElement('tr');
    
    newRow.innerHTML = `
        <td><input type="text" class="form-control form-control-sm bts-id-input" value="基站ID"></td>
        <td><input type="text" class="form-control form-control-sm bts-name-input" value="基站名称"></td>
        <td><input type="text" class="form-control form-control-sm bts-region-input" value="地区号"></td>
        <td><input type="text" class="form-control form-control-sm bts-coverage-input" value="覆盖范围"></td>
        <td><input type="text" class="form-control form-control-sm bts-longitude-input" value="经度"></td>
        <td><input type="text" class="form-control form-control-sm bts-latitude-input" value="纬度"></td>
        <td><button type="button" class="btn btn-danger btn-sm delete-row-btn">删除</button></td>
    `;
    
    tbody.appendChild(newRow);
    
    // 为新行绑定事件
    bindRowEvents(newRow);
    
    // 滚动到列表底部
    tbody.parentNode.scrollTop = tbody.parentNode.scrollHeight;
}

// 绑定行事件（删除按钮和输入框事件）
function bindRowEvents(row) {
    // 删除按钮事件
    const deleteBtn = row.querySelector('.delete-row-btn');
    deleteBtn.addEventListener('click', function() {
        row.remove();
    });
    
    // 输入框焦点事件 - 点击时如果是默认值则清空
    const inputs = row.querySelectorAll('input');
    inputs.forEach(input => {
        input.addEventListener('focus', function() {
            if (this.value === '基站ID' || this.value === '基站名称' || this.value === '地区号' || 
                this.value === '覆盖范围' || this.value === '经度' || this.value === '纬度') {
                this.value = '';
            }
        });
        
        // 输入框失焦事件 - 如果为空则恢复默认值
        input.addEventListener('blur', function() {
            if (this.value.trim() === '') {
                if (this.classList.contains('bts-id-input')) {
                    this.value = '基站ID';
                } else if (this.classList.contains('bts-name-input')) {
                    this.value = '基站名称';
                } else if (this.classList.contains('bts-region-input')) {
                    this.value = '地区号';
                } else if (this.classList.contains('bts-coverage-input')) {
                    this.value = '覆盖范围';
                } else if (this.classList.contains('bts-longitude-input')) {
                    this.value = '经度';
                } else if (this.classList.contains('bts-latitude-input')) {
                    this.value = '纬度';
                }
            }
        });
        
    });
}

// 初始化单元格编辑功能
function initCellEditing() {
    // 为现有行绑定事件（如果有）
    const rows = document.querySelectorAll('#terminalBtsTableBody tr');
    rows.forEach(row => bindRowEvents(row));
}

// 将所选添加到列表
function addSelectedToTerminalList() {
    const selectedBts = getSelectedBts();
    
    if (selectedBts.length === 0) {
        warningMessage('请至少选择一个基站');
        return;
    }
    
    // 将选中的基站添加到端站内当前基站列表
    addBtsToTerminalList(selectedBts);
    
    infoMessage(`已将${selectedBts.length}个基站添加到列表`);
}

// 使用所选覆盖列表
function overwriteTerminalList() {
    const selectedBts = getSelectedBts();
    
    if (selectedBts.length === 0) {
        warningMessage('请至少选择一个基站');
        return;
    }
    
    // 清空端站内当前基站列表
    const tbody = document.getElementById('terminalBtsTableBody');
    tbody.innerHTML = '';
    
    // 将选中的基站添加到端站内当前基站列表
    addBtsToTerminalList(selectedBts);
    
    infoMessage(`已使用${selectedBts.length}个基站覆盖列表`);
}

// 将基站添加到端站内当前基站列表
function addBtsToTerminalList(btsList) {
    const tbody = document.getElementById('terminalBtsTableBody');
    
    btsList.forEach(bts => {
        const newRow = document.createElement('tr');
        
        newRow.innerHTML = `
            <td><input type="text" class="form-control form-control-sm bts-id-input" value="${bts.bts_id}"></td>
            <td><input type="text" class="form-control form-control-sm bts-name-input" value="${bts.bts_name}"></td>
            <td><input type="text" class="form-control form-control-sm bts-region-input" value="${bts.region_code || ''}"></td>
            <td><input type="text" class="form-control form-control-sm bts-coverage-input" value="${bts.coverage_distance || ''}"></td>
            <td><input type="text" class="form-control form-control-sm bts-longitude-input" value="${bts.longitude || ''}"></td>
            <td><input type="text" class="form-control form-control-sm bts-latitude-input" value="${bts.latitude || ''}"></td>
            <td><button type="button" class="btn btn-danger btn-sm delete-row-btn">删除</button></td>
        `;
        
        tbody.appendChild(newRow);
        
        // 为新行绑定事件
        bindRowEvents(newRow);
    });
}

// 获取端站内当前基站列表中的所有基站
function getTerminalBtsList() {
    const btsList = [];
    const rows = document.querySelectorAll('#terminalBtsTableBody tr');
    
    rows.forEach(row => {
        const btsIdInput = row.querySelector('.bts-id-input');
        const btsNameInput = row.querySelector('.bts-name-input');
        const btsRegionInput = row.querySelector('.bts-region-input');
        const btsCoverageInput = row.querySelector('.bts-coverage-input');
        const btsLongitudeInput = row.querySelector('.bts-longitude-input');
        const btsLatitudeInput = row.querySelector('.bts-latitude-input');
        
        // 确保所有输入框都存在
        if (btsIdInput && btsNameInput && btsRegionInput && btsCoverageInput && btsLongitudeInput && btsLatitudeInput) {
            const btsId = btsIdInput.value.trim();
            const btsName = btsNameInput.value.trim();
            const regionCode = btsRegionInput.value.trim();
            const coverageDistance = btsCoverageInput.value.trim();
            const longitude = btsLongitudeInput.value.trim();
            const latitude = btsLatitudeInput.value.trim();
            
            // 确保基站ID不为空
            if (btsId) {
                btsList.push({
                    bts_id: btsId,
                    bts_name: btsName,
                    region_code: regionCode,
                    coverage_distance: coverageDistance,
                    longitude: longitude,
                    latitude: latitude
                });
            }
        }
    });
    
    console.log('端站内当前基站列表:', btsList);
    return btsList;
}

// 查询基站信息
function queryBtsInfo() {
    const terminal = getSelectedTerminal();
    
    if (!terminal) {
        warningMessage('请选择一个端站');
        return;
    }
    
    // 发送查询消息
    sendQueryMessageToTerminal(terminal);
    
    infoMessage(`正在向端站sn: ${terminal.sn}查询基站信息...`);
}

// 更新基站信息
function updateBtsInfo() {
    const terminalBtsList = getTerminalBtsList();
    const selectedTerminal = getSelectedTerminal();
    
    if (terminalBtsList.length === 0) {
        warningMessage('端站内当前基站列表为空，请先添加基站');
        return;
    }
    
    if (!selectedTerminal) {
        warningMessage('请选择一个端站');
        return;
    }
    
    // 发送消息给选中的端站（现在只有一个）
    sendSettingMessageToTerminal(selectedTerminal, terminalBtsList);
    
    infoMessage(`正在向端站sn: ${selectedTerminal.sn}发送基站信息...`);
}

// 向端站发送消息
// 设置基站列表
function sendSettingMessageToTerminal(terminal, stationList) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        errorMessage('WebSocket连接未建立，无法发送消息');
        return;
    }

    if (currentTerminalSN !== terminal.sn) {
        errorMessage(`currentTerminalSN与选中的端站SN不匹配: ${currentTerminalSN} !== ${terminal.sn}`);
        return;
    }
    
    // 向选中的端站发送消息
    const terminalSN = currentTerminalSN;
    const terminalIP = terminal.ip_address;
    const terminalPort = terminal.port_number;
    
    // 转换station_list格式为新的消息格式
    const convertedStationList = stationList.map(station => ({
        id: station.bts_id || '',
        bts_no: station.bts_id || '',
        bts_name: station.bts_name || '',
        cover: station.coverage_distance || '',
        group_no: station.region_code || '',
        longitude: station.longitude || '',
        latitude: station.latitude || ''
    }));
    
    // 按照协议文档构造消息
    const payload = {
        sn: terminalSN, // 消息的sn字段与端站匹配
        op: "update",
        op_sub: "base_station_import",
        station_list: convertedStationList // 直接使用转换后的对象，避免双重JSON序列化
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

// 查询基站信息
function sendQueryMessageToTerminal(terminal) {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
        errorMessage('WebSocket连接未建立，无法发送消息');
        return;
    }

    // 向选中的端站发送消息
    const terminalSN = currentTerminalSN;
    const terminalIP = terminal.ip_address;
    const terminalPort = terminal.port_number;

    // 按照协议文档构造消息
    const payload = {
        sn: terminalSN, // 消息的sn字段与端站匹配
        op: "query",
        op_sub: "base_station"
    };

    console.log(`发送查询请求给端站 ${terminalSN}:`, payload);
    console.log(`端站信息 - SN: ${terminalSN}, IP: ${terminalIP}, Port: ${terminalPort}`);

    // 构造最终消息对象
    const message = {
        type: 'control_command',
        sn: terminalSN,
        ip: terminalIP,
        port: terminalPort,
        module: 'query_station', // 设置默认模块名称
        payload: payload
    };

    // 发送消息
    ws.send(JSON.stringify(message));
}

// 处理响应消息
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

// 处理查询响应
function handleQueryResponse(message) {
    console.log("收到查询响应:", message);
    
    // 通信级别的错误
    if (message.success === false) {
        const errorMsg = `查询sn: ${currentTerminalSN}的基站信息失败，失败原因：${message.error || "操作失败：通信错误"}`;
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
    
    // const successMessage = `成功查询了sn: ${data.sn}的基站信息`;
    // infoMessage(successMessage);
    
    // 解析并显示基站信息
    if (data.station_list) {
        const stationList = data.station_list;
        displayStationInfo(stationList);
    }
    
}

// 页面加载完成后初始化
// 解析并显示基站信息
function displayStationInfo(stationList) {
    console.log('原始基站列表:', stationList);
    try {
        // 清空端站内当前基站列表
        const tbody = document.getElementById('terminalBtsTableBody');
        tbody.innerHTML = '';
        
        // 转换基站列表字段名
        // 这里忽略了bts_no字段，因为他实际上和id是等效的
        const convertedStationList = stationList.map(station => ({
            bts_id: station.id || '',
            bts_name: station.bts_name || '',
            region_code: station.group_no || '',
            coverage_distance: station.cover || '',
            longitude: station.longitude || '',
            latitude: station.latitude || ''
        }));
        
        // 将基站列表添加到表格中
        addBtsToTerminalList(convertedStationList);
        
        // 显示成功消息
        infoMessage(`成功加载${stationList.length}个基站信息`);
    } catch (error) {
        // 处理失败时显示错误消息
        errorMessage('处理基站信息失败: ' + error.message);
    }
}

document.addEventListener('DOMContentLoaded', init);