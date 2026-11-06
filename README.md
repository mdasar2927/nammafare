Chennai Commute Burden and Route Planner

A browser-based dashboard with two sides:

Commuter side: pick a source and destination in Chennai and get ranked route options across bus, metro and suburban rail, with estimated cost and time.
Planner (admin) side: a commute burden heat map of Chennai's traffic analysis zones, a ranked list of the worst zones, and a what-if simulator to test fixes (feeder bus, higher frequency, fare subsidy) before spending public money.

Built for the Theme 7 hackathon prototype. No backend: everything runs in the browser from pre-built JSON files.

Important: Zones, bus routes, metro lines and rail lines are real data. Household income, mode split, waiting times, speeds and some fares are assumptions and are labelled as such in the app. See Assumptions.

Why this project
Families in outer zones pay more, and travel longer, to reach work. A common planning target is to keep transport spending near 10% of income, but many households spend closer to 15%.
Commuters cannot easily compare bus, metro and suburban rail combinations in rupees and minutes, especially where a direct bus does not exist.
Planners cannot easily see which zones carry the heaviest burden, or test a fix first.
Women in Tamil Nadu travel free on eligible city buses, which changes both route choice and burden. Most tools ignore this.

Burden % = monthly commute cost ÷ monthly household income × 100

Features
User side: route planner
Source and destination picked from a zone dropdown or by clicking the map
Ranked route options: direct and at most one transfer (bus to bus, bus to metro or rail, metro to rail)
Two columns per option: cost (₹, one way) and time (minutes), plus legs, transfers and monthly cost
Cost priority / Time priority switch to re-sort results
Gender switch: when Female is selected, eligible bus legs cost ₹0 (the rule is a setting in fares.json)
Optional monthly income input to show cost as a percentage of income
Map of the selected option, coloured by mode
Clear message where there is no bus data, for example: "No bus stop data here, showing metro and rail options"
Heat map (shared page)
280 traffic analysis zones coloured by burden: green (below 10%), yellow (10 to 15%), orange (15 to 20%), red (above 20%), grey (no data)
Click a zone for district, assumed income, mode split, monthly cost and burden
Women's view toggle to show the effect of free eligible buses
Optional layer: daily commute minutes
Admin side: planning tools
Zones ranked from highest to lowest burden, with an adjustable threshold
What-if simulator:
add a feeder route (distance to nearest stop drops to 300 m or less)
change bus frequency (5 to 30 minute gaps)
apply a fare subsidy % to bus and rail
Map recolours immediately, with before and after cards (burden, monthly saving per household, zones leaving the red band)
Reset button to restore the baseline
The admin view is a plain tab with no login. A real deployment would need authentication.
Data

Raw files live in /data (from the Theme 7 package).

Dataset	Used for	Gap handled
MTC routes (1,348 lines, 680 route numbers)	Route numbers, source, destination, route geometry	No timetable, fares or ordered stop list
Bus stops (2,717 stops: GCC, Avadi, Tambaram)	Boarding points	No route numbers; matched to routes spatially (see below)
Metro lines and stations (51 stations)	Metro legs	Stations are named only by number
Suburban rail (53 segments, 70 stations)	Rail legs	Stations are named only "Station 1 to 70"
Traffic analysis zones (280)	Heat map and origin/destination	No income or population; lat and long columns are swapped; every row says "OLD CMA Area", so group by the 16 districts
Fare structure PDF	Suburban rail fares	Metro and MTC fares are links only, not data

Stop-to-route matching: in testing, about 98.7% of bus stops lie within roughly 130 m of at least one MTC route line (median 19 routes per stop). This lets the planner show real route numbers such as "take bus 29C" without a timetable.

How it works

Preprocessing (Python, run once): scripts/prepare_data.py reads the shapefiles, Excel and KML, fixes the swapped zone coordinates, reprojects to WGS84, matches stops to route lines (recording position along each line), simplifies geometry, and writes the JSON files used by the web app.

Routing (in the browser):

Direct bus: a route serving a stop near the origin and a later stop near the destination.
One transfer: bus to bus at a shared stop; bus to metro or rail where a stop and a station are within about 400 m; metro to rail the same way.
Metro and rail only: allowed when a station is within about 1,500 m of both ends, or reached by a feeder bus.

Time = walk to stop (metres ÷ 80) + wait (half the assumed gap) + ride (ride km ÷ speed) + transfer wait (5 min) + walk from stop.

Fares

Suburban rail: real slabs from the PDF, ₹5 for 1 to 20 km, ₹10 for 21 to 45 km, ₹15 for 46 to 70 km, ₹20 for 71 to 100 km
Bus: assumed stage-based table in fares.json, replace with MTC figures
Metro: assumed distance formula in fares.json until the fare matrix is entered
Free travel for women: eligible bus legs set to ₹0, eligibility list in fares.json

Zone burden: average monthly cost across modes, weighted by an assumed mode split that shifts with access to stops and stations, divided by assumed income. Assumptions are being calibrated so the spread of burden values is realistic (an early draft produced implausible values above 70%).

Assumptions and limitations

These are shown on screen in a persistent footer and an Assumptions drawer:

Household income (no source in the data; assumed by area type and distance from the centre, with a floor)
Mode split and the rules that shift it (no ridership data)
MTC bus fares and metro fares (placeholders until real tables are added)
Waiting times, speeds (bus 18, rail 40, metro 35 km/h) and transfer times (no timetable)
Which MTC services are free for women (confirm against the MTC fares page)

Other limits: zone-level planning only (no street addresses), at most one transfer, no live traffic or real-time buses, no login.

Tech stack
Plain HTML, CSS and JavaScript
Leaflet for maps
Chart.js for charts (optional)
Python (for data preparation only)
Project structure
/data                  raw files from Theme 7
/scripts
  prepare_data.py      one-off data preparation
/web
  index.html           top bar: User | Heat map | Admin
  engine.js            routing, time, cost, burden (shared module)
  app.js               maps and panels
  simulator.js         what-if controls
  zones.geojson        zones in WGS84, simplified
  zones.json           one record per zone
  stops.json           stops with the routes serving them
  routes.json          simplified route lines with route number and direction
  stations.json        metro and rail stations
  fares.json           all fare tables and rates (editable)
Getting started
bash
# 1. Prepare data (once)
pip install -r requirements.txt   # geopandas, pandas, shapely, pyproj, openpyxl, scipy
python scripts/prepare_data.py

# 2. Serve the web app
cd web
python -m http.server 8000
# open http://localhost:8000

Deploys as a static site on GitHub Pages or Netlify.

Roadmap
Data preparation and burden heat map
Zone panel and admin ranked list
Route planner: direct, metro and rail options, cost/time switch
One-transfer options and gender switch
What-if simulator with before and after
Assumptions drawer, polish, demo

Next steps beyond the prototype: replace assumed income and mode shares with census and ridership data, add real MTC and metro fares and timetables, name the stations, and pilot with CUMTA on a cluster of zones.

Demo (about 3 minutes)
Commuter: pick an outer zone (for example near Ennore) and a central zone, then flip between cost and time priority
Switch to Female and show eligible bus legs becoming free
Pick a zone with no bus data and show the metro and rail alternatives
Open the heat map, then the Admin worst-zones list
Add a feeder route to the worst zone and show it moving from red to yellow
