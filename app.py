import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from weibo_hotspot_analysis import WeiboHotspotAnalyzer, Config

# Initialize Analyzer
analyzer = WeiboHotspotAnalyzer()

# Background Task
async def scheduled_analysis():
    print("Scheduler started.")
    while True:
        print("Starting scheduled analysis task...")
        try:
            # Run the synchronous analysis in a thread pool
            # 1. Fetch
            await asyncio.to_thread(analyzer.fetch_hot_searches, True) # use_api=True
            # 2. Analyze
            await asyncio.to_thread(analyzer.analyze_topics)
            # 3. Generate Report
            await asyncio.to_thread(analyzer.generate_html_report)
            print("Analysis task complete. Report updated.")
        except Exception as e:
            print(f"Error during scheduled analysis: {e}")
        
        # Wait for 1 hour (3600 seconds)
        print("Sleeping for 1 hour...")
        await asyncio.sleep(3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run analysis immediately on startup (background)
    task = asyncio.create_task(scheduled_analysis())
    yield
    # Cleanup if needed (task.cancel())

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def read_root():
    report_path = os.path.join(Config.OUTPUT_DIR, "weibo_analysis_report.html")
    
    if os.path.exists(report_path):
        return FileResponse(report_path)
    else:
        return HTMLResponse(
            content="""
            <html>
                <head><meta http-equiv="refresh" content="5"></head>
                <body>
                    <h1>正在生成首份报告...</h1>
                    <p>系统刚刚启动，正在抓取和分析数据，请稍等几分钟。</p>
                </body>
            </html>
            """, 
            status_code=202
        )

if __name__ == "__main__":
    import uvicorn
    # Local development
    uvicorn.run(app, host="0.0.0.0", port=8000)
