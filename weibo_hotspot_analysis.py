#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Weibo Hotspot Analysis Script (Optimized)
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

# Constants
API_URL = "https://apis.tianapi.com/weibohot/index"
EXAMPLE_DATA_FILE = os.path.join(Config.BASE_DIR, "example_data.json")
HISTORY_DATA_FILE = os.path.join(Config.BASE_DIR, "history_data.json")
HTML_TEMPLATE_FILE = os.path.join(Config.BASE_DIR, "html_template.html")

class WeiboHotspotAnalyzer:
    """Main analyzer class for Weibo hot search data."""

    def __init__(self, api_key: str = Config.TIANAPI_KEY):
        self.api_key = api_key
        self.hot_searches = []
        # self.analysis_results will now hold the current batch results
        self.analysis_results = []
        self.history_data = self._load_history_data()
        
        # Initialize providers
        self.search_provider = get_search_provider(Config)
        self.llm_provider = get_llm_provider(Config)
        
        print(f"Initialized with Search Provider: {type(self.search_provider).__name__}")
        print(f"Initialized with LLM Provider: {type(self.llm_provider).__name__}")

    def _load_history_data(self) -> List[Dict[str, Any]]:
        """Load historical data from JSON file."""
        if os.path.exists(HISTORY_DATA_FILE):
            try:
                with open(HISTORY_DATA_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Failed to load history data: {e}")
                return []
        return []

    def _save_history_data(self):
        """Save updated history data to JSON file."""
        try:
            with open(HISTORY_DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history_data, f, ensure_ascii=False, indent=2)
            print(f"History data saved to {HISTORY_DATA_FILE}")
        except Exception as e:
            print(f"Failed to save history data: {e}")

    def fetch_hot_searches(self, use_api: bool = True) -> List[Dict[str, Any]]:
        """Fetch Weibo hot search data from API or example file."""
        if use_api:
            try:
                print(f"Calling TianAPI with key: {self.api_key[:4]}***")
                response = requests.get(
                    API_URL,
                    params={"key": self.api_key},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") != 200:
                    print(f"API returned error: {data.get('msg', 'Unknown error')}")
                    return self._load_example_data()

                # Extract and normalize data
                raw_items = data.get("result", {}).get("list", [])
                self.hot_searches = self._normalize_items(raw_items)
                print(f"Successfully fetched {len(self.hot_searches)} hot search items from API")

            except Exception as e:
                print(f"API call failed: {e}")
                print("Falling back to example data")
                return self._load_example_data()
        else:
            self.hot_searches = self._load_example_data()

        return self.hot_searches

    def _load_example_data(self) -> List[Dict[str, Any]]:
        """Load example data from file."""
        try:
            with open(EXAMPLE_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)

            raw_items = data.get("result", {}).get("list", [])
            return self._normalize_items(raw_items)

        except Exception as e:
            print(f"Failed to load example data: {e}")
            return [
                {"rank": 1, "title": "示例话题", "hot_value": "100万", "label": "热"},
                {"rank": 2, "title": "测试话题", "hot_value": "80万", "label": "新"}
            ]

    def _normalize_items(self, raw_items: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize API response items."""
        normalized = []
        limit = Config.MAX_TOPICS
        for i, item in enumerate(raw_items[:limit]):
            normalized.append({
                "rank": i + 1,
                "title": item.get("hotword", ""),
                "hot_value": item.get("hotwordnum", "").strip(),
                "label": item.get("hottag", "")
            })
        return normalized

    def _process_single_topic(self, topic: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single topic: Search -> LLM -> Result"""
        print(f"Processing topic: {topic['title']}...")
        
        # 1. Search
        search_query = f"{topic['title']} {datetime.now().year}年 最新消息"
        search_results = self.search_provider.search(search_query)
        
        search_context = "\n".join([
            f"- Title: {r['title']}\n  Snippet: {r['snippet']}" 
            for r in search_results
        ])
        
        # 2. LLM Generation
        current_date_str = datetime.now().strftime("%Y年%m月%d日")
        prompt = f"""
        当前日期是: {current_date_str}。
        请分析以下微博热搜话题: "{topic['title']}".
        
        搜索结果:
        {search_context}
        
        任务:
        1. 总结事件关键细节（150字左右）。
        2. 基于该话题生成2个产品创意。
           **重要限制**: 创意必须是 **软件产品 (App/Web)**、**AI应用** 或 **AI解决方案**。不接受实体产品或纯营销活动。
           创意应侧重于如何利用 AI 技术解决用户痛点或提供娱乐价值。
        3. 基于有趣度（趣味性/传播潜力）和有用度（实用价值）对创意进行评分。
        
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
                    }}
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
                
                # Calculate total score
                scores = creative.get("scores", {})
                interest = scores.get("interest", 0)
                usefulness = scores.get("usefulness", 0)
                total = (interest * 0.8) + (usefulness * 0.2)
                scores["total"] = total
                
                # Determine quality
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

    def analyze_topics(self) -> List[Dict[str, Any]]:
        """Analyze all fetched topics using concurrency."""
        if not self.hot_searches:
            print("No hot search data available.")
            return []

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=Config.CONCURRENCY) as executor:
            future_to_topic = {
                executor.submit(self._process_single_topic, topic): topic 
                for topic in self.hot_searches
            }
            
            for future in concurrent.futures.as_completed(future_to_topic):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    print(f"Topic processing generated an exception: {e}")

        # Sort results by rank to maintain order
        results.sort(key=lambda x: x["topic"]["rank"])
        self.analysis_results = results
        
        # Add to history
        current_time = datetime.now()
        timestamp_hour = current_time.strftime("%Y-%m-%d %H:00")
        batch_entry = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp_hour": timestamp_hour,
            "results": results
        }
        
        # Overwrite if same hour exists (latest update), else prepend
        if self.history_data and self.history_data[0].get("timestamp_hour") == timestamp_hour:
             print(f"Updating existing data for hour: {timestamp_hour}")
             self.history_data[0] = batch_entry
        else:
             print(f"Adding new data for hour: {timestamp_hour}")
             self.history_data.insert(0, batch_entry)

        # Keep only last 24 batches (24 hours) to avoid file getting too large
        self.history_data = self.history_data[:24]
        
        self._save_history_data()
        
        return results

    def generate_html_report(self, output_dir: str = Config.OUTPUT_DIR) -> str:
        """Generate HTML report from analysis results."""
        if not self.history_data:
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

        # Generate Options for Filter
        filter_options = []
        for batch in self.history_data:
            ts_hour = batch["timestamp_hour"]
            filter_options.append(f'<option value="{ts_hour}">{ts_hour}</option>')
        filter_options_html = "\n".join(filter_options)

        # Build Main Content (All Batches)
        all_batches_html = []
        
        # We need to calculate global stats based on the LATEST batch for the summary cards
        latest_batch = self.history_data[0]
        latest_results = latest_batch["results"]
        
        all_creatives = [c for r in latest_results for c in r["creatives"]]
        total_creatives = len(all_creatives)
        excellent_count = sum(1 for c in all_creatives if c.get("quality_class") == "excellent")
        good_count = sum(1 for c in all_creatives if c.get("quality_class") == "good")
        
        all_scores = [c["scores"]["total"] for c in all_creatives]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        max_score = max(all_scores) if all_scores else 0

        for batch in self.history_data:
            batch_ts = batch["timestamp"]
            batch_ts_hour = batch["timestamp_hour"]
            batch_results = batch["results"]
            
            topic_sections = []
            for result in batch_results:
                topic = result["topic"]
                research = result["research"]
                creatives = result["creatives"]

                timeline_html = "" # Removed timeline
                
                creatives_html = []
                for creative in creatives:
                    features_html = "\n".join(f'<li>{f}</li>' for f in creative.get("features", []))
                    
                    scores = creative.get("scores", {"interest": 0, "usefulness": 0, "total": 0})
                    
                    creative_html = f'''
                    <div class="creative-card {creative.get('quality_class', 'needs-improvement')}">
                        <div class="creative-header">
                            <h3 class="creative-name">{creative.get('name', '未命名')}</h3>
                            <span class="quality-badge badge-{creative.get('quality_class', 'needs-improvement')}">{creative.get('quality', '未知')}</span>
                        </div>
                        <div class="creative-features">
                            <ul>{features_html}</ul>
                        </div>
                        <div class="target-users">
                            <strong>目标用户:</strong> {creative.get('target_users', '未知')}
                        </div>
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

                topic_section = f'''
                <section class="topic-section">
                    <div class="topic-header">
                        <span class="topic-rank">{topic['rank']}</span>
                        <div style="flex-grow: 1;">
                            <h2 class="topic-title">{topic['title']}</h2>
                            <span class="topic-label">{topic['label']}</span>
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

        # Build recommendations (From Latest Batch)
        sorted_creatives = sorted(
            [(c["scores"]["total"], c["name"], r["topic"]["title"]) for r in latest_results for c in r["creatives"]], 
            key=lambda x: x[0], 
            reverse=True
        )[:3]
        
        recommendations_html = "\n".join(
            f'''
            <div class="recommendation-item">
                <h4>{i+1}. {name} (综合评分: {score:.1f})</h4>
                <p>来自话题: {topic}</p>
            </div>
            '''
            for i, (score, name, topic) in enumerate(sorted_creatives)
        )

        # Replace in template
        report_html = template
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to replace placeholders first (assuming template is updated)
        if '<!-- FILTER_OPTIONS_PLACEHOLDER -->' in report_html:
            report_html = report_html.replace('<!-- FILTER_OPTIONS_PLACEHOLDER -->', filter_options_html)
        
        if '<!-- CONTENT_PLACEHOLDER -->' in report_html:
            report_html = report_html.replace('<!-- CONTENT_PLACEHOLDER -->', "\n".join(all_batches_html))
        else:
            # Fallback for old template structure (replace first topic-section block)
             example_section_start = report_html.find('<section class="topic-section">')
             if example_section_start != -1:
                 example_section_end = report_html.find('</section>', example_section_start) + 10
                 # Find end of all topic sections? We can replace until recommendations
                 # Better to rely on updated template.
                 # Let's assume we will update template.
                 pass

        # Update stats
        report_html = report_html.replace('<div class="value">3</div>', f'<div class="value">{excellent_count}</div>')
        report_html = report_html.replace('<div class="value">2</div>', f'<div class="value">{good_count}</div>')
        report_html = report_html.replace('<div class="value">78.4</div>', f'<div class="value">{avg_score:.1f}</div>')
        report_html = report_html.replace('<div class="value">92</div>', f'<div class="value">{max_score:.1f}</div>')
        
        # Inject Recommendations
        recommendations_start = report_html.find('<div class="recommendation-item">')
        if recommendations_start != -1:
             recommendations_end = report_html.find('</section>', recommendations_start)
             if recommendations_end != -1:
                 report_html = (
                    report_html[:recommendations_start] +
                    recommendations_html +
                    report_html[recommendations_end:]
                )

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_html)

        print(f"HTML report generated: {output_path}")
        return output_path

def main():
    parser = argparse.ArgumentParser(description="Weibo Hotspot Analysis Script")
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
                print("Fetching Weibo hot search data...")
                analyzer.fetch_hot_searches(use_api=not args.use_example)

                print("Analyzing topics and generating creatives (Concurrency Enabled)...")
                analyzer.analyze_topics()

                print("Generating HTML report...")
                analyzer.generate_html_report()
                
                print(f"--- Batch Complete. Sleeping for {args.interval}s ---")
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\nStopped by user.")
                break
            except Exception as e:
                print(f"Error in loop: {e}")
                time.sleep(60) # Retry after 1 min on error
    else:
        print("Fetching Weibo hot search data...")
        analyzer.fetch_hot_searches(use_api=not args.use_example)

        print("Analyzing topics and generating creatives (Concurrency Enabled)...")
        analyzer.analyze_topics()

        print("Generating HTML report...")
        output_path = analyzer.generate_html_report()

        if output_path:
            print(f"\nAnalysis complete! Report saved to: {output_path}")
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
