import React, { useState, useEffect } from 'react';

export default function Dashboard({ backendUrl, onSelectProject, onCreateNew }) {
    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchProjects = async () => {
        try {
            const res = await fetch(`${backendUrl || "http://localhost:8000"}/api/projects`);
            if (res.ok) {
                const data = await res.json();
                setProjects(data.projects || []);
            }
        } catch (err) {
            console.error("Lỗi khi tải danh sách dự án:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
        // Tự động reload danh sách mỗi 10 giây để cập nhật tiến độ các task đang chạy
        const interval = setInterval(fetchProjects, 10000);
        return () => clearInterval(interval);
    }, [backendUrl]);

    const formatTime = (timestamp) => {
        if (!timestamp) return "-";
        const date = new Date(timestamp * 1000);
        return date.toLocaleString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    };

    return (
        <div className="animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.75rem', fontWeight: 800, background: 'linear-gradient(135deg, #fff 0%, var(--primary) 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    🗃️ Bảng Điều Khiển Dự Án
                </h2>
                <button 
                    type="button" 
                    className="btn btn-primary" 
                    onClick={onCreateNew}
                    style={{ gap: '0.5rem', padding: '0.8rem 1.5rem' }}
                >
                    ➕ Tạo Dự Án Mới
                </button>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-secondary)' }}>
                    Đang tải danh sách dự án...
                </div>
            ) : projects.length === 0 ? (
                <div style={{ 
                    textAlign: 'center', 
                    padding: '4rem 2rem', 
                    background: 'rgba(255,255,255,0.01)', 
                    border: '1px dashed var(--border-color)', 
                    borderRadius: '16px',
                    color: 'var(--text-secondary)'
                }}>
                    <p style={{ fontSize: '1.1rem', marginBottom: '1.5rem' }}>Bạn chưa có dự án tạo video nào.</p>
                    <button type="button" className="btn btn-primary" onClick={onCreateNew}>
                        Bắt đầu tạo ngay phân cảnh đầu tiên!
                    </button>
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {projects.map((project) => {
                        const isCompleted = project.status === 'completed';
                        const isFailed = project.status === 'failed';
                        const isProcessing = project.status === 'processing';
                        
                        return (
                            <div 
                                key={project.task_id}
                                className={`project-card ${isProcessing ? 'processing' : ''}`}
                                onClick={() => onSelectProject(project)}
                            >
                                {/* Cột thông tin dự án */}
                                <div style={{ flex: '1 1 250px' }}>
                                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.4rem', color: '#fff' }}>
                                        {project.title || `Dự án #${project.task_id.substring(0, 8)}`}
                                    </h3>
                                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                        Cập nhật: {formatTime(project.last_updated)}
                                    </p>
                                </div>

                                {/* Cột trạng thái */}
                                <div style={{ flex: '1 1 180px', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <span 
                                            className={`badge ${isCompleted ? 'badge-success' : isFailed ? 'badge-danger' : 'badge-primary'}`}
                                            style={{
                                                fontSize: '0.8rem',
                                                padding: '0.25rem 0.65rem'
                                            }}
                                        >
                                            {isCompleted ? '✓ Hoàn thành' : isFailed ? '✗ Thất bại' : '⚡ Đang render'}
                                        </span>
                                        {isProcessing && (
                                            <span style={{ fontSize: '0.85rem', fontWeight: 'bold', color: 'var(--primary)' }}>
                                                {project.progress || 0}%
                                            </span>
                                        )}
                                    </div>
                                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '220px' }}>
                                        {project.message || "Không có log."}
                                    </p>
                                </div>

                                {/* Thanh tiến trình nhỏ đối với task đang chạy */}
                                {isProcessing && (
                                    <div style={{ width: '100px', height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '2px', overflow: 'hidden' }}>
                                        <div style={{ width: `${project.progress || 0}%`, height: '100%', background: 'var(--primary)', borderRadius: '2px' }} />
                                    </div>
                                )}

                                {/* Nút hành động */}
                                <div style={{ display: 'flex', gap: '0.75rem' }}>
                                    {isCompleted ? (
                                        <button 
                                            type="button" 
                                            className="btn btn-secondary" 
                                            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', borderColor: 'var(--success)', color: 'var(--success)' }}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onSelectProject(project);
                                            }}
                                        >
                                            ▶ Xem Video
                                        </button>
                                    ) : isProcessing ? (
                                        <button 
                                            type="button" 
                                            className="btn btn-secondary" 
                                            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', borderColor: 'var(--primary)', color: 'var(--primary)' }}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onSelectProject(project);
                                            }}
                                        >
                                            ⚙ Theo Dõi
                                        </button>
                                    ) : (
                                        <button 
                                            type="button" 
                                            className="btn btn-secondary" 
                                            style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', borderColor: 'var(--danger)', color: 'var(--danger)' }}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onSelectProject(project);
                                            }}
                                        >
                                            ℹ Xem Chi Tiết
                                        </button>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
