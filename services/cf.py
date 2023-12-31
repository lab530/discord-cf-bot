import requests
import json
import datetime
from utils.tokens import get_tokens
import time

API_PREFIX = 'https://codeforces.com/api/'
CONTEST_URL_FMT = 'https://codeforces.com/contests/{}'
CONTEST_STANDING_FMT = 'https://codeforces.com/api/contest.standings?contestId={}&from=1&count=1'

class Contest:
    def __init__(self, name: str, cid: int, start_time: int, countdown: int, duration: int, url: str = None):
        self.name = name
        self.cid = cid
        self.url = CONTEST_URL_FMT.format(cid)
        # start time in UNIX timestamp
        self.start_time = start_time
        self.countdown = start_time - int(time.time())
        # duration in seconds
        self.duration = duration
    def __repr__(self):
        return f'Contest(name: "{self.name}", cid: {self.cid}, url: "{self.url}", start_time: {self.start_time}, countdown: {self.countdown}, duration: {self.duration})'
    def __str__(self):
        return f'''## {self.name}
Contest ID: {self.cid}
Start time: {self.stringify_start_time()}
Countdown: {self.stringify_countdown()}
Duration: {self.stringify_duration()}
URL: {self.url}'''

    def stringify_interval(s: int):
        seconds, minutes, hours, days = s % 60, s // 60 % 60, s // 60 // 60 % 24, s // 60 // 60 // 24
        ret = ''
        if days > 0:
            ret += f'{days}d'
        if hours > 0:
            ret += f'{hours}h'
        if minutes > 0:
            ret += f'{minutes}m'
        if seconds > 0:
            ret += f'{seconds}s'
        return ret

    def stringify_duration(self):
        return Contest.stringify_interval(self.duration)
    def stringify_start_time(self):
        return str(datetime.datetime.fromtimestamp(self.start_time))
    def stringify_countdown(self):
        return Contest.stringify_interval(self.countdown)

def get_contests(time_limit = 48):
    api_url = API_PREFIX + 'contest.list'
    raw = requests.get(api_url)
    if raw.status_code != 200:
        return None
    # now data is a list of all cf contest info
    contests = json.loads(raw.text)['result']
    # translate time_limit in hours to seconds
    time_limit = time_limit * 3600
    ret = []
    for contest in contests:
        # relativeTimeSeconds = current - contest start time
        relative_time = int(contest['relativeTimeSeconds'])
        # past contests
        if relative_time > 0:
            break
        # future contests but not in time limit
        elif -relative_time > time_limit:
            continue
        # passed condition, create this CFContest and append it to ret
        name = contest['name']
        cid = int(contest['id'])
        start_time = int(contest['startTimeSeconds'])
        duration = int(contest['durationSeconds'])
        countdown = -relative_time
        ret.append(Contest(name=name, cid=cid, start_time=start_time, countdown=countdown, duration=duration))
    return ret[::-1]

def get_contest_recent_one(time_limit = 7 * 24):
    cs = get_contests(time_limit)
    if len(cs) == 0:
        return None
    return cs[0]

class User:
    def __init__(self, name: str, rating: int, rank: str):
        self.name = name
        self.rating = rating
        self.rank = rank
    def __repr__(self):
        return f'User(name: "{self.name}", rating: {self.rating}, rank: "{self.rank}")'
    def __str__(self):
        return f'- {self.name} - {self.rating} - {self.rank}'

def get_ratings(rating_sorted=True):
    handles = get_tokens()['handles']
    # generate query URL
    api_url = API_PREFIX + 'user.info?handles={}'.format(';'.join(handles))
    raw_data = requests.get(api_url)
    if raw_data.status_code != 200:
        return None
    result = json.loads(raw_data.text)['result']
    ret = []
    for user in result:
        try:
            name = user['handle']
            rating = int(user['rating'])
            rank = user['rank']
            ret.append(User(name=name, rating=rating, rank=rank))
        except KeyError:
            continue

    if rating_sorted:
        ret.sort(key=lambda x: (-x.rating, x.name.lower()))
    else:
        ret.sort(key=lambda x: x.name.lower())

    return ret

class RatingChange:
    def __init__(self, cid: int, cname: str, name: str, rank: int, old_rat: int, new_rat: int):
        self.cid = cid
        self.cname = cname
        self.name = name
        self.rank = rank
        self.old_rat = old_rat
        self.new_rat = new_rat
    def __repr__(self):
        return f'RatingChange(cid: {self.cid}, cname: "{self.cname}", name: "{self.name}", rank: {self.rank}, old_rat: {self.old_rat}, new_rat: {self.new_rat})'
    def __str__(self):
        def explcit_sign(x: int):
            if x < 0:
                return str(x)
            else:
                return '+' + str(x)
        return f'- {self.name}({self.rank}): {self.old_rat} -> {self.new_rat} ({explcit_sign(self.new_rat - self.old_rat)})'

def get_rating_change(diff_sorted=True):
    handles = get_tokens()['handles']

    QUERY_URL_FMT = API_PREFIX + 'user.rating?handle={}'
    latest_records = []

    recent_contest_id, recent_contest_update_time = 0, 0

    for handle in handles:
        api_url = QUERY_URL_FMT.format(handle)
        raw_data = requests.get(api_url)
        if raw_data.status_code != 200:
            continue
        try:
            result = json.loads(raw_data.text)['result']
            if len(result) == 0:
                continue
            result.sort(key=lambda x: -int(x['ratingUpdateTimeSeconds']))
            latest_contest = result[0]

            cid = int(latest_contest['contestId'])
            cname = latest_contest['contestName']
            rank = int(latest_contest['rank'])
            old_rat = int(latest_contest['oldRating'])
            new_rat = int(latest_contest['newRating'])

            if latest_contest['ratingUpdateTimeSeconds'] > recent_contest_update_time:
                recent_contest_update_time = int(latest_contest['ratingUpdateTimeSeconds'])
                recent_contest_id = cid

            latest_records.append(RatingChange(cid=cid, cname=cname, name=handle, rank=rank, old_rat=old_rat, new_rat=new_rat))
        except ValueError:
            continue

    if len(latest_records) == 0:
        return latest_records

    ret = []
    for record in latest_records:
        if record.cid != recent_contest_id:
            continue
        ret.append(record)

    if diff_sorted:
        ret.sort(key=lambda x: x.old_rat - x.new_rat)
    else:
        ret.sort(key=lambda x: x.rank)

    return ret

class Problem:
    def __init__(self, cid: int, pid: int, pname: str, difficulty):
        self.cid = cid
        self.pid = pid
        self.pname = pname
        self.difficulty = difficulty
    def __repr__(self):
        return f'Problem(cid: {self.cid}, pid: {self.pid}, pname: {self.pname}, difficulty: {self.difficulty})'
    def __str__(self):
        if self.difficulty is not None:
            return f'- {self.pid}, {self.pname} - {self.difficulty}'
        else:
            return f'- {self.pid}, {self.pname}'

def get_contest_problems(cid: int):
    api_url = CONTEST_STANDING_FMT.format(cid)
    raw = requests.get(api_url)
    if raw.status_code != 200:
        return (None, None)

    result = json.loads(raw.text)['result']
    contest_json = result['contest']
    problmes_json = result['problems']

    contest = Contest(
        name=contest_json['name'],
        cid=int(contest_json['id']),
        start_time=int(contest_json['startTimeSeconds']),
        countdown=int(contest_json['durationSeconds']),
        duration=-int(contest_json['relativeTimeSeconds']),
    )
    problems = []

    for p in problmes_json:
        pid = p['index']
        pname = p['name']
        try:
            difficulty = p['rating']
        except:
            difficulty = None
        problems.append(Problem(cid=contest.cid, pid=pid, pname=pname, difficulty=difficulty))

    return (contest, problems)
