#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
授权系统测试脚本
用于验证授权功能是否正常工作
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from license import LicenseManager, MachineIdGenerator
from datetime import datetime, timedelta


def TestMachineId():
    """测试机器码生成"""
    print("=" * 60)
    print("测试1: 机器码生成")
    print("=" * 60)
    
    machine_id = MachineIdGenerator.GetMachineId()
    print(f"✅ 机器码: {machine_id}")
    print(f"   长度: {len(machine_id)}")
    print()


def TestActivate():
    """测试授权激活"""
    print("=" * 60)
    print("测试2: 授权激活")
    print("=" * 60)
    
    data_dir = Path(__file__).parent
    manager = LicenseManager(data_dir)
    
    # 测试激活
    test_codes = [
        "AUTOGLM-TRIAL-TEST001",
        "AUTOGLM-1M-TEST002",
        "AUTOGLM-3M-TEST003",
    ]
    
    for code in test_codes:
        success, message = manager.Activate(code)
        if success:
            print(f"✅ 激活成功: {code}")
            print(f"   消息: {message}")
        else:
            print(f"❌ 激活失败: {code}")
            print(f"   消息: {message}")
        print()


def TestCheckLicense():
    """测试授权检查"""
    print("=" * 60)
    print("测试3: 授权检查")
    print("=" * 60)
    
    data_dir = Path(__file__).parent
    manager = LicenseManager(data_dir)
    
    is_valid, message, license_data = manager.CheckLicense()
    
    if is_valid:
        print(f"✅ 授权有效")
        print(f"   消息: {message}")
        if license_data:
            print(f"   授权码: {license_data.get('license_code')}")
            print(f"   到期时间: {license_data.get('expire_time')}")
    else:
        print(f"❌ 授权无效")
        print(f"   消息: {message}")
    print()


def TestLicenseInfo():
    """测试授权信息获取"""
    print("=" * 60)
    print("测试4: 授权信息获取")
    print("=" * 60)
    
    data_dir = Path(__file__).parent
    manager = LicenseManager(data_dir)
    
    info = manager.GetLicenseInfo()
    
    print(f"授权状态:")
    print(f"  是否有效: {info.get('is_valid')}")
    print(f"  消息: {info.get('message')}")
    print(f"  机器码: {info.get('machine_id')}")
    print(f"  已激活: {info.get('activated')}")
    
    if info.get('activated'):
        print(f"  授权码: {info.get('license_code')}")
        print(f"  激活时间: {info.get('activate_time')}")
        print(f"  到期时间: {info.get('expire_time')}")
        print(f"  剩余天数: {info.get('remaining_days')}")
    print()


def TestInvalidLicense():
    """测试无效授权码"""
    print("=" * 60)
    print("测试5: 无效授权码处理")
    print("=" * 60)
    
    data_dir = Path(__file__).parent
    manager = LicenseManager(data_dir)
    
    invalid_codes = [
        "INVALID-CODE",
        "AUTOGLM-INVALID-TEST",
        "AUTOGLM-1M-",  # 空代码
        "",  # 空字符串
    ]
    
    for code in invalid_codes:
        success, message = manager.Activate(code)
        print(f"授权码: {code or '(空)'}")
        if success:
            print(f"  ✅ 激活成功（意外）")
        else:
            print(f"  ❌ 激活失败（预期）: {message}")
        print()


def Main():
    """主函数"""
    print("\n" + "=" * 60)
    print("AutoGLM 授权系统测试")
    print("=" * 60 + "\n")
    
    try:
        TestMachineId()
        TestActivate()
        TestCheckLicense()
        TestLicenseInfo()
        TestInvalidLicense()
        
        print("=" * 60)
        print("✅ 所有测试完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    Main()

