
import sys
import os
from weibo_hotspot_analysis import WeiboHotspotAnalyzer
from config import Config

def test_douyin_fetch():
    print("=== Testing Douyin Data Fetching ===")
    analyzer = WeiboHotspotAnalyzer()
    
    # Force API usage
    try:
        print(f"Fetching from: {Config.DOUYIN_API_URL}")
        items = analyzer.fetch_hot_searches(source="douyin", use_api=True)
        print(f"Items fetched: {len(items)}")
        if items:
            print("First item sample:")
            print(items[0])
            
            # Test processing one item
            print("\nTesting single item processing...")
            result = analyzer._process_single_topic(items[0])
            print("Processing result keys:", result.keys())
            if "creatives" in result:
                print(f"Generated {len(result['creatives'])} creatives")
        else:
            print("No items returned from API")
            
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_douyin_fetch()
