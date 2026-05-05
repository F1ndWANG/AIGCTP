"use client";

export default function OfflinePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
      <div className="text-center max-w-sm">
        <div className="text-6xl mb-4">📡</div>
        <h1 className="text-xl font-bold text-gray-800 mb-2">网络连接已断开</h1>
        <p className="text-sm text-gray-500 mb-6">
          请检查网络连接后重试。部分历史数据在恢复连接后可用。
        </p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition"
        >
          重新连接
        </button>
      </div>
    </div>
  );
}
