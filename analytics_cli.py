import argparse
from src.analytics import export_monthly_analytics_csv


def main():
    parser = argparse.ArgumentParser(description="Export analytics data to CSV")
    parser.add_argument('--user', type=int, required=True, help='User ID')
    parser.add_argument('--output', default='analytics.csv', help='Output CSV file')
    args = parser.parse_args()

    export_monthly_analytics_csv(args.user, args.output)
    print(f"Analytics exported to {args.output}")


if __name__ == '__main__':
    main()
