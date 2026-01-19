import asyncio, httpx, sqlite3, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from aiolimiter import AsyncLimiter

# Config
USER_AGENT = "Name your@email.com"
limiter = AsyncLimiter(9, 1) # Stay under 10 req/sec

def setup_db():
    conn = sqlite3.connect("form4.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS form4 
        (ticker TEXT, owner TEXT, date TEXT, type TEXT, shares REAL, price REAL)''')
    return conn

async def get_xml(client, url):
    async with limiter:
        try:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            return resp.text if resp.status_code == 200 else None
        except: return None

def parse_and_save(conn, xml_str):
    try:
        root = ET.fromstring(xml_str)
        ticker = root.findtext(".//issuerTradingSymbol")
        owner = root.findtext(".//rptOwnerName")
        
        for tx in root.findall(".//nonDerivativeTransaction"):
            vals = (
                ticker, owner,
                tx.findtext(".//transactionDate/value"),
                tx.findtext(".//transactionAcquiredDisposedCode/value"),
                float(tx.findtext(".//transactionShares/value") or 0),
                float(tx.findtext(".//transactionPricePerShare/value") or 0)
            )
            print(vals)
            conn.execute("INSERT INTO form4 VALUES (?,?,?,?,?,?)", vals)
        conn.commit()
    except: pass

async def update_days(n_days):
    conn = setup_db()
    async with httpx.AsyncClient(timeout=10) as client:
        for i in range(n_days):
            date_dt = datetime.now() - timedelta(days=i)
            date_str = date_dt.strftime("%Y%m%d")
            year, qtr = date_str[:4], f"QTR{(date_dt.month-1)//3 + 1}"
            exists = conn.execute(" SELECT 1 FROM form4 WHERE date = ? LIMIT 1", (date_str,)).fetchone()
            if exists:
                print(f"Data for {date_str} already exists, skipping.")
                continue
            
            print(f"Checking {date_str}...")
            idx_url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/{qtr}/form.{date_str}.idx"
            idx_data = await get_xml(client, idx_url)
            
            if not idx_data: continue # Skip weekends/holidays

            # Find all Form 4 paths in the index
            xml_urls = []
            for line in idx_data.splitlines():
                if line.startswith("4  ") or line.startswith("4/A"):
                    path = line.split()[-1].replace("-", "").replace(".txt", "/form4.xml")
                    xml_urls.append(f"https://www.sec.gov/Archives/{path}")

            # Download and parse
            print(f"Found {len(xml_urls)} filings. Downloading...")
            tasks = [get_xml(client, u) for u in xml_urls]
            results = await asyncio.gather(*tasks)
            
            for xml in results:
                if xml: parse_and_save(conn, xml)
                
    conn.close()
    print("Done.")

def show_recent_trades(limit=10):
    conn = sqlite3.connect("form4.db")
    cursor = conn.cursor()
    
    # 1. Execute the query
    cursor.execute("SELECT * FROM form4 ORDER BY date DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    # 2. Print Header
    print(f"{'TICKER':<8} | {'TYPE':<5} | {'SHARES':<10} | {'PRICE':<8} | {'OWNER'}")
    print("-" * 60)
    
    # 3. Print Rows
    for r in rows:
        # r[0]=ticker, r[1]=owner, r[2]=date, r[3]=type, r[4]=shares, r[5]=price
        print(f"{r[0]:<8} | {r[3]:<5} | {r[4]:<10,.0f} | ${r[5]:<7.2f} | {r[1]}")
    
    conn.close()

if __name__ == "__main__":
    with open("data/")
    asyncio.run(update_days(4)) # Change 3 to however many days you want
    show_recent_trades(20)
