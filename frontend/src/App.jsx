import React, { useState, useEffect, useRef } from 'react';
import Dashboard from './components/Dashboard';
import StepForm from './components/StepForm';
import ScriptEditor from './components/ScriptEditor';
import ProgressBar from './components/ProgressBar';
import VideoPreview from './components/VideoPreview';

const BACKEND_URL = "http://localhost:8000";

export default function App() {
    const [step, setStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [scriptData, setScriptData] = useState(null);
    const [taskId, setTaskId] = useState(null);
    const [renderStatus, setRenderStatus] = useState("processing");
    const [renderProgress, setRenderProgress] = useState(0);
    const [renderMessage, setRenderMessage] = useState("");
    const [videoUrl, setVideoUrl] = useState(null);
    const [errorMsg, setErrorMsg] = useState("");

    const pollingInterval = useRef(null);

    // Dọn dẹp interval khi unmount
    useEffect(() => {
        return () => {
            if (pollingInterval.current) clearInterval(pollingInterval.current);
        };
    }, []);

    // Bước 1 -> Bước 2: Sinh kịch bản từ Gemini
    const handleGenerateScript = async (formData) => {
        setLoading(true);
        setErrorMsg("");
        try {
            const response = await fetch(`${BACKEND_URL}/api/generate-script`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });
            
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Không thể sinh kịch bản!");
            }
            
            const data = await response.json();
            // Thêm seed vào dữ liệu kịch bản để gửi đi ở bước tiếp theo
            setScriptData({
                ...data,
                seed: formData.seed,
                voice_type: formData.voice_type
            });
            setStep(2);
        } catch (error) {
            console.error(error);
            alert(`Lỗi: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    // Bước 2 -> Bước 3: Gửi kịch bản đi render video
    const handleGenerateVideo = async (editedScript) => {
        setLoading(true);
        setErrorMsg("");
        try {
            const response = await fetch(`${BACKEND_URL}/api/generate-video`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(editedScript)
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Không thể khởi động render video!");
            }

            const data = await response.json();
            setTaskId(data.task_id);
            setRenderStatus("processing");
            setRenderProgress(0);
            setRenderMessage("Đang khởi tạo render...");
            setStep(3);
            
            // Bắt đầu gọi API thăm dò (polling) tiến độ render
            startPolling(data.task_id);
        } catch (error) {
            console.error(error);
            alert(`Lỗi: ${error.message}`);
        } finally {
            setLoading(false);
        }
    };

    // Polling API để lấy trạng thái render ngầm
    const startPolling = (tid) => {
        if (pollingInterval.current) clearInterval(pollingInterval.current);
        
        pollingInterval.current = setInterval(async () => {
            try {
                const response = await fetch(`${BACKEND_URL}/api/tasks/${tid}`);
                if (!response.ok) throw new Error("Không thể lấy trạng thái task!");
                
                const data = await response.json();
                setRenderStatus(data.status);
                setRenderProgress(data.progress || 0);
                setRenderMessage(data.message || "");
                
                if (data.status === 'completed') {
                    clearInterval(pollingInterval.current);
                    setVideoUrl(data.video_url);
                    setStep(4);
                } else if (data.status === 'failed') {
                    clearInterval(pollingInterval.current);
                    setErrorMsg(data.message);
                }
            } catch (error) {
                console.error("Lỗi polling: ", error);
                // Giữ nguyên trạng thái cũ, không ngắt loop ngay lập tức phòng lỗi mạng tạm thời
            }
        }, 2000); // Thăm dò mỗi 2 giây
    };

    const handleReset = () => {
        if (pollingInterval.current) clearInterval(pollingInterval.current);
        setStep(0);
        setScriptData(null);
        setTaskId(null);
        setRenderProgress(0);
        setRenderMessage("");
        setVideoUrl(null);
        setErrorMsg("");
    };

    const handleSelectProject = (project) => {
        if (project.status === 'completed') {
            setVideoUrl(project.video_url);
            setStep(4);
        } else if (project.status === 'processing') {
            setTaskId(project.task_id);
            setRenderStatus(project.status);
            setRenderProgress(project.progress || 0);
            setRenderMessage(project.message || "");
            setStep(3);
            startPolling(project.task_id);
        } else if (project.status === 'failed') {
            setRenderStatus(project.status);
            setRenderMessage(project.message || "");
            setErrorMsg(project.message || "Lỗi render");
            setStep(3);
        }
    };

    return (
        <div className="app-container">
            <header style={{ marginBottom: '2.5rem', textAlign: 'center' }}>
                <h1 className="app-title" style={{ cursor: 'pointer' }} onClick={handleReset}>Auto Video Generator</h1>
                <p className="app-subtitle">Tự động hóa kịch bản, giọng nói và dựng video AI</p>
            </header>

            {/* Nút quay lại Bảng điều khiển nếu không ở trang chủ */}
            {step !== 0 && (
                <div style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <button 
                        type="button" 
                        className="btn btn-secondary" 
                        onClick={handleReset}
                        style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}
                    >
                        🏠 Quay lại Bảng điều khiển
                    </button>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                        Đang thực hiện quy trình tạo video
                    </span>
                </div>
            )}

            {/* Chỉ báo các bước (Ẩn nếu ở Dashboard) */}
            {step !== 0 && (
                <div className="steps-indicator">
                    <div className={`step-indicator-item ${step === 1 ? 'active' : ''} ${step > 1 ? 'completed' : ''}`}>
                        <div className="step-number">1</div>
                        <span>Cấu hình</span>
                    </div>
                    <div className={`step-indicator-item ${step === 2 ? 'active' : ''} ${step > 2 ? 'completed' : ''}`}>
                        <div className="step-number">2</div>
                        <span>Kịch bản</span>
                    </div>
                    <div className={`step-indicator-item ${step === 3 ? 'active' : ''} ${step > 3 ? 'completed' : ''}`}>
                        <div className="step-number">3</div>
                        <span>Sản xuất</span>
                    </div>
                    <div className={`step-indicator-item ${step === 4 ? 'active' : ''} ${step > 4 ? 'completed' : ''}`}>
                        <div className="step-number">4</div>
                        <span>Thành phẩm</span>
                    </div>
                </div>
            )}

            {/* Phần hiển thị nội dung chính */}
            <main className="glass-card">
                {step === 0 && (
                    <Dashboard 
                        backendUrl={BACKEND_URL}
                        onSelectProject={handleSelectProject}
                        onCreateNew={() => setStep(1)}
                    />
                )}
                {step === 1 && (
                    <StepForm onSubmit={handleGenerateScript} loading={loading} backendUrl={BACKEND_URL} />
                )}
                {step === 2 && (
                    <ScriptEditor 
                        scriptData={scriptData} 
                        onBack={() => setStep(1)} 
                        onGenerateVideo={handleGenerateVideo}
                        loading={loading}
                    />
                )}
                {step === 3 && (
                    <ProgressBar 
                        status={renderStatus} 
                        progress={renderProgress} 
                        message={renderMessage} 
                        errorMsg={errorMsg}
                        onReset={handleReset}
                    />
                )}
                {step === 4 && (
                    <VideoPreview 
                        videoUrl={videoUrl} 
                        onReset={handleReset} 
                        backendUrl={BACKEND_URL}
                    />
                )}
            </main>
        </div>
    );
}
