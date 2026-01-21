# Weibo Hotspot Analysis Skill - Implementation Guide

## Overview
This document provides technical implementation details for the Weibo Hotspot Analysis skill. The skill fetches real-time Weibo hot search data, researches each topic via web search, generates product创意 ideas with scoring, and produces an HTML report.

## 1. API Integration

### 1.1 Endpoint Details
- **URL**: `https://apis.tianapi.com/weibohot/index?key=6e333e2407e88821ce16a6a8cba513e8`
- **Method**: GET
- **Authentication**: API key passed as query parameter
- **Response Format**: JSON with UTF-8 encoding

### 1.2 Response Structure
```json
{
  "code": 200,
  "msg": "success",
  "result": {
    "list": [
      {
        "hotword": "话题标题",
        "hotwordnum": "热度值",
        "hottag": "标签"
      }
    ]
  }
}
```

### 1.3 Data Processing
1. **Validate Response**: Check `code === 200`
2. **Extract Topics**: Get `result.list` array
3. **Limit Topics**: Select first 5 items for analysis
4. **Normalize Fields**:
   - `rank`: index + 1
   - `title`: `hotword`
   - `hot_value`: `hotwordnum` (may contain prefixes like "剧集 ")
   - `label`: `hottag` (may be empty string)

### 1.4 Error Handling
- **API Failure**: Fall back to example data (`example_data.json`)
- **Invalid Key**: Return error message to user
- **Rate Limiting**: Implement exponential backoff if needed

## 2. Web Search Strategy

### 2.1 Search Query Construction
For each hot search topic, construct Chinese search queries:
```
"{topic_title} 事件脉络 最新消息 背景 2026年"
```

Example: `"春节红包大战升级 事件脉络 最新消息 背景 2026年"`

### 2.2 Domain Filtering
Prefer Chinese news and social media domains:
- `sina.com.cn`
- `sohu.com`
- `baidu.com`
- `weibo.com`
- `zhihu.com`

### 2.3 Information Extraction
From search results, extract the following information for each topic:

1. **事件脉络 (Timeline)**: Key events in chronological order
2. **背景信息 (Background)**: Context and historical details
3. **关键人物 (Key Figures)**: Main individuals/organizations involved
4. **争议点 (Controversies)**: Points of debate or conflict
5. **公众反应 (Public Reaction)**: Sentiment and user comments
6. **相关趋势 (Related Trends)**: Sub-topics or emerging patterns

### 2.4 Search Result Processing
- Limit to 3-5 most relevant results per topic
- Synthesize information into a cohesive 150-200 word summary
- Include citations from search results where applicable

## 3. Product创意 Generation

### 3.1 Creative Framework
Each product创意 should follow this structure:

```
创意名称: [Descriptive, catchy name in Chinese]
核心功能:
- Feature 1: [Primary functionality]
- Feature 2: [Secondary functionality]
- Feature 3: [Optional additional feature]
目标用户: [Specific user demographic, behaviors, needs]
市场机会: [Brief market analysis - optional]
```

### 3.2 Scoring Methodology

#### Interesting Score (有趣度: 0-100)
评估娱乐性、情感共鸣、传播潜力:
- **90-100**: 高度娱乐性，病毒式传播潜力，强烈情感共鸣
- **80-89**: 有吸引力，易于分享，良好的娱乐价值
- **70-79**: 中等有趣，有一定吸引力
- **60-69**: 轻微有趣，吸引力有限
- **Below 60**: 缺乏娱乐性

#### Usefulness Score (有用度: 0-100)
评估实用性、问题解决能力、市场需求:
- **90-100**: 解决真实问题，明确市场需求，高实用性
- **80-89**: 满足真实需求，良好的实用价值
- **70-79**: 有一定用处，有限的问题解决能力
- **60-69**: 边际效用，小众应用
- **Below 60**: 几乎没有实用价值

#### Total Score Calculation
```
综合评分 = (有趣度 × 0.8) + (有用度 × 0.2)
```

### 3.3 Quality Classification
- **优秀 (Excellent)**: Total score ≥ 80 (绿色高亮)
- **良好 (Good)**: 60 ≤ Total score < 80 (黄色高亮)
- **需要改进 (Needs Improvement)**: Total score < 60 (红色高亮)

### 3.4 Justification Requirements
For each score, provide 1-2 sentence explanation:
- Why the有趣度 score was assigned
- Why the有用度 score was assigned
- Key strengths and weaknesses of the创意

## 4. HTML Report Generation

### 4.1 File Naming Convention
```
weibo_hotspot_analysis_YYYYMMDD_HHMM.html
```
Example: `weibo_hotspot_analysis_20260119_2345.html`

### 4.2 Template Structure
The HTML template (`html_template.html`) includes:

1. **Header**: Title, generation timestamp, data source
2. **Executive Summary**: Statistics and overview
3. **Topic Sections** (one per hot search):
   - Topic header with rank, title, label, hot value
   - 事件脉络 timeline
   - 热点详细信息 summary
   - Product创意 cards with scoring visualization
4. **Recommendations**: Top 3创意 with highest scores
5. **Methodology**: Scoring explanation
6. **Footer**: Generation info and disclaimer

### 4.3 CSS Styling Principles
- **简约专业**: Clean, professional, content-focused design
- **Color Coding**:
  - Green (#10b981) for 优秀
  - Yellow (#f59e0b) for 良好
  - Red (#ef4444) for 需要改进
- **Responsive Design**: Mobile-friendly with CSS grid/flexbox
- **Typography Hierarchy**: Clear heading levels and readable text

### 4.4 Dynamic Content Replacement
When generating the report:
1. Replace timestamp with current date/time
2. Replace topic data with actual API/web search results
3. Update summary statistics based on actual scores
4. Adjust score bars to reflect actual percentages
5. Set appropriate quality badges based on scores

## 5. Implementation Workflow

### 5.1 Step-by-Step Execution
1. **Fetch Data**: Call API or load example data
2. **Research Topics**: Web search for each topic (limit 5)
3. **Generate创意**: Create 1-2 product创意 per topic with scoring
4. **Calculate Statistics**: Compute averages, counts, distributions
5. **Generate HTML**: Populate template with actual data
6. **Save File**: Write HTML to disk with timestamped filename
7. **Present Results**: Show summary and file path to user

### 5.2 Performance Considerations
- Limit to top 5 topics to ensure timely completion
- Cache web search results if possible
- Use asynchronous processing for independent tasks
- Total execution time target: < 10 minutes

### 5.3 Error Recovery
- **API Failure**: Fall back to example data with clear warning
- **Web Search Failure**: Continue with available information, note limitations
- **File Write Failure**: Check permissions, suggest alternative location
- **Scoring Inconsistency**: Apply consistent criteria across all topics

## 6. Testing and Validation

### 6.1 Test Scenarios
1. **API Test**: Verify successful data retrieval
2. **Web Search Test**: Ensure relevant Chinese results
3. **Creative Generation Test**: Validate scoring consistency
4. **HTML Generation Test**: Check proper rendering in browsers
5. **Error Handling Test**: Verify fallback mechanisms work

### 6.2 Success Criteria
- HTML report generated with all 5 topics analyzed
- Each topic has至少 1 product创意 with proper scoring
- Report displays correct quality badges (优秀/良好)
- Chinese characters render properly in HTML
- Report follows简约专业 design principles
- Skill works end-to-end without manual intervention

## 7. Dependencies and Requirements

### 7.1 Required Tools
- **Bash**: For API calls with curl
- **WebSearch Tool**: For gathering background information
- **File Write Permissions**: For creating HTML files
- **JSON Parsing**: Built-in or via jq command

### 7.2 Skill Configuration
- API key embedded in SKILL.md instructions
- Example data file for fallback scenarios
- HTML template for report generation
- Scoring rubric for consistent evaluation

## 8. Future Enhancements
- **Multi-language Support**: Expand beyond Chinese content
- **Export Formats**: Add PDF, CSV, or Markdown exports
- **Advanced Analytics**: Sentiment analysis, trend prediction
- **Custom Templates**: Allow users to provide custom HTML templates
- **Batch Processing**: Analyze historical hot search data