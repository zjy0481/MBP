document.addEventListener('DOMContentLoaded', function () {
    // -------------------------------------------------------------------
    // 全局变量和DOM元素获取
    // -------------------------------------------------------------------
    let map;
    let shipOverlays = {}; // 存储每艘船的覆盖物
    let gisSocket = null;  // 用于WebSocket连接
    let currentMmsi = null; // 当前显示的船舶MMSI

    const sidebar = document.getElementById('gis-sidebar');
    const toggleBtn = document.getElementById('toggle-sidebar-btn');
    const searchInput = document.getElementById('ship-search-input');
    const shipListContainer = document.getElementById('ship-list-container');
    const shipListItems = document.querySelectorAll('#ship-list-container .list-group-item');
    
    const timeRangeSelect = document.getElementById('time-range-select');
    const customTimeRangeDiv = document.getElementById('custom-time-range');
    const startTimeInput = document.getElementById('start-time');
    const endTimeInput = document.getElementById('end-time');
    
    const distanceSlider = document.getElementById('distance-slider');
    const distanceInput = document.getElementById('distance-input');

    const timeConfirmBtn = document.getElementById('time-confirm-btn');
    const distanceConfirmBtn = document.getElementById('distance-confirm-btn');

    // -------------------------------------------------------------------
    // WGS84 to BD-09 坐标转换函数 (略)
    // -------------------------------------------------------------------
    function wgs84ToBd09(wgsLng, wgsLat) { const { lng: gcjLng, lat: gcjLat } = wgs84ToGcj02(wgsLng, wgsLat); const { lng: bdLng, lat: bdLat } = gcj02ToBd09(gcjLng, gcjLat); return { lng: bdLng, lat: bdLat }; }
    function wgs84ToGcj02(wgsLng, wgsLat) { if (outOfChina(wgsLng, wgsLat)) { return { lng: wgsLng, lat: wgsLat }; } let dLat = transformLat(wgsLng - 105.0, wgsLat - 35.0); let dLng = transformLng(wgsLng - 105.0, wgsLat - 35.0); const radLat = wgsLat / 180.0 * Math.PI; let magic = Math.sin(radLat); magic = 1 - 0.00669342162296594323 * magic * magic; const sqrtMagic = Math.sqrt(magic); dLat = (dLat * 180.0) / ((6378245.0 * (1 - 0.00669342162296594323)) / (magic * sqrtMagic) * Math.PI); dLng = (dLng * 180.0) / (6378245.0 / sqrtMagic * Math.cos(radLat) * Math.PI); const mgLat = wgsLat + dLat; const mgLng = wgsLng + dLng; return { lng: mgLng, lat: mgLat }; }
    function gcj02ToBd09(gcjLng, gcjLat) { const x = gcjLng, y = gcjLat; const z = Math.sqrt(x * x + y * y) + 0.00002 * Math.sin(y * Math.PI * 3000.0 / 180.0); const theta = Math.atan2(y, x) + 0.000003 * Math.cos(x * Math.PI * 3000.0 / 180.0); const bdLng = z * Math.cos(theta) + 0.0065; const bdLat = z * Math.sin(theta) + 0.006; return { lng: bdLng, lat: bdLat }; }
    function outOfChina(lng, lat) { return (lng < 72.004 || lng > 137.8347) || (lat < 0.8293 || lat > 55.8271); }
    function transformLat(x, y) { let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x)); ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0; ret += (20.0 * Math.sin(y * Math.PI) + 40.0 * Math.sin(y / 3.0 * Math.PI)) * 2.0 / 3.0; ret += (160.0 * Math.sin(y / 12.0 * Math.PI) + 320 * Math.sin(y * Math.PI / 30.0)) * 2.0 / 3.0; return ret; }
    function transformLng(x, y) { let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x)); ret += (20.0 * Math.sin(6.0 * x * Math.PI) + 20.0 * Math.sin(2.0 * x * Math.PI)) * 2.0 / 3.0; ret += (20.0 * Math.sin(x * Math.PI) + 40.0 * Math.sin(x / 3.0 * Math.PI)) * 2.0 / 3.0; ret += (150.0 * Math.sin(x / 12.0 * Math.PI) + 300.0 * Math.sin(x / 30.0 * Math.PI)) * 2.0 / 3.0; return ret; }

    // -------------------------------------------------------------------
    // WebSocket 功能
    // -------------------------------------------------------------------
    function connectWebSocket() {
        // 如果已有连接，并且连接正常，则无需重连
        if (gisSocket && gisSocket.readyState < 2) {
            return;
        }

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // **核心修正：连接到通用的 /ws/data/ 接口**
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/data/`;
        
        gisSocket = new WebSocket(wsUrl);

        gisSocket.onopen = function(e) {
            console.log(`WebSocket connection established to general data stream.`);
        };

        gisSocket.onmessage = function(e) {
            const data = JSON.parse(e.data);
            
            // 检查是否是状态上报消息
            if (data.type === 'report_data' && data.message) {
                const report = data.message;
                
                // **这里的逻辑不变：前端自行判断消息是否与当前船只相关**
                if (report.mmsi !== currentMmsi) return;

                const reportTime = new Date(`${report.report_date}T${report.report_time}`);
                const { startTime, endTime } = getCurrentTimeRange();
                if (reportTime >= startTime && reportTime <= endTime) {
                    console.log("Received relevant live data, refreshing path...");
                    fetchAndDrawPath(currentMmsi);
                }
            }
        };

        gisSocket.onclose = function(e) {
            console.log('WebSocket connection closed.');
            gisSocket = null; // 清理变量
        };

        gisSocket.onerror = function(e) {
            console.error('WebSocket error:', e);
        };
    }

    // -------------------------------------------------------------------
    // 地图核心功能函数
    // -------------------------------------------------------------------
    function initMap() {
        map = new BMap.Map("map-container");
        map.centerAndZoom(new BMap.Point(121.497310, 31.245128), 12);
        map.enableScrollWheelZoom(true);
        map.addControl(new BMap.NavigationControl());
        map.addControl(new BMap.ScaleControl());
        map.addControl(new BMap.OverviewMapControl());
    }

    function clearAllShipOverlays() {
        // 遍历存储覆盖物的对象的所有键 (MMSI)
        Object.keys(shipOverlays).forEach(mmsi => {
            // 移除每个MMSI对应的标记点和路径
            if (shipOverlays[mmsi]) {
                shipOverlays[mmsi].markers.forEach(marker => map.removeOverlay(marker));
                if (shipOverlays[mmsi].polyline) {
                    map.removeOverlay(shipOverlays[mmsi].polyline);
                }
            }
        });
        // 清空整个存储对象，重置状态
        shipOverlays = {};
    }

    function clearSingleShipOverlays(mmsi) {
        if (shipOverlays[mmsi]) {
            shipOverlays[mmsi].markers.forEach(marker => map.removeOverlay(marker));
            if (shipOverlays[mmsi].polyline) {
                map.removeOverlay(shipOverlays[mmsi].polyline);
            }
            delete shipOverlays[mmsi];
        }
    }

    function createMarkerLabel(report) {
        const convertedPoint = wgs84ToBd09(report.long, report.lat);
        const content = `
            <div style="padding: 5px; background: white; border: 1px solid gray; font-size: 12px; white-space: nowrap;">
                <strong>时间:</strong> ${report.report_date} ${report.report_time}<br>
                <strong>经纬度:</strong> ${convertedPoint.lng.toFixed(6)}, ${convertedPoint.lat.toFixed(6)}<br>
                <strong>方位角:</strong> ${report.yaw}°<br>
                <strong>船舶名称:</strong> ${report.ship_name}<br>
                <strong>MMSI:</strong> ${report.mmsi}<br>
                <strong>船东:</strong> ${report.ship_owner || 'N/A'}<br>
                <strong>端站SN:</strong> ${report.sn}<br>
                <strong>基站名称:</strong> ${report.bts_name || 'N/A'}
            </div>
        `;
        const label = new BMap.Label(content, {
            offset: new BMap.Size(25, 25) // 标签相对图标的偏移
        });
        label.setStyle({ display: "none" }); // 初始隐藏
        return label;
    }

    async function fetchAndDrawPath(mmsi, showAlert = false) {
        clearAllShipOverlays(); // 清除所有船只的轨迹

        currentMmsi = mmsi; // 更新当前显示的MMSI
        if (!mmsi) {
            console.error("MMSI is required.");
            return;
        }

        const { startTime, endTime, shouldDraw } = getCurrentTimeRange();
        if (!shouldDraw) {  //用户选择“不显示轨迹”时
            if (showAlert) alert("已清除轨迹显示。");
            return;
        }

        const minDistance = parseInt(distanceInput.value, 10);
        const apiUrl = `/api/get_track/?mmsi=${mmsi}&start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}`;

        try {
            const response = await fetch(apiUrl);
            if (!response.ok) { throw new Error(await response.text()); }
            const reports = await response.json();

            if (reports.length === 0) {
                if (showAlert) alert("在选定时间段内没有符合要求的上报数据");
                return;
            }

            // 建立或确认通用数据流的WebSocket连接
            connectWebSocket();

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
                const point = new BMap.Point(...Object.values(wgs84ToBd09(report.long, report.lat)));
                bmapPoints.push(point);
                const icon = new BMap.Icon("/static/images/direction.png", new BMap.Size(48, 48), { anchor: new BMap.Size(24, 24), imageSize: new BMap.Size(48, 48) });
                const marker = new BMap.Marker(point, { icon: icon, rotation: report.yaw });
                
                marker.reportData = report;
                marker.isLabelSticky = false; // 自定义属性，用于判断标签是否常驻

                const label = createMarkerLabel(report);
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
                });

                map.addOverlay(marker);
                newMarkers.push(marker);
            });

            let polyline = null;
            if (bmapPoints.length > 1) {
                polyline = new BMap.Polyline(bmapPoints, { strokeColor: "blue", strokeWeight: 3, strokeOpacity: 0.6 });
                map.addOverlay(polyline);
            }

            shipOverlays[mmsi] = { markers: newMarkers, polyline: polyline };
            if (bmapPoints.length > 0) {
                map.setViewport(bmapPoints);
            }
            
            if (showAlert) alert("设置已应用成功！轨迹已更新。");

        } catch (error) {
            console.error("加载轨迹数据时发生错误:", error);
            alert("加载轨迹数据时发生客户端错误。");
        }
    }
    
    // -------------------------------------------------------------------
    // 事件监听与辅助函数
    // -------------------------------------------------------------------
    
    function getCurrentTimeRange() {
        const timeOption = timeRangeSelect.value;
        let startTime, endTime;
        let shouldDraw = true;

        if (timeOption === "none") {
            shouldDraw = false;
        } else if (timeOption === 'custom') {
            if (!startTimeInput.value || !endTimeInput.value) {
                alert("自定义时间模式下，开始和结束时间不能为空。");
                shouldDraw = false;
            }
            startTime = new Date(startTimeInput.value);
            endTime = new Date(endTimeInput.value);
        } else {
            endTime = new Date();
            const durationMap = { '6h': 6, '12h': 12, '1d': 24, '3d': 72, '1w': 168 };
            const hours = durationMap[timeOption];
            startTime = new Date(endTime.getTime() - hours * 60 * 60 * 1000);
        }
        return { startTime, endTime, shouldDraw };
    }

    toggleBtn.addEventListener('click', () => sidebar.classList.toggle('collapsed'));
    searchInput.addEventListener('input', function() { const filter = this.value.toUpperCase(); shipListItems.forEach(item => { item.style.display = (item.textContent.toUpperCase().indexOf(filter) > -1) ? "" : "none"; }); });

    shipListContainer.addEventListener('click', function(e) {
        const target = e.target.closest('.list-group-item');
        if (!target || target.classList.contains('active')) return;
        e.preventDefault();
        shipListItems.forEach(li => li.classList.remove('active'));
        target.classList.add('active');
        fetchAndDrawPath(target.dataset.mmsi);
    });

    timeRangeSelect.addEventListener('change', () => { customTimeRangeDiv.style.display = (timeRangeSelect.value === 'custom') ? 'block' : 'none'; });
    distanceSlider.addEventListener('input', () => { distanceInput.value = distanceSlider.value; });
    distanceInput.addEventListener('input', () => { distanceSlider.value = distanceInput.value; });

    function handleConfirmClick(showAlert) {
        const activeShip = document.querySelector('#ship-list-container .list-group-item.active');
        if (!activeShip) { alert("请先从左侧列表选择一艘船。"); return; }
        const distVal = parseInt(distanceInput.value, 10);
        if (isNaN(distVal) || distVal < 100 || distVal > 10000) { alert("请输入100~10000之间的任意整数作为最小距离。"); return; }
        const mmsi = activeShip.dataset.mmsi;
        if (!mmsi) { alert("发生了一个内部错误，无法识别当前船只。"); return; }
        fetchAndDrawPath(mmsi, showAlert);
    }
    
    timeConfirmBtn.addEventListener('click', () => handleConfirmClick(true));
    distanceConfirmBtn.addEventListener('click', () => handleConfirmClick(true));

    // -------------------------------------------------------------------
    // 页面初始化
    // -------------------------------------------------------------------
    initMap();

    const firstShipElement = document.querySelector('#ship-list-container .list-group-item[data-mmsi]');
    if (firstShipElement) {
        const defaultMmsi = firstShipElement.dataset.mmsi;
        if (defaultMmsi) {
            firstShipElement.classList.add('active');
            fetchAndDrawPath(defaultMmsi);
        }
    }
});