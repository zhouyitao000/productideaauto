经过检查 `config.py` 和 `providers.py` 文件，以下是当前代码中配置的 API 地址和大模型信息：

### 1. API 接口地址
*   **微博热搜 API**: `https://apis.tianapi.com/weibohot/index`
*   **抖音热搜 API**: `https://apis.tianapi.com/douyinhot/index`
*   **大模型 (LLM) API**: `https://api.deepseek.com` (DeepSeek 官方接口)
*   **Google 搜索 API (Serper)**: `https://google.serper.dev/search`

### 2. 大模型配置
*   **使用模型**: `deepseek-chat` (DeepSeek-V3)
*   **默认配置**: 如果没有在 `.env` 文件中特殊指定，系统默认使用上述 DeepSeek 配置。

### 3. 搜索工具配置
*   **当前默认**: `duckduckgo` (无需 API Key)
*   **可选支持**: `google` (需配置 Serper Key) 和 `baidu` (爬虫模式)

**结论**：代码已完全切换为使用 **DeepSeek** 进行创意分析，并且保留了天聚数行的热搜数据源。无需做任何修改，目前的配置符合您的要求。