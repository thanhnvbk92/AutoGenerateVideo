import React, { useState, useEffect } from 'react';

const CHARACTER_PRESETS = [
    {
        name: "Chàng trai công nghệ trẻ tuổi",
        desc: "A 25-year-old Vietnamese man, short wavy black hair, modern eyeglasses, wearing a clean black t-shirt, intelligent smile, photorealistic, 8k"
    },
    {
        name: "Cô gái Việt Nam áo dài truyền thống",
        desc: "A 22-year-old Vietnamese woman, long straight black hair, big friendly eyes, wearing a traditional white Ao Dai, smiling, photorealistic, 8k"
    },
    {
        name: "Nhà khoa học lớn tuổi thông thái",
        desc: "A 60-year-old Asian professor, neat grey hair, wrinkles around eyes showing wisdom, wearing a grey jacket, warm and academic look, 8k"
    }
];

export default function StepForm({ onSubmit, loading, backendUrl }) {
    const [topic, setTopic] = useState("");
    const [charDesc, setCharDesc] = useState(CHARACTER_PRESETS[0].desc);
    const [voice, setVoice] = useState("vi-VN-HoaiMyNeural");
    const [duration, setDuration] = useState(7);
    const [seed, setSeed] = useState(() => Math.floor(Math.random() * 1000000));
    const [useMusic, setUseMusic] = useState(true);
    const [bgMusic, setBgMusic] = useState("default_music.mp3");
    const [musicList, setMusicList] = useState(["default_music.mp3"]);

    // Lấy danh sách nhạc nền từ API
    useEffect(() => {
        const fetchMusicList = async () => {
            try {
                const res = await fetch(`${backendUrl || "http://localhost:8000"}/api/music-list`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.music_files && data.music_files.length > 0) {
                        setMusicList(data.music_files);
                        setBgMusic(data.music_files[0]);
                    }
                }
            } catch (err) {
                console.error("Lỗi khi tải danh sách nhạc:", err);
            }
        };
        fetchMusicList();
    }, [backendUrl]);

    const handlePresetSelect = (desc) => {
        setCharDesc(desc);
    };

    const handleRandomSeed = () => {
        setSeed(Math.floor(Math.random() * 1000000));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!topic.trim()) return alert("Vui lòng nhập chủ đề video!");
        if (!charDesc.trim()) return alert("Vui lòng nhập mô tả nhân vật!");
        onSubmit({
            topic,
            character_description: charDesc,
            voice_type: voice,
            duration_minutes: duration,
            seed,
            use_music: useMusic,
            bg_music_name: bgMusic
        });
    };

    return (
        <form onSubmit={handleSubmit} className="animate-fade-in">
            <h2 style={{ fontSize: '1.5rem', marginBottom: '1.5rem', fontWeight: 700 }}>
                1. Thiết Lập Dự Án
            </h2>

            {/* Chủ đề */}
            <div className="form-group">
                <label className="form-label" htmlFor="topic">Chủ đề Video hoặc Bài viết gốc</label>
                <textarea
                    id="topic"
                    className="form-input"
                    style={{ minHeight: '120px' }}
                    placeholder="Ví dụ: Bí ẩn của vũ trụ và hố đen khổng lồ, hoặc dán một bài báo/bài viết ngắn của bạn tại đây để AI biên soạn thành kịch bản..."
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    required
                />
            </div>

            {/* Mô tả nhân vật */}
            <div className="form-group">
                <label className="form-label" htmlFor="char-desc">Mô tả ngoại hình nhân vật chính (Giữ đồng nhất xuyên suốt video)</label>
                <textarea
                    id="char-desc"
                    className="form-input"
                    style={{ minHeight: '80px' }}
                    placeholder="Mô tả tuổi tác, giới tính, kiểu tóc, kính, trang phục..."
                    value={charDesc}
                    onChange={(e) => setCharDesc(e.target.value)}
                    required
                />
                
                {/* Preset gợi ý */}
                <div style={{ marginTop: '0.75rem' }}>
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>Gợi ý mẫu nhân vật:</span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.25rem' }}>
                        {CHARACTER_PRESETS.map((preset, index) => (
                            <button
                                key={index}
                                type="button"
                                className="btn btn-secondary"
                                style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', borderRadius: '8px' }}
                                onClick={() => handlePresetSelect(preset.desc)}
                            >
                                {preset.name}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="responsive-grid-2">
                {/* Giọng đọc */}
                <div className="form-group">
                    <label className="form-label" htmlFor="voice">Giọng đọc thuyết minh (Edge-TTS)</label>
                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                        <select
                            id="voice"
                            className="form-select"
                            value={voice}
                            onChange={(e) => setVoice(e.target.value)}
                            style={{ flex: 1 }}
                        >
                            <option value="vi-VN-HoaiMyNeural">Hoài Mỹ (Giọng Nữ VN cực mượt)</option>
                            <option value="vi-VN-NamMinhNeural">Nam Minh (Giọng Nam VN trầm ấm)</option>
                        </select>
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={async () => {
                                try {
                                    const audioUrl = `${backendUrl || "http://localhost:8000"}/api/preview-voice?voice=${voice}`;
                                    const audio = new Audio(audioUrl);
                                    await audio.play();
                                } catch (err) {
                                    alert("Không thể phát thử giọng đọc này!");
                                }
                            }}
                            style={{ whiteSpace: 'nowrap', padding: '0.8rem 1.2rem' }}
                        >
                            🔊 Nghe Thử
                        </button>
                    </div>
                </div>

                {/* Độ dài */}
                <div className="form-group">
                    <label className="form-label" htmlFor="duration">Thời lượng video mong muốn</label>
                    <select
                        id="duration"
                        className="form-select"
                        value={duration}
                        onChange={(e) => setDuration(Number(e.target.value))}
                    >
                        <option value={3}>Khoảng 3 phút (Dự án ngắn)</option>
                        <option value={5}>Khoảng 5 phút (Vừa phải)</option>
                        <option value={7}>Khoảng 7-8 phút (Yêu cầu của bạn)</option>
                        <option value={10}>Khoảng 10 phút (Dài)</option>
                    </select>
                </div>
            </div>

            {/* Nhạc nền */}
            <div className="responsive-grid-1-2" style={{ marginTop: '0.5rem', marginBottom: '1.5rem', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', height: '100%' }}>
                    <input
                        id="use-music"
                        type="checkbox"
                        checked={useMusic}
                        onChange={(e) => setUseMusic(e.target.checked)}
                        style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: 'var(--primary)' }}
                    />
                    <label className="form-label" htmlFor="use-music" style={{ margin: 0, cursor: 'pointer', userSelect: 'none' }}>
                        Sử dụng Nhạc nền
                    </label>
                </div>

                <div>
                    <label className="form-label" htmlFor="bg-music">Chọn bản nhạc nền</label>
                    <select
                        id="bg-music"
                        className="form-select"
                        value={bgMusic}
                        onChange={(e) => setBgMusic(e.target.value)}
                        disabled={!useMusic}
                    >
                        {musicList.map((file, idx) => (
                            <option key={idx} value={file}>
                                {file === 'default_music.mp3' ? 'Nhạc nền mặc định (Chill nhẹ)' : file}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Seed cho nhân vật */}
            <div className="form-group">
                <label className="form-label" htmlFor="seed">Seed cố định (Số ngẫu nhiên tạo ảnh đồng nhất)</label>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <input
                        id="seed"
                        type="number"
                        className="form-input"
                        value={seed}
                        onChange={(e) => setSeed(Number(e.target.value))}
                        required
                    />
                    <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={handleRandomSeed}
                    >
                        Làm Mới Seed
                    </button>
                </div>
                <small style={{ color: 'var(--text-muted)', display: 'block', marginTop: '0.4rem' }}>
                    Cùng một số Seed sẽ giúp gương mặt và phong cách nhân vật do AI vẽ ra giống nhau nhất ở các phân cảnh.
                </small>
            </div>

            {/* Nút gửi */}
            <div style={{ marginTop: '2.5rem', textAlign: 'right' }}>
                <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                    style={{ minWidth: '180px' }}
                >
                    {loading ? "Đang xử lý..." : "Bước tiếp theo: Tạo Kịch Bản ➜"}
                </button>
            </div>
        </form>
    );
}
