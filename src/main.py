from datetime import datetime

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"Daily Market Note started: {today}")

if __name__ == "__main__":
    main()
