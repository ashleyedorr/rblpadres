import os
import heapq

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from operator import itemgetter

from helpers import apology, login_required, percent, truncate, prep

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///padres.db")


## Display homepage
@app.route("/")
def home():

    ## Figure out if it's baseball season yet, if not display last year's info
    now = datetime.now()
    if now.month < 5:
        year = int(now.year) - 1
    else:
        year = int(now.year)
    ranks = db.execute('SELECT * FROM playerStats where year = :year', year=year)
    if not ranks:
        return apology("Unable to load data", 400)

    ranks = prep(ranks)

    ## Tabulate current highest ranking players
    rows = db.execute('SELECT * FROM standings WHERE year = :year AND team = "Padres"', year=year)

    ## Determine number of games played
    for row in rows:
        games = (int(row['win']) + int(row['loss']) + int(row['tie'])) * 2.1

    ## Determine if min is hit to be included in current rankings
    avgs = db.execute('SELECT player, h, ab FROM playerStats where year = :year AND ab > :games', year=year, games=games)
    for aver in avgs:
        if aver['ab'] > 0:
            avg = truncate(aver['h']/aver['ab'], 3)
            aver['avg'] = avg

    ## Calculate current rankings
    avgsort = sorted(avgs, key=itemgetter('avg'), reverse=True)[:5]
    for x in avgsort:
        x['avg'] = "{:.3f}".format(float(x['avg']))

    hsort = sorted(ranks, key=itemgetter('h'), reverse=True)[:5]

    rsort = sorted(ranks, key=itemgetter('r'), reverse=True)[:5]

    rbisort = sorted(ranks, key=itemgetter('rbi'), reverse=True)[:5]

    sbsort = sorted(ranks, key=itemgetter('sb'), reverse=True)[:5]

    tbsort = sorted(ranks, key=itemgetter('tb'), reverse=True)[:5]

    wsort = sorted(ranks, key=itemgetter('w'), reverse=True)[:2]

    kpsort = sorted(ranks, key=itemgetter('kp'), reverse=True)[:2]

    ipsort = sorted(ranks, key=itemgetter('ip'), reverse=True)[:2]
    for x in ipsort:
        x['ip'] = "{:.2f}".format(float(x['ip']))

    ## Determine if min is hit to be included in current rankings
    eras = db.execute('SELECT player, er, ip FROM playerStats where year = :year AND ip > 10', year=year)
    for eraa in eras:
        if eraa['ip'] > 0:
            era = (9*eraa['er'])/(eraa['ip'])
            eraa['era'] = era
        else:
            eraa['era'] = " "

    erasort = sorted(eras, key=itemgetter('era'), reverse=False)[:2]
    for x in erasort:
        if x['era'] == 100000000:
            x['era'] = 'N/A'
        else:
            x['era'] = "{:.2f}".format(float(x['era']))


    ## Tabulate current standings across league
    rows = db.execute('SELECT * FROM standings WHERE year = :year', year=year)
    if not rows:
        return apology("Unable to load data", 400)

    ## Pull recap data
    res = db.execute('SELECT * FROM recap')
    recapsort = sorted(res, key=itemgetter('date'), reverse=True)[:5]

    return render_template("home.html", recapsort=recapsort, rows=rows, ranks=ranks, avgsort=avgsort, hsort=hsort, rsort=rsort, rbisort=rbisort, sbsort=sbsort, tbsort=tbsort, wsort=wsort, kpsort=kpsort, ipsort=ipsort, erasort=erasort, year=year)


## Display team page
@app.route("/viewteam", methods=["GET", "POST"])
def viewteam():

    ## Select players who are listed as "current" in database and all of their related info for display
    rows = db.execute('SELECT * FROM players WHERE status = "current" ORDER BY number')

    return render_template("viewteam.html", rows=rows)


## Display game schedule
@app.route("/sched")
def schedule():

    ## Pull schedule from database
    rows = db.execute('SELECT * FROM schedule')

    return render_template("sched.html", rows=rows)


## Display team stats
@app.route("/team")
def team():

    """Show team wide stats"""

    # Pull data from database for the team
    rows = db.execute("SELECT * FROM teamStats")
    if not rows:
        return apology("Unable to load data", 400)

    # For each row, tabulate data
    for row in rows:
        row['pct'] = percent(int(row['win']) / (int(row['win']) + int(row['loss']) + int(row['tie'])))

    return render_template("team.html", rows=rows)

## Display records page
@app.route("/records")
def records():

    ranks = db.execute("SELECT player, SUM(ab), SUM(r), SUM(h), SUM(rbi), SUM(twob), SUM(threeb), SUM(hr), SUM(sac), SUM(sb), SUM(hbp), SUM(bb), SUM(k), SUM(ip), SUM(hp), SUM(rp), SUM(er), SUM(bbp), SUM(kp), SUM(w), SUM(l), SUM(s), SUM(so), AVG(er), AVG(ip), AVG(h), AVG(hbp), AVG(bb), AVG(ab), AVG(twob), AVG(threeb), AVG(hr) FROM playerStats GROUP BY player")
    if not ranks:
        return apology("Unable to load data", 400)

    for x in ranks:
        oneb = int(x['SUM(h)']) - (int(x['SUM(twob)']) + int(x['SUM(threeb)']) + int(x['SUM(hr)']))
        x['oneb'] = oneb
        x['tb'] = int(x['oneb'] + ((int(x['SUM(twob)']) * 2) + (int(x['SUM(threeb)']) * 3) + (int(x['SUM(hr)']) * 4)))
        x['ip'] = float(x['SUM(ip)'])
        x['kp'] = int(x['SUM(kp)'])
        if int(x['SUM(ab)']) > 0:
            avg = truncate(x['AVG(h)']/x['AVG(ab)'], 3)
            x['avg'] = avg
            slg = truncate((x['tb']/int(x['SUM(ab)'])), 3)
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if int(x['SUM(ab)']) + x['SUM(hbp)'] + int(x['SUM(bb)']) > 0:
            obp = truncate((x['AVG(h)'] + x['AVG(hbp)'] + x['AVG(bb)']) / (x['AVG(ab)'] + x['AVG(hbp)'] + x['AVG(bb)']), 3)
            x['obp'] = obp
        else:
            x['obp'] = 'N/A'
        if x['ip'] > 0:
            era = truncate((9*x['AVG(er)'])/(x['AVG(ip)']), 2)
            x['era'] = era
        else:
            x['era'] = 'N/A'

        if x['ip'] > 0:
            oppsba = truncate(int(x['SUM(hp)'])/((x['ip']*3)+int(x['SUM(hp)'])), 3)
            whip = truncate((int(x['SUM(bbp)'])+ int(x['SUM(hp)']))/(x['ip']), 3)
        else:
            oppsba = "N/A"
            whip = "N/A"
        x['ip'] = "{:.2f}".format(float(x['SUM(ip)']))

        if int(x['SUM(ab)']) > 200:
            avg = truncate(int(x['SUM(h)'])/int(x['SUM(ab)']), 3)
            x['avg'] = float(avg)
        else:
            x['avg'] = 0

    ## Calculate current rankings
    avgsort = sorted(ranks, key=itemgetter('avg'), reverse=True)[:5]
    for x in avgsort:
        x['avg'] = "{:.3f}".format(float(x['avg']))

    hsort = sorted(ranks, key=itemgetter('SUM(h)'), reverse=True)[:5]

    rsort = sorted(ranks, key=itemgetter('SUM(r)'), reverse=True)[:5]

    dsort = sorted(ranks, key=itemgetter('SUM(twob)'), reverse=True)[:5]

    tsort = sorted(ranks, key=itemgetter('SUM(threeb)'), reverse=True)[:5]

    hrsort = sorted(ranks, key=itemgetter('SUM(hr)'), reverse=True)[:5]

    rbisort = sorted(ranks, key=itemgetter('SUM(rbi)'), reverse=True)[:5]

    bbsort = sorted(ranks, key=itemgetter('SUM(bb)'), reverse=True)[:5]

    hbpsort = sorted(ranks, key=itemgetter('SUM(hbp)'), reverse=True)[:5]

    sbsort = sorted(ranks, key=itemgetter('SUM(sb)'), reverse=True)[:5]

    tbsort = sorted(ranks, key=itemgetter('tb'), reverse=True)[:5]

    wsort = sorted(ranks, key=itemgetter('SUM(w)'), reverse=True)[:5]

    kpsort = sorted(ranks, key=itemgetter('SUM(kp)'), reverse=True)[:5]

    ipsort = sorted(ranks, key=itemgetter('SUM(ip)'), reverse=True)[:5]
    for x in ipsort:
        x['ip'] = "{:.2f}".format(float(x['ip']))

    ## Determine if min is hit to be included in current rankings ##
    eras = db.execute('SELECT player, SUM(er), SUM(ip), SUM(s), SUM(so) FROM playerStats WHERE ip > 1 GROUP BY player')
    for x in eras:
        if x['SUM(ip)'] > 74:
            era = (9*(x['SUM(er)']))/(x['SUM(ip)'])
            x['era'] = era
        else:
            x['era'] = 1000000

    erasort = sorted(eras, key=itemgetter('era'), reverse=False)[:5]
    for x in erasort:
        x['era'] = "{:.2f}".format(float(x['era']))

    ssort = sorted(ranks, key=itemgetter('SUM(s)'), reverse=True)[:5]

    sosort = sorted(ranks, key=itemgetter('SUM(so)'), reverse=True)[:5]

    return render_template("records.html", hrsort=hrsort, sosort=sosort, ssort=ssort, hbpsort=hbpsort, bbsort=bbsort, ranks=ranks, dsort=dsort, tsort=tsort, avgsort=avgsort, hsort=hsort, rsort=rsort, rbisort=rbisort, sbsort=sbsort, tbsort=tbsort, wsort=wsort, kpsort=kpsort, ipsort=ipsort, erasort=erasort)


## Display Season Records page
@app.route("/seasonrecords")
def seasonrecords():

    ## Calculate most wins in a year
    rows = db.execute('SELECT win, year FROM standings WHERE team = "Padres"')
    if not rows:
        return apology("Unable to load data", 400)

    winsort = sorted(rows, key=itemgetter('win'), reverse=True)[:2]

    ## Calculate most runs in a year
    runrows = db.execute("SELECT SUM(r), year FROM playerStats GROUP BY year")
    if not runrows:
        return apology("Unable to load data", 400)

    rsort = sorted(runrows, key=itemgetter('SUM(r)'), reverse=True)[:1]

    ## Calculate least runs allowed in a year
    rrows = db.execute("SELECT SUM(rp), year FROM playerStats GROUP BY year")
    if not rrows:
        return apology("Unable to load data", 400)

    ## Calculate hits record per player
    runsort = sorted(rrows, key=itemgetter('SUM(rp)'), reverse=False)[:2]

    hitrows = db.execute("SELECT player, h, year FROM playerStats")
    if not hitrows:
        return apology("Unable to load data", 400)

    hitsort = sorted(hitrows, key=itemgetter('h'), reverse=True)[:1]

    ## Calculate doubles record per player

    dubrows = db.execute("SELECT player, twob, year FROM playerStats")
    if not dubrows:
        return apology("Unable to load data", 400)

    dubsorts = sorted(dubrows, key=itemgetter('twob'), reverse=True)[:2]

    triprows = db.execute("SELECT player, threeb, year FROM playerStats")
    if not triprows:
        return apology("Unable to load data", 400)

    tripsorts = sorted(triprows, key=itemgetter('threeb'), reverse=True)[:1]

    homerows = db.execute("SELECT player, hr, year FROM playerStats")
    if not homerows:
        return apology("Unable to load data", 400)

    homesort = sorted(homerows, key=itemgetter('hr'), reverse=True)[:1]

    sbrows = db.execute("SELECT player, sb, year FROM playerStats")
    if not sbrows:
        return apology("Unable to load data", 400)

    sbsort = sorted(sbrows, key=itemgetter('sb'), reverse=True)[:1]

    runsrows = db.execute("SELECT player, r, year FROM playerStats")
    if not runsrows:
        return apology("Unable to load data", 400)

    runssort = sorted(runsrows, key=itemgetter('r'), reverse=True)[:2]

    rbisrows = db.execute("SELECT player, rbi, year FROM playerStats")
    if not rbisrows:
        return apology("Unable to load data", 400)

    rbissort = sorted(rbisrows, key=itemgetter('rbi'), reverse=True)[:1]

    bbsrows = db.execute("SELECT player, bb, year FROM playerStats")
    if not bbsrows:
        return apology("Unable to load data", 400)

    bbssort = sorted(bbsrows, key=itemgetter('bb'), reverse=True)[:1]

    hbpsrows = db.execute("SELECT player, hbp, year FROM playerStats")
    if not hbpsrows:
        return apology("Unable to load data", 400)

    hbpssort = sorted(hbpsrows, key=itemgetter('hbp'), reverse=True)[:1]

    strikerows = db.execute("SELECT player, k, year FROM playerStats")
    if not strikerows:
        return apology("Unable to load data", 400)

    strikesort = sorted(strikerows, key=itemgetter('k'), reverse=True)[:1]

    pwrows = db.execute("SELECT player, w, year FROM playerStats")
    if not pwrows:
        return apology("Unable to load data", 400)

    pwsort = sorted(pwrows, key=itemgetter('w'), reverse=True)[:1]

    strrows = db.execute("SELECT player, kp, year FROM playerStats")
    if not strrows:
        return apology("Unable to load data", 400)

    strsort = sorted(strrows, key=itemgetter('kp'), reverse=True)[:1]

    perarows = db.execute("SELECT player, ip, er, year FROM playerStats WHERE ip > 10")
    if not perarows:
        return apology("Unable to load data", 400)

    for x in perarows:
        era = (9*(x['er']))/(x['ip'])
        x['era'] = "{:.2f}".format(era)

    perasort = sorted(perarows, key=itemgetter('era'), reverse=False)[:2]

    shutrows = db.execute("SELECT player, so, year FROM playerStats")
    if not shutrows:
        return apology("Unable to load data", 400)

    shutsort = sorted(shutrows, key=itemgetter('so'), reverse=True)[:1]

    piprows = db.execute("SELECT player, ip, year FROM playerStats")
    if not piprows:
        return apology("Unable to load data", 400)

    pipsort = sorted(piprows, key=itemgetter('ip'), reverse=True)[:1]


    return render_template("seasonrecords.html", pipsort=pipsort, shutsort=shutsort, perasort=perasort, strsort=strsort, pwsort=pwsort, strikesort=strikesort, hbpssort=hbpssort, bbssort=bbssort, rbissort=rbissort, runssort=runssort, sbsort=sbsort, winsort=winsort, runsort=runsort, rsort=rsort, hitsort=hitsort, dubsorts=dubsorts, tripsorts=tripsorts, homesort=homesort)


## Display Career Pitching page
@app.route("/pitching")
def pitching():

    rows = db.execute("SELECT player, SUM(ip), SUM(hp), SUM(rp), SUM(er), SUM(bbp), SUM(kp), SUM(w), SUM(l), SUM(s), SUM(so), AVG(er), AVG(ip) FROM playerStats GROUP BY player")
    if not rows:
        return apology("Unable to load data", 400)

    for x in rows:
        x['ip'] = float(x['SUM(ip)'])
        x['kp'] = int(x['SUM(kp)'])
        if x['ip'] > 0:
            era = truncate((9*x['AVG(er)'])/(x['AVG(ip)']), 2)
            x['era'] = era
        else:
            x['era'] = 'N/A'
        x['ip'] = "{:.2f}".format(float(x['SUM(ip)']))

    rowsort = sorted(rows, key=itemgetter('SUM(ip)'), reverse=True)

    totals = db.execute("SELECT player, SUM(ip), SUM(hp), SUM(rp), SUM(er), SUM(bbp), SUM(kp), SUM(w), SUM(l), SUM(s), SUM(so), AVG(er), AVG(ip) FROM playerStats")
    if not totals:
        return apology("Unable to load data", 400)

    for x in totals:
        x['ip'] = float(x['SUM(ip)'])
        x['kp'] = int(x['SUM(kp)'])
        if x['ip'] > 0:
            era = truncate((9*x['AVG(er)'])/(x['AVG(ip)']), 2)
            x['era'] = era
        else:
            x['era'] = 'N/A'

        if x['ip'] > 0:
            oppsba = truncate(int(x['SUM(hp)'])/((x['ip']*3)+int(x['SUM(hp)'])), 3)
            whip = truncate((int(x['SUM(bbp)'])+ int(x['SUM(hp)']))/(x['ip']), 3)
        else:
            oppsba = "N/A"
            whip = "N/A"
        if x['ip'] > 0:
            oppsba = truncate(int(x['SUM(hp)'])/((x['ip']*3)+int(x['SUM(hp)'])), 3)
            whip = truncate((int(x['SUM(bbp)'])+ int(x['SUM(hp)']))/(x['ip']), 3)
        else:
            oppsba = "N/A"
            whip = "N/A"
        x['ip'] = "{:.2f}".format(float(x['SUM(ip)']))

    return render_template("pitching.html", rowsort=rowsort, totals=totals, oppsba=oppsba, whip=whip)


## Display Career Hitting page
@app.route("/hitting")
def hitting():

    rows = db.execute("SELECT player, SUM(ab), SUM(r), SUM(h), SUM(rbi), SUM(twob), SUM(threeb), SUM(hr), SUM(sac), SUM(sb), SUM(hbp), SUM(bb), SUM(k), AVG(h), AVG(hbp), AVG(bb), AVG(ab), AVG(twob), AVG(threeb), AVG(hr) FROM playerStats GROUP BY player")
    if not rows:
        return apology("Unable to load data", 400)

    for x in rows:
        oneb = int(x['SUM(h)']) - (int(x['SUM(twob)']) + int(x['SUM(threeb)']) + int(x['SUM(hr)']))
        x['oneb'] = oneb
        x['tb'] = int(x['oneb'] + ((int(x['SUM(twob)']) * 2) + (int(x['SUM(threeb)']) * 3) + (int(x['SUM(hr)']) * 4)))
        if int(x['SUM(ab)']) > 0:
            avg = truncate(x['AVG(h)']/x['AVG(ab)'], 3)
            x['avg'] = avg
            slg = truncate((x['tb']/int(x['SUM(ab)'])), 3)
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if int(x['SUM(ab)']) + x['SUM(hbp)'] + int(x['SUM(bb)']) > 0:
            obp = truncate((x['AVG(h)'] + x['AVG(hbp)'] + x['AVG(bb)']) / (x['AVG(ab)'] + x['AVG(hbp)'] + x['AVG(bb)']), 3)
            x['obp'] = obp
        else:
            x['obp'] = 'N/A'

    rows = sorted(rows, key=itemgetter('SUM(ab)'), reverse=True)

    totals = db.execute("SELECT player, SUM(ab), SUM(r), SUM(h), SUM(rbi), SUM(twob), SUM(threeb), SUM(hr), SUM(sac), SUM(sb), SUM(hbp), SUM(bb), SUM(k), AVG(h), AVG(hbp), AVG(bb), AVG(ab), AVG(twob), AVG(threeb), AVG(hr) FROM playerStats")
    if not totals:
        return apology("Unable to load data", 400)

    for x in totals:
        oneb = int(x['SUM(h)']) - (int(x['SUM(twob)']) + int(x['SUM(threeb)']) + int(x['SUM(hr)']))
        x['oneb'] = oneb
        x['tb'] = int(x['oneb'] + ((int(x['SUM(twob)']) * 2) + (int(x['SUM(threeb)']) * 3) + (int(x['SUM(hr)']) * 4)))
        if int(x['SUM(ab)']) > 0:
            avg = truncate(x['AVG(h)']/x['AVG(ab)'], 3)
            x['avg'] = avg
            slg = truncate((x['tb']/int(x['SUM(ab)'])), 3)
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if int(x['SUM(ab)']) + x['SUM(hbp)'] + int(x['SUM(bb)']) > 0:
            obp = truncate((x['AVG(h)'] + x['AVG(hbp)'] + x['AVG(bb)']) / (x['AVG(ab)'] + x['AVG(hbp)'] + x['AVG(bb)']), 3)
            x['obp'] = obp
        else:
            x['obp'] = 'N/A'

    return render_template("hitting.html", rows=rows, totals=totals)


## Display stats by year
@app.route("/year", methods=["GET", "POST"])
def year():

    if request.method == "POST":
        ## Pull data from database for players
        rows = db.execute("SELECT * FROM playerStats WHERE year = :year ORDER BY player", year=request.form.get('years'))
        if not rows:
            return apology("Unable to load data", 400)

        rows = prep(rows)

        rows = sorted(rows, key=itemgetter('avg'), reverse=True)

        erasorts = sorted(rows, key=itemgetter('era'), reverse=False)
        for erasort in erasorts:
            if erasort['era'] == 100000000:
                erasort['era'] = 'N/A'
            else:
                erasort['era'] = "{:.2f}".format(float(erasort['era']))

        totals = db.execute("SELECT SUM(ab), SUM(r), SUM(h), SUM(rbi), SUM(twob), SUM(threeb), SUM(hr), SUM(sac), SUM(sb), SUM(hbp), SUM(bb), SUM(k), SUM(ip), SUM(hp), SUM(rp), SUM(er), SUM(bbp), SUM(kp), SUM(w), SUM(l), SUM(s), SUM(so), AVG(er), AVG(ip), AVG(h), AVG(hbp), AVG(bb), AVG(ab), AVG(twob), AVG(threeb), AVG(hr) FROM playerStats WHERE year = :year", year=request.form.get('years'))
        if not totals:
            return apology("Unable to load data", 400)

        for x in totals:
            oneb = int(x['SUM(h)']) - (int(x['SUM(twob)']) + int(x['SUM(threeb)']) + int(x['SUM(hr)']))
            x['oneb'] = oneb
            x['tb'] = int(x['oneb'] + ((int(x['SUM(twob)']) * 2) + (int(x['SUM(threeb)']) * 3) + (int(x['SUM(hr)']) * 4)))
            x['ip'] = float(x['SUM(ip)'])
            x['kp'] = int(x['SUM(kp)'])
        if int(x['SUM(ab)']) > 0:
            avg = truncate(x['AVG(h)']/x['AVG(ab)'], 3)
            x['avg'] = avg
            slg = truncate((x['tb']/int(x['SUM(ab)'])), 3)
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if int(x['SUM(ab)']) + x['SUM(hbp)'] + int(x['SUM(bb)']) > 0:
            obp = truncate((x['AVG(h)'] + x['AVG(hbp)'] + x['AVG(bb)']) / (x['AVG(ab)'] + x['AVG(hbp)'] + x['AVG(bb)']), 3)
            x['obp'] = obp
        else:
            x['obp'] = 'N/A'
        if x['ip'] > 0:
            era = truncate((9*x['AVG(er)'])/(x['AVG(ip)']), 2)
            x['era'] = era
        else:
            x['era'] = 'N/A'

        if x['ip'] > 0:
            oppsba = truncate(int(x['SUM(hp)'])/((x['ip']*3)+int(x['SUM(hp)'])), 3)
            whip = truncate((int(x['SUM(bbp)'])+ int(x['SUM(hp)']))/(x['ip']), 3)
        else:
            oppsba = "N/A"
            whip = "N/A"
        x['ip'] = "{:.2f}".format(float(x['SUM(ip)']))

        return render_template("selectedyear.html", rows=rows, totals=totals, oppsba=oppsba, whip=whip, year=request.form.get('years'), erasorts=erasorts)

    if request.method == "GET":
        ## Pull data from database for players
        rows = db.execute("SELECT DISTINCT year FROM playerStats ORDER BY year")
        if not rows:
            return apology("Unable to load data", 400)

        return render_template("year.html", rows=rows)


## Display stats by player
@app.route("/player", methods=["GET", "POST"])
def current():

    ## When the form is completed
    if request.method == 'POST':

        rows = db.execute("SELECT * FROM playerStats WHERE player = :player ORDER BY year", player=request.form.get("currplayers"))
        player = request.form.get('currplayers')
        if not rows:
            return apology("Unable to load data", 400)

        rows = prep(rows)

        for row in rows:
            if row['era'] == 100000000:
                row['era'] = 'N/A'
            else:
                row['era'] = "{:.2f}".format(row['era'])

        ## Find total for all player data
        totals = db.execute("SELECT SUM(ab), SUM(r), SUM(h), SUM(rbi), SUM(twob), SUM(threeb), SUM(hr), SUM(sac), SUM(sb), SUM(hbp), SUM(bb), SUM(k), SUM(ip), SUM(hp), SUM(rp), SUM(er), SUM(bbp), SUM(kp), SUM(w), SUM(l), SUM(s), SUM(so), AVG(er), AVG(ip), AVG(h), AVG(hbp), AVG(bb), AVG(ab), AVG(twob), AVG(threeb), AVG(hr) FROM playerStats WHERE player = :play", play=request.form.get('currplayers'))
        if not totals:
            return apology("Unable to load data", 400)

        for x in totals:
            oneb = int(x['SUM(h)']) - (int(x['SUM(twob)']) + int(x['SUM(threeb)']) + int(x['SUM(hr)']))
            x['oneb'] = oneb
            x['tb'] = int(x['oneb'] + ((int(x['SUM(twob)']) * 2) + (int(x['SUM(threeb)']) * 3) + (int(x['SUM(hr)']) * 4)))
            x['ip'] = float(x['SUM(ip)'])
            x['kp'] = int(x['SUM(kp)'])
        if int(x['SUM(ab)']) > 0:
            avg = truncate(x['AVG(h)']/x['AVG(ab)'], 3)
            x['avg'] = avg
            slg = truncate((x['tb']/int(x['SUM(ab)'])), 3)
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if int(x['SUM(ab)']) + x['SUM(hbp)'] + int(x['SUM(bb)']) > 0:
            obp = truncate((x['AVG(h)'] + x['AVG(hbp)'] + x['AVG(bb)']) / (x['AVG(ab)'] + x['AVG(hbp)'] + x['AVG(bb)']), 3)
            x['obp'] = obp
        else:
            x['obp'] = 'N/A'
        if x['ip'] > 0:
            era = truncate((9*x['AVG(er)'])/(x['AVG(ip)']), 2)
            x['era'] = era
        else:
            x['era'] = 'N/A'

        if x['ip'] > 0:
            oppsba = truncate(int(x['SUM(hp)'])/((x['ip']*3)+int(x['SUM(hp)'])), 3)
            whip = truncate((int(x['SUM(bbp)'])+ int(x['SUM(hp)']))/(x['ip']), 3)
        else:
            oppsba = "N/A"
            whip = "N/A"
        x['ip'] = "{:.2f}".format(float(x['SUM(ip)']))

        return render_template("selectedplayer.html", player=player, rows=rows, avg=avg, obp=obp, oneb=oneb, totals=totals, slg=slg, oppsba=oppsba, whip=whip)

    else:
        ## Pull data from database for players
        rows = db.execute("SELECT name FROM players WHERE status = 'current' ORDER BY name")
        if not rows:
            return apology("Unable to load data", 400)

        return render_template("player.html", rows=rows)


## Display stats by legacy player
@app.route("/legacy", methods=["GET", "POST"])
def legacy():

        ## When the form is completed
    if request.method == 'POST':

        rows = db.execute("SELECT * FROM playerStats WHERE player = :player ORDER BY year", player=request.form.get("legplayers"))
        player = request.form.get('legplayers')
        if not rows:
            return apology("Unable to load data", 400)

        rows = prep(rows)
        for row in rows:
            if row['era'] == 100000000:
                row['era'] = 'N/A'
            else:
                row['era'] = "{:.2f}".format(row['era'])

        ## Find total for all player data
        totals = db.execute("SELECT SUM(ab), SUM(r), SUM(h), SUM(rbi), SUM(twob), SUM(threeb), SUM(hr), SUM(sac), SUM(sb), SUM(hbp), SUM(bb), SUM(k), SUM(ip), SUM(hp), SUM(rp), SUM(er), SUM(bbp), SUM(kp), SUM(w), SUM(l), SUM(s), SUM(so), AVG(er), AVG(ip), AVG(h), AVG(hbp), AVG(bb), AVG(ab), AVG(twob), AVG(threeb), AVG(hr) FROM playerStats WHERE player = :play", play=request.form.get('legplayers'))
        if not totals:
            return apology("Unable to load data", 400)

        for x in totals:
            oneb = int(x['SUM(h)']) - (int(x['SUM(twob)']) + int(x['SUM(threeb)']) + int(x['SUM(hr)']))
            x['oneb'] = oneb
            x['tb'] = int(x['oneb'] + ((int(x['SUM(twob)']) * 2) + (int(x['SUM(threeb)']) * 3) + (int(x['SUM(hr)']) * 4)))
            x['ip'] = float(x['SUM(ip)'])
            x['kp'] = int(x['SUM(kp)'])
        if int(x['SUM(ab)']) > 0:
            avg = truncate(x['AVG(h)']/x['AVG(ab)'], 3)
            x['avg'] = avg
            slg = truncate((x['tb']/int(x['SUM(ab)'])), 3)
            x['slg'] = slg
        else:
            x['avg'] = 'N/A'
            x['slg'] = 'N/A'
        if int(x['SUM(ab)']) + x['SUM(hbp)'] + int(x['SUM(bb)']) > 0:
            obp = truncate((x['AVG(h)'] + x['AVG(hbp)'] + x['AVG(bb)']) / (x['AVG(ab)'] + x['AVG(hbp)'] + x['AVG(bb)']), 3)
            x['obp'] = obp
        else:
            x['obp'] = 'N/A'
        if x['ip'] > 0:
            era = truncate((9*x['AVG(er)'])/(x['AVG(ip)']), 2)
            x['era'] = era
        else:
            x['era'] = 'N/A'

        if x['ip'] > 0:
            oppsba = truncate(int(x['SUM(hp)'])/((x['ip']*3)+int(x['SUM(hp)'])), 3)
            whip = truncate((int(x['SUM(bbp)'])+ int(x['SUM(hp)']))/(x['ip']), 3)
        else:
            oppsba = "N/A"
            whip = "N/A"
        x['ip'] = "{:.2f}".format(float(x['SUM(ip)']))

        return render_template("selectedlegacy.html", rows=rows, totals=totals, oppsba=oppsba, whip=whip, player=player)

    else:
        ## Pull data from database for players
        rows = db.execute("SELECT name FROM players WHERE status = 'legacy' ORDER BY name")
        if not rows:
            return apology("Unable to load data", 400)

        return render_template("legacy.html", rows=rows)


## Display form to enter retired numbers
@app.route("/retired", methods=["GET", "POST"])
def retired():

        records = db.execute('SELECT * FROM retired')

        return render_template("retired.html", records=records)


## Display form to enter recap
@app.route("/newrecap", methods=["GET", "POST"])
@login_required
def newrecap():

    if request.method == 'POST':
    ## Update the database with the new information
        try:
            rows = db.execute('SELECT * FROM recap WHERE date = :date', date=request.form.get('date'))
            if not rows:
                db.execute("INSERT INTO recap (date, name, recap) VALUES(:date, :name, :recap)", name=request.form.get('name'), date=request.form.get('date'), recap=request.form.get('recap'))
            else:
                db.execute('DELETE FROM recap WHERE date = :date', date=request.form.get('date'))
                db.execute("INSERT INTO recap (date, name, recap) VALUES(:date, :name, :recap)", name=request.form.get('name'), date=request.form.get('date'), recap=request.form.get('recap'))

            return redirect("/")

        except:
            return apology("Unable to add data", 400)

    else:
        return render_template("newrecap.html")


## Display form to enter retired numbers
@app.route("/newretired", methods=["GET", "POST"])
@login_required
def newretired():

    if request.method == 'POST':
    ## Check to see if info alread exists. If so, delete and re-enter. If not, enter.
        try:
            rows = db.execute('SELECT * FROM retired WHERE number = :number', number=request.form.get('number'))
            if not rows:
                db.execute("INSERT INTO retired (number, name, date, info) VALUES(:number, :name, :date, :info)", number=request.form.get('number'), name=request.form.get('name'), date=request.form.get('date'), info=request.form.get('info'))

            else:
                db.execute('DELETE * FROM retired WHERE number = :number', number=request.form.get('number'))
                db.execute("INSERT INTO retired (number, name, date, info) VALUES(:number, :name, :date, :info)", number=request.form.get('number'), name=request.form.get('name'), date=request.form.get('date'), info=request.form.get('info'))

            return render_template("retired.html")

        except:
            return apology("Unable to add data", 400)

    else:
        return render_template("newretired.html")


## Tabulate and update database for entries of new teamwide data
@app.route("/newannual", methods=["GET", "POST"])
@login_required
def newannual():

    ## When the form is completed
    if request.method == 'POST':

    ## Update the database with the new information
        try:
            db.execute("INSERT INTO teamStats (year, win, loss, tie, result, mvp, batchamp) VALUES(:year, :win, :loss, :tie, :result, :mvp, :batchamp)", year=request.form.get('year'), win=request.form.get('win'), loss=request.form.get('loss'), tie=request.form.get('tie'), result=request.form.get('result'), mvp=request.form.get('mvp'), batchamp=request.form.get('batchamp'))
            return render_template("newannual.html")

        except:
            return apology("Unable to add data", 400)

    ## Display the form
    else:
        return render_template("newannual.html")


@app.route("/newplayer", methods=["GET", "POST"])
@login_required
def newplayer():

    if request.method == 'POST':
        ## If the player has no stats for the year, create the row in the database and input user entered data
        try:
            rows = db.execute("SELECT * FROM playerStats where player = :play AND year = :year", play=request.form.get('play'), year=request.form.get("playyear"))
            if not rows:
                db.execute("INSERT INTO playerStats (ab, r, h, rbi, twob, threeb, hr, sac, sb, hbp, bb, k, ip, hp, rp, er, bbp, kp, w, l, s, so, player, year) VALUES(:ab, :r, :h, :rbi, :twob, :threeb, :hr, :sac, :sb, :hbp, :bb, :k, :ip, :hp, :rp, :er, :bbp, :kp, :w, :l, :s, :so, :play, :playyear)", ab=request.form.get('ab'), r=request.form.get('r'), h=request.form.get('h'), rbi=request.form.get('rbi'),
                           twob=request.form.get('twob'), threeb=request.form.get('threeb'), hr=request.form.get('hr'), sac=request.form.get('sac'), sb=request.form.get('sb'), hbp=request.form.get('hbp'), bb=request.form.get('bb'), k=request.form.get('k'), ip=request.form.get('ip'), hp=request.form.get('hp'), rp=request.form.get('rp'), er=request.form.get('er'), bbp=request.form.get('bbp'), kp=request.form.get('kp'), w=request.form.get('w'),
                           l=request.form.get('l'), s=request.form.get('s'), so=request.form.get('so'), play=request.form.get('play'), playyear=request.form.get('playyear'))


            ## Otherwise, update their existing stats
            else:
                db.execute("UPDATE playerStats SET ab = ab + :nab WHERE player = :play AND year = :year", nab=request.form.get('ab'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET r = r + :nr WHERE player = :play AND year = :year", nr=request.form.get('r'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET h = h + :nh WHERE player = :play AND year = :year", nh=request.form.get('h'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET rbi = rbi + :nrbi WHERE player = :play AND year = :year", nrbi=request.form.get('rbi'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET twob = twob + :ntwob WHERE player = :play AND year = :year", ntwob=request.form.get('twob'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET threeb = threeb + :nthreeb WHERE player = :play AND year = :year", nthreeb=request.form.get('threeb'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET hr = hr + :nhr WHERE player = :play AND year = :year", nhr=request.form.get('hr'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET sac = sac + :nsac WHERE player = :play AND year = :year", nsac=request.form.get('sac'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET sb = sb + :nsb WHERE player = :play AND year = :year", nsb=request.form.get('sb'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET hbp = hbp + :nhbp WHERE player = :play AND year = :year", nhbp=request.form.get('hbp'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET bb = bb + :nbb WHERE player = :play AND year = :year", nbb=request.form.get('bb'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET k = k + :nk WHERE player = :play AND year = :year", nk=request.form.get('k'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET ip = ip + :nip WHERE player = :play AND year = :year", nip=request.form.get('ip'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET hp = hp + :nhp WHERE player = :play AND year = :year", nhp=request.form.get('hp'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET rp = rp + :nrp WHERE player = :play AND year = :year", nrp=request.form.get('rp'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET er = er + :ner WHERE player = :play AND year = :year", ner=request.form.get('er'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET bbp = bbp + :nbbp WHERE player = :play AND year = :year", nbbp=request.form.get('bbp'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET kp = kp + :nkp WHERE player = :play AND year = :year", nkp=request.form.get('kp'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET w = w + :nw WHERE player = :play AND year = :year", nw=request.form.get('w'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET l = l + :nl WHERE player = :play AND year = :year", nl=request.form.get('l'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET s = s + :ns WHERE player = :play AND year = :year", ns=request.form.get('s'), play=request.form.get('play'), year=request.form.get("playyear"))
                db.execute("UPDATE playerStats SET so = so + :nso WHERE player = :play AND year = :year", nso=request.form.get('s'), play=request.form.get('play'), year=request.form.get("playyear"))

            if request.form.get('status') == 'legacy':
                rows = db.execute("SELECT name, status FROM players WHERE name = :play", play=request.form.get('play'))
                if not rows:
                    db.execute("INSERT INTO players (name, status) VALUES(:play, :status)", play=request.form.get('play'), status=request.form.get('status'))
                else:
                    db.execute("UPDATE players SET status = 'legacy' WHERE name = :play", play=request.form.get('play'))
            elif request.form.get('status') == 'current':
                rows = db.execute("SELECT name, status FROM players WHERE name = :play", play=request.form.get('play'))
                if not rows:
                    db.execute("INSERT INTO players (name, status) VALUES(:play, :status)", play=request.form.get('play'), status=request.form.get('status'))
                else:
                    db.execute("UPDATE players SET status = 'current' WHERE name = :play", play=request.form.get('play'))

            return render_template("newplayer.html")

        except:
            return apology("Unable to add data", 400)

    ## Display the form
    else:
        return render_template("newplayer.html")


@app.route("/newleague", methods=["GET", "POST"])
@login_required
def newleague():

    if request.method == 'POST':
        ## If the league has no stats for the year, create the row in the database and input user entered data ##
        try:
            rows = db.execute("SELECT * FROM standings WHERE year = :year", year=request.form.get('year'))
            if not rows:
                db.execute("INSERT INTO standings (year, team, win, loss, tie) VALUES(:year, :team, :win, :loss, :tie)", year=request.form.get('year'), team=request.form.get('team'), win=request.form.get('win'), loss=request.form.get('loss'), tie=request.form.get('tie'))

            ## Otherwise, update their existing stats ##
            else:
                db.execute("UPDATE standings SET win = win + :nwin WHERE team = :team AND year = :year", nwin=request.form.get('win'), team=request.form.get('team'), year=request.form.get('year'))
                db.execute("UPDATE standings SET loss = loss + :nloss WHERE team = :team AND year = :year", nloss=request.form.get('loss'), team=request.form.get('team'), year=request.form.get('year'))
                db.execute("UPDATE standings SET tie = tie + :ntie WHERE team = :team AND year = :year", ntie=request.form.get('tie'), team=request.form.get('team'), year=request.form.get('year'))

            return render_template("newleague.html")
        except:
            return apology("Unable to add data", 400)

    ## Display the form
    else:
        return render_template("newleague.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/home")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
