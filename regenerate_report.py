from weibo_hotspot_analysis import WeiboHotspotAnalyzer

def main():
    print("Regenerating HTML report from existing history data...")
    analyzer = WeiboHotspotAnalyzer()
    output_path = analyzer.generate_html_report()
    print(f"Report regenerated at: {output_path}")

if __name__ == "__main__":
    main()
