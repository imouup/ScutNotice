// 获取最后一次更新时间
window.onload = function() {
    // 后端API的地址，你需要替换成你自己的实际地址
    const apiUrl = 'https://scutnotice.nyaku.moe/lastUpdated';

    // 使用 fetch API 向后端请求数据
    fetch(apiUrl)
        .then(response => {
            // 检查请求是否成功
            if (!response.ok) {
                throw new Error('Network response was not ok ' + response.statusText);
            }
            // 将响应体解析为JSON格式
            return response.json();
        })
        .then(data => {
            // 获取用于显示更新时间的HTML元素
            const lastUpdatedElement = document.getElementById('last_update_time');
            // 将从后端获取的日期字符串转换为Date对象
            const lastUpdatedDate = new Date(data.lastUpdated);
            // 将日期格式化为本地可读的字符串，并更新到页面上
            lastUpdatedElement.textContent = lastUpdatedDate.toLocaleString('zh-CN');
        })
        .catch(error => {
            // 如果请求过程中发生任何错误，在控制台打印错误信息
            console.error('获取最后更新时间失败:', error);
            // 同时在页面上向用户显示加载失败
            const lastUpdatedElement = document.getElementById('last_update_time');
            lastUpdatedElement.textContent = '加载失败';
        });
};