import React from 'react';

export default function ProgressBar({ status, progress, message, errorMsg, onReset }) {
    const isFailed = status === 'failed';
    
    return (
        <div className="animate-fade-in" style={{ textAlign: 'center', padding: '2rem 0' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '2rem', fontWeight: 700 }}>
                3. Tiến Trình Sản Xuất Video
            </h2>

            {/* Spinner hoặc Icon trạng thái */}
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '2rem' }}>
                {!isFailed ? (
                    <div style={{ position: 'relative', width: '120px', height: '120px' }}>
                        {/* Vòng xoay neon */}
                        <div 
                            style={{ 
                                width: '100%', 
                                height: '100%', 
                                borderRadius: '50%', 
                                border: '4px solid rgba(139, 92, 246, 0.1)', 
                                borderTopColor: 'var(--primary)', 
                                borderRightColor: 'var(--secondary)',
                                boxShadow: '0 0 15px rgba(6, 182, 212, 0.25), inset 0 0 15px rgba(139, 92, 246, 0.25)',
                                animation: 'spin 1.5s linear infinite' 
                            }} 
                        />
                        {/* Text phần trăm ở giữa */}
                        <div 
                            style={{ 
                                position: 'absolute', 
                                top: '50%', 
                                left: '50%', 
                                transform: 'translate(-50%, -50%)',
                                fontSize: '1.5rem',
                                fontWeight: 700,
                                color: 'var(--text-primary)'
                            }}
                        >
                            {progress}%
                        </div>
                    </div>
                ) : (
                    <div 
                        style={{ 
                            width: '90px', 
                            height: '90px', 
                            borderRadius: '50%', 
                            background: 'rgba(239, 68, 68, 0.1)', 
                            border: '2px solid var(--danger)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '2.5rem',
                            color: 'var(--danger)',
                            boxShadow: '0 0 15px rgba(239, 68, 68, 0.2)'
                        }}
                    >
                        ✗
                    </div>
                )}
            </div>

            {/* Thanh tiến trình */}
            <div style={{ maxWidth: '600px', margin: '0 auto 2rem', padding: '0 1rem' }}>
                <div 
                    style={{ 
                        height: '8px', 
                        width: '100%', 
                        background: 'rgba(255,255,255,0.06)', 
                        borderRadius: '9999px',
                        overflow: 'hidden',
                        position: 'relative'
                    }}
                >
                    <div 
                        style={{ 
                            height: '100%', 
                            width: `${progress}%`, 
                            background: isFailed ? 'var(--danger)' : 'linear-gradient(90deg, var(--primary) 0%, var(--secondary) 100%)',
                            borderRadius: '9999px',
                            transition: 'width 0.4s ease',
                            boxShadow: isFailed ? 'none' : '0 0 10px var(--secondary-glow)'
                        }}
                    />
                </div>
            </div>

            {/* Message log */}
            <div 
                style={{ 
                    background: 'rgba(0,0,0,0.2)', 
                    border: '1px solid var(--border-color)', 
                    borderRadius: '12px', 
                    padding: '1.5rem', 
                    maxWidth: '600px', 
                    margin: '0 auto',
                    textAlign: 'left'
                }}
            >
                <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
                    Nhật ký xử lý:
                </div>
                <div 
                    style={{ 
                        fontSize: '0.95rem', 
                        color: isFailed ? 'var(--danger)' : 'var(--text-primary)', 
                        fontWeight: 500,
                        lineHeight: '1.5'
                    }}
                >
                    {isFailed ? `Đã xảy ra lỗi: ${errorMsg || message}` : message}
                </div>
            </div>

            {/* Nút điều hướng chân trang */}
            <div style={{ marginTop: '2.5rem', display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                {isFailed && (
                    <button type="button" className="btn btn-primary" onClick={onReset} style={{ background: 'var(--danger)', color: '#fff', boxShadow: 'none' }}>
                        ◀ Thử lại cấu hình
                    </button>
                )}
                <button type="button" className="btn btn-secondary" onClick={onReset}>
                    🏠 Quay lại Bảng điều khiển
                </button>
            </div>
        </div>
    );
}
