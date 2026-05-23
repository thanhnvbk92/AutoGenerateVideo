import React, { useState, useEffect, useRef } from 'react';
import StepForm from './components/StepForm';
import ScriptEditor from './components/ScriptEditor';
import ProgressBar from './components/ProgressBar';
import VideoPreview from './components/VideoPreview';

const BACKEND_URL = "http://localhost:8000";

export default function App() {
    const [step, setStep] = useState(1);
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
        setStep(1);
        setScriptData(null);
        setTaskId(null);
        setRenderProgress(0);
        setRenderMessage("");
        setVideoUrl(null);
        setErrorMsg("");
    };

    return (
        <div className="app-container">
            <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
                <h1 className="app-title">Auto Video Generator</h1>
                <p className="app-subtitle">Tự động hóa kịch bản, giọng nói và dựng video AI</p>
            </header>

            {/* Chỉ báo các bước (Steps Indicator) */}
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

            {/* Phần hiển thị nội dung chính */}
            <main className="glass-card">
                {step === 1 && (
                    <StepForm onSubmit={handleGenerateScript} loading={loading} />
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
