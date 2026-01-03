// static/js/systemmanage.js

// 全局变量
var ws = null;
let currentTerminalSN = null;

// 初始化函数
function init() {
    console.log("SystemManage.js: Initializing page...");
    
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
        console.log('SystemManage: WebSocket connection established successfully.');
        
        // WebSocket连接建立后，尝试从全局状态获取已保存的端站选择
        // 这样可以确保在WebSocket连接建立后再发送请求
        const savedTerminal = getCurrentTerminal();
        if (savedTerminal && savedTerminal.sn) {
            console.log("SystemManage: WebSocket连接后从全局状态获取到端站选择:", savedTerminal);
            currentTerminalSN = savedTerminal.sn;
            
            // 查找并设置对应的端站项为活动状态
            const terminalItems = document.querySelectorAll('#terminal-list .list-group-item');
            terminalItems.forEach(item => {
                if (item.dataset.sn === savedTerminal.sn) {
                    item.classList.add('active');
                }
            });
            
            // 重置所有状态
            resetAllStatus();
            
            // 获取服务器升级文件列表
            getServerUpgradeFiles(false);
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
        console.error('SystemManage: WebSocket connection closed!');
        // 尝试重连
        setTimeout(initWebSocket, 5000);
    };

    // 错误事件
    ws.onerror = function(e) {
        console.error('SystemManage: WebSocket error:', e);
    };
}

// WebSocket消息处理器
function handleWebSocketMessage(message) {
    // 检查是否有回调函数需要调用
    if (message.frontend_request_id && commandCallbacks.has(message.frontend_request_id)) {
        const callback = commandCallbacks.get(message.frontend_request_id);
        commandCallbacks.delete(message.frontend_request_id);
        callback(message);
    }

    if (message.type !== 'control_response') return;

    if (message.success) {
        const responseData = message.data;
        const module = message.module;
        
        if (responseData.hasOwnProperty('result')) {    // 处理端站响应级别的失败
            console.log("success为true且有result字段");
            console.log(responseData.result);
            if (responseData.result === '0' || responseData.result === 0) {
                infoMessage(`操作 ${module} 成功！`);
            } else {
                let errorMsg = `操作 ${module} 失败。`;
                if (responseData.error) {
                    errorMsg += `\n错误信息: ${responseData.error}`;
                }
                errorMessage(errorMsg);
            }
        } else {
            // 根据模块处理响应
            switch (message.module) {
                // case 'query_work_mode':
                //     handleWorkModeResponse(responseData);
                //     break;
                case 'query_rtc':
                    handleRtcResponse(responseData);
                    infoMessage(`操作成功！模块: ${module}`);
                    break;
                case 'query_report_config':
                    handleReportConfigResponse(responseData);
                    infoMessage(`操作成功！模块: ${module}`);
                    break;
                case 'query_version':
                    handleVersionResponse(responseData);
                    infoMessage(`操作成功！模块: ${module}`);
                    break;
                case 'upload_file_list':
                    // 更新文件列表
                    clearUpgradeFilesTable();
                    // console.log("正在更新端站升级文件列表");
                    
                    if (responseData && responseData.files && responseData.files.length > 0) {
                        responseData.files.forEach(file => {
                            // 将fileId存储在fileData对象中
                            const fileData = {
                                id: file.fileId || file.id, // 兼容旧版本
                                name: file.fileName || file.name,
                                type: file.fileType === 'adu' ? 'ADU' : 'ACU',
                                size: formatFileSize(file.fileSize || file.size), // 兼容fileSize和size字段
                                uploadTime: formatDateTime(file.uploadTime),
                                status: typeof file.status === 'number' ? (file.status === 0 ? '可用' : '不可用') : file.status, // 兼容数字和字符串类型的status
                                pathName: file.status === 'complete' ? file.pathName : ''
                            };
                            generateUpgradeFileTableRow(fileData);
                        });
                    } else {
                        // 如果没有文件，添加一个空行提示
                        const tableBody = document.getElementById('upgrade_files_table_body');
                        if (tableBody) {
                            const emptyRow = document.createElement('tr');
                            const emptyCell = document.createElement('td');
                            emptyCell.colSpan = 6;
                            emptyCell.textContent = '暂无升级文件';
                            emptyCell.className = 'text-center';
                            emptyRow.appendChild(emptyCell);
                            tableBody.appendChild(emptyRow);
                        }
                    }
                    infoMessage(`操作成功！模块: ${module}`);
                    break;
                // 设置类和复位类操作成功后只提示，不做UI更新
                // case 'set_work_mode': break;
                case 'adu_rst': infoMessage(`操作成功！模块: ${module}`); break;
                case 'set_rtc': infoMessage(`操作成功！模块: ${module}`); break;
                case 'set_report_config': infoMessage(`操作成功！模块: ${module}`); break;
                // case 'upload_update_file': break;   // 已弃用
                // case 'software_update': break;      // 已弃用
                // 文件上传相关逻辑不在此进行处理，通过回调函数实现
                default: break;
            }
        }

    } else {
        // 这部分逻辑处理WebSocket通信级别的失败（如超时），保持不变
        // todo 可能需要仅指定模块显示errorMessage
        errorMessage(`操作失败！\n模块: ${message.module}\n错误信息: ${message.error}`);
    }
}

// 事件监听器绑定
function bindEventListeners() {
    // --- 事件监听 ---
    document.addEventListener('terminalSelected', function(e) {
        const detail = e.detail;
        console.log("SystemManage page received selection:", detail);
        
        // 切换端站时，重置所有状态
        resetAllStatus();
        
        // 获取服务器升级文件列表
        getServerUpgradeFiles(false);
    });

    // 监听全局端站状态变化
    if (window.globalTerminalState) {
        window.globalTerminalState.subscribe(function(terminal) {
            if (terminal && terminal.sn) {
                console.log("SystemManage page received global terminal change:", terminal);
                currentTerminalSN = terminal.sn;
                
                // 查找并设置对应的端站项为活动状态
                const terminalItems = document.querySelectorAll('#terminal-list .list-group-item');
                terminalItems.forEach(item => {
                    if (item.dataset.sn === terminal.sn) {
                        item.classList.add('active');
                    } else {
                        item.classList.remove('active');
                    }
                });
                
                // 切换端站时，重置所有状态
                resetAllStatus();
                
                // 获取服务器升级文件列表
                getServerUpgradeFiles(false);
            }
        });
    }

    // 初始化时尝试从全局状态获取已保存的端站选择
    // 注意：这个逻辑现在移到了ws.onopen事件处理器中，确保WebSocket连接建立后再执行
    // const savedTerminal = getCurrentTerminal();
    // if (savedTerminal && savedTerminal.sn) {
    //     console.log("SystemManage: 初始化时从全局状态获取到端站选择:", savedTerminal);
    //     currentTerminalSN = savedTerminal.sn;
    //     
    //     // 查找并设置对应的端站项为活动状态
    //     const terminalItems = document.querySelectorAll('#terminal-list .list-group-item');
    //     terminalItems.forEach(item => {
    //         if (item.dataset.sn === savedTerminal.sn) {
    //             item.classList.add('active');
    //         }
    //     });
    //     
    //     // 重置所有状态
    //     resetAllStatus();
    //     
    //     // 获取服务器升级文件列表
    //     getServerUpgradeFiles(false);
    // }
}

// 格式化文件大小为易读格式
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// 格式化日期时间
function formatDateTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString();
}

// 注册消息处理器
// if (window.webSocketOnMessageHandlers) {
//     window.webSocketOnMessageHandlers = [];
//     window.webSocketOnMessageHandlers.push(systemManagePageMessageHandler);
// }

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
        setStatus('report_RTC_status', `端站当前是否上报RTC：${RTCMap[data.RTC] || '未知'}`, 1);
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

// 开始文件上传流程
function startFileUpload(file, fileType, progressBar) {
    // 生成唯一的fileId
    const fileId = generateFileId(file);
    const chunkSize = 1 * 1024; // 1KB
    const totalChunks = Math.ceil(file.size / chunkSize);
    let currentChunk = 0;
    let retryCount = 0;
    const maxRetries = 3;
    
    // 读取文件内容
    const reader = new FileReader();
    reader.onload = function(e) {
        const fileData = e.target.result;
        
        // 初始化文件上传
        initFileUpload(fileId, file.name, fileType, file.size, totalChunks, function(success) {
            if (success) {
                // 初始化成功，开始发送文件分片
                sendNextChunk(fileId, fileData, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar);
            } else {
                // 初始化失败
                errorMessage('文件上传初始化失败！');
                progressBar.parentElement.style.display = 'none';
            }
        });
    };
    
    reader.onerror = function() {
        errorMessage('读取文件时发生错误！');
        progressBar.parentElement.style.display = 'none';
    };
    
    reader.readAsArrayBuffer(file);
}

// 生成唯一的fileId
function generateFileId(file) {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 10000);
    return `file-${timestamp}-${random}-${file.name}`;
}

// 初始化文件上传
function initFileUpload(fileId, fileName, fileType, totalSize, totalChunks, callback) {
    sendControlCommand('upload_file_init', {
        fileId: fileId,
        fileName: fileName,
        fileType: fileType,
        totalSize: totalSize,
        totalChunks: totalChunks
    }, function(response) {
        if (response && response.success) {
            // 初始化成功
            callback(true);
        } else {
            // 初始化失败
            callback(false);
        }
    });
}

// 发送文件分片
function sendNextChunk(fileId, fileData, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar) {
    if (currentChunk >= totalChunks) {
        // 所有分片都已发送完成
        completeFileUpload(fileId, function(success) {
            if (success) {
                infoMessage('文件上传完成！');
            } else {
                errorMessage('文件上传完成通知失败！');
            }
            // 隐藏进度条
            progressBar.parentElement.style.display = 'none';
        });
        return;
    }
    
    // 计算当前分片的起始位置和结束位置
    const start = currentChunk * chunkSize;
    const end = Math.min(start + chunkSize, fileData.byteLength);
    const chunk = fileData.slice(start, end);
    
    // 将分片转换为Base64编码
    const chunkBase64 = btoa(String.fromCharCode(...new Uint8Array(chunk)));
    
    // 发送分片
    sendControlCommand('upload_file_chunk', {
        fileId: fileId,
        chunkIndex: currentChunk,
        chunkData: chunkBase64
    }, function(response) {
        if (response && response.success) {
            // 分片发送成功
            retryCount = 0;
            currentChunk++;
            
            // 更新进度条 - 使用响应中的progress字段，如果没有则使用本地计算
            const progress = response.data && response.data.progress ? response.data.progress : Math.floor((currentChunk / totalChunks) * 100);
            progressBar.style.width = `${progress}%`;
            progressBar.textContent = `${progress}%`;
            
            // 发送下一个分片
            sendNextChunk(fileId, fileData, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar);
        } else {
            // 分片发送失败，重试
            retryCount++;
            warningMessage(`分片发送失败，正在重试... (第 ${retryCount} 次失败)`);
            
            if (retryCount >= maxRetries) {
                // 重试次数超过上限
                errorMessage('文件上传失败：分片发送多次失败！');
                progressBar.parentElement.style.display = 'none';
            } else {
                // 重新发送当前分片
                sendNextChunk(fileId, fileData, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar);
            }
        }
    });
}

// 完成文件上传
function completeFileUpload(fileId, callback) {
    sendControlCommand('upload_file_complete', {
        fileId: fileId
    }, function(response) {
        if (response && response.success) {
            callback(true);
        } else {
            callback(false);
        }
    });
}

// 升级文件列表查询按钮事件
const queryUpgradeFilesBtn = document.getElementById('query_upgrade_files');
if (queryUpgradeFilesBtn) {
    queryUpgradeFilesBtn.addEventListener('click', () => {
        console.log('查询升级文件列表按钮被点击');
        // 发送查询升级文件列表的请求
        sendControlCommand('upload_file_list', {});
    });
}

// 生成服务器升级文件列表表格行
function generateServerUpgradeFileTableRow(fileData) {
    const tableBody = document.getElementById('server_upgrade_files_table_body');
    if (!tableBody) return;

    // 根据文件名判断类型
    const fileName = fileData.name || '';
    let fileType = '未知';
    if (fileName.toLowerCase().startsWith('adu')) {
        fileType = 'adu';
    } else if (fileName.toLowerCase().startsWith('acu')) {
        fileType = 'acu';
    }

    // 格式化文件大小
    const fileSize = fileData.size || 0;
    const formattedSize = formatFileSize(fileSize);

    // 创建表格行
    const row = document.createElement('tr');
    row.dataset.fileId = fileData.id || '';
    
    // 文件名列
    const nameCell = document.createElement('td');
    nameCell.textContent = fileName;
    row.appendChild(nameCell);
    
    // 类型列
    const typeCell = document.createElement('td');
    typeCell.textContent = fileType;
    row.appendChild(typeCell);
    
    // 大小列
    const sizeCell = document.createElement('td');
    sizeCell.textContent = formattedSize;
    row.appendChild(sizeCell);
    
    // 操作列
    const actionCell = document.createElement('td');
    
    // 上传按钮
    const uploadBtn = document.createElement('button');
    uploadBtn.className = 'btn btn-primary btn-sm';
    uploadBtn.textContent = '上传';
    actionCell.appendChild(uploadBtn);
    
    // 进度条（隐藏）
    const progressDiv = document.createElement('div');
    progressDiv.className = 'progress';
    progressDiv.style.display = 'none';
    progressDiv.style.width = '200px';
    progressDiv.style.marginLeft = '10px';
    
    const progressBar = document.createElement('div');
    progressBar.className = 'progress-bar';
    progressBar.role = 'progressbar';
    progressBar.style.width = '0%';
    progressBar.setAttribute('aria-valuenow', '0');
    progressBar.setAttribute('aria-valuemin', '0');
    progressBar.setAttribute('aria-valuemax', '100');
    progressBar.textContent = '0%';
    
    progressDiv.appendChild(progressBar);
    actionCell.appendChild(progressDiv);
    
    row.appendChild(actionCell);
    tableBody.appendChild(row);

    // 为上传按钮添加点击事件
    uploadBtn.addEventListener('click', () => {
        console.log('上传文件按钮被点击，文件：', fileName);
        // 显示进度条
        progressDiv.style.display = 'inline-block';
        // 禁用上传按钮防止重复点击
        uploadBtn.disabled = true;
        uploadBtn.textContent = '上传中...';
        
        // 调用上传文件函数
        uploadServerFile(fileName, fileType, fileSize, progressBar, () => {
            // 上传完成后恢复按钮状态
            uploadBtn.disabled = false;
            uploadBtn.textContent = '上传';
        });
    });
}

// 上传服务器文件到端站
function uploadServerFile(fileName, fileType, totalSize, progressBar, callback) {
    // 生成唯一的fileId
    const fileId = generateFileId({name: fileName});
    
    // 上传参数配置
    const chunkSize = 1024; // 1KB per chunk
    const totalChunks = Math.ceil(totalSize / chunkSize);
    
    // 初始化文件上传
    initFileUpload(fileId, fileName, fileType, totalSize, totalChunks, function(success) {
        if (success) {
            // 初始化成功，开始发送文件分片
            sendNextChunk(fileId, fileName, fileType, chunkSize, 0, totalChunks, 0, 3, progressBar, callback);
        } else {
            // 初始化失败
            errorMessage('文件上传初始化失败！');
            progressBar.parentElement.style.display = 'none';
            callback();
        }
    });
}

// 初始化文件上传
function initFileUpload(fileId, fileName, fileType, totalSize, totalChunks, callback) {
    sendControlCommand('upload_file_init', {
        fileId: fileId,
        fileName: fileName,
        fileType: fileType,
        totalSize: totalSize,
        totalChunks: totalChunks
    }, function(response) {
        if (response && response.success) {
            // 初始化成功
            callback(true);
        } else {
            // 初始化失败
            callback(false);
        }
    });
}

// 发送文件分片
function sendNextChunk(fileId, fileName, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar, callback) {
    if (currentChunk >= totalChunks) {
        // 所有分片都已发送完成
        completeFileUpload(fileId, function(success) {
            if (success) {
                infoMessage('文件上传完成！');
            } else {
                errorMessage('文件上传完成通知失败！');
            }
            // 隐藏进度条
            progressBar.parentElement.style.display = 'none';
            callback();
        });
        return;
    }
    
    // 发送分片请求到后端
    sendControlCommand('upload_file_chunk', {
        fileId: fileId,
        fileName: fileName,
        chunkIndex: currentChunk,
        chunkSize: chunkSize
    }, function(response) {
        if (response && response.success) {
            // 分片发送成功
            retryCount = 0;
            currentChunk++;
            
            // 更新进度条
            const progress = Math.floor((currentChunk / totalChunks) * 100);
            progressBar.style.width = `${progress}%`;
            progressBar.setAttribute('aria-valuenow', progress);
            progressBar.textContent = `${progress}%`;
            
            // 发送下一个分片
            sendNextChunk(fileId, fileName, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar, callback);
        } else {
            // 分片发送失败，重试
            retryCount++;
            warningMessage(`分片发送失败，正在重试... (第 ${retryCount} 次失败)`);
            
            if (retryCount >= maxRetries) {
                // 重试次数超过上限
                errorMessage('文件上传失败：分片发送多次失败！');
                progressBar.parentElement.style.display = 'none';
                callback();
            } else {
                // 重新发送当前分片
                sendNextChunk(fileId, fileName, fileType, chunkSize, currentChunk, totalChunks, retryCount, maxRetries, progressBar, callback);
            }
        }
    });
}

// 完成文件上传
function completeFileUpload(fileId, callback) {
    sendControlCommand('upload_file_complete', {
        fileId: fileId
    }, function(response) {
        if (response && response.success) {
            callback(true);
        } else {
            callback(false);
        }
    });
}

// 生成升级文件列表表格行
function generateUpgradeFileTableRow(fileData) {
    const tableBody = document.getElementById('upgrade_files_table_body');
    if (!tableBody) return;
    // console.log(fileData.pathName);

    const row = document.createElement('tr');
    row.dataset.fileId = fileData.id;
    
    // 文件名列
    const nameCell = document.createElement('td');
    nameCell.textContent = fileData.name;
    row.appendChild(nameCell);
    
    // 类型列
    const typeCell = document.createElement('td');
    typeCell.textContent = fileData.type;
    row.appendChild(typeCell);
    
    // 大小列
    const sizeCell = document.createElement('td');
    sizeCell.textContent = fileData.size;
    row.appendChild(sizeCell);
    
    // 上传时间列
    const timeCell = document.createElement('td');
    timeCell.textContent = fileData.uploadTime;
    row.appendChild(timeCell);
    
    // 状态列
    const statusCell = document.createElement('td');
    statusCell.textContent = fileData.status;
    row.appendChild(statusCell);
    
    // 操作列
    const actionCell = document.createElement('td');
    
    // 删除按钮
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'btn btn-danger btn-sm mr-2';
    deleteBtn.textContent = '删除';
    deleteBtn.addEventListener('click', () => {
        // 发送删除文件请求
        sendControlCommand('upload_file_delete', {
            fileId: fileData.id,
            pathName: fileData.pathName
        }, function(response) {
            if (response && response.success) {
                // 删除成功，移除表格行
                row.remove();
                infoMessage('文件删除成功！');
            } else {
                errorMessage('文件删除失败！');
            }
        });
    });
    actionCell.appendChild(deleteBtn);
    
    // 升级按钮
    const upgradeBtn = document.createElement('button');
    upgradeBtn.className = 'btn btn-primary btn-sm';
    upgradeBtn.textContent = '升级';
    upgradeBtn.addEventListener('click', () => {
        // 发送升级请求
        sendControlCommand('software_upgrade', {
            fileId: fileData.id
        });
        infoMessage('升级命令已发送！');
    });
    actionCell.appendChild(upgradeBtn);
    
    row.appendChild(actionCell);
    tableBody.appendChild(row);
}

// 清空升级文件列表
function clearUpgradeFilesTable() {
    const tableBody = document.getElementById('upgrade_files_table_body');
    if (tableBody) {
        tableBody.innerHTML = '';
    }
}

// 清空服务器升级文件列表
function clearServerUpgradeFilesTable() {
    const tableBody = document.getElementById('server_upgrade_files_table_body');
    if (tableBody) {
        tableBody.innerHTML = '';
    }
}

// 获取服务器升级文件列表
function getServerUpgradeFiles(show_info_message = true) {
    // 清空服务器升级文件列表
    clearServerUpgradeFilesTable();
    
    // 发送AJAX请求获取服务器文件列表
    fetch('/api/get_server_upgrade_files/')
        .then(response => response.json())
        .then(data => {
            if (data && data.files && data.files.length > 0) {
                data.files.forEach(file => {
                    // 生成服务器升级文件列表表格行
                    generateServerUpgradeFileTableRow(file);
                });
            } else {
                // 如果没有文件，添加一个空行提示
                const tableBody = document.getElementById('server_upgrade_files_table_body');
                if (tableBody) {
                    const emptyRow = document.createElement('tr');
                    const emptyCell = document.createElement('td');
                    emptyCell.colSpan = 4; // 服务器升级文件列表表格有4列
                    emptyCell.textContent = '暂无升级文件';
                    emptyCell.className = 'text-center';
                    emptyRow.appendChild(emptyCell);
                    tableBody.appendChild(emptyRow);
                }
            }
            if (show_info_message) {
                infoMessage('服务器升级文件列表获取成功！');
            }
        })
        .catch(error => {
            console.error('获取服务器升级文件列表失败:', error);
            errorMessage('获取服务器升级文件列表失败，请稍后重试！');
        });
}

// 显示/隐藏进度条
function showProgressBar(type, show) {
    const progressBar = document.getElementById(`${type}_progress`);
    if (progressBar) {
        progressBar.style.display = show ? 'block' : 'none';
    }
}

// 更新进度条
function updateProgressBar(type, percentage) {
    const progressBar = document.getElementById(`${type}_progress_bar`);
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute('aria-valuenow', percentage);
        progressBar.textContent = `${percentage}%`;
    }
}

// --- 事件绑定 ---
// 保存回调函数的映射表，使用frontend_request_id作为键
const commandCallbacks = new Map();

function sendControlCommand(module, payload = {}, callback = null) {
    const activeItem = document.querySelector('#terminal-list .list-group-item.active');
    if (!activeItem) {
        console.error('错误：activeItem为空！');
        return;
    }
    const sn = activeItem.dataset.sn;
    const ip = activeItem.dataset.ip;
    const port = activeItem.dataset.port;

    // 生成唯一的frontend_request_id
    const frontendRequestId = `req_${Date.now()}_${Math.floor(Math.random() * 10000)}`;
    
    const message = {
        type: 'control_command', 
        sn, 
        ip, 
        port, 
        module, 
        payload, 
        frontend_request_id: frontendRequestId
    };
    
    // 如果有回调函数，将其存储在映射表中
    if (callback) {
        commandCallbacks.set(frontendRequestId, callback);
    }
    
    window.ws.send(JSON.stringify(message));
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

// 刷新服务器文件列表按钮事件
document.getElementById('refresh_server_files').addEventListener('click', () => {
    console.log('刷新服务器文件列表按钮被点击');
    getServerUpgradeFiles(true);
});

// 页面初始化
init();