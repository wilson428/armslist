#!/usr/bin/env python

from utils import download, write, read
from lxml.html import fromstring, tostring
import os, re, json, argparse
import sqlite3
import urllib2
import uuid
import datetime
import utils

ROOT = "www.armslist.com/posts/"
DATA_DIR = "data/"

conn = sqlite3.connect("db/guns.sqlite")
cur = conn.cursor()

# table definitions
cur.execute("CREATE TABLE IF NOT EXISTS postings \
    (gid VARCHAR(32) PRIMARY KEY, \
    title TEXT, \
    url VARCHAR(256), \
    seller VARCHAR(100), \
    location VARCHAR(200), \
    price VARCHAR (50), \
    date DATETIME, \
    category VARCHAR (50), \
    text TEXT)")

cur.execute("CREATE TABLE IF NOT EXISTS locations \
    (original VARCHAR(160) PRIMARY KEY, \
    ids TEXT, \
    place VARCHAR(50), \
    lat FLOAT, \
    lng FLOAT)")

cur.execute("CREATE TABLE IF NOT EXISTS members (gid VARCHAR(32) PRIMARY KEY, uid VARCHAR(100))")

# place record in SQLite database
def store(post):
    # get date, give up on fail
    try:
        dt = datetime.datetime.strptime(post["listed_on"], "%A, %B %d, %Y").strftime("%Y-%m-%d")
    except:
        print post
        return

    location = post["location"][:-1].strip().title()

    # add location to locations table
    cur.execute("INSERT OR IGNORE INTO locations (original) VALUES ('%s')" % location)
    
    cur.execute('''INSERT OR IGNORE INTO postings
        (gid, title, url, seller, location, price, date, category, text)
        VALUES (?,?,?,?,?,?,?,?,?)''', (post['gid'], post['title'], post['url'], post['seller'], location, post['price'], dt, post['listed_in'], post['text']))



# get data from a cached HTML page of a post
def extract(root_dir, directory, filename):
    path = root_dir + directory + "/" + filename
    data = {
        "url": "http://www.armslist.com/posts/" + directory + "/" + filename,
        "gid": directory
    }
    
    page = read(path).decode("ascii", "replace")
    pairs = re.findall("<dt>([\w\s]+):</dt>\s+<dd(?:\sclass=\"[\w\s-]+\")?>(.*?)<", page, flags=re.DOTALL)
    for pair in pairs:
        data[pair[0].strip().lower().replace(" ", "_")] = pair[1].strip()

    doc = fromstring(page)
    try:
        data["title"] = doc.xpath("//h1[@class='title']/text()")[0]
    except:
        print "ERROR", directory, filename
        return
    
    data["text"] = doc.xpath("//section[@class='content']")[0].text_content().strip()
    data["images"] = doc.xpath("//section[@class='images']/figure/img/@src")
    write(json.dumps(data, indent=2), "postings/" + data["gid"] + ".json")
    return data

# get data from all postings in /data/postings/
def extract_all(offset, limit, inc):
    c = offset
    posts = os.listdir(ROOT)
    if offset:
        posts = posts[offset:]
    if limit:
        posts = posts[:limit]
    filenames = [[(x,y) for y in os.listdir(ROOT + x) if y[0] != "."][0] for x in posts]
    print "Extracting data from %d records" % len(posts)
    for post, filename in filenames:
        data = extract(ROOT, post, filename)
        store(data)
        c += 1
        if inc > 0 and c % inc == 0:
            print c, post
            conn.commit()
    conn.commit()
            
# useful catch-all for any postings we may have missed    
def store_all(offset, limit, inc):
    posts = [x for x in os.listdir("data/postings/") if x[0] != "."]
    if offset:
        posts = posts[offset:]
    if limit:
        posts = posts[:limit]
    c = 0

    for p in posts:
        post = json.load(open("data/postings/" + p, "r"))
        store(post)        
        c += 1
        if inc > 0 and c % inc == 0:
            conn.commit()
            print c
    conn.commit()
                
# recursively scan a user's page
def scan_page(url):
    page = fromstring(urllib2.urlopen(url).read())
    posts = page.xpath("//article/div/div[@class='title']/a/@href")
    myid = None
    inserts=[]
    for post in posts:
        gid = post.split("/")[2]
        inserts.append(gid)
        
        m = cur.execute("SELECT * from members WHERE gid=%s" % gid).fetchone()
        if not m:
            inserts.append(gid)

    #check for next pages
    nxt = page.xpath("//li[@class='next']/a/@href")
    if len(nxt):
        inserts += scan_page("http://www.armslist.com" + nxt[0])
    return inserts

# group postings by member
def collate(limit, inc):
    c = 0
    total = 0
    posts = [x[0] for x in cur.execute("SELECT gid FROM postings as p WHERE p.gid NOT IN (SELECT m.gid FROM members as m)").fetchall()]
    print "Found %d records in the postings table not present in the members table" % len(posts)
    
    if not limit:
        limit = len(posts)

    while len(posts) and c < limit:
        post = posts.pop(0)
        url = "http://www.armslist.com/classifieds/search?relatedto=%s" % post
        inserts = scan_page(url)

        #print len(posts), len(inserts)
        posts = [x for x in posts if x not in inserts]
        
        inserts.append(post)
                
        myid = None
            
        #see if we recognize any of these handles:
        for gid in inserts:
            m = cur.execute("SELECT * from members WHERE gid=%s" % gid).fetchone()
            if m:
                if myid and myid != m[1]:
                    print "ERROR", myid, m[1]
                    return
                else:
                    myid = m[1]
        
        if not myid:
            myid = str(uuid.uuid1())

        c += 1
        total += len(inserts)
        if c % 25 == 0:
            print c, total, len(posts)
        for insert in inserts:
            cur.execute('''INSERT OR IGNORE INTO members (gid, uid) VALUES (?, ?)''', (insert, myid))
        conn.commit()

    conn.commit()

def update(inc):
    c = 0
    extras = cur.execute("SELECT gid FROM members as m WHERE m.gid NOT IN (SELECT p.gid FROM postings as p)").fetchall()    
    print "Found %d records in the members table not present in the postings table" % len(extras)
    for p in extras:    
        page = urllib2.urlopen("http://www.armslist.com/posts/%s" % p[0])
        filename = page.url.split("/")[-1]
        utils.write(page.read(), "/Users/cewilson/Desktop/source/guns/www.armslist.com/posts/%s/%s.html" % (p[0], filename), '')
        c += 1
        if c % inc == 0:
            print c, p[0], filename

    extract_all(0, None, inc)            

def status():
    print "Raw postings: %d" % len(os.listdir(ROOT))
    print "Extracted data files: %d" % len(os.listdir("data/postings/"))
    print "Posts in database: %d" % cur.execute("SELECT count(*) FROM postings").fetchone()[0]
    print "Members in database: %d" % cur.execute("SELECT count(*) FROM members").fetchone()[0]
    

def main():
    parser = argparse.ArgumentParser(description="Extract and store data from ArmsList.com cache")
    
    parser.add_argument("command", type=str, default="extract",
                        help="Which command to run.")
    
    parser.add_argument("-o", "--offset", dest="offset", type=int, default=0,
                        help="the number of records to skip before beginning the mass extraction. Default is 0.")
    parser.add_argument("-l", "--limit", dest="limit", type=int, default=None,
                        help="The number of records to extract. Default is all of them.")
    parser.add_argument("-i", "--increment", dest="increment", type=int, default=100,
                        help="Increment at which to print progress. Default is 100. Values of 0 or less hide outputs.")
    
    args = parser.parse_args()
    if args.command == "store":
        store_all(args.offset, args.limit, args.increment)
    elif args.command == "members":
        collate(args.limit, args.increment)
    elif args.command == "update":
        update(args.increment)
    elif args.command == "status":
        status()
    elif args.command == "extract":
        extract_all(args.offset, args.limit, args.increment)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
