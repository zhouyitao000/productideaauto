#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weibo & Douyin Hotspot Analysis Script
"""

import json
import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
import concurrent.futures
from config import Config
from providers import get_search_provider, get_llm_provider
import time
import shutil
from datetime import datetime, timedelta, timezone

# Constants
CHINA_TZ = timezone(timedelta(hours=8))
HISTORY_DATA_WEIBO_FILE = os.path.join(Config.BASE_DIR, "history_data.json")
HISTORY_DATA_DOUYIN_FILE = os.path.join(Config.BASE_DIR, "history_data_douyin.json")
HTML_TEMPLATE_FILE = os.path.join(Config.BASE_DIR, "html_template.html")

class WeiboHotspotAnalyzer:
    """Main analyzer class for Weibo and Douyin hot search data."""

    def __init__(self, api_key: str = Config.TIANAPI_KEY):
        self.api_key = api_key
        
        # Load histories
        self.history_weibo = self._load_history_data(HISTORY_DATA_WEIBO_FILE)
        self.history_douyin = self._load_history_data(HISTORY_DATA_DOUYIN_FILE)
        
        # Initialize providers
        self.search_provider = get_search_provider(Config)
        self.llm_provider = get_llm_provider(Config)
        
        print(f"Initialized with Search Provider: {type(self.search_provider).__name__}")
        print(f"Initialized with LLM Provider: {type(self.llm_provider).__name__}")

    def _load_history_data(self, filepath: str) -> List[Dict[str, Any]]:
        """Load historical data from JSON file."""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load history data from {filepath}: {e}")
                return []
        return []

    def _save_history_data(self, data: List[Dict], filepath: str):
        """Save updated history data to JSON file."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"History data saved to {filepath}")
        except Exception as e:
            print(f"Failed to save history data to {filepath}: {e}")

    def run_full_analysis_cycle(self, use_api: bool = True):
        """Run the full analysis cycle for both Weibo and Douyin."""
        print("\n=== Starting Full Analysis Cycle ===")
        
        # 1. Weibo Analysis
        print("--- Fetching & Analyzing Weibo Data ---")
        weibo_topics = self.fetch_hot_searches(source="weibo", use_api=use_api)
        if weibo_topics:
            self.analyze_topics(weibo_topics, source="weibo")
        
        # 2. Douyin Analysis
        print("--- Fetching & Analyzing Douyin Data ---")
        douyin_topics = self.fetch_hot_searches(source="douyin", use_api=use_api)
        if douyin_topics:
            self.analyze_topics(douyin_topics, source="douyin")
            
        # 3. Generate Report
        print("--- Generating Report ---")
        self.generate_html_report()
        print("=== Cycle Complete ===\n")

    def fetch_hot_searches(self, source: str = "weibo", use_api: bool = True) -> List[Dict[str, Any]]:
        """Fetch hot search data from API or example file."""
        if use_api:
            try:
                url = Config.WEIBO_API_URL if source == "weibo" else Config.DOUYIN_API_URL
                print(f"Calling TianAPI ({source}) with key: {self.api_key[:4]}***")
                
                response = requests.get(
                    url,
                    params={"key": self.api_key},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 200:
                    print(f"API returned error: {data.get('msg', 'Unknown error')}")
                    return self._load_example_data(source)

                # Extract and normalize data
                raw_items = data.get("result", {}).get("list", [])
                normalized_items = self._normalize_items(raw_items, source)
                print(f"Successfully fetched {len(normalized_items)} {source} items from API")
                return normalized_items

            except Exception as e:
                print(f"API call failed: {e}")
                print("Falling back to example data")
                return self._load_example_data(source)
        else:
            return self._load_example_data(source)

    def _load_example_data(self, source: str) -> List[Dict[str, Any]]:
        """Load example data (fallback)."""
        # For simplicity, returning dummy data if file not found or just dummy data
        return [
            {"rank": 1, "title": f"示例{source}话题1", "hot_value": "100万", "label": "热", "source": source},
            {"rank": 2, "title": f"示例{source}话题2", "hot_value": "80万", "label": "新", "source": source}
        ]

    def _normalize_items(self, raw_items: List[Dict], source: str) -> List[Dict[str, Any]]:
        """Normalize API response items."""
        normalized = []
        limit = Config.MAX_TOPICS
        for i, item in enumerate(raw_items[:limit]):
            if source == "weibo":
                normalized.append({
                    "rank": i + 1,
                    "title": item.get("hotword", ""),
                    "hot_value": item.get("hotwordnum", "").strip(),
                    "label": item.get("hottag", ""),
                    "source": "weibo"
                })
            elif source == "douyin":
                # TianAPI Douyin format assumption: word, hotindex
                hot_index = item.get("hotindex", 0)
                try:
                    hot_value_str = f"{int(hot_index) / 10000:.1f}万"
                except (ValueError, TypeError):
                    hot_value_str = str(hot_index)

                normalized.append({
                    "rank": i + 1,
                    "title": item.get("word", ""),
                    "hot_value": hot_value_str,
                    "label": "", # Douyin usually doesn't have tag
                    "source": "douyin"
                })
        return normalized

    def _process_single_topic(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single topic: Search -> LLM -> Result"""
        print(f"Processing {topic.get('source', 'unknown')} topic: {topic['title']}...")
        
        # 1. Search
        current_year = datetime.now(CHINA_TZ).year
        search_query = f"{topic['title']} {current_year}年 最新消息"
        search_results = self.search_provider.search(search_query)
        
        search_context = "\n".join([
            f"- Title: {r['title']}\n  Snippet: {r['snippet']}" 
            for r in search_results
        ])
        
        # 2. LLM Generation
        current_date_str = datetime.now(CHINA_TZ).strftime("%Y年%m月%d日")
        prompt = f"""
        当前日期是: {current_date_str}。
        请分析以下{topic.get('source', '微博')}热搜话题: "{topic['title']}".
        
        搜索结果:
        {search_context}
        
        任务:
        1. 总结事件关键细节（150字左右）。
        2. 基于该话题生成2个产品创意。
           **重要限制**: 创意必须是 **软件产品 (App/Web)**、**AI应用** 或 **AI解决方案**。不接受实体产品或纯营销活动。
           创意应侧重于如何利用 AI 技术解决用户痛点或提供娱乐价值。
        3. 基于有趣度（趣味性/传播潜力）和有用度（实用价值）对创意进行评分。
        4. 为每个创意提供一个用于搜索竞品的关键词（search_keywords），用于寻找市场上已有的类似产品。

        输出格式 (仅JSON):
        {{
            "research": {{
                "summary": "综合摘要 (150字左右)"
            }},
            "creatives": [
                {{
                    "name": "创意名称",
                    "features": ["功能点1", "功能点2"],
                    "target_users": "目标用户",
                    "scores": {{
                        "interest": 85,
                        "usefulness": 70
                    }},
                    "justification": {{
                        "interest": "有趣度评分理由",
                        "usefulness": "有用度评分理由"
                    }},
                    "search_keywords": "用于搜索竞品的关键词 (请提供具体的App类别或功能名称，不要用泛泛的词)"
                }}
            ]
        }}
        请确保所有生成的内容（摘要、创意名称、功能、理由等）都是中文。
        """
        
        try:
            llm_result = self.llm_provider.generate_json(prompt)
            
            # Post-process to add derived fields (total score, quality)
            creatives = llm_result.get("creatives", [])
            for i, creative in enumerate(creatives):
                creative["id"] = f"{topic['rank']}-{i+1}"
                
                # 3. Competitor Search (New Step)
                search_keywords = creative.get("search_keywords", creative["name"])
                print(f"  Searching competitors for '{creative['name']}' using keywords: '{search_keywords}'...")
                
                competitors = []
                try:
                    # Search for similar products - Use Chinese query to avoid English grammar results
                    # Previously "similar product app" caused dictionary lookups for "similar"
                    comp_query = f"{search_keywords} 类似App 竞品"
                    comp_results = self.search_provider.search(comp_query)
                    
                    # Take top 2 results, filtering out similarweb and dictionary/grammar sites
                    count = 0
                    for res in comp_results:
                        if count >= 2:
                            break
                        
                        link = res['link'].lower()
                        title = res['title'].lower()
                        
                        # Skip analytics tools
                        if "similarweb.com" in link or "similarweb" in title:
                            continue
                            
                        # Skip dictionary/grammar sites (common DDG issue with 'similar')
                        if any(x in link or x in title for x in ['dictionary', 'thesaurus', 'grammar', 'stackexchange', 'definition', 'meaning']):
                            continue
                            
                        competitors.append({
                            "name": res['title'],
                            "url": res['link']
                        })
                        count += 1
                except Exception as e:
                    print(f"  Competitor search failed: {e}")
                
                creative["competitors"] = competitors
                
                # Calculate total score
                scores = creative.get("scores", {})
                interest = scores.get("interest", 0)
                usefulness = scores.get("usefulness", 0)
                total = (interest * 0.8) + (usefulness * 0.2)
                scores["total"] = total
                
                # Determine quality (kept for internal logic, though removed from UI)
                if total >= 80:
                    creative["quality"] = "优秀"
                    creative["quality_class"] = "excellent"
                elif total >= 60:
                    creative["quality"] = "良好"
                    creative["quality_class"] = "good"
                else:
                    creative["quality"] = "需要改进"
                    creative["quality_class"] = "needs-improvement"

            return {
                "topic": topic,
                "research": llm_result.get("research", {"summary": "分析失败"}),
                "creatives": creatives
            }
            
        except Exception as e:
            print(f"Error processing topic {topic['title']}: {e}")
            return {
                "topic": topic,
                "research": {"timeline": [], "summary": "分析过程中发生错误"},
                "creatives": []
            }

    def analyze_topics(self, topics: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
        """Analyze topics using concurrency and update history."""
        if not topics:
            print(f"No {source} data available.")
            return []

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=Config.CONCURRENCY) as executor:
            future_to_topic = {
                executor.submit(self._process_single_topic, topic): topic 
                for topic in topics
            }
            
            for future in concurrent.futures.as_completed(future_to_topic):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Topic processing generated an exception: {e}")

        # Sort results by rank to maintain order
        results.sort(key=lambda x: x["topic"]["rank"])
        
        # Add to history
        # Use China Standard Time (UTC+8)
        current_time = datetime.now(CHINA_TZ)
        timestamp_hour = current_time.strftime("%Y-%m-%d %H:00")
        batch_entry = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_hour": timestamp_hour,
            "results": results
        }
        
        # Select correct history list and file
        if source == "weibo":
            history_list = self.history_weibo
            history_file = HISTORY_DATA_WEIBO_FILE
        else:
            history_list = self.history_douyin
            history_file = HISTORY_DATA_DOUYIN_FILE

        # Overwrite if same hour exists (latest update), else prepend
        if history_list and history_list[0].get("timestamp_hour") == timestamp_hour:
             print(f"Updating existing {source} data for hour: {timestamp_hour}")
             history_list[0] = batch_entry
        else:
             print(f"Adding new {source} data for hour: {timestamp_hour}")
             history_list.insert(0, batch_entry)

        # Keep only last 24 batches
        if len(history_list) > 24:
            history_list.pop() # Remove last
        
        self._save_history_data(history_list, history_file)
        
        return results

    def _generate_section_html(self, history_data: List[Dict], default_source: str = "unknown") -> str:
        """Helper to generate HTML for a specific history list."""
        if not history_data:
            return "<p>暂无数据</p>"

        all_batches_html = []
        for batch in history_data:
            batch_ts = batch["timestamp"]
            batch_ts_hour = batch["timestamp_hour"]
            batch_results = batch["results"]
            
            topic_sections = []
            for result in batch_results:
                topic = result["topic"]
                research = result["research"]
                creatives = result["creatives"]
                source_platform = topic.get('source', default_source)

                creatives_html = []
                for i, creative in enumerate(creatives):
                    features_html = "\n".join(f'<li>{f}</li>' for f in creative.get("features", []))
                    scores = creative.get("scores", {"interest": 0, "usefulness": 0, "total": 0})
                    
                    # Construct creative data for favorite function
                    creative_id = f"{source_platform}_{batch_ts_hour}_{topic['rank']}_{i}"
                    creative_data = {
                        "id": creative_id,
                        "source": source_platform,
                        "time": batch_ts,
                        "topic_title": topic['title'],
                        "hot_value": topic['hot_value'],
                        "name": creative.get('name', '未命名'),
                        "features": creative.get('features', []),
                        "target_users": creative.get('target_users', '未知'),
                        "scores": scores,
                        "competitors": creative.get("competitors", [])
                    }
                    creative_json = json.dumps(creative_data).replace('"', '&quot;').replace("'", "&#39;")
                    
                    competitors_html = ""
                    competitors = creative.get("competitors", [])
                    if competitors:
                        comp_links = []
                        for comp in competitors:
                            comp_links.append(f'<a href="{comp["url"]}" target="_blank" rel="noopener noreferrer">{comp["name"]}</a>')
                        competitors_html = f'''
                        <div class="competitors-section">
                            <strong>🔍 参考竞品:</strong> {", ".join(comp_links)}
                        </div>
                        '''

                    creative_html = f'''
                    <div class="creative-card" data-id="{creative_id}">
                        <div class="creative-header">
                            <h3 class="creative-name">{creative.get('name', '未命名')}</h3>
                            <button class="fav-btn" onclick="toggleFavorite(this, {creative_json})">
                                <span class="fav-icon">☆</span> 收藏
                            </button>
                        </div>
                        <div class="creative-features">
                            <ul>{features_html}</ul>
                        </div>
                        <div class="target-users">
                            <strong>目标用户:</strong> {creative.get('target_users', '未知')}
                        </div>
                        {competitors_html}
                        <div class="score-section">
                            <div class="score-breakdown">
                                <div class="score-bar">
                                    <div class="score-fill score-fill-interest" style="width: {scores.get('interest', 0)}%"></div>
                                </div>
                                <span>有趣度: {scores.get('interest', 0)}/100</span>
                            </div>
                            <div class="score-breakdown">
                                <div class="score-bar">
                                    <div class="score-fill score-fill-useful" style="width: {scores.get('usefulness', 0)}%"></div>
                                </div>
                                <span>有用度: {scores.get('usefulness', 0)}/100</span>
                            </div>
                            <div class="total-score">综合评分: {scores.get('total', 0):.1f}/100</div>
                        </div>
                    </div>
                    '''
                    creatives_html.append(creative_html)

                topic_label_html = f'<span class="topic-label">{topic["label"]}</span>' if topic.get("label") and topic["label"].strip() else ""
                
                topic_section = f'''
                <section class="topic-section">
                    <div class="topic-header">
                        <span class="topic-rank">{topic['rank']}</span>
                        <div style="flex-grow: 1;">
                            <h2 class="topic-title">{topic['title']}</h2>
                            {topic_label_html}
                            <span class="hot-value">🔥 {topic['hot_value']}</span>
                        </div>
                    </div>

                    <div class="summary-section">
                        <h4>热点详细信息</h4>
                        <p>{research.get('summary', '')}</p>
                    </div>

                    <div class="creative-section">
                        <h4>产品创意 (AI/软件)</h4>
                        <div class="creative-grid">
                            {"".join(creatives_html)}
                        </div>
                    </div>
                </section>
                '''
                topic_sections.append(topic_section)
            
            # Wrap in Batch Container
            batch_html = f'''
            <div class="data-batch" data-hour="{batch_ts_hour}">
                <div class="batch-header" style="margin: 2rem 0; padding-bottom: 0.5rem; border-bottom: 2px solid #e5e7eb;">
                    <h2 style="color: #4b5563;">数据时间: {batch_ts}</h2>
                </div>
                {"".join(topic_sections)}
            </div>
            '''
            all_batches_html.append(batch_html)
            
        return "\n".join(all_batches_html)

    def generate_html_report(self, output_dir: str = Config.OUTPUT_DIR) -> str:
        """Generate HTML report from analysis results."""
        if not self.history_weibo and not self.history_douyin:
            print("No analysis results available.")
            return ""

        try:
            with open(HTML_TEMPLATE_FILE, 'r', encoding='utf-8') as f:
                template = f.read()
        except FileNotFoundError:
            print(f"HTML template not found: {HTML_TEMPLATE_FILE}")
            return ""

        output_filename = "weibo_analysis_report.html"
        output_path = os.path.join(output_dir, output_filename)

        # 1. Generate Filter Options (Combine timestamps from both? Or just use Weibo as main?)
        # For simplicity, use all unique timestamps from both, sorted.
        timestamps = set()
        for batch in self.history_weibo:
            timestamps.add(batch["timestamp_hour"])
        for batch in self.history_douyin:
            timestamps.add(batch["timestamp_hour"])
        
        sorted_timestamps = sorted(list(timestamps), reverse=True)
        
        filter_options = []
        for ts_hour in sorted_timestamps:
            filter_options.append(f'<option value="{ts_hour}">{ts_hour}</option>')
        filter_options_html = "\n".join(filter_options)

        # 2. Generate Content for Weibo
        weibo_html = self._generate_section_html(self.history_weibo, default_source="weibo")
        
        # 3. Generate Content for Douyin
        douyin_html = self._generate_section_html(self.history_douyin, default_source="douyin")

        # 4. Generate Recommendations - REMOVED per user request
        
        # 5. Replace in template
        report_html = template
        # Use China Standard Time (UTC+8) for update time
        current_time = datetime.now(CHINA_TZ).strftime("%Y-%m-%d %H:%M:%S")
        
        report_html = report_html.replace('<!-- UPDATE_TIME_PLACEHOLDER -->', current_time)
        report_html = report_html.replace('<!-- FILTER_OPTIONS_PLACEHOLDER -->', filter_options_html)
        report_html = report_html.replace('<!-- WEIBO_CONTENT_PLACEHOLDER -->', weibo_html)
        report_html = report_html.replace('<!-- DOUYIN_CONTENT_PLACEHOLDER -->', douyin_html)
        # report_html = report_html.replace('<!-- RECOMMENDATIONS_PLACEHOLDER -->', recommendations_html) # Placeholder removed from template

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_html)

        print(f"HTML report generated: {output_path}")
        return output_path

def main():
    parser = argparse.ArgumentParser(description="Weibo & Douyin Hotspot Analysis Script")
    parser.add_argument("--api-key", default=Config.TIANAPI_KEY, help="API key for TianAPI")
    parser.add_argument("--output-dir", default=Config.OUTPUT_DIR, help="Output directory")
    parser.add_argument("--use-example", action="store_true", help="Use example data instead of API")
    parser.add_argument("--interval", type=int, default=0, help="Interval in seconds for loop mode (e.g. 3600 for 1 hour). 0 to run once.")
    args = parser.parse_args()

    # Update config if args provided
    if args.api_key:
        Config.TIANAPI_KEY = args.api_key
    if args.output_dir:
        Config.OUTPUT_DIR = args.output_dir

    analyzer = WeiboHotspotAnalyzer()
    
    if args.interval > 0:
        print(f"Starting scheduled mode. Running every {args.interval} seconds...")
        while True:
            try:
                print(f"\n--- Starting Analysis Batch at {datetime.now()} ---")
                analyzer.run_full_analysis_cycle(use_api=not args.use_example)
                print(f"--- Batch Complete. Sleeping for {args.interval}s ---")
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nStopped by user.")
                break
            except Exception as e:
                print(f"Error in loop: {e}")
                time.sleep(60) # Retry after 1 min on error
    else:
        analyzer.run_full_analysis_cycle(use_api=not args.use_example)

if __name__ == "__main__":
    main()
