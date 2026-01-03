// GIS页面专用全局变量
var ws = null;

// 全局变量定义
let map;
let shipOverlays = {}; // 存储每艘船的【固定】点
let currentSn = null; // 当前显示的船舶SN
let tempPointOverlay = { marker: null, polyline: null }; // 存储【临时】点和其连接线
let lastFixedPoint = null;    // 存储最后一个【固定】点的信息 {point, report}
let stickyLabels = new Set(); // 使用Set来存储被用户打开（固定）的标签的唯一标识

// DOM元素引用
let sidebar, toggleBtn, searchInput, shipListContainer, shipListItems;
let timeRangeSelect, customTimeRangeDiv, startTimeInput, endTimeInput;
let distanceSlider, distanceInput;

// 定义统一的航迹线样式常量
const MAIN_POLYLINE_STYLE = {
    strokeColor: "blue",
    strokeWeight: 3,
    strokeOpacity: 0.6
};

// 页面初始化函数
function init() {
    console.log("GIS.js: Initializing page...");
    
    // 获取DOM元素
    initializeDOMElements();
    
    // 初始化WebSocket连接
    initWebSocket();
    
    // 初始化页面逻辑
    initializePageLogic();
}

// 初始化DOM元素引用
function initializeDOMElements() {
    sidebar = document.getElementById('gis-sidebar');
    toggleBtn = document.getElementById('toggle-sidebar-btn');
    searchInput = document.getElementById('ship-search-input');
    shipListContainer = document.getElementById('ship-list-container');
    shipListItems = document.querySelectorAll('#ship-list-container .list-group-item');
    
    timeRangeSelect = document.getElementById('time-range-select');
    customTimeRangeDiv = document.getElementById('custom-time-range');
    startTimeInput = document.getElementById('start-time');
    endTimeInput = document.getElementById('end-time');
    
    distanceSlider = document.getElementById('distance-slider');
    distanceInput = document.getElementById('distance-input');
}

// 初始化WebSocket连接
function initWebSocket() {
    // 创建WebSocket连接
    ws = new WebSocket(
        'ws://' + window.location.host + '/ws/data/'
    );

    // 连接打开事件
    ws.onopen = function(e) {
        console.log('GIS: WebSocket connection established successfully.');
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
        console.error('GIS: WebSocket connection closed!');
        // 尝试重连
        setTimeout(initWebSocket, 5000);
    };

    // 错误事件
    ws.onerror = function(e) {
        console.error('GIS: WebSocket error:', e);
    };
}

// 处理WebSocket消息
function handleWebSocketMessage(message) {
    console.log("GIS: Received message:", message);
    if (message.type === 'gis_update_data' && message.data) {
        handleGisUpdateData(message.data);
    }
}

// GIS页面WebSocket数据处理器
function handleGisUpdateData(data) {
    console.log("这里是gis专用处理器，收到数据:", data);
    
    // 复制原有的 gisPageMessageHandler 逻辑
    const report = data;
    report.long = parseFloat(report.long);
    report.lat = parseFloat(report.lat);

    if (isNaN(report.long) || isNaN(report.lat)) {
        console.error("收到的WebSocket数据经纬度无效:", data);
        return;
    }

    if (report.sn !== currentSn) {
        console.warn("消息与当前船只无关");
        return; // 消息与当前船只无关，直接返回
    }

    if (!lastFixedPoint) {
        console.log("当前无固定点，使用WebSocket数据初始化轨迹...");
        initializeTrackWithFirstPoint(report);
        return; // 初始化完成后，本次更新结束
    }

    const reportTime = new Date(`${report.report_date}T${report.report_time}`);
    const { startTime, endTime } = getCurrentTimeRange();
    if (reportTime < startTime || reportTime > endTime) {
        console.warn("消息不在当前设定的时间范围内");
        return; // 消息不在当前设定的时间范围内，则忽略
    }

    // --- 开始处理临时点 ---
    // 1. 清除旧的临时点（如果存在）
    if (tempPointOverlay.marker) map.removeOverlay(tempPointOverlay.marker);
    if (tempPointOverlay.polyline) map.removeOverlay(tempPointOverlay.polyline);

    // 2. 创建新的临时点
    const longitude = parseFloat(report.long) || 0;
    const latitude = parseFloat(report.lat) || 0;
    const yaw = parseFloat(report.yaw) || 0;
    
    const tempBMapPoint = new BMap.Point(...Object.values(wgs84ToBd09(longitude, latitude)));
    const icon = new BMap.Icon("/static/images/direction.png", new BMap.Size(48, 48), { anchor: new BMap.Size(24, 24), imageSize: new BMap.Size(48, 48) });
    const tempMarker = new BMap.Marker(tempBMapPoint, { icon: icon, rotation: yaw });
    
    // 绑定数据和标签（包含标签状态持久化逻辑）
    setupMarker(tempMarker, report);
    
    // 3. 创建连接最后一个固定点和临时点的临时路径线
    const tempPolyline = new BMap.Polyline(
        [lastFixedPoint.point, tempBMapPoint],
        MAIN_POLYLINE_STYLE
    );

    // 4. 在地图上显示并缓存临时覆盖物
    map.addOverlay(tempMarker);
    map.addOverlay(tempPolyline);
    tempPointOverlay = { marker: tempMarker, polyline: tempPolyline };

    // 5. 平滑移动地图中心到临时点
    map.panTo(tempBMapPoint);

    // 6. 判断是否需要将临时点"晋升"为固定点
    const minDistance = parseInt(distanceInput.value, 10);
    const distanceFromLastFixed = map.getDistance(lastFixedPoint.point, tempBMapPoint);

    if (distanceFromLastFixed >= minDistance) {
        console.log("距离足够，将临时点晋升为固定点。");
        // a. 在主轨迹线上追加点
        const mainPolyline = shipOverlays[currentSn].polyline;
        const mainPath = mainPolyline.getPath();
        mainPath.push(tempBMapPoint);
        mainPolyline.setPath(mainPath);

        // b. 将临时marker"固化"到shipOverlays中
        shipOverlays[currentSn].markers.push(tempMarker);
        
        // c. 更新最后一个固定点的信息
        lastFixedPoint = { point: tempBMapPoint, report: report };

        // d. 清空临时点覆盖物（因为它已经被"晋升"了）
        tempPointOverlay = { marker: null, polyline: null };
    }
}

// 初始化页面逻辑
function initializePageLogic() {
    console.log("GIS.js: Initializing page logic...");
    
    // 地图核心功能函数
    initMap();
    setupDistanceTool();
    
    // 事件监听器
    setupEventListeners();
    
    // 初始化默认船只轨迹
    setTimeout(initializeDefaultShip, 100); // 0.1秒后初始化，确保WebSocket连接已建立
}

// WGS84 to BD-09 坐标转换函数
function wgs84ToBd09(wgsLng, wgsLat) { const { lng: gcjLng, lat: gcjLat } = wgs84ToGcj02(wgsLng, wgsLat); const { lng: bdLng, lat: bdLat } = gcj02ToBd09(gcjLng, gcjLat); return { lng: bdLng, lat: bdLat }; }
function wgs84ToGcj02(wgsLng, wgsLat) { if (outOfChina(wgsLng, wgsLat)) { return { lng: wgsLng, lat: wgsLat }; } let dLat = transformLat(wgsLng - 105.0, wgsLat - 35.0); let dLng = transformLng(wgsLng - 105.0, wgsLat - 35.0); const radLat = wgsLat / 180.0 * Math.PI; let magic = Math.sin(radLat); magic = 1 - 0.00669342162296594323 * magic * magic; const sqrtMagic = Math.sqrt(magic); dLat = (dLat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtMagic) * Math.PI); dLng = (dLng * 180.0) / (6378245.0 / sqrtMagic * Math.cos(radLat) * Math.PI); const mgLat = wgsLat + dLat; const mgLng = wgsLng + dLng; return { lng: mgLng, lat: mgLat }; }
function gcj02ToBd09(gcjLng, gcjLat) { const x = gcjLng, y = gcjLat; const z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * Math.PI * 3000.0 / 180.0); const theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * Math.PI * 3000.0 / 180.0); const bdLng = z * Math.cos(theta) + 0.0065; const bdLat = z * Math.sin(theta) + 0.006; return { lng: bdLng, lat: bdLat }; }
function outOfChina(lng, lat) { return (lng < 72.004 || lng > 137.8347) || (lat < 0.8293 || lat > 55.8271); }
function transformLat(x, y) { let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x)); ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0; ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0; ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0; return ret; }
function transformLng(x, y) { let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x)); ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0; ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0; ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0; return ret; }

// 地图核心功能函数
function initMap() {
    map = new BMap.Map("map-container");
    map.centerAndZoom(new BMap.Point(121.497310, 31.245128), 12);
    map.enableScrollWheelZoom(true);
    map.addControl(new BMap.NavigationControl());
    map.addControl(new BMap.ScaleControl());
    map.addControl(new BMap.OverviewMapControl());
}

function setupDistanceTool() {
    const measureBtn = document.getElementById('measure-distance-btn');
    let isMeasuring = false;

    // 1. 实例化测距工具
    const distanceTool = new BMapLib.DistanceTool(map);

    // 2. 监听 "绘制结束" 事件 (用户双击时触发)
    distanceTool.addEventListener('drawend', () => {
        if (isMeasuring) { 
            isMeasuring = false;
            measureBtn.textContent = '测距';
            measureBtn.classList.replace('btn-primary', 'btn-outline-primary');
        }
    });

    // 3. 监听我们自己的按钮点击事件
    measureBtn.addEventListener('click', () => {
        isMeasuring = !isMeasuring;
        if (isMeasuring) {
            distanceTool.open();
            measureBtn.textContent = '退出测距';
            measureBtn.classList.replace('btn-outline-primary', 'btn-primary');
        } else {
            distanceTool.close();
            measureBtn.textContent = '测距';
            measureBtn.classList.replace('btn-primary', 'btn-outline-primary');
        }
    });

    // 4. 监听测距工具的 "close" 事件
    distanceTool.addEventListener('close', () => {
        if (isMeasuring) { 
            isMeasuring = false;
            measureBtn.textContent = '测距';
            measureBtn.classList.replace('btn-primary', 'btn-outline-primary');
        }
    });
}

// 清除所有船只轨迹
function clearAllShipOverlays() {
    Object.keys(shipOverlays).forEach(sn => {
        if (shipOverlays[sn]) {
            shipOverlays[sn].markers.forEach(marker => map.removeOverlay(marker));
            if (shipOverlays[sn].polyline) map.removeOverlay(shipOverlays[sn].polyline);
        }
    });
    shipOverlays = {};

    // 同时清除临时点
    if (tempPointOverlay.marker) map.removeOverlay(tempPointOverlay.marker);
    if (tempPointOverlay.polyline) map.removeOverlay(tempPointOverlay.polyline);
    tempPointOverlay = { marker: null, polyline: null };
    lastFixedPoint = null;
}

// 清除单个船只轨迹
function clearSingleShipOverlays(sn) {
    if (shipOverlays[sn]) {
        shipOverlays[sn].markers.forEach(marker => map.removeOverlay(marker));
        if (shipOverlays[sn].polyline) {
            map.removeOverlay(shipOverlays[sn].polyline);
        }
        delete shipOverlays[sn];
    }
}

// 创建Marker标签
function createMarkerLabel(report) {
    // 安全转换为数字，如果无法转换则使用默认值
    const longitude = parseFloat(report.long) || 0;
    const latitude = parseFloat(report.lat) || 0;
    const yaw = parseFloat(report.yaw) || 0;
    
    const content = `
        <div class = "map-marker-label">
            <strong>${report.ship_name || 'Unknown Ship'}</strong> <br>
            经纬度: ${longitude.toFixed(4)}, ${latitude.toFixed(4)}<br>
            方位角: ${yaw.toFixed(2)}°<br>
            基站名称: ${report.bts_name || 'N/A'}<br>
            通信制式: ${report.standard || 'N/A'}, 
            pci: ${report.pci || 'N/A'}, 
            rsrp: ${report.rsrp || 'N/A'}, 
            sinr: ${report.sinr || 'N/A'}, 
            rssi: ${report.rssi || 'N/A'} <br>
            时间: ${report.report_date || 'N/A'} ${report.report_time || 'N/A'}
        </div>
    `;
    const label = new BMap.Label(content, {
        offset: new BMap.Size(35, 35) // 标签相对图标的偏移
    });
    label.setStyle({ display: "none" }); // 初始隐藏
    return label;
}

// 设置单个Marker的属性、标签和事件（包含状态持久化）
function setupMarker(marker, report) {
    const reportTimestamp = `${report.report_date} ${report.report_time}`;
    marker.reportData = report;

    // 关键：从全局Set中恢复标签的粘性状态
    marker.isLabelSticky = stickyLabels.has(reportTimestamp);
    
    const label = createMarkerLabel(report);
    
    // 如果标签本应是打开的，则立即显示
    if (marker.isLabelSticky) {
        label.setStyle({ display: "block" });
    }
    marker.setLabel(label);

    marker.addEventListener("mouseover", () => label.setStyle({ display: "block" }));
    marker.addEventListener("mouseout", () => {
        if (!marker.isLabelSticky) {
            label.setStyle({ display: "none" });
        }
    });
    marker.addEventListener("click", () => {
        marker.isLabelSticky = !marker.isLabelSticky;
        label.setStyle({ display: marker.isLabelSticky ? "block" : "none" });
        
        // 关键：在全局Set中同步标签的最新状态
        if (marker.isLabelSticky) {
            stickyLabels.add(reportTimestamp);
        } else {
            stickyLabels.delete(reportTimestamp);
        }
    });
}

// 处理无初始数据的情况
function initializeTrackWithFirstPoint(report) {
    // 1. 创建第一个点和marker
    const longitude = parseFloat(report.long) || 0;
    const latitude = parseFloat(report.lat) || 0;
    const yaw = parseFloat(report.yaw) || 0;
    
    const point = new BMap.Point(...Object.values(wgs84ToBd09(longitude, latitude)));
    const icon = new BMap.Icon("/static/images/direction.png", new BMap.Size(48, 48), { anchor: new BMap.Size(24, 24), imageSize: new BMap.Size(48, 48) });
    const marker = new BMap.Marker(point, { icon: icon, rotation: yaw });
    
    setupMarker(marker, report);
    map.addOverlay(marker);

    // 2. 创建主轨迹线（即使只有一个点也要创建）
    const polyline = new BMap.Polyline([point], MAIN_POLYLINE_STYLE);
    map.addOverlay(polyline);

    // 3. 初始化缓存
    shipOverlays[currentSn] = { markers: [marker], polyline: polyline };

    // 4. 设置最后一个固定点
    lastFixedPoint = { point: point, report: report };

    // 5. 将地图中心移动到这个点，并设置一个合适的缩放级别
    map.centerAndZoom(point, 15); // 15是一个比较适中的近景级别
}

// 获取当前时间范围
function getCurrentTimeRange() {
    const timeOption = timeRangeSelect.value;
    let startTime, endTime;
    let shouldDraw = true;

    if (timeOption === "none") {
        shouldDraw = false;
    } else if (timeOption === 'custom') {
        if (!startTimeInput.value || !endTimeInput.value) {
            warningMessage("自定义时间模式下，开始和结束时间不能为空。");
            shouldDraw = false;
        }
        startTime = new Date(startTimeInput.value);
        endTime = new Date(endTimeInput.value);
        
        // 添加逻辑：如果开始时间晚于结束时间，自动对调
        if (startTime > endTime) {
            [startTime, endTime] = [endTime, startTime];
            // 更新输入框的值，让用户看到调整后的结果（保持本地时区）
            startTimeInput.value = startTime.getFullYear() + '-' + 
                                  String(startTime.getMonth() + 1).padStart(2, '0') + '-' + 
                                  String(startTime.getDate()).padStart(2, '0') + 'T' + 
                                  String(startTime.getHours()).padStart(2, '0') + ':' + 
                                  String(startTime.getMinutes()).padStart(2, '0');
            endTimeInput.value = endTime.getFullYear() + '-' + 
                                String(endTime.getMonth() + 1).padStart(2, '0') + '-' + 
                                String(endTime.getDate()).padStart(2, '0') + 'T' + 
                                String(endTime.getHours()).padStart(2, '0') + ':' + 
                                String(endTime.getMinutes()).padStart(2, '0');
            // 提示用户时间已经被调整
            warningMessage("开始时间晚于结束时间，已自动调整时间范围。");
        }
    } else {
        endTime = new Date();
        const durationMap = { '6h': 6, '12h': 12, '1d': 24, '3d': 72, '1w': 168 };
        const hours = durationMap[timeOption];
        startTime = new Date(endTime.getTime() - hours * 60 * 60 * 1000);
    }
    return { startTime, endTime, shouldDraw };
}

// 获取轨迹数据并绘制
async function fetchAndDrawPath(sn, ifzoom = false) {
    console.log(`--- fetchAndDrawPath called for SN: ${sn}. ifzoom: ${ifzoom} ---`);
    
    clearAllShipOverlays(); // 清除所有船只的轨迹

    currentSn = sn; // 更新当前显示的SN
    if (!sn) {
        console.error("SN is required.");
        return;
    }

    const { startTime, endTime, shouldDraw } = getCurrentTimeRange();
    if (!shouldDraw) {  //用户选择"不显示轨迹"时
        console.log("已清除轨迹显示。");
        return;
    }

    const minDistance = parseInt(distanceInput.value, 10);
    const apiUrl = `/api/get_track/?sn=${sn}&start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}`;

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) { throw new Error(await response.text()); }
        const reports = await response.json();

        if (reports.length === 0) {
            warningMessage("在选定时间段内没有符合要求的上报数据");
            return;
        }

        const markersToDraw = [];
        if (reports.length > 0) {
            markersToDraw.push(reports[0]);
            let lastBMapPoint = new BMap.Point(...Object.values(wgs84ToBd09(reports[0].long, reports[0].lat)));
            for (let i = 1; i < reports.length; i++) {
                const currentBMapPoint = new BMap.Point(...Object.values(wgs84ToBd09(reports[i].long, reports[i].lat)));
                if (map.getDistance(lastBMapPoint, currentBMapPoint) >= minDistance) {
                    markersToDraw.push(reports[i]);
                    lastBMapPoint = currentBMapPoint;
                }
            }
        }
        
        const bmapPoints = [];
        const newMarkers = [];
        markersToDraw.reverse();

        markersToDraw.forEach(report => {
            const longitude = parseFloat(report.long) || 0;
            const latitude = parseFloat(report.lat) || 0;
            const yaw = parseFloat(report.yaw) || 0;
            
            const point = new BMap.Point(...Object.values(wgs84ToBd09(longitude, latitude)));
            bmapPoints.push(point);
            const icon = new BMap.Icon("/static/images/direction.png", new BMap.Size(48, 48), { anchor: new BMap.Size(24, 24), imageSize: new BMap.Size(48, 48) });
            const marker = new BMap.Marker(point, { icon: icon, rotation: yaw });
            
            // 使用新的辅助函数来设置marker
            setupMarker(marker, report);

            map.addOverlay(marker);
            newMarkers.push(marker);
        });

        let polyline = null;
        if (bmapPoints.length > 1) {
            polyline = new BMap.Polyline(bmapPoints, MAIN_POLYLINE_STYLE);
            map.addOverlay(polyline);
        }

        shipOverlays[sn] = { markers: newMarkers, polyline: polyline };
        
        // 记录最后一个固定点，为websocket实时更新做准备
        if (bmapPoints.length > 0) {
            lastFixedPoint = {
                point: bmapPoints[bmapPoints.length - 1],
                report: markersToDraw[0] // markersToDraw被反转过，所以第一个是时间最新的
            };
        }

        if (bmapPoints.length > 0) {
            // 首次进入网页时，采用setViewport来同时调整地图中心以及缩放等级
            if(ifzoom) {
                map.setViewport(bmapPoints);
                console.log("缩放并调整中心");
            }
            // 后续为了用户的良好体验，仅作地图中心点更改
            else {
                const latestPoint = bmapPoints[bmapPoints.length - 1];
                map.panTo(latestPoint);
                console.log("仅调整中心");
            }
        }
        
        infoMessage("设置已应用成功！轨迹已更新。");

    } catch (error) {
        errorMessage("加载轨迹数据时发生错误:", error);
    }
}

// 设置事件监听器
function setupEventListeners() {
    toggleBtn.addEventListener('click', () => sidebar.classList.toggle('collapsed'));
    searchInput.addEventListener('input', function() { 
        const filter = this.value.toUpperCase(); 
        shipListItems.forEach(item => { 
            item.style.display = (item.textContent.toUpperCase().indexOf(filter) > -1) ? "" : "none"; 
        }); 
    });

    shipListContainer.addEventListener('click', function(e) {
        const target = e.target.closest('.list-group-item');
        if (!target || target.classList.contains('active')) return;
        e.preventDefault();
        shipListItems.forEach(li => li.classList.remove('active'));
        target.classList.add('active');
        currentSn = target.dataset.sn;
        
        // 保存端站选择到全局状态
        const terminalData = {
            sn: target.dataset.sn,
            name: target.textContent.trim(),
            selectedAt: new Date().toISOString()
        };
        setCurrentTerminal(terminalData);
        
        fetchAndDrawPath(target.dataset.sn);
    });

    timeRangeSelect.addEventListener('change', () => { 
        customTimeRangeDiv.style.display = (timeRangeSelect.value === 'custom') ? 'block' : 'none'; 
    });
    
    distanceSlider.addEventListener('input', () => { distanceInput.value = distanceSlider.value; });
    distanceInput.addEventListener('input', () => { distanceSlider.value = distanceInput.value; });

    function handleConfirmClick() {
        const activeShip = document.querySelector('#ship-list-container .list-group-item.active');
        if (!activeShip) { console.error("activeShip为空。"); return; }
        const distVal = parseInt(distanceInput.value, 10);
        if (isNaN(distVal) || distVal < 100 || distVal > 50000) { 
            alert("请输入100~50000之间的任意整数作为最小距离。"); 
            return; 
        }
        const sn = activeShip.dataset.sn;
        if (!sn) { errorMessage("发生了一个内部错误，无法识别当前船只。"); return; }
        fetchAndDrawPath(sn);
    }
    
    const displaySettingsConfirmBtn = document.getElementById('display-settings-confirm-btn');
    displaySettingsConfirmBtn.addEventListener('click', () => handleConfirmClick());
}

// 初始化默认船只轨迹
function initializeDefaultShip() {
    // 尝试从全局状态获取已保存的端站选择
    const savedTerminal = getCurrentTerminal();
    
    // 优先使用全局状态中保存的端站选择
    if (savedTerminal && savedTerminal.sn) {
        console.log("使用全局状态中保存的端站选择:", savedTerminal);
        const terminalElement = document.querySelector(`#ship-list-container .list-group-item[data-sn="${savedTerminal.sn}"]`);
        if (terminalElement) {
            // 清除所有活动状态并设置当前端站为活动状态
            shipListItems.forEach(li => li.classList.remove('active'));
            terminalElement.classList.add('active');
            
            // 更新当前船舶SN并绘制轨迹
            currentSn = savedTerminal.sn;
            fetchAndDrawPath(savedTerminal.sn);
            return;
        }
    }
    
    // 如果全局状态中没有有效的端站选择，则使用第一个端站
    const firstShipElement = document.querySelector('#ship-list-container .list-group-item[data-sn]');
    if (firstShipElement) {
        const defaultSn = firstShipElement.dataset.sn;
        if (defaultSn) {
            firstShipElement.classList.add('active');
            currentSn = defaultSn;
            fetchAndDrawPath(defaultSn, false, true);
        }
    }
}

// 消息显示函数
function warningMessage(msg) {
    console.warn(msg);
    // 这里可以添加实际的警告消息显示逻辑
}

function errorMessage(msg, error) {
    console.error(msg, error);
    // 这里可以添加实际的错误消息显示逻辑
}

function infoMessage(msg) {
    console.info(msg);
    // 这里可以添加实际的信息消息显示逻辑
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    init();
});