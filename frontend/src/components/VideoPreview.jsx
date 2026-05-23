import React from 'react';

export default function VideoPreview({ videoUrl, onReset, backendUrl }) {
    // Kết hợp đường dẫn API Backend nếu videoUrl không phải đường dẫn tuyệt đối
    const fullVideoUrl = videoUrl.startsWith('http') 
        ? videoUrl 
        : `${backendUrl}${videoUrl}`;
        
    return (
        <div className="animate-fade-in" style={{ textAlign: 'center' }}>
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem', fontWeight: 700 }}>
                4. Video Thành Phẩm Hoàn Thành!
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
                Video dài 7-8 phút của bạn với nhân vật đồng nhất đã được tạo hoàn chỉnh.
            </p>

            {/* Trình phát Video */}
            <div 
                style={{ 
                    maxWidth: '800px', 
                    margin: '0 auto 2.5rem', 
                    borderRadius: '16px', 
                    overflow: 'hidden', 
                    boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6), 0 0 30px var(--primary-glow)',
                    border: '1px solid var(--border-color)',
                    background: '#000'
                }}
            >
                <video 
                    src={fullVideoUrl} 
                    controls 
                    style={{ width: '100%', display: 'block' }}
                    preload="auto"
                >
                    Trình duyệt của bạn không hỗ trợ tag video.
                </video>
            </div>

            {/* Các nút hành động */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1.5rem' }}>
                <a 
                    href={fullVideoUrl} 
                    download="final_video.mp4" 
                    target="_blank" 
                    rel="noreferrer"
                    className="btn btn-primary"
                    style={{ minWidth: '180px', textDecoration: 'none' }}
                >
                    📥 Tải Video Về Máy
                </a>
                <button 
                    type="button" 
                    className="btn btn-secondary" 
                    onClick={onReset}
                    style={{ minWidth: '180px' }}
                >
                    🔄 Tạo Video Mới
                </button>
            </div>
        </div>
    );
}
