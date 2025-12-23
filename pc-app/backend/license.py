# -*- coding: utf-8 -*-
"""
AutoGLM 本地授权系统 V0
完全离线的软件授权控制机制
"""

import os
import json
import hashlib
import base64
import platform
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple


class LicenseError(Exception):
    """授权相关异常"""
    pass


class MachineIdGenerator:
    """机器码生成器"""
    
    @staticmethod
    def GetWindowsMachineId() -> str:
        """获取Windows机器码"""
        try:
            components = []
            
            # 1. CPU信息
            try:
                result = subprocess.run(
                    ['wmic', 'cpu', 'get', 'ProcessorId'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    cpu_id = result.stdout.strip().split('\n')[-1].strip()
                    if cpu_id:
                        components.append(f"CPU:{cpu_id}")
            except:
                pass
            
            # 2. 主板序列号
            try:
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'SerialNumber'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    board_sn = result.stdout.strip().split('\n')[-1].strip()
                    if board_sn and board_sn != "To be filled by O.E.M.":
                        components.append(f"BOARD:{board_sn}")
            except:
                pass
            
            # 3. 系统盘序列号
            try:
                result = subprocess.run(
                    ['wmic', 'logicaldisk', 'where', 'DeviceID="C:"', 'get', 'VolumeSerialNumber'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    disk_sn = result.stdout.strip().split('\n')[-1].strip()
                    if disk_sn:
                        components.append(f"DISK:{disk_sn}")
            except:
                pass
            
            # 4. 计算机名
            try:
                computer_name = platform.node()
                if computer_name:
                    components.append(f"NAME:{computer_name}")
            except:
                pass
            
            # 5. MAC地址(第一个网络适配器)
            try:
                result = subprocess.run(
                    ['getmac', '/fo', 'csv', '/nh'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if lines and len(lines) > 0:
                        mac = lines[0].split(',')[0].strip().replace('-', '')
                        if mac and mac != "N/A":
                            components.append(f"MAC:{mac}")
            except:
                pass
            
            if not components:
                # 降级方案: 使用计算机名和用户名
                components.append(f"NAME:{platform.node()}")
                components.append(f"USER:{os.getenv('USERNAME', 'UNKNOWN')}")
            
            # 生成机器码
            machine_string = "|".join(components)
            machine_id = hashlib.sha256(machine_string.encode('utf-8')).hexdigest()[:16].upper()
            return machine_id
            
        except Exception as e:
            # 最后的降级方案
            fallback = f"{platform.node()}{os.getenv('USERNAME', 'UNKNOWN')}"
            return hashlib.sha256(fallback.encode('utf-8')).hexdigest()[:16].upper()
    
    @staticmethod
    def GetMachineId() -> str:
        """获取当前机器的机器码"""
        if platform.system() == "Windows":
            return MachineIdGenerator.GetWindowsMachineId()
        else:
            # Linux/Mac 降级方案
            fallback = f"{platform.node()}{os.getenv('USER', 'UNKNOWN')}"
            return hashlib.sha256(fallback.encode('utf-8')).hexdigest()[:16].upper()


class LicenseManager:
    """授权管理器"""
    
    # 授权周期定义(天数)
    DURATION_DAYS = {
        "trial": 7,      # 体验版 7天
        "1m": 30,        # 1个月
        "3m": 90,        # 3个月
        "6m": 180,       # 6个月
        "1y": 365,       # 1年
    }
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.license_file = data_dir / "license.json"
        self.machine_id = MachineIdGenerator.GetMachineId()
        
    def _LoadLicense(self) -> Optional[Dict]:
        """加载授权文件"""
        if not self.license_file.exists():
            return None
        
        try:
            with open(self.license_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Base64解码授权数据
            if 'data' in data:
                encoded = data['data']
                decoded = base64.b64decode(encoded).decode('utf-8')
                license_data = json.loads(decoded)
                return license_data
            
            # 兼容旧格式(未加密)
            return data
        except Exception as e:
            print(f"[License] 加载授权文件失败: {e}")
            return None
    
    def _SaveLicense(self, license_data: Dict):
        """保存授权文件(加密)"""
        try:
            # Base64编码授权数据
            json_str = json.dumps(license_data, ensure_ascii=False)
            encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            
            # 添加校验和
            checksum = hashlib.md5(f"{encoded}{self.machine_id}".encode('utf-8')).hexdigest()
            
            save_data = {
                "data": encoded,
                "checksum": checksum,
                "version": "1.0"
            }
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise LicenseError(f"保存授权文件失败: {e}")
    
    def _ValidateChecksum(self, license_data: Dict, checksum: str) -> bool:
        """验证校验和"""
        try:
            json_str = json.dumps(license_data, ensure_ascii=False)
            encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            expected_checksum = hashlib.md5(f"{encoded}{self.machine_id}".encode('utf-8')).hexdigest()
            return expected_checksum == checksum
        except:
            return False
    
    def Activate(self, license_code: str) -> Tuple[bool, str]:
        """
        激活授权码
        
        Args:
            license_code: 授权码格式: AUTOGLM-{DURATION}-{CODE}
                        例如: AUTOGLM-1M-ABC123
            
        Returns:
            (成功标志, 消息)
        """
        try:
            # 解析授权码
            parts = license_code.upper().split('-')
            if len(parts) != 3 or parts[0] != 'AUTOGLM':
                return False, "授权码格式错误，应为: AUTOGLM-{周期}-{代码}"
            
            duration_key = parts[1]
            if duration_key not in self.DURATION_DAYS:
                return False, f"无效的授权周期: {duration_key}，支持: trial/1m/3m/6m/1y"
            
            duration_days = self.DURATION_DAYS[duration_key]
            code = parts[2]
            
            # 验证授权码(简单校验，V0阶段)
            # 实际应用中，这里应该验证授权码的有效性(如与服务器校验)
            # V0阶段: 简单格式校验即可
            
            # 计算到期时间
            activate_time = datetime.now()
            expire_time = activate_time + timedelta(days=duration_days)
            
            # 保存授权信息
            license_data = {
                "license_code": license_code.upper(),
                "machine_id": self.machine_id,
                "activate_time": activate_time.isoformat(),
                "expire_time": expire_time.isoformat(),
                "duration_days": duration_days,
                "last_check_time": activate_time.isoformat(),
            }
            
            self._SaveLicense(license_data)
            
            return True, f"授权激活成功！到期时间: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}"
            
        except Exception as e:
            return False, f"激活失败: {str(e)}"
    
    def CheckLicense(self) -> Tuple[bool, str, Optional[Dict]]:
        """
        检查授权状态
        
        Returns:
            (是否有效, 消息, 授权信息)
        """
        license_data = self._LoadLicense()
        
        if not license_data:
            return False, "未激活授权", None
        
        try:
            # 验证机器码绑定
            if license_data.get('machine_id') != self.machine_id:
                return False, "授权码与当前设备不匹配", None
            
            # 检查时间回拨
            last_check_time_str = license_data.get('last_check_time')
            if last_check_time_str:
                last_check_time = datetime.fromisoformat(last_check_time_str)
                current_time = datetime.now()
                
                # 检测时间倒退(允许5分钟误差)
                if current_time < last_check_time - timedelta(minutes=5):
                    return False, "检测到系统时间被回拨，授权已锁定", None
                
                # 更新最后检查时间
                license_data['last_check_time'] = current_time.isoformat()
                self._SaveLicense(license_data)
            
            # 检查是否过期
            expire_time_str = license_data.get('expire_time')
            if not expire_time_str:
                return False, "授权数据损坏", None
            
            expire_time = datetime.fromisoformat(expire_time_str)
            current_time = datetime.now()
            
            if current_time >= expire_time:
                remaining_days = 0
                return False, f"授权已过期 (到期时间: {expire_time.strftime('%Y-%m-%d %H:%M:%S')})", license_data
            
            # 计算剩余天数
            remaining = expire_time - current_time
            remaining_days = remaining.days
            
            return True, f"授权有效，剩余 {remaining_days} 天", license_data
            
        except Exception as e:
            return False, f"授权检查失败: {str(e)}", None
    
    def GetLicenseInfo(self) -> Dict:
        """获取授权信息(用于显示)"""
        is_valid, message, license_data = self.CheckLicense()
        
        info = {
            "is_valid": is_valid,
            "message": message,
            "machine_id": self.machine_id,
            "activated": license_data is not None,
        }
        
        if license_data:
            info.update({
                "license_code": license_data.get('license_code', ''),
                "activate_time": license_data.get('activate_time', ''),
                "expire_time": license_data.get('expire_time', ''),
                "duration_days": license_data.get('duration_days', 0),
            })
            
            # 计算剩余天数
            if is_valid:
                expire_time = datetime.fromisoformat(license_data['expire_time'])
                remaining = expire_time - datetime.now()
                info["remaining_days"] = remaining.days
            else:
                info["remaining_days"] = 0
        else:
            info.update({
                "license_code": "",
                "activate_time": "",
                "expire_time": "",
                "duration_days": 0,
                "remaining_days": 0,
            })
        
        return info
    
    def IsValid(self) -> bool:
        """快速检查授权是否有效"""
        is_valid, _, _ = self.CheckLicense()
        return is_valid

