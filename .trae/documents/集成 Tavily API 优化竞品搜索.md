您反馈的“竞品网站抓取不准”问题，通常是因为通用搜索引擎（如 DuckDuckGo）的排名算法更侧重内容相关性而非“产品相似性”。您提议使用的 **Tavily** 是专为 AI Agent 设计的搜索引擎，它在处理“类似产品”查询时效果通常更好。

我将按照您的要求，集成 Tavily API 来替换现有的搜索方案。

### 修改计划

#### 1. 安装依赖
在 `requirements.txt` 中添加 `tavily-python`。

#### 2. 更新配置 (`config.py`)
*   添加 `TAVILY_API_KEY` 配置项。
*   在 `SEARCH_PROVIDER` 选项中支持 `tavily`。

#### 3. 实现 `TavilySearchProvider` (`providers.py`)
创建一个新的搜索提供者类，封装 Tavily 的调用逻辑。
*   **输入**: 查询语句 (例如：`帮我搜索类似 {产品名} 的网页/软件/产品`)
*   **参数**: `search_depth="advanced"` (深度搜索模式)
*   **输出**: 统一格式的搜索结果列表 (`title`, `link`, `snippet`)

#### 4. 注册提供者 (`providers.py`)
修改 `get_search_provider` 函数，当配置为 `tavily` 时返回 `TavilySearchProvider` 实例。

#### 5. 调整主程序 (`weibo_hotspot_analysis.py`)
确保在竞品搜索环节，能够正确调用新的搜索逻辑。由于您之前还重构了 Prompt (CoT)，我将确保 Tavily 搜索与新的 Prompt 逻辑（生成的 `search_keywords`）无缝对接。

### 准备工作
请确保您拥有 Tavily 的 API Key。如果您还没有，可以在代码中先使用您示例中的 Key (`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`) 进行测试（**注意：示例 Key 可能已失效或有额度限制，建议替换为您自己的 Key**）。

接下来我将执行这些代码变更。