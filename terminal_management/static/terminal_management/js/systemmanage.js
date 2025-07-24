
let logined = false;    // 是否已经登录
let func = null;        // 回调处理函数

// 显示密码页面
function checkPassword(){
    if(!logined) {
        let form_password = document.getElementById("form_password");
        let password = document.getElementById("password");
        // form_password.style.visibility = "visible";
        form_password.style.display = "block";
        form_password.style.height = "200px";
        password.value = '';
        password.focus();

        // 显示密码认证界面的方式
        // window.open("authentication.html", '密码认证', "height=380, width=500, top=50%, left=50%, " +
        //     "toolbar=no, menubar=no, scrollbars=no, resizable=no,location=no, status=no")
    }

    // if(!logined){
    //     let passwd = prompt("请输入管理员密码：");
    //     if (passwd === "comdicomdi"){
    //         logined = true;
    //         if (func != null) {
    //             func();     // 调用回调处理函数
    //         }
    //     }else{
    //         logined = false;
    //         alert("密码错误，不允许修改配置");
    //     }
    // }
}

function onFormPasswordOK(){
    let nodePassword = document.getElementById("password");
    if(nodePassword.value === "comdicomdi"){
        logined = true;
        if (func != null) {
            func();  // 调用处理函数
        }
    }else{
        logined = false;
        alert("密码错误，不允许修改配置");
    }
    let form_password = document.getElementById("form_password");
    // form_password.style.visibility = "hidden";
    form_password.style.display = "none";
    form_password.style.height = "0px";
}

 function onFormPasswordCancel(){
    logined = false;
    let form_password = document.getElementById("form_password");
    // form_password.style.visibility = "hidden";
    form_password.style.display = "none";
    form_password.style.height = "0px";
}

////////////////////////////////////////////////////////////////
function onSetBusinessReset(){
    if(!logined){
        func = setBusinessReset;     // 赋值回调函数
        checkPassword();
    }else{
        setBusinessReset();
    }
}

function setBusinessReset(){
    const data = {
        cmd:0x13,   // 设置系统复位
        resetType:0x00,     // 业务复位
        text:"Set business reset"
    };
    parent.ws.send(JSON.stringify(data));
}

function onSetSoftwareReset(){
    if(!logined){
        func = setSoftwareReset;     // 赋值回调函数
        checkPassword();
    }else{
        setSoftwareReset();
    }
}

function setSoftwareReset(){
    const data = {
        cmd:0x13,   // 设置系统复位
        resetType:0x01,     // 软件复位
        text:"Set software reset"
    };
    parent.ws.send(JSON.stringify(data));
}

function showSystemResetType(msg){
    const node = document.getElementById("reset_type");
    let resetType = msg["resetType"];
    let result = msg["result"]

    let strResetType = "";
    switch (resetType){
        case 0:
            strResetType = "业务复位";
            break;
        case 1:
            strResetType = "软件复位";
            break
    }
    if (result === 0x00){
        parent.showOnStatusBarAndLog_T("设置系统复位成功:" + strResetType);
    }
    else {
        parent.showOnStatusBarAndLog_T("设置系统复位失败:" + strResetType, 2,"darkorange");
    }
}

function onQueryRtc() {
    const queryRtc = {
        cmd: 0x36,   // 查询RTC参数
        text: "query RTC param."
        };
    parent.ws.send(JSON.stringify(queryRtc));
}

function onSetRtc(){
    if(!logined){
        func = setRtc;     // 赋值回调函数
        checkPassword();
    }else{
        setRtc();
    }
}

function setRtc(){
    const nodeDatetimeRtc = document.getElementById("datetime_rtc");
    const rtc = new Date(nodeDatetimeRtc.value)
    const setRtc = {
        cmd:0x16,   // 设置RTC
        year: rtc.getFullYear(),
        month:rtc.getMonth(),
        day:rtc.getDay(),
        hour:rtc.getHours(),
        minute:rtc.getMinutes(),
        second:rtc.getSeconds(),
        text:"set RTC param."
        };
    parent.ws.send(JSON.stringify(setRtc));
}

function showRtcParam(msg) {
    const nodeDatetimeRtc = document.getElementById("datetime_rtc");
    const strRtc = `${msg['year']}-${msg['month']}-${msg['day']} ${msg['hour']}:${msg['minute']}:${msg['second']}}`;
    console.assert(strRtc);
    nodeDatetimeRtc.value = strRtc;
}

function onQueryUpdateCfgParam(){
    const queryUpdateCfgParam={
        cmd:0x31,
        text:"query update param."
    };
    parent.ws.send(JSON.stringify(queryUpdateCfgParam));
}

function onSetUpdateCfgParam() {
    if(!logined){
        func = setUpdateCfgParam;     // 赋值回调函数
        checkPassword();
    }else{
        setUpdateCfgParam();
    }
}

function setUpdateCfgParam(){
    const node_ip_1 = document.getElementById("ip_1");
    const node_ip_2 = document.getElementById("ip_2");
    const node_ip_3 = document.getElementById("ip_3");
    const node_ip_4 = document.getElementById("ip_4");
    const node_port = document.getElementById("port");
    const node_update_mode = document.getElementById("update_mode");
    const node_with_rtc_time = document.getElementById("with_rtc_time");
    const node_interval = document.getElementById("interval");

    if (node_ip_1.value === "")
    {
        alert("请输入IP地址");
        node_ip_1.focus();
        return;
    }
    if (node_ip_2.value === "")
    {
        alert("请输入IP地址");
        node_ip_2.focus();
        return;
    }
    if (node_ip_3.value === "")
    {
        alert("请输入IP地址");
        node_ip_3.focus();
        return;
    }
    if (node_ip_4.value === "")
    {
        alert("请输入IP地址");
        node_ip_4.focus();
        return;
    }
    if (node_port.value === "" || node_port.value > 65535 || node_port < 0)
    {
        alert("请输入正确的端口号");
        node_port.focus();
        return;
    }
    if (node_interval.value === "" || node_interval.value > 65535 || node_interval < 0)
    {
        alert("请输入正确的时间间隔");
        node_interval.focus();
        return;
    }
    const updateCfgParam={
        cmd:0x11,
        ip1:node_ip_1.value,
        ip2:node_ip_2.value,
        ip3:node_ip_3.value,
        ip4:node_ip_4.value,
        port:node_port.value,
        interval:node_interval.value,
        updateRtc:node_with_rtc_time.value,
        updateMode:node_update_mode.value,
        text:"set update param."
    };
    parent.ws.send(JSON.stringify(updateCfgParam));
}

function showUpdateCfgParam(msg) {
    const node_ip_1 = document.getElementById("ip_1");
    const node_ip_2 = document.getElementById("ip_2");
    const node_ip_3 = document.getElementById("ip_3");
    const node_ip_4 = document.getElementById("ip_4");
    const node_port = document.getElementById("port");
    const node_update_mode = document.getElementById("update_mode");
    const node_with_rtc_time = document.getElementById("with_rtc_time");
    const node_interval = document.getElementById("interval");

    node_ip_1.value = msg['ip1'];
    node_ip_2.value = msg['ip2'];
    node_ip_3.value = msg['ip3'];
    node_ip_4.value = msg['ip4'];
    node_port.value = msg['port'];
    node_interval.value = msg['interval'];
    node_with_rtc_time.value = msg['updateRtc'];
    node_update_mode.value = msg['updateMode'];

    parent.showOnStatusBarAndLog_T("查询上报配置参数成功");
}

function onSetFactoryParam(){
    if(!logined){
        func = setFactoryParam;     // 赋值回调函数
        checkPassword();
    }else{
        setFactoryParam();
    }
}

function setFactoryParam(){
    const nodeProductMode = document.getElementById("product_mode");
    const nodeSn = document.getElementById("product_sn");
    const nodeHardwareVersion = document.getElementById("hardware_version");
    const nodeConstructionVersion = document.getElementById("construction_version");

    if (nodeProductMode.value === ""){
        alert("请设置有效产品类型号");
        nodeProductMode.focus();
        return;
    }
    if (nodeSn.value === ""){
        alert("请设置有效序列号");
        nodeSn.focus();
        return;
    }
    if (nodeHardwareVersion.value === ""){
        alert("请设置有效硬件版本号");
        nodeHardwareVersion.focus();
        return;
    }
    if (nodeConstructionVersion.value === ""){
        alert("请设置有效结构版本号");
        nodeConstructionVersion.focus();
        return;
    }

    const setFactoryParamCmd = {
        cmd: 0x12,   // 设置出厂参数
        productMode: nodeProductMode.value,
        SN: nodeSn.value,
        hardwareVersion: nodeHardwareVersion.value,
        constructionVersion: nodeConstructionVersion.value,
        text: "set factory param."
    };
    parent.ws.send(JSON.stringify(setFactoryParamCmd));
}

function onQueryFactoryParam(){
    const queryFactoryParam = {
        cmd: 0x32,   // 查询出厂配置参数
        text: "query factory param."
        };
    parent.ws.send(JSON.stringify(queryFactoryParam));
}
// 比版本查询多了产品型号，少了ADU软件版本号
function showFactoryParam(factoryParam){
    const productMode = document.getElementById("product_mode");
    const nodeSn = document.getElementById("product_sn");
    const nodeHardwareVersion = document.getElementById("hardware_version");
    const nodeConstructionVersion = document.getElementById("construction_version");
    const nodeAcuSoftwareVersion = document.getElementById("acu_software_version");
    const nodeAduSoftwareVersion= document.getElementById('adu_software_version');

    productMode.value = factoryParam['productMode'];
    nodeSn.value = factoryParam['SN'];
    nodeHardwareVersion.value = factoryParam['hardwareVersion'];
    nodeConstructionVersion.value = factoryParam['constructionVersion'];
    nodeAduSoftwareVersion.value = factoryParam['aduSoftwareVersion'];
    nodeAcuSoftwareVersion.value = factoryParam['acuSoftwareVersion'];
    // console.log(factoryParam);

    parent.showOnStatusBarAndLog_T("查询工厂配置成功");
}

// 比工厂设置多了ADU软件版本号，少了产品类型
function showVersion(msg){
    const aduSoftwareVersion = msg["softwareVersion"];
    const hardwareVersion = msg["hardwareVersion"];
    const constructionVersion = msg["constructionVersion"];
    const acuSoftwareVersion = msg["ACUSoftwareversion"];


    document.getElementById("adu_software_version").value = aduSoftwareVersion;
    document.getElementById("hardware_version").value = hardwareVersion;
    document.getElementById("construction_version").value = constructionVersion;
    document.getElementById("acu_software_version").value = acuSoftwareVersion;
    // console.log(msg);

    // parent.showOnStatusBarAndLog_T("查询版本信息成功");
}

function onQuerySystemWorkMode(){
    const data = {
        cmd: 0x34,   // 查询系统工作模式
        text: "Query system work mode."
    };
    parent.ws.send(JSON.stringify(data));
}

function onSetSystemWorkMode() {
    if (!logined) {
        func = setSystemWorkMode;     // 赋值回调函数
        checkPassword();
    } else {
        setSystemWorkMode();
    }
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


function isInteger(obj) {
    return parseInt(obj, 10) === obj
}
