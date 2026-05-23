import React, { useState } from 'react';

export default function ScriptEditor({ scriptData, onBack, onGenerateVideo, loading }) {
    const [title, setTitle] = useState(scriptData.title || "");
    const [scenes, setScenes] = useState(scriptData.scenes || []);

    const handleSceneChange = (index, field, value) => {
        const updatedScenes = [...scenes];
        updatedScenes[index] = {
            ...updatedScenes[index],
            [field]: value
        };
        setScenes(updatedScenes);
    };

    const handleSceneDelete = (index) => {
        if (scenes.length <= 1) return alert("Kịch bản phải có tối thiểu 1 phân cảnh!");
        const updatedScenes = scenes.filter((_, i) => i !== index);
        // Sắp xếp lại số thứ tự scene_number
        const reordered = updatedScenes.map((scene, i) => ({
            ...scene,
            scene_number: i + 1
        }));
        setScenes(reordered);
    };

    const handleAddScene = () => {
        const newSceneNum = scenes.length + 1;
        const newScene = {
            scene_number: newSceneNum,
            visual_prompt: scriptData.character_description + ", standing, looking forward, photorealistic, 8k",
            narration_text: "Đây là câu thoại thuyết minh của phân cảnh mới.",
            estimated_duration: 10
        };
        setScenes([...scenes, newScene]);
    };

    const handleSubmit = () => {
        if (!title.trim()) return alert("Vui lòng điền tiêu đề video!");
        onGenerateVideo({
            ...scriptData,
            title,
            scenes
        });
    };

    return (
        <div className="animate-fade-in">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>
                    2. Biên Tập Kịch Bản Phân Cảnh
                </h2>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button type="button" className="btn btn-secondary" onClick={onBack} disabled={loading}>
                        ◀ Quay lại
                    </button>
                    <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
                        {loading ? "Đang xử lý..." : "Bắt đầu tạo Video 🚀"}
                    </button>
                </div>
            </div>

            {/* Tiêu đề dự án */}
            <div className="form-group" style={{ background: 'rgba(255,255,255,0.02)', padding: '1.5rem', borderRadius: '12px', border: '1px solid var(--border-color)' }}>
                <label className="form-label" htmlFor="project-title" style={{ color: 'var(--primary)' }}>Tiêu Đề Video Thành Phẩm</label>
                <input
                    id="project-title"
                    type="text"
                    className="form-input"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Điền tên cho video của bạn..."
                    required
                />
                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    Tổng số phân cảnh: <b>{scenes.length}</b> | Ước tính thời lượng: <b>{Math.round((scenes.reduce((acc, curr) => acc + (curr.estimated_duration || 12), 0)) / 60)} phút</b>
                </div>
            </div>

            {/* Danh sách các scene */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '2rem' }}>
                {scenes.map((scene, index) => (
                    <div 
                        key={index} 
                        style={{ 
                            background: 'rgba(255, 255, 255, 0.01)', 
                            border: '1px solid var(--border-color)', 
                            borderRadius: '16px', 
                            padding: '1.5rem',
                            position: 'relative'
                        }}
                    >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <span className="badge" style={{ background: 'var(--primary-glow)', color: 'var(--primary)', border: '1px solid rgba(139, 92, 246, 0.2)', fontSize: '0.85rem', padding: '0.35rem 0.9rem' }}>
                                Phân cảnh #{scene.scene_number}
                            </span>
                            <button
                                type="button"
                                className="btn btn-secondary"
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem', color: 'var(--danger)', borderColor: 'rgba(239, 68, 68, 0.2)' }}
                                onClick={() => handleSceneDelete(index)}
                                disabled={loading}
                            >
                                Xóa Cảnh
                            </button>
                        </div>

                        {/* Lời thoại */}
                        <div className="form-group">
                            <label className="form-label">Lời thoại bình tiếng Việt (Voiceover text)</label>
                            <textarea
                                className="form-input"
                                style={{ minHeight: '60px' }}
                                value={scene.narration_text}
                                onChange={(e) => handleSceneChange(index, "narration_text", e.target.value)}
                                disabled={loading}
                            />
                        </div>

                        {/* Visual Prompt (tiếng Anh) */}
                        <div className="form-group" style={{ marginBottom: 0 }}>
                            <label className="form-label">Mô tả hình ảnh phục vụ AI vẽ (Visual Prompt bằng tiếng Anh)</label>
                            <textarea
                                className="form-input"
                                style={{ minHeight: '60px', borderColor: 'rgba(6, 182, 212, 0.3)' }}
                                value={scene.visual_prompt}
                                onChange={(e) => handleSceneChange(index, "visual_prompt", e.target.value)}
                                disabled={loading}
                            />
                            <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: '0.4rem' }}>
                                Luôn bắt đầu bằng mô tả nhân vật mặc định để giữ tính đồng nhất khuôn mặt.
                            </small>
                        </div>
                    </div>
                ))}
            </div>

            {/* Nút thêm phân cảnh */}
            <div style={{ textAlign: 'center', marginTop: '2rem' }}>
                <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ borderStyle: 'dashed', borderWidth: '2px', width: '100%', maxWidth: '300px' }}
                    onClick={handleAddScene}
                    disabled={loading}
                >
                    + Thêm Phân Cảnh Mới
                </button>
            </div>

            {/* Nút điều hướng chân trang */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '3rem', borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem' }}>
                <button type="button" className="btn btn-secondary" onClick={onBack} disabled={loading}>
                    ◀ Quay lại
                </button>
                <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={loading} style={{ minWidth: '180px' }}>
                    {loading ? "Đang xử lý..." : "Tạo Video Ngay 🚀"}
                </button>
            </div>
        </div>
    );
}
