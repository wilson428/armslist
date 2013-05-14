#!/usr/bin/env python

import sqlite3, os
from collections import defaultdict
import json, re

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn = sqlite3.connect("db/guns.sqlite")
conn.row_factory = dict_factory
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS guns \
    (gid VARCHAR(32) PRIMARY KEY, seller, title TEXT, text TEXT, category, wanted, firearm_type, manufacturer, action, model, price, location, date, uid, count)")

#get all known makes
m = cur.execute("SELECT manufacturer FROM guns GROUP BY manufacturer").fetchall()
makers = [x['manufacturer'].replace("&amp;", "&") for x in m if x['manufacturer']]

models = [
    "([A-Z\&]+)(?:\s|-)?(\.?[0-9]+)",
    "([A-z\&]+)-?(\.?[0-9]+)",
    "(" + "|".join(makers) + ") ?(\.?[0-9]+)",
    "()(\.?[0-9]+)"
]

# tests regex for model detection
def test(gid):
    text = cur.execute("SELECT title,text from postings WHERE gid='%s'" % gid).fetchone()["title"]
    for mod in models:
        print mod
        match = re.search(mod, text)
        if match:
            if match.group(1) == '':
                name = manufacturer + " " + match.group(2)
            else:
                name = match.group(1).upper() + "-" + match.group(2)
            print name
            return
    print "none found"
        
def guess_model(text, manufacturer):
    for mod in models:
        match = re.search(mod, text)
        if match:
            if len(mod) > 50:
                return match.group(1).upper() + " " + match.group(3)
            elif match.group(1) == '':
                return manufacturer + " " + match.group(2)
            else:
                return match.group(1).upper() + "-" + match.group(2)
    return ""
    
def parse():
    cur.execute("DELETE FROM guns")
    
    model_types = defaultdict(int)

    # At present, we're disambiguating guns by unique combinations of user and category
    # probably undercounts
    for m in cur.execute("SELECT p.gid, p.seller, p.title, p.text, p.category, p.price, p.location, p.date, m.uid, COUNT(*) as count FROM postings as p JOIN members as m ON m.gid = p.gid WHERE (p.category='Handguns' OR p.category='Rifles' OR p.category='Shotguns') GROUP BY m.uid,p.category").fetchall():
        transaction = "Buyer" if m['title'].split(":")[0] == "Want To Buy" else "Seller"
        title = m['title'].split(":")[1]
        text = m['text']
        try:
            price = float(m['price'].replace("$", "").replace(",", ""))
        except:
            price = 0
            
        post = json.load(open("data/postings/%s.json" % m['gid'], "r"))
        action = None if "action" not in post else post["action"].strip()
        firearm_type = None if "firearm_type" not in post else post["firearm_type"].strip()
        manufacturer = '' if "manufacturer" not in post else post["manufacturer"].strip()
        name = ''
        
        # fill in missing manufacturer
        if not manufacturer:
            for maker in makers:
                if maker.lower() in text.lower():
                    manufacturer = maker
                    break
                    
        name = guess_model(m['title'], manufacturer)
        if name == "":
            name = guess_model(m['text'], manufacturer)        

        cur.execute('''INSERT OR IGNORE INTO guns
                (gid, seller, title, text, category, wanted, firearm_type,manufacturer, action, model, price, location, date, uid, count)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)''',
                (m['gid'], m['seller'], m['title'],m['text'],m['category'], transaction, firearm_type, manufacturer, action, name.strip(), price, m['location'], m['date'], m['uid'], m['count']))
    conn.commit()

parse()

#test("1000004")

conn.commit()
conn.close()
