function setSystemStatus(status){
    // 先把状态灯设成无效状态
    let statuslights = document.querySelectorAll("#antenna_status .statusLight");
    for(var i=0; i<statuslights.length; i++)
    {
        statuslights[i].style.backgroundColor = "lightgray";
    }

    // 根据状态值点灯
    switch (status)
    {
        case 0:
            document.getElementById("light_none").style.backgroundColor = "limegreen";
            break;
        case 1:
            document.getElementById("light_init").style.backgroundColor = "limegreen";
            break;
        case 2:
            document.getElementById("light_presearch").style.backgroundColor = "limegreen";
            break;
        case 3:
            document.getElementById("light_track").style.backgroundColor = "limegreen";
            break;
        case 4:
            document.getElementById("light_fault").style.backgroundColor = "red";
            break;
        default:
            break;
    }

}

function setLinkStatus(status)
{
    // 先把状态灯设成无效状态
    const linklights = document.querySelectorAll("#link_status .statusLight");
    for(let i=0; i<linklights.length; i++)
    {
        linklights[i].style.backgroundColor = "lightgray";
    }

    // 根据状态值点灯
    switch (status)
    {
        case 0:
            document.getElementById("dtu_unlink").style.backgroundColor = "red";
            break;
        case 1:
            document.getElementById("dtu_state_dial").style.backgroundColor = "limegreen";
            break;
        case 2:
            document.getElementById("dtu_state_normal").style.backgroundColor = "limegreen";
            break;
        default:
           break;
    }
}

function showMbpInfo(msg)
{
    // console.log(msg);
    const systemState = msg["systemState"];                     // 系统状态
    const btsName = msg["btsName"]                              // 宏基站名称
    const btsLongitude = msg["btsLongitude"];                   // 宏基站的经度
    const btsLatitude = msg["btsLatitude"];                     // 宏基站的纬度
    const longitude = msg["longitude"]                          // MBP当前经度
    const latitude = msg["latitude"]                            // MBP当前纬度
    const theoryYaw = msg["theoryYaw"];                         // 理论方位角
    // const theoryPitch = msg["theoryPitch"];                     // 理论俯仰角
    const yaw = msg["yaw"];                                     // 方位角
    const pitch = msg["pitch"];                                 // 俯仰角
    const roll = msg["roll"];                                   // 横滚角
    const yawLimitState = msg["yawLimitState"]                  // 方位限位
    const temperature = msg["temperature"];                     // 温度
    const humidity = msg["humidity"];                           // 湿度

    // console.log("systemState" + systemState.toString())
    // console.log("longitude" + longitude.toString())

    const nodeBtsname = document.getElementById("bts_name");
    const nodeBtsLongitude = document.getElementById("bts_longitude");
    const nodeBtsLatitude = document.getElementById("bts_latitude");
    const nodeLongitude = document.getElementById("longitude");
    const nodeLatitude = document.getElementById("latitude");
    const nodeTheoryYaw = document.getElementById("theory_yaw");
    const nodeTheoryPitch = document.getElementById("theory_pitch");
    const nodeYaw = document.getElementById("yaw");
    const nodePitch = document.getElementById("pitch");
    const nodeRoll = document.getElementById("roll");
    const nodeYawLimit = document.getElementById("yaw_limit");
    const nodeTemperature = document.getElementById("temperature");
    const nodeHumidity = document.getElementById("humidity");

    // 设置系统状态
    setSystemStatus(systemState);

    // 显示上报信息
    nodeBtsname.value = btsName;
    nodeBtsLongitude.value = btsLongitude.toFixed(3);
    nodeBtsLatitude.value = btsLatitude.toFixed(3);
    nodeLongitude.value = longitude.toFixed(3);
    nodeLatitude.value = latitude.toFixed(3);
    nodeTheoryYaw.value = theoryYaw.toFixed(2);
    // nodeTheoryPitch.value = theoryPitch.toFixed(2);
    nodeYaw.value = yaw.toFixed(2);
    nodePitch.value = pitch.toFixed(2);
    nodeRoll.value = roll.toFixed(2);
    switch (yawLimitState)
    {
        case 0:
            nodeYawLimit.value = "无接触";
            break;
        case 1:
            nodeYawLimit.value = "左限位";
            break;
        case 2:
            nodeYawLimit.value = "右限位";
            break;
    }
    nodeTemperature.value = temperature.toFixed(2);
    nodeHumidity.value = humidity.toFixed(2);
}

// stream = {upstream: value, downstream: value1}
function showLinkspeed(stream)
{
    const nodeLinkspeed = document.getElementById("link_speed");

    nodeLinkspeed.innerHTML="<h4> 上行：" + stream["upstream"] + "bps&nbsp;&nbsp;下行：" + stream["downstream"] + "bps</h4>";
}

// value = {rsrp: value, rssi: value1, sinr: value2} //4G网络没有rssi
function  showNetworkState(param)
{
    // 网络状态数据
    const nodeDtuPlmn = document.getElementById("dtu_plmn");
    const nodeDtuStandard = document.getElementById("dtu_standard");
    const ndoeDtuCellid = document.getElementById("dtu_cellid");
    const nodeDtuPci = document.getElementById("dtu_pci");
    const nodeDtuRsrp = document.getElementById("dtu_rsrp");
    const nodeDtuRssi = document.getElementById("dtu_rssi");
    const nodeDtuSinr  = document.getElementById("dtu_sinr");

    switch (param["plmn"]) {
        case 46000:
        case 46002:
        case 46004:
        case 46007:
        case 46008:
        case 46013:
            nodeDtuPlmn.value = "中国移动";
            break;
        case 46001:
        case 46006:
        case 46009:
        case 46010:
            nodeDtuPlmn.value = "中国联通";
            break;
        case 46003:
        case 46005:
        case 46011:
        case 46012:
            nodeDtuPlmn.value = "中国电信";
            break;
        case 46015:
            nodeDtuPlmn.value = "中国广电";
            break;
        default:
            nodeDtuPlmn.value = "未知运营商";
            break;
    }

    nodeDtuStandard.value = param["standard"];
    ndoeDtuCellid.value = param["cellid"];
    nodeDtuPci.value = param["pci"];
    nodeDtuRsrp.value = param['rsrp'];
    nodeDtuRssi.value = param['rssi'];
    nodeDtuSinr.value = param['sinr'];

    // 设置RSRP图示指标
    const nodeRsrp = document.getElementById("rsrp_value");
    const nodeRsrpMeter = document.getElementById("rsrp_meter");

    nodeRsrp.innerHTML = "<h1>" + param["rsrp"] + "dBm </h1>";
    // rsrp换算加150，-80变成70，-120变成30
    nodeRsrpMeter.value = param["rsrp"] + 150;
}

function querySystemWorkMode(){
    const data = {
        cmd: 0x34,   // 查询系统工作模式
        text: "Query system work mode."
    };
    parent.ws.send(JSON.stringify(data));
}

function setSystemWorkMode(){
    const workMode = Number(document.getElementById("work_mode").value);
    const data = {
        cmd: 0x14,   // 设置系统工作模式
        workMode: workMode,
        text: "Set system work mode."
    };
    parent.ws.send(JSON.stringify(data));
}

function showSystemWorkMode(workMode){
    const nodeWorkMode = document.getElementById("work_mode");
    nodeWorkMode.value = workMode;
    // console.log("workMode", workMode);

    let strWorkMode;
    switch (workMode){
        case 0: //00，自动模式
            strWorkMode = "自动模式";
            break;
        case 1: //01，手动模式
            strWorkMode = "手动模式";
            break;
    }
    parent.window.showOnStatusBarAndLog_T("系统工作模式为：" + strWorkMode);
}

function getNumberWithLimit(obj, topLimit, lowLimit){
    const num = Number(obj.value);

    if (isNaN(num) || num > topLimit || num < lowLimit){
        alert("必须是：" + topLimit + "~" + lowLimit + "之间的数字");
        obj.focus();
        return NaN;
    }

    return num;
}

function  onTurn( axis, direct, angleTopLimit, angleLowLimit, comment){
    // 获得旋转角度
    const nodeAngle = document.getElementById("turn_angle");
    const turnAngle = getNumberWithLimit(nodeAngle, angleTopLimit, angleLowLimit);
    // 判断是否正确获得旋转角度值
    if (isNaN(turnAngle)){
        return;
    }
    // 获取调节模式
    const nodeMode = document.getElementById("turn_mode");
    const turnMode = Number(nodeMode.value);

    // 构造数据帧
    const data = {
        cmd:0x15,
        mode:turnMode,
        axis:axis,          // 旋转轴  00，方位   01，俯仰   02，极化（仅在增量模式下可用）    03，横滚
        direct:direct,      // 旋转方向 00，向上运动 或 向右运动 或 顺时针; 01，向下运动 或 向左运动 或 逆时针
        angle:turnAngle,
        text:comment
    };
    // 发送给websocket
    parent.ws.send(JSON.stringify(data));
}

// function onTurnLevorotation() {
//     // 横滚， 逆时针， 限制 +- 100度
//     onTurn(0x03, 0x01, 100, -100, "turn Levorotation");
// }
//
// function onTurnDextrorotation(){
//     // 横滚， 顺时针， 限制 +- 100度
//     onTurn(0x03, 0x00, 100, -100, "turn Dextrorotation");
// }

function onTurnUp(){
    // 俯仰， 向上， 限制 +- 90度
    onTurn(0x01, 0x00, 90, -90, "turn Up");
}

function onTurnDown(){
    // 俯仰， 向下， 限制 +- 90度
    onTurn(0x01, 0x01, 90, -90, "turn down");
}

function onTurnLeft(){
    // 方位， 向左， 限制 +- 360度
    onTurn(0x00, 0x01, 360, -360, "turn Left");
}

function onTurnRight(){
    // 方位， 向右， 限制 +- 360度
    onTurn(0x00, 0x00, 360, -360, "turn Right");
}

// function onTurnInverseclock(){
//     // 极化， 逆时针， 限制 +- 360度
//     onTurn(0x02, 0x01, 360, -360, "turn Inverseclock");
// }
//
// function onTurnClockwise(){
//     // 极化， 顺时针， 限制 +- 360度
//     onTurn(0x02, 0x00, 360, -360, "turn Clockwise");
// }

function setLight(id, status){
    switch (status){
        case 0:
            document.getElementById(id).style.backgroundColor="limegreen";
            break;
        case 1:
            document.getElementById(id).style.backgroundColor="red";
            break;
        default:
            document.getElementById(id).style.backgroundColor="lightgray";
    }
}

function showDevicesStatus(status){
    const IMUState = status["IMUState"];
    const DGPSState = status["DGPSState"];
    const storageState = status["storageState"];

    const yawMotoState = status["yawMotoState"];
    const pitchMotoState = status["pitchMotoState"];
    const yawLimitState = status["yawLimitState"];
    const pitchLimitState = status["pitchLimitState"];

    setLight("IMUState", IMUState);
    setLight("DGPSState", DGPSState);
    setLight("storageState", storageState);
    setLight("yawMotoState", yawMotoState);
    setLight("pitchMotoState", pitchMotoState);
    setLight("yawLimitState", yawLimitState);
    setLight("pitchLimitState", pitchLimitState);

    parent.showOnStatusBarAndLog_T("查询设备状态成功");
}

function queryDevicesStatus(){
    const data = {
        cmd:0x33,  //查询设备状态
        text:"Query devices status."
    };

    // console.log(JSON.stringify(data));
    parent.ws.send(JSON.stringify(data));
}

// 暂时不用的函数
// function showGPS(value)
// {
//     // GPSValue = JSON.parse("{\"longitude\": 9.403955927617072e-38, \"latitude\": -1.1102230246251565e-16}")
//     var node = document.getElementById("GPS_value");
//     var longitude = "", latitude = "";
//     if(value['longitude'] >= 0){
//         longitude = value['longitude'].toFixed(3) + ' °E';
//     } else {
//         longitude = value['longitude'].toFixed(3) + ' °W';
//     }
//     if(value['latitude'] >= 0){
//         latitude = value['latitude'].toFixed(3) + " °N";
//     } else {
//         latitude = value['latitude'].toFixed(3) + " °S";
//     }
//     node.innerHTML="<h4> 经度：" + longitude + "&nbsp;&nbsp;&nbsp;纬度：" + latitude + "</h4>";
// }
//
// function setAGC(value)
// {
//     var nodeAGCvalue = document.getElementById("AGC_value");
//     var nodeAGCmeter = document.getElementById("AGC_meter");
//
//     nodeAGCvalue.innerHTML="<h1>" + value.toFixed(2) + "</h1>";
//     nodeAGCmeter.value=value.toFixed(2)/3*10;  //以3为基数，计算百分比
// }


