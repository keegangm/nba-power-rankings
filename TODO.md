## To Dos for NBA Power Rankings

> #### [Project Landing Page](https://github.com/keegangm/nba-power-rankings)

### Formatting
- [x] Maintain legend width when drilled down
- [x] Maintain YTick label width even when single-digit values
- [x] Fix attribution alignment
- [x] Add attributions
- [x] Fix titling
- [x] XY Ticks labels too big
- [x] Filters header needs changing
- [x] Change hover to show "Week:" when week is selected
- [ ] Date selectors
- [ ] Update xtick labels for date mode
 
### Features
- [ ] Animate over time
- [ ] Add team records / strength of schedule
- [ ] Add event annotations
- [ ] Add climbers / fallers

###

Sunday

```
def get_nba_week_no(date=today):
    """Get NBA Week number"""
    wk = read_nba_week()
    nba_week_no = wk[wk['sunday'] <= date].nba_week.max()

    return nba_week_no
```
```
def sunday_lookup(week: int):
"""Lookup date for Sunday of week number."""
try:
    wk = read_nba_week()
    return (wk.loc[wk['nba_week'] == week, 'sunday']).item()
except:
    return None

```