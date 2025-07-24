// 主页启动时的设置
// zhangxiaoxiang
window.onload=function (){
    ////////////////////////////////////////////////////////////////////////////////////////////////////////
    // 控制窗口样式和滑动变化
    //获取dom元素
    const arrowE1 = document.querySelector("#head .headMain > .arrow");
    const liNodes = document.querySelectorAll(" #head .headMain > .navigate > .list > li");
    const upNodes = document.querySelectorAll(" #head .headMain > .navigate > .list > li .up");
    const firstLiNode = liNodes[0];
    const firstUpNode = firstLiNode.querySelector(".up");

    const head = document.querySelector("#head");
    const content = document.querySelector("#content");
    const cLiNodes = document.querySelectorAll("#content .listPage > li");
    const cList = document.querySelector("#content .listPage");
    const dotList = document.querySelectorAll("#content .listNavDot > li");

    //保存当前屏的索引
    let nowIndex = 0;
    let timer = 0;

    // 内容区交互
    window.onresize=function(){
        contentBind();
        //滑动箭头
        arrowE1.style.left = liNodes[nowIndex].offsetLeft + liNodes[nowIndex].offsetWidth/2 - arrowE1.offsetWidth/2 + "px";
        //滑动内容页面
        cList.style.top = -nowIndex*(document.documentElement.clientHeight - head.offsetHeight) + "px";
    }

    // 内容区交互
    // if(content.addEventListener){
    //     content.addEventListener("DOMMouseScroll", function(ev){
    //         ev = ev||event;
    //         // 让DOMMouseScroll只触发一次
    //         clearTimeout(timer);
    //         timer = setTimeout(function (){
    //             fn(ev);
    //             }, 150);
    //     });
    // }
    content.onmousewheel=function (ev) {
        ev = ev||event;
        // 让DOMMouseScroll只触发一次
        clearTimeout(timer);
        timer = setTimeout(function (){
            fnWheel(ev);
        }, 150);
    };
    function fnWheel(ev){
        ev = ev||event;

        let dir = "";
        if(ev.wheelDelta){
            dir = ev.wheelDelta>0?"up":"down";
        } else if(ev.detail){
            dir = ev.wheelDelta<0?"up":"down";
        }

        switch (dir) {
            case "up":
                if (nowIndex>0){
                    nowIndex  --;
                    move(nowIndex);
                }
                break;
            case "down":
                if (nowIndex < cLiNodes.length-1){
                    nowIndex ++;
                    move(nowIndex);
                }
                break;
        }
    }

    contentBind();
    function contentBind(){
        content.style.height = document.documentElement.clientHeight - head.offsetHeight + "px";
        for(var i=0; i<cLiNodes.length; i++){
            cLiNodes[i].style.height = document.documentElement.clientHeight - head.offsetHeight + "px";
        }
    }

    // 头部交互
    headBind();
    function headBind(){
        let i;
        // 通过过度小箭头移动到标签下
        firstUpNode.style.width = "100%";
        // 小箭头移动的位置
        arrowE1.style.left = firstLiNode.offsetLeft + firstLiNode.offsetWidth/2 - arrowE1.offsetWidth/2 + "px";
        for(i = 0; i<liNodes.length; i++){
            liNodes[i].index = i;
            liNodes[i].onclick=function (){
                // i:liNodes.length 5(越界), 所有要有上面“liNodes[i].index = i;”转绑
                nowIndex = this.index;
                move(nowIndex);
            }
        }

        dotList[0].style.background = "lightSkyBlue"
        for(i = 0; i<dotList.length; i++){
            dotList[i].index = i;
            dotList[i].onclick=function (){
                // i:liNodes.length 5(越界), 所有要有上面“liNodes[i].index = i;”转绑
                nowIndex = this.index;
                move(nowIndex);
            }
        }
    }

    // 动画翻屏效果
    function move(index){
        let i;
        for(i = 0; i<upNodes.length; i++){
            // 这样不用设成0，会更改内联样式
            upNodes[i].style.width = "";
        }
        upNodes[index].style.width = "100%";
        //滑动箭头
        arrowE1.style.left = liNodes[index].offsetLeft + liNodes[index].offsetWidth/2 - arrowE1.offsetWidth/2 + "px";
        //滑动内容页面
        cList.style.top = -index*(document.documentElement.clientHeight - head.offsetHeight) + "px";

        for(i = 0; i<dotList.length; i++){
            // 这样不用设成0，会更改内联样式
            dotList[i].style.background = "";
        }
        dotList[index].style.background = "lightSkyBlue";
    }

}

/////////////////////////////////////////////////////////////////////////////////////////////
    // Websocket部分
    // 1.定义长连接
    var ws = null;  // 此处必须用var定义

    // 2.定义连接函数
    function connect() {
        // 先断开之前的连接
        disconnect();

        if ("WebSocket" in window){
            ws = new WebSocket("ws://192.168.222.5:8000/websocket?id=comdi");   // ACU（web服务器）地址
            // ws = new WebSocket("ws://192.168.0.22:8000/websocket?id=comdi");   // todo: 发布时修改
            // console.log(ws);

            //alert("启动websocket!")
            // 建立连接
            ws.onopen=function(){
                // console.log("连接成功");
                showOnStatusBarAndLog_T("同ACU连接成功");
                document.getElementById("light_acu_connect").style.backgroundColor = "limegreen";

                // 查询ADU连接状态
                let data = {
                    cmd:0xF2,
                    msg:"Query ADU connect state."
                };
                ws.send(JSON.stringify(data));

                // // 查询当前配置编号
                // let cfgNumber = {
                //     cmd:0x87,
                //     cfgNumber:0,
                //     msg:"Query current config number."
                // };
                // parent.ws.send(JSON.stringify(cfgNumber));
                //
                // // 暂停一会儿，否则ADU响应不了
                // setTimeout(function (){
                //     // 查询卫星配置参数列表
                //     let cfgList = {
                //         cmd:0x88,
                //         msg:"Query param list of satellite."
                //     };
                //     parent.ws.send(JSON.stringify(cfgList));
                // }, 500)
            }

            // 接收ADU->ACU->web上报消息
            ws.onmessage=function(evt){
                const recevied_msg = evt.data;
                // 信息反序列化
                const msg = JSON.parse(recevied_msg);
                // console.log(msg);

                switch (msg['cmd'])
                {
                    // set
                    case 0x10:
                        // 添加宏站信息
                        if(msg['result'] == 0) {
                            showOnStatusBarAndLog_T("设置宏基站数据成功");
                        } else {
                            showOnStatusBarAndLog_T("设置宏基站数据失败", 2, "darkorange");
                        }
                        break;
                    case 0x11:
                        // 设置上报配置参数
                        if(msg['result'] == 0) {
                            showOnStatusBarAndLog_T("设置上报配置参数成功");
                        } else {
                            showOnStatusBarAndLog_T("设置上报配置参数失败", 2, "darkorange");
                        }
                        break;
                    case 0x12:
                        // 设置出厂参数的应答消息
                        if(msg['result'] == 0) {
                            showOnStatusBarAndLog_T("设置出厂参数成功");
                        } else {
                            showOnStatusBarAndLog_T("设置出厂参数失败", 2, "darkorange");
                        }
                        break;
                    case 0x13:
                        // 设置系统复位的应答消息
                        antenna.window.showSystemResetType(msg);
                        break;
                    case 0x14:
                        // 设置工作模式的应答消息
                        if(msg['result'] == 0) {
                            showOnStatusBarAndLog_T("设置系统工作模式成功");
                        } else {
                            showOnStatusBarAndLog_T("设置系统工作模式失败", 2, "darkorange");
                        }
                        break;
                    case 0x15:
                        // 设置手动参数的应答消息
                        if(msg['result'] == 0) {
                            showOnStatusBarAndLog_T("手动调节成功");
                        } else {
                            showOnStatusBarAndLog_T("手动调节失败", 2, "darkorange");
                        }
                        break;
                    case 0x16:
                        // 设置RTC参数应答消息
                        if(msg['result'] == 0) {
                            showOnStatusBarAndLog_T("设置RTC参数成功");
                        } else {
                            showOnStatusBarAndLog_T("设置RTC参数失败", 2, "darkorange");
                        }
                        break;
                    case 0x17:
                        // 下发给ADU的CPE/DTU数据，不应该在这里出现
                        log.window.addLog_T(2, "下发给ADU的CPE/DTU数据，不应该在页面出现" + msg);
                        break;
                    // get
                    case 0x30:
                        // 查询基站信息
                        btsmanage.window.showBtsList(msg['btsList']);
                        break;
                    case 0x31:
                        // 查询上报配置参数
                        systemmanage.window.showUpdateCfgParam(msg);
                        break;
                    case 0x32:
                        // 查询出厂参数配置
                        systemmanage.window.showFactoryParam(msg);
                        break;
                    case 0x33:
                        // 查询设备状态
                        antenna.window.showDevicesStatus(msg);
                        break;
                    case 0x34:
                        // 查询工作模式
                        antenna.window.showSystemWorkMode(msg['result']);
                        systemmanage.window.showSystemWorkMode(msg['result']);
                        break;
                    case 0x35:
                        // ADU系统信息上报
                        // console.log(msg);
                        antenna.window.showMbpInfo(msg);
                        break;
                    case 0x36:
                        systemmanage.window.showRtcParam(msg);
                        break;
                    case 0x37:
                        // 查询版本
                        systemmanage.window.showVersion(msg);
                        break;
                    case 0x50:
                        // 网络质量数据
                        antenna.window.showNetworkState(msg);
                        break;
                    case 0x51:
                        // 流量数据
                        antenna.window.showLinkspeed(msg);
                        break;
                    case 0x52:
                        antenna.window.setLinkStatus(msg['linkstate']);
                        break;
                    case 0xF1:
                        // 日志类消息, 带时间信息。上位机自定义消息
                        // console.log(msg);
                        log.window.addLog(msg);
                        break;
                    case 0xF2:
                        // 天线连接状态消息。上位机自定义消息
                        if (msg['isConnected'] == true){
                            document.getElementById("light_adu_connect").style.backgroundColor = "limegreen";
                        } else {
                            document.getElementById("light_adu_connect").style.backgroundColor = "red";
                            showOnStatusBarAndLog_T("未能连接到卫星天线，请确认接线是否正确", 3, "red");
                        }
                        break;
                    default:
                        // showMsgOnStatusBar(msg, 'red');
                        log.window.addLog_T(2, "未知消息" + msg);
                }
            }

            // 关闭连接
            ws.onclose=function(){
                showOnStatusBarAndLog_T("同ACU间的连接断开", 2, "darkorange");
                document.getElementById("light_acu_connect").style.backgroundColor = "red";
            }
        }else{
            alert("浏览器不支持websockt!");
        }
    }

    // 3.定义断开连接的函数
    function disconnect(){
        if (ws != null){
            ws.close();
            ws = null;
        }
    }

    // 4.刷新页面时候，断开连接，重新连接，断线重连判断
    if (ws == null){
        connect();
    }else{
        disconnect();
    }

    let logReady = false;
    function showOnStatusBarAndLog_T(text, level = 1, color="black")
    {
        if (logReady)
        {
            log.window.addLog_T(level, text);
        }
        showMsgOnStatusBar(text, color)
    }

    let timeoutID;
    function showMsgOnStatusBar(msg, color="black")
    {
        const starusBar = document.getElementById('statusbar');

        starusBar.style= "color: " + color + ";";
        starusBar.innerHTML = "<p><strong>" + msg + "</strong></p>";

        //一段时间后恢复默认显示
        // console.log(timeoutID)
        clearTimeout(timeoutID);
        timeoutID=setTimeout("resetStatusBar()", 10000);
    }

    function resetStatusBar()
    {
        const starusBar = document.getElementById('statusbar');
        starusBar.style= "color: balck;";
        starusBar.innerHTML = "<p><strong> 南京京迪通信设备有限公司 </strong></p>";
    }