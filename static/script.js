// 文件上傳處理
document.addEventListener('DOMContentLoaded', function() {
    // 文件上傳表單處理
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            // 處理上傳結果
        });
    }

    // 分析按鈕處理
    const analyzeBtn = document.getElementById('analyzeBtn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', async function() {
            const selectedFiles = []; // 獲取選中的文件
            const analysisMethod = document.querySelector('input[name="analysis_method"]:checked').value;
            
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    filenames: selectedFiles,
                    analysis_method: analysisMethod
                })
            });
            const result = await response.json();
            // 處理分析結果
        });
    }
});