# _*_ coding: utf-8 _*_

"""
定义同下位机通信用的数据帧结构
@date 2021-3-9
"""
import struct
from inspect import signature
from struct import Struct
from enum import Enum
import threading
from utils import gl_logger


# 命令字
class CommandWord(Enum):

    ############MBP命令字###############
    # 设置宏站信息
    SET_BTS_INFO = 0x10
    # 设置上报配置参数
    SET_ADU_UPDATE_CFG = 0x11
    # 设置出厂参数
    SET_FACTORY_PARAM = 0x12
    # 设置系统复位
    SET_SYSTEM_RESET_TYPE = 0x13
    # 设置系统工作模式
    SET_SYSTEM_WORK_MODE = 0x14
    # 设置手动参数
    SET_MANUAL_PARAM = 0x15
    # 设置RTC参数
    SET_RTC_PARAM = 0x16
    # CPE/DTU参数下发ADU
    SET_DTU_PARAM = 0x17

    # 查询宏站信息
    GET_BTS_INFO = 0x30
    # 查询上报配置参数
    GET_ADU_UPDATE_CFG = 0x31
    # 查询出厂参数
    GET_FACTORY_PARAM = 0x32
    # 查询设备状态
    GET_DEVICE_STATUS = 0x33
    # 查询系统工作模式
    GET_SYSTEM_WORK_MODE = 0x34
    # 系统信息上报
    GET_ADU_UPDATE_INFO = 0x35
    # 查询RTC参数
    GET_RTC_PARAM = 0x36
    # 查询版本
    GET_VERSION = 0x37

# end of class CommandWord

class Protocol:
    # 帧头长度，头标识2字节，命令字1字节，长度2字节，设备序列号8字节， 签名4个字节，校验位1字节，共18字节
    __FRAME_HEAD_LEN = 18
    # 帧头识别码
    # 请求帧的标识头
    GC_TO_ADU_FRAME_HEAD = 0x55AA
    # __GC_TO_ADU_FRAME_HEAD_L = 0x55
    # __GC_TO_ADU_FRAME_HEAD_H = 0xAA
    __GC_TO_ADU_FRAME_HEAD_BA = b'\xAA\x55'
    # 应答帧的标识头
    GC_FROM_ADU_FRAME_HEAD = 0x5AA5
    # __GC_FROM_ADU_FRAME_HEAD_L = 0x5A
    # __GC_FROM_ADU_FRAME_HEAD_H = 0xA5
    __GC_FROM_ADU_FRAME_HEAD_BA = b'\xA5\x5A'

    def __init__(self):
        # 接收缓存区
        self.__recvBuff = bytearray()
        self.__rLock = threading.RLock()

    """
    /*
     * 1）	头标识：2个字节，请求为0xAA 0x55，应答为0xA5 0x5A。
     * 2）	命令标识：1个字节。
     * 3）	长度：2个字节，无符号数，其值为数据体数据长度，不超过0xFFFF。
     * 4）	校验位：1个字节，计算命令、长度及数据体中数据的校验位。
     * 5）	数据体：数据内容和长度根据功能的不同而不同。
    */
    struct DataFrame{
        unsigned short head;            //帧头
        unsigned char cmd;              //命令字
        unsigned short len;             //长度
        unsigned char[8] sn;            //设备序列号
        unsigned int signature;         //签名
        unsigned char parity;           //校验
        //char* data;                   //数据指针
    };
    返回打包好的数据帧的二进制数组
    """
    def framePack(self, head, cmd, sn, signature: int, baData: bytes):
        strFormat = '<HBH8sIB'

        if not isinstance(baData, bytes):
            return "baData必须为一个数组"

        b_sn = sn.encode('utf-8')
        length = len(baData)
        parity = (self.getParity(length.to_bytes(length=2, byteorder='little')) ^
                  self.getParity(b_sn) ^
                  self.getParity(signature.to_bytes(length=4, byteorder='little')) ^
                  self.getParity(baData))
        # 头标识2字节，命令字1字节，长度2字节，设备序列号8个字节，签名4个字节，校验位1字节，共18字节 加 数据体
        return Struct(strFormat).pack(head, cmd, length, b_sn, signature, parity) + baData

    #
    # 数据帧解包
    # 返回：数据字典，如何得到完整的一帧，result = True，如果没能得到完整一帧，result = False
    #
    def frameUnpark(self, baData):
        if len(baData) >= self.__FRAME_HEAD_LEN:  # 帧长度最少要大于等于帧头长度才可以分析
            strFormat = '<HBH8sIB'
            frameHead = Struct(strFormat).unpack(baData[:self.__FRAME_HEAD_LEN])  # 解包为6个数字的数组
            head = frameHead[0]  # 帧头2字节
            cmd = frameHead[1]  # 命令字1字节
            length = frameHead[2]  # 数据区长度2字节
            sn = frameHead[3]  # 设备序列号8字节
            signature = frameHead[4]  # 签名4字节
            parity = frameHead[5]  # 校验1字节
            if (head == self.GC_TO_ADU_FRAME_HEAD) or (head == self.GC_FROM_ADU_FRAME_HEAD):
                if len(baData) >= (self.__FRAME_HEAD_LEN + length):  # 已经接收到一帧数据
                    return dict(
                        result=True,
                        head=head,
                        cmd=cmd,
                        length=length,
                        sn=sn.decode('utf-8'),
                        signature=signature,
                        parity=parity,
                        data=baData[self.__FRAME_HEAD_LEN:self.__FRAME_HEAD_LEN + length]
                    )
                else:  # 接收到的数据不够一帧
                    pass
            else:  # 不是一帧的开头
                pass

        return dict(
            result=False  # 未能得到完整的一帧
        )

    #
    # 返回字节数组的校验值
    #
    def getParity(self, baData: bytes):
        ret = 0
        # 数据体异或
        for i in baData:
            ret ^= i
        return ret

    #
    # 打印16进制数组
    #
    def print_hex(self, bytes):
        l = [hex(i) for i in bytes]
        print(" ".join(l))

    #
    # 剪除帧头前的无线数据，这里只处理ADU上报数据
    #
    def trimHead(self, baData: bytearray):
        index = baData.find(self.__GC_FROM_ADU_FRAME_HEAD_BA)
        if index != -1:
            return baData[index:]  # 说明有有效数据，返回帧头开始的数组
        else:
            return b''  # bytearray()      # 说明都是无效数据，返回空数组

        # 接收数据

    def recvData(self, baData: bytes):
        with self.__rLock:
            self.__recvBuff += baData
            # print("recvbuff:", self.__recvBuff)

    # 得到第一个完整的数据帧，并把它数据队列中截除
    def getFirstFrame(self):
        with self.__rLock:
            # 清理无效字节
            self.__recvBuff = self.trimHead(self.__recvBuff)

            ret = self.frameUnpark(self.__recvBuff)
            if ret['result']:
                self.__recvBuff = self.__recvBuff[self.__FRAME_HEAD_LEN + ret['length']:]  # 接收队列清除第一个数据帧
                # print("recvbuff after get first frame:", self.__recvBuff)

        return ret

    #######################################################################################################################
    # 命名规则
    # 方向：ACU -> ADU，发送设置命令，命令字为set，需要构造数据帧，帧构造函数以set开头
    # 方向：ADU -> ACU，响应帧，命令字为set，帧处理函数为onSet开头
    # 方向：ACU -> ADU，发送查询命令，命令字为get，需要构造数据帧，帧构造函数以get开头
    # 方向：ADU -> ACU，响应帧，命令字为get，帧处理函数为onGet开头

    """
    unsgined char btsCount;
    struct BtsInfo
    {
       double longitude;
       double latitude;
       char[32] bts_name;
       float cover;  
       unsigned int bts_no;
       unsigned int group_no;
    }
    """
    def setBtsInfoList(self, btsList, sn='sn888888', signature=0):
        # 基站个数
        data = Struct('<B').pack(len(btsList))
        for bts in btsList:
            data += self.setBtsParamData(bts['longitude'], bts['latitude'],
                                            bts['bts_name'].encode('utf-8'), bts['cover'],
                                            bts['bts_no'], bts['group_no'])
        # print(f"给ADU的基站列表数据：{data}")
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.SET_BTS_INFO.value,
                                  sn=sn, signature=signature, baData=data)
        except Exception as err:
            gl_logger.error(str(err))
            return False

    # 打包单个基站信息成二进制流
    def setBtsParamData(self, longitude, latitude, bts_name, cover, bts_no, group_no):
        strFormat = '<dd32sfII'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(longitude, latitude, bts_name, cover, bts_no, group_no)

    # 查询基站信息列表
    def getBtsInfoList(self, sn='sn888888', signature=0):
        # 构造数据帧
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_BTS_INFO.value,
                              sn=sn, signature=signature, baData=b'')

    # 获取基站信息列表
    def onGetBtsInfoList(self, baData):
        # todo:如果基站信息修改，这里需要同步修改
        BTS_INFO_LEN = 60  # 单个基站信息的结构长度

        bts_count = baData[0]  # 第一个字节是基站数量
        # 数据检查
        if len(baData) != BTS_INFO_LEN*bts_count+1:
            return []

        bts_list = baData[1:]  # 获取BTS列表
        ret = []
        for i in range(0, bts_count):
            btsData = bts_list[(i * BTS_INFO_LEN):(i + 1) * BTS_INFO_LEN]
            ret.append(self.getBtsInfoParam(btsData))

        # gl_log.logger.info(ret)
        return ret

    def getBtsInfoParam(self, baData):
        strFormat = '<dd32sfII'
        try:
            baUnpack = Struct(strFormat).unpack(baData)
            return dict(
                id=baUnpack[4],     # 模拟页面的dataset
                longitude=baUnpack[0],
                latitude=baUnpack[1],
                bts_name=baUnpack[2].decode('utf-8'),
                cover=baUnpack[3],
                bts_no=baUnpack[4],
                group_no=baUnpack[5])
        except Exception as err:
            gl_logger.error(str(err))
            return False

    """
    # 查询ADU上报的配置参数
    struct UpdateCfg
    {
        unsigned char ip1;
        unsigned char ip2;
        unsigned char ip3;
        unsigned char ip4;
        unsigned short port;
        unsigned long interval;
        unsigned char updateRtc;
        unsigned char updateMode;
    }
    """
    def setAduUpdateCfgData(self, ip1, ip2, ip3, ip4, port, interval, updateRtc, updateMode):
        strFormat = '<BBBBHLBB'
        return Struct(strFormat).pack(ip1, ip2, ip3, ip4, port,interval, updateRtc, updateMode)

    def setAduUpdateCfg(self, ip1, ip2, ip3, ip4, port, interval, updateRtc, updateMode,
                        sn='sn888888', signature=0):
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD,cmd=CommandWord.SET_ADU_UPDATE_CFG.value,
                                  sn=sn, signature=signature,
                                  baData=self.setAduUpdateCfgData(ip1, ip2, ip3, ip4,
                                                                  port, interval, updateRtc, updateMode))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    # 查询ADU上报配置
    def getAduUpdateCfg(self, sn='sn888888', signature=0):
        # 构造数据帧
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_ADU_UPDATE_CFG.value,
                              sn=sn, signature=signature, baData=b'')

    # 查询ADU上报配置的应答解析
    def onGetAduUpdateCfg(self, baData):
        strFormat = '<BBBBHLBB'
        baUnpack = Struct(strFormat).unpack(baData)
        return dict(
            ip1=baUnpack[0],
            ip2=baUnpack[1],
            ip3=baUnpack[2],
            ip4=baUnpack[3],
            port=baUnpack[4],
            interval=baUnpack[5],
            updateRtc=baUnpack[6],
            updateMode=baUnpack[7]
        )

    """
    # 设置工场配置参数
    struct SetFactoryParam
    {
        char productMode[7];
        char SN[8];
        char hardwareVersion[4];
        char constructionVersion[4];
    };
    # 返回打包好的二进制字节数组
    """
    # 暂时未使用
    def setFactoryParamData(self, productMode, SN, hardwareVersion, constructionVersion):
        strFormat = '<7s8s4s4s'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(productMode, SN, hardwareVersion, constructionVersion)

    def setFactoryParam(self, productMode, SN, hardwareVersion, constructionVersion, sn='sn888888', signature=0):
        # print(bytes(productMode, 'UTF-8'))
        # print(hardwareVersion)
        # print(constructionVersion)
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.SET_FACTORY_PARAM.value,
                                  sn=sn, signature=signature,
                                  baData=self.setFactoryParamData(bytes(productMode, 'utf-8'),
                                                                  bytes(SN, 'utf-8'),
                                                                  bytes(hardwareVersion, 'utf-8'),
                                                                  bytes(constructionVersion, 'utf-8')))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    """
    # 查询工场配置参数
    struct GetFactoryParam
    {
        char productMode[7];
        char SN[8];
        char hardwareVersion[4];
        char constructionVersion[4];
    };
    """
    def getFactoryParam(self, sn='sn888888', signature=0):
        # 构造数据帧
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_FACTORY_PARAM.value,
                              sn=sn, signature=signature, baData=b'')
    # 返回解包后的数据字典
    def onGetFactoryParam(self, baData):
        # strFormat = '<8s4s4s'  # 按上面Struct定义的结构的格式串,小字序
        # baUnparked = Struct(strFormat).unpack(baData)
        productMode = baData[:7].decode(encoding='utf-8', errors='strict')
        SN = baData[7:15].decode(encoding='utf-8', errors='strict')
        hardwareVersion = baData[15:19].decode(encoding='utf-8', errors='strict')
        constructionVersion = baData[19:23].decode(encoding='utf-8', errors='strict')
        aduSoftwareVersion = baData[23:].decode(encoding='utf-8', errors='strict')

        return dict(
            productMode=productMode,
            SN=SN,
            hardwareVersion=hardwareVersion,
            constructionVersion=constructionVersion,
            aduSoftwareVersion=aduSoftwareVersion
        )

    # 返回打包好的二进制字节数组，暂时未使用
    def getFactoryParamPack(self, productMode, SN, hardwareVersion, constructionVersion):
        strFormat = '<7s8s4s4s'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(productMode, SN, hardwareVersion, constructionVersion)

    """
    # 查询设备状态
    struct GetDeviceState
    {
        unsigned char   yawMoto;        //方位电机
        unsigned char   pitchMoto;      //俯仰电机
        unsigned char   yawLimit;       //方位限位
        unsigned char   pitchLimit;     //俯仰限位
        unsigned char   IMUState;       //惯导
        unsigned char   DGPSState;      //DGPS
        unsigned char   DTUState;       //DTU
        unsigned char   storageState    //存储   
    };
    """
    # 查询设备状态信息
    def getDevicesStatus(self, sn='sn888888', signature=0):
        # 构造数据帧
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_DEVICE_STATUS.value,
                              sn=sn, signature=signature, baData=b'')

    # 返回解包后的数据字典
    def onGetDevicesStatus(self, baData):
        strFormat = '<BBBBBBBB'  # 按上面Struct定义的结构的格式串,小字序
        baUnpack = Struct(strFormat).unpack(baData)
        return dict(
            yawMotoState=baUnpack[0],
            pitchMotoState=baUnpack[1],
            yawLimitState=baUnpack[2],
            pitchLimitState=baUnpack[3],
            IMUState=baUnpack[4],
            DGPSState=baUnpack[5],
            DTUState=baUnpack[6],
            storageState=baUnpack[7]
        )

    """
    # 复位系统
    struct SetSystemReset
    {
        unsigned char resetType;    //复位类型： 00，业务复位，将状态机切换到初始化状态  01，软件复位，重启软件
    };
    # 返回打包好的二进制字节数组
    """
    def setSystemResetTypeData(self, resetType):
        strFormat = '<B'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(resetType)

    def setSystemResetType(self, resetType, sn='sn888888', signature=0):
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.SET_SYSTEM_RESET_TYPE.value,
                                  sn=sn, signature=signature, baData=self.setSystemResetTypeData(resetType))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    # 返回解包后的数据字典
    def onSetSystemReset(self, baData):
        strFormat = '<BB'  # 按上面Struct定义的结构的格式串,小字序
        baUnpack = Struct(strFormat).unpack(baData)
        return dict(
            resetType=baUnpack[0],
            result=baUnpack[1]
        )

    """
    # 设置系统工作模式
    struct SetSystemWorkMode
    {
        unsigned char systemWortMode;      //工作模式：00，自动模式    01，手动模式 
    };
    # 返回打包好的二进制字节数组
    """
    def setSystemWorkModeData(self, workMode):
        strFormat = '<B'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(workMode)

    def setSystemWorkMode(self, workMode, sn='sn888888', signature=0):
        # print("workMode:", workMode)
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.SET_SYSTEM_WORK_MODE.value,
                                  sn=sn, signature=signature, baData=self.setSystemWorkModeData(workMode))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    def onSetSystemWorkMode(self, baData):
        strFormat = '<BB'  # 按上面Struct定义的结构的格式串,小字序
        baUnpack = Struct(strFormat).unpack(baData)
        return dict(
            workMode=baUnpack[0],
            result=baUnpack[1]
        )
    """
    # 查询系统工作模式
    struct GetSystemWorkMode
    {
        unsigned char systemWortMode;       //工作模式：00，自动模式    01，手动模式 
        unsigned char result;               //操作结果： 00，设置成功    01，设置失败
    };
    """
    def getSystemWorkMode(self, sn='sn888888', signature=0):
        # 构造数据帧
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_SYSTEM_WORK_MODE.value,
                              sn=sn, signature=signature, baData=b'')

    # 返回解包后的数据字典
    def onGetSystemWorkMode(self, baData):
        strFormat = '<BB'  # 按上面Struct定义的结构的格式串,小字序
        baUnpack = Struct(strFormat).unpack(baData)
        return dict(
            systemWortMode=baUnpack[0],
            result=baUnpack[1]
        )

    # 返回打包好的二进制字节数组，暂时未使用
    def getSystemWorkModePack(self, systemWorkMode, result):
        strFormat = '<BB'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(systemWorkMode, result)

    """
    # 设置手动调节参数
    struct SetManualParam
    {
       unsigned char   angleMode;      //角度模式： 00，绝对模式，转到导航系目标位置    01，增量模式，在载体系中转动一定角度
       unsigned char   axis;           //运动轴   00，方位    01，俯仰    
       unsigned char   direction;      //方位运动方向，仅在增量模式下有效：   00，向上运动 或 向右运动 或 顺时针    01，向下运动 或 向左运动 或 逆时针
       float           angle;          //运动角度，单位：度。
    };
    """
    def setManualParamData(self, mode, axis, direct, angle):
        strFormat = '<BBBf'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(mode, axis, direct, angle)

    def setManualParam(self, mode, axis, direct, angle, sn='sn888888', signature=0):
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.SET_MANUAL_PARAM.value,
                                  sn=sn, signature=signature, baData=self.setManualParamData(mode, axis, direct, angle))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    """
    # 设置RTC参数
    struct RTCParam
    {
        unsigned short year;
        unsigned char month;
        unsigned char day;  
        unsigned char hour;
        unsigned char minute;
        unsigned char second;
    }
    """
    def setRtcParamData(self, year, month, day, hour, minute, second):
        strFormat = '<HBBBBB'
        return Struct(strFormat).pack(year, month, day, hour, minute, second)

    def setRTCParam(self, year, month, day, hour, minute, second, sn='sn888888', signature=0):
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD,   cmd=CommandWord.SET_RTC_PARAM.value,
                                  sn=sn, signature=signature, baData=self.setRtcParamData(year, month, day, hour, minute, second))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    def getRtcParam(self, sn='sn888888', signature=0):
        # 构造数据帧
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_RTC_PARAM.value,
                              sn=sn, signature=signature, baData=b'')

    def onGetRtcParam(self, baData):
        strFormat = '<HBBBBB'
        try:
            baUnpack = Struct(strFormat).unpack(baData)
            return dict(
                year=baUnpack[0],
                month=baUnpack[1],
                day=baUnpack[2],
                hour=baUnpack[3],
                minute=baUnpack[4],
                second=baUnpack[5]
            )
        except Exception as err:
            gl_logger.error(str(err))
            return False

    """
        # 下发CPE/DTU网络指标参数给ADU
        struct DtuParam
        {
            unsigned char standard[8];
            int plmn;  
            int cellid;
            int pci;
            int rsrp;
            int rssi;
            int sinr;
        }
        """
    def setDtuParamData(self, standard, plmn, cellid, pci, rsrp, rssi, sinr):
        strFormat = '<8siiiiii'
        # 整理数据
        if rssi == 'N/A':
            rssi = 0
        if sinr == 'N/A':
            sinr = 0
        return Struct(strFormat).pack(standard, plmn, cellid, pci, rsrp, rssi, sinr)

    def setDtuParam(self, standard, plmn, cellid, pci, rsrp, rssi, sinr, sn='sn888888', signature=0):
        try:
            return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.SET_DTU_PARAM.value,
                                  sn=sn, signature=signature,
                                  baData=self.setDtuParamData(standard.encode('utf_8'), plmn, cellid, pci, rsrp, rssi, sinr))
        except Exception as err:
            gl_logger.error(str(err))
            return False

    """
    # 查询版本信息
    struct GetVersion
    {
        char sorftwareVersion[4];
        char hardwareVersion[4];
        char constructionVersion[4];
    };
    """
    def getVersion(self, sn='sn888888', signature=0):
        return self.framePack(head=self.GC_TO_ADU_FRAME_HEAD, cmd=CommandWord.GET_VERSION.value,
                              sn=sn, signature=signature, baData=b'')

    # 返回解包后的数据字典
    def onGetVersion(self, baData):
        # strFormat = '<4s4s4s'  # 按上面Struct定义的结构的格式串,小字序
        # baUnpack = Struct(strFormat).unpack(baData)
        softwareVersion = baData[:4].decode()
        hardwareVersion = baData[4:8].decode()
        constructionVersion = baData[8:].decode()
        # print("softwareVersion",softwareVersion)
        # print("hardwareVersion",hardwareVersion)
        # print("constructionVersion",constructionVersion)
        return dict(
            softwareVersion=str(softwareVersion),
            hardwareVersion=str(hardwareVersion),
            constructionVersion=str(constructionVersion)
        )

    # 返回打包好的二进制字节数组
    def getVersionPack(self, softwareVersion, hardwareVersion, constructionVersion):
        strFormat = '<4s4s4s'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(softwareVersion, hardwareVersion, constructionVersion)

    """
    # 查询执行结果
    struct GetResult
    {
        unsigned char result;       //操作结果： 00，设置成功    01，设置失败
    };
    """
    # 通用的命令响应解析，单字节结果帧处理
    # 返回解包后的数据字典,结果放在result中
    def onGetResult(self, baData):
        strFormat = '<B'  # 按上面Struct定义的结构的格式串,小字序
        baUnparked = Struct(strFormat).unpack(baData)
        return dict(
            result=baUnparked[0]
        )

    # 返回打包好的二进制字节数组
    def getResultPack(self, result):
        strFormat = '<B'  # 按上面Struct定义的结构的格式串,小字序
        return Struct(strFormat).pack(result)

    """
    # MBP状态上报
    struct AduUpdateInfo
    {
        unsigned char   systemState;        //系统状态  业务模式。00，无状态 01，初始化 02，预搜索 03，搜索 04，故障
        double          btsLongitude;       //当前指向宏站经度
        double          btsLatitude;        //当前指向宏站纬度
        unsigned char   btsName[32];        //基站名称
        float           cover;              //基站覆盖半径
        unsigned int    btsNo;              //基站编号
        unsigned int    groupNo;            //基站组号
        double          longitude;          //设备所在经度
        double          latitude;           //设备所在纬度
        float           theoryYaw;          //理论方位角
        float           yaw;                //方位角
        float           pitch;              //俯仰角
        float           roll;               //横滚角
        unsigned char   yawLimitState;      //方位限位状态    00，无接触 01，接触左限位 10，接触右限位
        float           temperature;        //温度
        float           humidity;           //湿度
        unsigned int    dgps_err;           //DGPS错误帧数目
        unsigned int    dgps_start;         //DGPS启动时间
    };
    """
    # 返回解包后的数据字典
    def onGetAduUpdateInfo(self, baData):
        strFormat = '<Bdd32sfIIddffffBffII'  # 按上面Struct定义的结构的格式串,小字序

        try:
            baUnpack = Struct(strFormat).unpack(baData)
            return dict(
                systemState=baUnpack[0],  # 系统状态
                btsLongitude=baUnpack[1], #当前指向宏站经度
                btsLatitude=baUnpack[2],  #当前指向宏站纬度
                btsName=baUnpack[3].decode('utf-8'),  # 基站名称
                coverR=baUnpack[4],        #基站覆盖半径
                btsNo=baUnpack[5],        #基站编号
                groupNo=baUnpack[6],      #基站组号
                longitude=baUnpack[7],    #设备所在经度
                latitude=baUnpack[8],     #设备所在纬度
                theoryYaw=baUnpack[9],    # 理论方位角
                yaw=baUnpack[10],  # 方位角
                pitch=baUnpack[11],  # 俯仰角
                roll=baUnpack[12],  # 横滚角
                yawLimitState=baUnpack[13], # 方位限位器状态
                temperature=baUnpack[14],  # 温度
                humidity=baUnpack[15],  # 湿度
                dgps_err=baUnpack[16], # DGPS错误帧数目
                dgps_start=baUnpack[17] # DGPS启动时间
            )
        except Exception as err:
            gl_logger.error(str(err))
            return False

##################################################################################################################

if __name__ == "__main__":
    p = Protocol()

    # cfgNumber = 1
    # polarity = 0
    # longitude = 134.0
    # beaconFrequency = 5188.0
    # symbolRate = 6888
    # trackingMode = 0
    # upperLimitVoltage = 1.2
    # lowerLimitVoltage = 1.5
    # lnbVoltage = 3
    # satParm = p.setSearchSatelliteParam(cfgNumber, polarity, longitude, beaconFrequency, symbolRate,
    #                                     trackingMode, upperLimitVoltage, lowerLimitVoltage, lnbVoltage)
    # print("satParam:")
    # p.print_hex(satParm)
    # strFormat = '<BBffHBffB'  # 按上面Struct定义的结构的格式串,小字序
    # baUnparked = Struct(strFormat).unpack(satParm)
    # param = baUnparked[4]
    # print("Unpacked param:", param)
    # data = p.framePack(p.GC_SET_FRAME_HEAD, CommandWord.SET_SEARCH_SATELLITE_PARAM.value, satParm)
    # print(data)
    #
    # print("packed frame:")
    # p.print_hex(data)
    # unparkData = p.frameUnpark(data)
    # print("unparked frame:")
    # p.print_hex(unparkData)
    # baUnparked = Struct(strFormat).unpack(unparkData)
    # param = baUnparked[4]
    # print("Unpacked Frame param:", param)
    # # p.print_hex(p.framePack(const.GC_SET_FRAME_HEAD, CommandWord.SET_SEARCH_SATELLITE_PARAM.value, satParm)[:5])
    # # p.print_hex(p.framePack(const.GC_SET_FRAME_HEAD, CommandWord.SET_SEARCH_SATELLITE_PARAM.value, satParm)[5:])
    #
    # antennaInfo = p.getAntennaInfoPack(30.5, 22, 15.8, 22, 38, 41, 55, 28, 1.28, 1.2, 1.5, 0, 38.5, 45, 1)
    # print(p.getAntennaInfo(antennaInfo))
    #
    # print("配置组编号：", p.setConfigNumber(1))
    #
    # print("版本号：", p.getVersionPack(b"12.3", b"01.5"))
    #
    # factory = p.setFactoryParam(b'12345678', b'1.20', b'3.44')
    # print(p.getFactoryParam(factory))
    #
    # p.print_hex(p.setManualParam(0, 0, 12, 1, 30, 0, 50, 1, 60))

    # data = bytearray().fromhex('00 00 00 00 00 00 00 00 A5 5A 81 08 09 00 00 11 00 00 22 00 00 A5 5A 81 08 7F 30 00 00 00 10 00 00 00 A5 5A 81 08 01 00 00 20 00 01 01 02')
    # # data = bytearray().fromhex('01 02 00 04 05 A5 A5 5A 80 36 82 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 33 33 34 43 00 00 F0 41 00 00 00 00 9A 99 99 3F 00 00 00 00 00 00 2C C2 00 00 86 C2 11 00 00 C8 41 00 00 A0 42 07 A5 5A 81 14 FC 00 00 00 00 00 00 00 00 A5 5A 81 14 82 00 00 00 00 00 00 00')
    # print('data:', data)
    #
    # p.handleData(data)
    # print('data2:', data)

    frame = p.framePack(p.GC_TO_ADU_FRAME_HEAD, 0x60, 0, 0, b'')
    p.print_hex(frame)

    d = p.frameUnpark(frame)
    print(d)
    p.print_hex(d['head'].to_bytes(2, 'little'))
    p.print_hex(d['data'])
