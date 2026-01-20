import pandas as pd
import asyncio, httpx, sqlite3, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from aiolimiter import AsyncLimiter
import re
# Config
USER_AGENT = "Leo leo@gmail.com"
limiter = AsyncLimiter(9, 1) # Stay under 10 req/sec

def setup_db():
    conn = sqlite3.connect("../data.db")
    conn.execute('''CREATE TABLE IF NOT EXISTS form4 
        (ticker TEXT, owner TEXT, date TEXT, type TEXT, shares REAL, price REAL)''')
    return conn

async def get_xml(client, url):
    async with limiter:
        headers = {
            "User-Agent": "Leo leo@gmail.com", 
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov"
        }
        try:
            resp = await client.get(url, headers=headers, follow_redirects=True)
            
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"No data for URL")
                return None
        except Exception as e:
            print(f"Request Error: {e}")
            return None
def parse_and_save(conn, raw_str, date_str):
    try:
        m = re.search(r'<ownershipDocument>(.*?)</ownershipDocument>', raw_str, re.DOTALL)
        if not m:
            m = re.search(r'<XML>(.*?)</XML>', raw_str, re.DOTALL)
        if not m: return

        xml_content = f"<ownershipDocument>{m.group(1)}</ownershipDocument>".replace("& ", "&amp; ")
        root = ET.fromstring(xml_content)
        
        ticker = root.findtext(".//issuerTradingSymbol")
        owner = root.findtext(".//rptOwnerName")
        
        for tx in root.findall(".//nonDerivativeTransaction"):
            shares = tx.findtext(".//transactionShares/value") or "0"
            price = tx.findtext(".//transactionPricePerShare/value") or "0"
            code = tx.findtext(".//transactionAcquiredDisposedCode/value") or ""
            
            conn.execute("INSERT INTO form4 VALUES (?,?,?,?,?,?)", 
                         (ticker, owner, date_str, code, float(shares), float(price)))
        conn.commit()
    except Exception as e:
        print(f"Error: {e}")
        


async def update_days(n_days, CIKs=None):
    # Ensure CIKs are strings and padded to 10 digits
    if CIKs:
        CIKs = [str(c).zfill(10) for c in CIKs]

    conn = setup_db()
    async with httpx.AsyncClient(timeout=20) as client:
        for i in range(n_days):
            date_dt = datetime.now() - timedelta(days=i)
            date_str = date_dt.strftime("%Y%m%d")
            year, qtr = date_str[:4], f"QTR{(date_dt.month-1)//3 + 1}"
            
            # Check if we already processed this index date
            exists = conn.execute("SELECT 1 FROM form4 WHERE date = ? LIMIT 1", (date_str,)).fetchone()
            if exists:
                print(f"Data for {date_str} already exists.")
                continue
            
            idx_url = f"https://www.sec.gov/Archives/edgar/daily-index/{year}/{qtr}/form.{date_str}.idx"
            idx_data = await get_xml(client, idx_url)
            if not idx_data: continue 

            xml_urls = []
            for line in idx_data.splitlines():
                if line.startswith("4  ") or line.startswith("4/A"):
                    parts = line.split()
                    path = parts[-1]
                    cik = parts[-3].zfill(10)
                    
                    if CIKs is None or cik in CIKs:
                        xml_urls.append(f"https://www.sec.gov/Archives/{path}")

            if not xml_urls: continue
            print(f"Found {len(xml_urls)} filings for {date_str}. Downloading...")
            
            for i in range(0, len(xml_urls), 10):
                chunk = xml_urls[i:i+10]
                tasks = [get_xml(client, u) for u in chunk]
                results = await asyncio.gather(*tasks)
                
                for raw_text in results:
                    if raw_text: parse_and_save(conn, raw_text, date_str)
                
    conn.close()
    print("Done.")

def show_recent_trades(limit=10):
    conn = sqlite3.connect("../data.db")
    cursor = conn.cursor()
    
    # 1. Execute the query
    cursor.execute("SELECT * FROM form4 WHERE TYPE == 'A' ORDER BY date DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    
    # 2. Print Header
    print(f"{'TICKER':<8} | {'DATE':<8} | {'TYPE':<5} | {'SHARES':<10} | {'PRICE':<8} | {'OWNER'}")
    print("-" * 60)
    
    # 3. Print Rows
    for r in rows:
        # r[0]=ticker, r[1]=owner, r[2]=date, r[3]=type, r[4]=shares, r[5]=price
        print(f"{r[0]:<8} | {r[2]:<8} | {r[3]:<5} | {r[4]:<10,.0f} | ${r[5]:<7.2f} | {r[1]}")
    
    conn.close()

if __name__ == "__main__":
    CIKs = pd.read_csv("../data/fundamentals.csv")["CIK"].tolist()
    asyncio.run(update_days(10, CIKs)) # Change 3 to however many days you want
    show_recent_trades(20)
