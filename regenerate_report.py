import os
import sys
from datetime import datetime, timedelta, timezone
from weibo_hotspot_analysis import WeiboHotspotAnalyzer, CHINA_TZ

def main():
    print("Regenerating HTML report from existing history data...")
    analyzer = WeiboHotspotAnalyzer()
    
    # Force report generation
    output_path = analyzer.generate_html_report()
    print(f"Done! Report regenerated at: {output_path}")

if __name__ == "__main__":
    main()
