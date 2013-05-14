An analysis of ArmsList.com 
=========

# Scraping the data
The raw data for this project was retrieved en mass using ```wget``` form the command line:

	wget \
		 --recursive \
		 --no-clobber \
		 --html-extension \
		 --restrict-file-names=windows \
		 --domains armslist.com \
			 www.armslist.com
         
This command takes several hours to execute, and typically retrieves between 75,000 and 125,000 
raw html files for individual posts. Each is stored in a document in folder with a unique integer
ID in the /posts/ directory that the wget command creates 

## Page format:
	
All classifieds for guns and accesories are displayed on the site with the same URL format:

	http://www.armslist.com/posts/1349611/cincinnati-ohio-optics-for-sale--new-eotech-512-holographic-weapon-sight-aa-batteries

The integer id is unique to the post, not the user who posted it, so the text after the id is 
not necessary in order to create a unique ID for a post. If the site receives a URL with the
id but not the string after it, it correctly locates the listing (if the listing is still active).

Users can be imputed from the "Listings from this user" page:

	http://www.armslist.com/classifieds/search?relatedto=1349611

These pages are paginated to 20 listings per page. 

# Data

A small collection of Python scripts and helper libraries make sense of these HTML files.

It's recommended you first create and activate a virtualenv with:

    virtualenv virt
    source virt/bin/activate

You don't have to call it "virt", but the project's gitignore is set up to ignore it already if you do.

Whether or not you use virtualenv:

    pip install -r requirements.txt

## Extracting data from the raw HTML

The ```extracts.py``` script parses the HTML in each file and creates a small JSON file for
each post, stored in the data directory. Run from the command line like so:

	./scripts/extract.py extract
	
The script takes three optional arguments: ```--offset```, ```--limit```, and ```--increment```. 
Use the ```--help``` flag for details.

This script creates a JSON file for each posting with the vital information and saves it in the ```/data/postings``` directory.
The file name is the unique ID from the URL.

## Storing in SQLite database
In addition to storing each post as a JSON file, the ```extract``` script enters the info into a SQLite database
for easy querying, stored in ```db/guns.sqlite```. The script makes a new row for the posting when it extracts the 
information.

To ensure that all postings made it into the database, you can run the script with the "store" command:

	./scripts/extract.py store

This will go over every JSON file and try to add it the database. Because the posting's ID is ```UNIQUE```,
it will not create duplicates. 

The script also enters the location of the posting, exactly as written on ArmsList.com, in a separate table
called ```locations```. This separation is used to reduce the load when geocoding these raw addresses.

## Members
To collate the postings by user, use the "members" argument:

	./scripts/extract.py members

This script is slow, since it requires thousands of calls to the user pages at ArmsList.com. It creates a 
database table called "members" that assigns the posts a uid corresponding to the user.

In theory, this table, when completed, should be the same length as the "postings" table. To test that
assertion, you can run the same script with the command "status":

	./scripts/extract.py status

## Guns
A separate table called ```guns``` condenses the postings to just weapons and attempts to find 
the maker and model. You can create this table by running the ```parse.py``` script:

	./scripts/parse.py

The script rebuilds this table from scratch on each run, since it does not involve any live URL calls and because
we can expect the parsing code to change frequently.

## Locations

Geocode the locations using the ```locations.py``` script. Be forewarned that it currently uses the Google Maps API,
which limits an individual IP address to 2,500 queries per day.

	./scripts/locations.py geocode

# Mapping

To generate CSV files of locations for guns ads, run:

	./scripts/write_data.py --type=Handguns
	
Other valid types are "Rifles" and "Shotguns."

To limit the results to a certain region, give the script the coordinates of the center point and a radius in miles:

	./scripts/write_data.py --type=Handguns --point=41.85,-87.65 --radius=150

The coordinates are latitude and longitude.