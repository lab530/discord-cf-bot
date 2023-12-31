from pycqBot import Message
import utils.fake_db as db
from utils.time import get_readable_time
import services.cf as cfs
import utils.tokens as tokens
import json

def _err(message: Message):
    # TODO never reach?
    message.reply('未知错误，请查看后台。')
    # TODO handle errors

def ping(_, message: Message):
    message.reply('pong')

class FakeMessage:
    def __init__(self):
        self.msg = ''
    def reply(self, msg: str):
        self.msg += msg
    def get(self):
        return self.msg.strip() + f'\n\n（该数据于 {get_readable_time(db.get_latest_succeed_time())} 更新，仅供参考）'

def cf(_, message_: Message):
    message = FakeMessage()
    contests = db.get_recent_contests()
    if contests is None:
        _err(message)
    elif len(contests) == 0:
        message.reply('最近 48 小时内无 Codeforces 竞赛。')
    else:
        message.reply('\n\n'.join(str(c) for c in contests))
    message_.reply(message.get())

def cf1(_, message_: Message):
    message = FakeMessage()
    contest = db.get_one_recent_contest()
    if contest is None:
        message.reply('最近 7 天内无 Codeforces 竞赛。')
    else:
        message.reply(str(contest))
    message_.reply(message.get())

def cfr(_, message_: Message):
    message = FakeMessage()
    lst_users = db.get_ratings()

    rating_change = db.get_rating_change()
    rc_dict = dict()
    for rc in rating_change:
        rc_dict[rc.name] = rc.new_rat - rc.old_rat

    if lst_users is None:
        _err(message)
    else:
        replication = ''
        for u in lst_users:
            if u.name in rc_dict:
                increment = ('+' if rc_dict[u.name] >= 0 else '') + str(rc_dict[u.name])
                replication += f'- {u.name} - {u.rating}({increment}) - {u.rank}\n'
            else:
                replication += str(u) + '\n'
        message.reply(replication)
    message_.reply(message.get())

def cfc(_, message_: Message):
    message = FakeMessage()
    lst_rating_change = db.get_rating_change()
    if lst_rating_change is None:
        _err(message)
    elif len(lst_rating_change) == 0:
        message.reply('无信息。')
    else:
        message.reply(f'## {lst_rating_change[0].cname}\n' + '\n'.join(str(rc) for rc in lst_rating_change))
    message_.reply(message.get())

def regular_update(_, message: Message):
    message.reply('正在更新数据库数据…')
    err = db.update_db()
    if err is None:
        message.reply(f'于 {get_readable_time(db.get_latest_succeed_time())} 更新成功。')
    else:
        message.reply(f'错误：{err}')

def cp(params, message: Message):
    cid = int(' '.join(params))
    contest, problems = cfs.get_contest_problems(cid)

    if contest is None or problems is None:
        message.reply('获取竞赛题失败，请检查竞赛 ID 是否合法。')
        return

    msg = ''
    msg += f'## {contest.name}\n'
    msg += f'URL: {contest.url}\n'
    for p in problems:
        msg += str(p) + '\n'

    message.reply(msg.strip())

def user_add(users, message: Message):
    t = tokens.get_tokens()
    reply = ''
    for user in users:
        if user in t['handles']:
            reply += f'{user} 已在列表中\n'
        else:
            t['handles'].append(user)
            reply += f'欢迎 {user}！\n'
    try:
        with open('tokens.json', 'w') as fp:
            json.dump(t, fp, indent=4)
    except:
        reply = '写回失败！'
    message.reply(reply.strip())

def user_del(users, message: Message):
    t = tokens.get_tokens()
    reply = ''
    for user in users:
        if user in t['handles']:
            t['handles'].remove(user)
            reply += f'移除 {user}，有缘再见！\n'
        else:
            reply += f'{user} 不在列表中\n'
    try:
        with open('tokens.json', 'w') as fp:
            json.dump(t, fp, indent=4)
    except:
        reply = '写回失败！'
    message.reply(reply.strip())

def fetch_handles(_, message: Message):
    t = tokens.get_tokens()
    message.reply(str(t['handles']))
