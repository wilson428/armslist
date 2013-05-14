#!/usr/bin/env python

import sqlite3, os
from collections import defaultdict
import json, re, csv
import argparse
from delta import delta_coords as delta
import codecs

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

conn = sqlite3.connect("db/guns.sqlite")
conn.row_factory = dict_factory
c = conn.cursor()

def enc(post):
    for k,v in post.items():
        if type(v) is unicode:
            post[k] = "".join([y if ord(y) < 128 else '?' for y in post[k].encode("utf-8")])    
    return post

def write_posts(posts, filename, point, radius):
    l = len(posts)
    if point:
        posts = [x for x in posts if delta(x['lat'], x['lng'], point[0], point[1]) < radius]
        print "%d of %d locations inside radius" % (len(posts), l)
    posts = map(enc, posts)
    
    f = open("/Users/cewilson/Dropbox/Private/projects/guns/site/data/files/" + filename, "wb")
    #f = codecs.open('out.txt', mode="w", encoding="utf-8")
    dict_writer = csv.DictWriter(f, posts[0].keys())
    dict_writer.writer.writerow(posts[0].keys())
    dict_writer.writerows(posts)
    f.close()
    return posts

def write_gids(gids, filename):
    postings = []
    for gid in gids:
        query = '''SELECT gid, title, price FROM postings WHERE gid = %s''' % gid
        postings.append(c.execute(query).fetchone())
    write_posts(postings, filename, None, None)

def write_grouped(gun_type, point, radius):
    # collated, sellers
    query = '''SELECT g.gid, l.place, l.lat, l.lng, count(*) as count, GROUP_CONCAT(g.gid) as gids
                        FROM guns as g JOIN locations as l ON g.location=l.original
                        WHERE category="%s" AND wanted LIKE "Seller%%"
                        GROUP BY l.place''' % gun_type
    posts = c.execute(query).fetchall()
    posts = write_posts(posts, "%s_Sell_Grouped.csv" % gun_type, point, radius)

    # uncollated, sellers
    query = '''SELECT g.gid, g.location, l.lat, l.lng
                        FROM guns as g JOIN locations as l ON g.location=l.original
                        WHERE category="%s" AND wanted LIKE "Seller%%"''' % gun_type
    posts = c.execute(query).fetchall()
    posts = write_posts(posts, "%s_Sell_Ungrouped.csv" % gun_type, point, radius)

    gids = [x['gid'] for x in posts]

    # collated, buyers
    query = '''SELECT g.gid, g.location, l.place, l.lat, l.lng, count(*) as count, GROUP_CONCAT(g.gid) as gids
                        FROM guns as g JOIN locations as l ON g.location=l.original
                        WHERE category="%s" AND wanted = "Buyer"
                        GROUP BY g.location''' % gun_type
    posts = c.execute(query).fetchall()
    posts = write_posts(posts, "%s_Buy_Grouped.csv" % gun_type, point, radius)

    gids += [x['gid'] for x in posts]
    write_gids(gids, "%s_Ads.csv" % gun_type)

    # uncollated, buyers
    query = '''SELECT g.gid, g.location, l.lat, l.lng
                        FROM guns as g JOIN locations as l ON g.location=l.original
                        WHERE category="%s" AND wanted = "Buyer"''' % gun_type
    posts = c.execute(query).fetchall()
    posts = write_posts(posts, "%s_Buy_Ungrouped.csv" % gun_type, point, radius)
    
def main():
    parser = argparse.ArgumentParser(description="Extract and store data from ArmsList.com cache")
    
    parser.add_argument("-t", "--type", dest="gun_type", type=str, default=None,
                        help="type of gun ('Handguns', 'Shotguns', 'Rifles')")

    parser.add_argument("-p", "--point", dest="latlng", type=str, default=None,
                        help="coordinates (lat,lng)")

    parser.add_argument("-r", "--radius", dest="radius", type=int, default=100,
                        help="radius from centroid (in miles). Default is 100")

    args = parser.parse_args()
    if args.latlng:
        args.latlng = [float(x) for x in args.latlng.split(",")]

    write_grouped(args.gun_type, args.latlng, args.radius)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()
