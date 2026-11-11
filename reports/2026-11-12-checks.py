"""Re-runnable checks for reports/2026-11-12-careers.md (python3 -I reports/2026-11-12-checks.py)."""
import json, collections, datetime as d, re
s = json.load(open('work/summary.json'))
rep = open('reports/2026-11-12-careers.md').read()
t = d.date(2026, 11, 12)
bad = 0
def chk(label, stated, actual):
    global bad
    ok = stated == actual
    bad += not ok
    print(f"{'OK ' if ok else 'DIFF'} {label}: stated {stated} / computed {actual}")
fits = collections.Counter(r['fit'] for r in s['new_roles'])
chk('new roles', 23, len(s['new_roles']))
chk('strong', 0, fits['strong']); chk('possible', 9, fits['possible']); chk('signal', 14, fits['signal'])
win = t + d.timedelta(14)
chk('window end', '2026-11-26', win.isoformat())
chk('deadlines within 2 weeks', 11, len([r for r in s['deadlines_soon'] if r['closes'] <= win.isoformat()]))
chk('weekday 12 Nov', 'Thursday', t.strftime('%A'))
for day, wd in [('2026-11-13','Fri'),('2026-11-16','Mon'),('2026-11-18','Wed'),('2026-11-28','Sat')]:
    chk(f'weekday {day}', wd, d.date.fromisoformat(day).strftime('%a'))
chk('EY 28 Nov days after window end', 2, (d.date(2026,11,28)-win).days)
a = s['applications']
chk('applications this week', 0, a['this_week']); chk('last 4 weeks', 41, a['last_4_weeks']); chk('total', 41, a['total']); chk('target', 8, a['weekly_target'])
chk('apply-queue rows in report (25 minus the RMIT duplicate)', len(s['apply_queue'])-1, len(re.findall(r'^\| .* \| \[link\]', rep.split('## Apply this week')[1].split('## Suggested')[0], re.M)))
chk('companies checked', 347, len(s['companies_checked']) if isinstance(s['companies_checked'], list) else s['companies_checked'])
searches = {1:7,2:7,3:6,4:7,5:7,6:5,7:6,8:6,9:5,10:7,11:5,12:7,13:5,14:7,15:5,16:6,17:7,18:7,19:5,20:6}  # from batch replies
chk('WebSearch calls used', 123, sum(searches.values()))
print('WebSearch total:', sum(searches.values()), 'of', 7*len(searches))
uk = open('work/uk-jobs.txt').readline()
for n, v in [('225',' 225 matching'),('England 158','England 158'),('Scotland 38','Scotland 38'),('Wales 11','Wales 11'),('Northern Ireland 18','Northern Ireland 18')]:
    chk('UK file '+n, True, v in uk)
chk('SEEK AU 305', True, ' 305 matching' in open('work/seek-AU.txt').readline())
nz = open('work/seek-NZ.txt').readline(); print('NZ header:', nz.strip())
chk('MHA days to 11 Jan', 60, (d.date(2027,1,11)-t).days)
print('FLAGGED:', bad)
