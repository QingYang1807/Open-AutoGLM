# AutoGLM 授权系统 V0 设计文档

## 一、系统概述

### 1.1 设计目标

实现一个**完全离线**的本地授权控制系统，用于：
- ✅ 控制软件分发
- ✅ 控制使用时长
- ✅ 提高客户粘性
- ✅ **本周内可完成并上线使用**

### 1.2 核心约束

- ❌ 不做后台服务器
- ❌ 不做账号系统
- ❌ 不做支付
- ❌ 不引入复杂授权平台
- ✅ 用最简单的方式先"打鱼窝"，后续再迭代

---

## 二、核心功能设计

### 2.1 机器码生成

#### Windows 机器码生成逻辑

使用组合方式生成稳定的机器标识：

```python
机器码 = SHA256(CPU_ID | 主板序列号 | 系统盘序列号 | 计算机名 | MAC地址)[:16]
```

**实现细节：**
1. **CPU信息**: `wmic cpu get ProcessorId`
2. **主板序列号**: `wmic baseboard get SerialNumber`
3. **系统盘序列号**: `wmic logicaldisk where DeviceID="C:" get VolumeSerialNumber`
4. **计算机名**: `platform.node()`
5. **MAC地址**: `getmac /fo csv /nh` (第一个非回环地址)

**降级方案：**
- 如果上述方法失败，使用 `计算机名 + 用户名` 作为降级标识
- 确保同一设备稳定，不同设备基本不同

#### Android 机器码生成逻辑（预留）

```python
机器码 = SHA256(ANDROID_ID | APP签名Hash | 设备特征)[:16]
```

---

### 2.2 授权码格式

**格式：** `AUTOGLM-{周期}-{代码}`

**示例：**
- `AUTOGLM-TRIAL-ABC123` - 体验版（7天）
- `AUTOGLM-1M-XYZ789` - 1个月
- `AUTOGLM-3M-DEF456` - 3个月
- `AUTOGLM-6M-GHI789` - 6个月
- `AUTOGLM-1Y-JKL012` - 1年

**周期定义：**
```python
DURATION_DAYS = {
    "trial": 7,      # 体验版 7天
    "1m": 30,        # 1个月
    "3m": 90,        # 3个月
    "6m": 180,       # 6个月
    "1y": 365,       # 1年
}
```

---

### 2.3 授权数据结构

#### 内存结构（Python Dict）

```python
{
    "license_code": "AUTOGLM-1M-ABC123",      # 授权码
    "machine_id": "A1B2C3D4E5F6G7H8",         # 绑定的机器码
    "activate_time": "2025-01-15T10:30:00",  # 激活时间（ISO格式）
    "expire_time": "2025-02-14T10:30:00",    # 到期时间（ISO格式）
    "duration_days": 30,                       # 授权天数
    "last_check_time": "2025-01-20T15:45:00"  # 最后检查时间（用于时间回拨检测）
}
```

#### 存储格式（加密后）

```json
{
    "data": "base64编码的授权数据",
    "checksum": "MD5校验和",
    "version": "1.0"
}
```

**加密方式：**
- 授权数据 JSON → Base64 编码
- 校验和 = MD5(Base64数据 + 机器码)

---

### 2.4 授权校验流程

#### 校验时机

**⚠️ 关键：必须在执行层拦截，不能只在UI层**

1. **任务执行入口** (`execute_task` 函数)
   - 每次执行任务前检查授权
   - 无授权/已到期 → 直接返回错误，不执行任何自动化动作

2. **前端UI层**（辅助提示）
   - 显示授权状态
   - 执行前提示（但不能绕过）

#### 校验步骤

```python
def CheckLicense():
    1. 加载授权文件
    2. Base64解码授权数据
    3. 验证校验和
    4. 验证机器码绑定
    5. 检查时间回拨（如果当前时间 < 上次检查时间 - 5分钟 → 锁定）
    6. 检查是否过期（当前时间 >= 到期时间 → 无效）
    7. 更新最后检查时间
    8. 返回 (是否有效, 消息, 授权信息)
```

---

### 2.5 时间回拨检测

**检测逻辑：**

```python
last_check_time = 授权数据['last_check_time']
current_time = datetime.now()

# 检测时间倒退（允许5分钟误差）
if current_time < last_check_time - timedelta(minutes=5):
    return False, "检测到系统时间被回拨，授权已锁定"
```

**防护措施：**
- 记录首次激活时间
- 记录最近一次运行时间
- 如果检测到时间倒退 → 直接锁定授权

---

## 三、技术实现

### 3.1 文件结构

```
pc-app/backend/
├── license.py          # 授权核心模块
└── web_server.py      # Flask服务器（集成授权校验）

pc-app/frontend/src/
├── components/
│   └── LicenseModal.jsx  # 授权管理界面
└── services/
    └── api.js            # API服务（添加授权相关接口）
```

### 3.2 关键代码位置

#### 后端授权校验（执行层拦截）

**文件：** `pc-app/backend/web_server.py`

```python
def execute_task(task, task_id, is_continue=False):
    # ⚠️ 授权校验 - 在执行层拦截
    if not license_manager.IsValid():
        is_valid, message, _ = license_manager.CheckLicense()
        error_msg = f"授权验证失败: {message}"
        current_task["status"] = "error"
        current_task["result"] = error_msg
        return  # 直接返回，不执行任务
```

#### 前端授权检查（UI层提示）

**文件：** `pc-app/frontend/src/App.jsx`

```javascript
const handleExecute = async () => {
    // Check license before execution
    if (!licenseValid) {
        toast.error('授权验证失败，请先激活授权');
        setShowLicense(true);
        return;
    }
    // ... 执行任务
};
```

---

## 四、API 接口设计

### 4.1 获取授权信息

**接口：** `GET /api/license/info`

**响应：**
```json
{
    "success": true,
    "info": {
        "is_valid": true,
        "message": "授权有效，剩余 25 天",
        "machine_id": "A1B2C3D4E5F6G7H8",
        "activated": true,
        "license_code": "AUTOGLM-1M-ABC123",
        "activate_time": "2025-01-15T10:30:00",
        "expire_time": "2025-02-14T10:30:00",
        "duration_days": 30,
        "remaining_days": 25
    }
}
```

### 4.2 激活授权码

**接口：** `POST /api/license/activate`

**请求：**
```json
{
    "license_code": "AUTOGLM-1M-ABC123"
}
```

**响应：**
```json
{
    "success": true,
    "message": "授权激活成功！到期时间: 2025-02-14 10:30:00",
    "info": { ... }
}
```

### 4.3 检查授权状态

**接口：** `GET /api/license/check`

**响应：**
```json
{
    "success": true,
    "is_valid": true,
    "message": "授权有效，剩余 25 天",
    "license_data": { ... }
}
```

### 4.4 获取机器码

**接口：** `GET /api/license/machine-id`

**响应：**
```json
{
    "success": true,
    "machine_id": "A1B2C3D4E5F6G7H8"
}
```

---

## 五、前端界面设计

### 5.1 授权状态指示器

**位置：** 顶部导航栏右侧

**显示：**
- ✅ **已授权**（绿色）：授权有效
- ❌ **未授权**（红色，闪烁）：授权无效或未激活

**交互：**
- 点击 → 打开授权管理弹窗

### 5.2 授权管理弹窗

**功能：**
1. 显示当前授权状态（有效/无效）
2. 显示授权信息（授权码、激活时间、到期时间、剩余天数）
3. 显示机器码（可复制）
4. 输入授权码激活/重新激活
5. 显示授权说明

---

## 六、风控措施

### 6.1 数据加密

- ✅ Base64 编码授权数据
- ✅ MD5 校验和防止篡改
- ✅ 机器码绑定防止复制

### 6.2 时间回拨检测

- ✅ 记录最后检查时间
- ✅ 检测时间倒退（允许5分钟误差）
- ✅ 时间回拨 → 直接锁定

### 6.3 执行层拦截

- ✅ 授权校验在 `execute_task` 函数入口
- ✅ UI层提示 + 执行层拦截双重保护
- ✅ 无授权 = 所有自动化动作不执行

---

## 七、后续升级路径

### 7.1 V1 升级方案（服务器授权）

**升级点：**
1. 授权码验证改为服务器校验
2. 添加在线激活接口
3. 支持授权码撤销/续期
4. 添加使用统计

**兼容性：**
- V0 授权数据可平滑迁移
- 保留本地校验作为降级方案

### 7.2 功能级授权（预留）

**支持场景：**
- 免费版：限功能/限流程/限次数
- 付费版：完整流程/更强算力/更稳定执行

**实现方式：**
```python
授权数据中添加功能开关：
{
    "features": {
        "full_automation": true,
        "advanced_ai": true,
        "unlimited_tasks": true
    }
}
```

---

## 八、测试用例

### 8.1 基础功能测试

- [x] 机器码生成（Windows）
- [x] 授权码激活
- [x] 授权状态检查
- [x] 到期时间计算
- [x] 执行层拦截

### 8.2 风控测试

- [x] 时间回拨检测
- [x] 机器码绑定验证
- [x] 授权数据篡改检测
- [x] 过期授权拦截

### 8.3 边界测试

- [x] 未激活授权
- [x] 已过期授权
- [x] 机器码不匹配
- [x] 授权文件损坏

---

## 九、部署说明

### 9.1 授权文件位置

```
{DATA_DIR}/license.json
```

**DATA_DIR 优先级：**
1. 环境变量 `AUTOGLM_DATA_DIR`
2. 默认：`pc-app/backend/`

### 9.2 授权码生成（V0阶段）

**当前实现：**
- V0阶段：客户端只校验，不生成
- 授权码由外部工具/脚本生成（不在本文档范围）

**后续升级：**
- V1阶段：服务器端生成授权码
- 支持在线激活/续期

---

## 十、总结

### 10.1 核心特点

✅ **完全离线**：无需服务器，本地验证  
✅ **执行层拦截**：核心功能不可绕过  
✅ **时间回拨检测**：防止时间作弊  
✅ **数据加密**：Base64 + MD5校验  
✅ **快速上线**：本周内可完成  

### 10.2 适用场景

- ✅ 0→1 落地验证阶段
- ✅ 快速推向市场
- ✅ 控制软件分发
- ✅ 控制使用时长

### 10.3 后续迭代

- V1: 服务器授权 + 在线激活
- V2: 功能级授权 + 使用统计
- V3: 账号系统 + 支付集成

---

**文档版本：** V0.1  
**最后更新：** 2025-01-20  
**作者：** AutoGLM Team

