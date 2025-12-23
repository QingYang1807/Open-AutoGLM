import React, { useState, useEffect } from 'react';
import { X, Key, Copy, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import { toast } from 'react-hot-toast';
import clsx from 'clsx';
import { useLanguage } from '../i18n/i18n.jsx';

export default function LicenseModal({ isOpen, onClose }) {
  const { t } = useLanguage();
  const [licenseCode, setLicenseCode] = useState('');
  const [licenseInfo, setLicenseInfo] = useState(null);
  const [machineId, setMachineId] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      LoadLicenseInfo();
      LoadMachineId();
    }
  }, [isOpen]);

  const LoadLicenseInfo = async () => {
    try {
      const res = await api.getLicenseInfo();
      if (res.success) {
        setLicenseInfo(res.info);
      }
    } catch (e) {
      console.error('Failed to load license info:', e);
    }
  };

  const LoadMachineId = async () => {
    try {
      const res = await api.getMachineId();
      if (res.success) {
        setMachineId(res.machine_id);
      }
    } catch (e) {
      console.error('Failed to load machine ID:', e);
    }
  };

  const HandleActivate = async () => {
    if (!licenseCode.trim()) {
      toast.error('请输入授权码');
      return;
    }

    setLoading(true);
    try {
      const res = await api.activateLicense(licenseCode.trim());
      if (res.success) {
        toast.success(res.message || '授权激活成功');
        setLicenseCode('');
        await LoadLicenseInfo();
        onClose();
      } else {
        toast.error(res.message || '激活失败');
      }
    } catch (e) {
      toast.error('激活失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const CopyMachineId = () => {
    if (machineId) {
      navigator.clipboard.writeText(machineId);
      setCopied(true);
      toast.success('机器码已复制');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (!isOpen) return null;

  const isActivated = licenseInfo?.activated;
  const isValid = licenseInfo?.is_valid;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-background-secondary border border-white/10 rounded-xl p-6 max-w-lg w-full mx-4 shadow-2xl max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-accent-primary/20 rounded-lg flex items-center justify-center">
              <Key size={20} className="text-accent-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-text-primary">授权管理</h3>
              <p className="text-xs text-text-muted">本地授权系统</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-text-muted hover:text-text-primary hover:bg-white/5 rounded transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* License Status */}
        {isActivated && (
          <div className={clsx(
            "mb-6 p-4 rounded-lg border",
            isValid
              ? "bg-status-success/10 border-status-success/20"
              : "bg-status-error/10 border-status-error/20"
          )}>
            <div className="flex items-start gap-3">
              {isValid ? (
                <CheckCircle size={20} className="text-status-success mt-0.5" />
              ) : (
                <XCircle size={20} className="text-status-error mt-0.5" />
              )}
              <div className="flex-1">
                <div className="font-medium text-text-primary mb-1">
                  {isValid ? '授权有效' : '授权无效'}
                </div>
                <div className="text-sm text-text-secondary space-y-1">
                  <div>授权码: {licenseInfo?.license_code || 'N/A'}</div>
                  {licenseInfo?.activate_time && (
                    <div>激活时间: {new Date(licenseInfo.activate_time).toLocaleString('zh-CN')}</div>
                  )}
                  {licenseInfo?.expire_time && (
                    <div>到期时间: {new Date(licenseInfo.expire_time).toLocaleString('zh-CN')}</div>
                  )}
                  {isValid && licenseInfo?.remaining_days !== undefined && (
                    <div className="text-status-success font-medium">
                      剩余天数: {licenseInfo.remaining_days} 天
                    </div>
                  )}
                  {!isValid && (
                    <div className="text-status-error font-medium">
                      {licenseInfo?.message || '授权已过期'}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Machine ID */}
        <div className="mb-6 p-4 bg-background-tertiary rounded-lg border border-white/5">
          <div className="text-xs font-medium text-text-muted mb-2">机器码</div>
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 bg-background-primary rounded text-sm font-mono text-text-primary border border-white/5">
              {machineId || '加载中...'}
            </code>
            <button
              onClick={CopyMachineId}
              className={clsx(
                "p-2 rounded transition-colors",
                copied
                  ? "bg-status-success/20 text-status-success"
                  : "bg-background-primary hover:bg-white/5 text-text-muted hover:text-text-primary border border-white/5"
              )}
              title="复制机器码"
            >
              {copied ? <CheckCircle size={16} /> : <Copy size={16} />}
            </button>
          </div>
          <div className="text-xs text-text-muted mt-2">
            授权码需要绑定此机器码，请妥善保管
          </div>
        </div>

        {/* Activation Form */}
        {!isActivated && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle size={16} className="text-status-error" />
              <div className="text-sm font-medium text-text-primary">未激活授权</div>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-text-muted mb-1.5">
                  授权码格式: AUTOGLM-{'{周期}'}-{'{代码}'}
                </label>
                <input
                  type="text"
                  value={licenseCode}
                  onChange={(e) => setLicenseCode(e.target.value.toUpperCase())}
                  placeholder="例如: AUTOGLM-1M-ABC123"
                  className="w-full px-3 py-2 bg-background-primary border border-white/10 rounded-lg text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !loading) {
                      HandleActivate();
                    }
                  }}
                />
                <div className="text-xs text-text-muted mt-1.5">
                  支持周期: trial(7天) / 1m(1月) / 3m(3月) / 6m(6月) / 1y(1年)
                </div>
              </div>
              <button
                onClick={HandleActivate}
                disabled={loading || !licenseCode.trim()}
                className="w-full bg-accent-primary hover:bg-accent-secondary text-white px-4 py-2 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '激活中...' : '激活授权'}
              </button>
            </div>
          </div>
        )}

        {/* Re-activate */}
        {isActivated && !isValid && (
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle size={16} className="text-status-error" />
              <div className="text-sm font-medium text-text-primary">授权已过期</div>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={licenseCode}
                onChange={(e) => setLicenseCode(e.target.value.toUpperCase())}
                placeholder="输入新的授权码"
                className="w-full px-3 py-2 bg-background-primary border border-white/10 rounded-lg text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-accent-primary/50"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !loading) {
                    HandleActivate();
                  }
                }}
              />
              <button
                onClick={HandleActivate}
                disabled={loading || !licenseCode.trim()}
                className="w-full bg-accent-primary hover:bg-accent-secondary text-white px-4 py-2 rounded-lg font-medium transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? '激活中...' : '重新激活'}
              </button>
            </div>
          </div>
        )}

        {/* Footer Info */}
        <div className="pt-4 border-t border-white/5">
          <div className="text-xs text-text-muted space-y-1">
            <div>• 授权码与机器码绑定，无法在其他设备使用</div>
            <div>• 检测到系统时间回拨将自动锁定授权</div>
            <div>• 授权数据已加密存储，请勿手动修改</div>
          </div>
        </div>
      </div>
    </div>
  );
}

