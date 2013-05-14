#!/usr/bin/env python

import sqlite3, os
from collections import defaultdict
import json
import argparse
from utils import write

from geopy import geocoders
g = geocoders.GoogleV3()

conn = sqlite3.connect("db/guns.sqlite")
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS locations \
    (original VARCHAR(160) PRIMARY KEY, \
    ids TEXT, \
    place VARCHAR(50), \
    lat FLOAT, \
    lng FLOAT)")

#take the raw string from the locations and guess whereabouts
def update_locations():
    for m in cur.execute("SELECT gid,location FROM postings").fetchall():
        #print m
        cur.execute("INSERT OR IGNORE INTO locations (original) VALUES ('%s')" % m[1])
    conn.commit()

'''
def states():
    for m in cur.execute("SELECT original FROM locations").fetchall():
        state = m[0].split(",")[-1].strip()
        if state == "United States":
            state = m[0].split(",")[-2].strip()
        if state == "South Florida":
            state = "Florida"
        cur.execute("UPDATE locations SET state='%s' WHERE original='%s'" % (state, m[0]))
    conn.commit()
'''
    
def geocode_locations(gun_type):
    update_locations()
    
    c = 0
    if gun_type:
        candidates = cur.execute("SELECT p.location, l.lat FROM postings as p INNER JOIN locations as l on p.location = l.original WHERE l.lat IS NULL and p.category = '%s'" % gun_type).fetchall()
    else:
        candidates = cur.execute("SELECT p.location, l.lat FROM postings as p INNER JOIN locations as l on p.location = l.original WHERE l.lat IS NULL").fetchall()
        
    print "Found %d locations that need geocoding." % len(candidates)

    # thanks, Google rate limiting
    candidates = candidates[:2500]
    for m in candidates:
        try:
            place, (lat, lng) = list(g.geocode(m[0], exactly_one=False))[0]
        except:
            print "<--------ERROR", m[0]
            location = ", ".join(m[0].split(",")[1:]).replace("  ", " ").strip()
            try:
                place, (lat, lng) = list(g.geocode(location, exactly_one=False))[0]
                print "RESOLVED", location
            except:
                print "<------- SECOND ERROR", location
                location = ", ".join(m[0].split(",")[1:]).replace("  ", " ").strip()
                try:
                    place, (lat, lng) = list(g.geocode(location, exactly_one=False))[0]
                    print "RESOLVED", location
                except:
                    print "<------- THIRD ERROR", location
                    continue
        cur.execute('''UPDATE locations SET place=?, lat=?, lng=? WHERE original = ?''', (place, lat, lng, m[0]))
        c += 1
        if c % 10 == 0:
            print c
            conn.commit()            
    conn.commit()

def write_locations(gun_type, seller_type):
    if seller_type and seller_type == "Buy":
        candidates = cur.execute("SELECT count(*) as count, l.place, l.lat, l.lng FROM guns as g INNER JOIN locations as l on g.location = l.original WHERE l.lat IS NOT NULL AND category='%s' and wanted LIKE 'For%%' GROUP BY l.place" % gun_type).fetchall()
    elif seller_type and seller_type == "Sell":
        candidates = cur.execute("SELECT count(*) as count, l.place, l.lat, l.lng FROM guns as g INNER JOIN locations as l on g.location = l.original WHERE l.lat IS NOT NULL AND category='%s' and wanted LIKE 'Want%%' GROUP BY l.place" % gun_type).fetchall()
    else:
        candidates = cur.execute("SELECT count(*) as count, l.place, l.lat, l.lng FROM guns as g INNER JOIN locations as l on g.location = l.original WHERE l.lat IS NOT NULL AND category='%s' GROUP BY l.place" % gun_type).fetchall()

    write(json.dumps(candidates, indent=2), "data/%s_%s.json" % (gun_type, seller_type))

def main():
    parser = argparse.ArgumentParser(description="Extract and store data from ArmsList.com cache")
    
    parser.add_argument("command", type=str, default="geocode",
                        help="Which command to run (geocode, update, write).")
    
    parser.add_argument("-t", "--type", dest="gun_type", type=str, default=None,
                        help="type of gun ('Handguns', 'Shotguns', 'Rigles')")

    parser.add_argument("-s", "--seller", dest="seller_type", type=str, default=None,
                        help="type of gun ('Sell', 'Buy')")

    args = parser.parse_args()

    try:
        if args.command == "geocode":
            geocode_locations(args.gun_type)
        elif args.command == "update":
            update_locations()
        elif args.command == "write":
            write_locations(args.gun_type, args.seller_type)
    except KeyboardInterrupt:
        print "Script stopped by user"
        conn.commit()
        conn.close()
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
