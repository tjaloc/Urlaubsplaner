"""Get optimized vacation dates based on:
    the year
    holidays this year
    your number of vacation days
    your number of vacations

    Holidays are provided by free api 'https://www.api-feiertage.de/'
"""

import pandas as pd
import datetime as dt
import requests
from itertools import product

STATES = {
    'bb': 'Brandenburg',
    'be': 'Berlin',
    'bw': 'Baden',
    'by': 'Bayern',
    'hb': 'Bremen',
    'he': 'Hessen',
    'hh': 'Hamburg',
    'mv': 'Mecklenburg-Vorpommern',
    'ni': 'Niedersachsen',
    'nw': 'Nordrhein-Westfalen',
    'rp': 'Rheinland-Pfalz',
    'sh': 'Schleswig-Holstein',
    'sl': 'Saarland',
    'sn': 'Sachsen',
    'st': 'Sachsen-Anhalt',
    'th': 'Thüringen',
}

class VacationUI():
    def __init__(self):
        self.year = self.get_year()
        self.state = self.get_state()
        self.days = self.get_days()
        self.vacations = self.get_vacations()

    def get_year(self):
        while True:
            year = input('Jahr:_').strip()
            year_now = dt.datetime.now().year
            year_max = year_now + 2
            if year.isdigit() and year_now <= int(year) <= year_max:
                return int(year)
            else:
                print(f'Bitte, gib ein Jahr zwischen {year_now} und {year_max} an.')

    def get_days(self):
        while True:
            days = input('Wieviele Tage Urlaub:_').strip()
            if days.isdigit():
                return int(days)
            else:
                print(f'Bitte, gib deine Urlaubstage als Zahl an.')

    def get_vacations(self):
        while True:
            vacations = input('Wie oft möchtest du Urlaub machen?:_').strip()
            if vacations.isdigit():
                return int(vacations)
            else:
                print(f'Bitte, gib deine Urlaube als Zahl an.')

    def get_state(self):
        print('Wähle dein Bundesland.')
        for key, val in STATES.items():
            print('\t', key, val)

        while True:
            state = input('\nBundesland (z.B. BE):_').strip().lower()
            if state in STATES.keys():
                return state
            else:
                print('Bitte gib die korrekte Abkürzung für dein Bundesland an.')

    def print_recommendations(self, rec_df):
        print(f'\nBeste Urlaubszeiten {self.year} in {STATES[self.state]}\n'
              f'\n'
              f'Urlaubstage: {self.days}\n'
              f'Urlaube: {self.vacations}\n'
              f'\n')

        for row in range(len(rec_df)):
            start_date = rec_df.iloc[row]['date'].strftime('%d-%m-%Y')
            end_date = rec_df.iloc[row]['end_date'].strftime('%d-%m-%Y')
            days_total = rec_df.iloc[row]['days_total']
            incl_holidays = ', '.join(rec_df.iloc[row]['incl_holidays'])
            workdays = rec_df.iloc[row]['workdays_total']

            if incl_holidays:
                print(f'von {start_date} bis {end_date} \n\t{workdays} Arbeitstage\n\t{days_total} Tage insgesamt inkl. {incl_holidays}\n')
            else:
                print(f'von {start_date} bis {end_date} \n\t{workdays} Arbeitstage\n\t{days_total} Tage insgesamt\n')

class ApiHandler():
    def __init__(self, year, state):
        self.baseurl = 'https://get.api-feiertage.de/'
        self.params = {'years': year, 'states': state}
        self.json = self.get_holidays()
        self.df = self.json_to_dataframe()

    def get_holidays(self):
        # Beispiel: https://get.api-feiertage.de?years=2024,2025&states=bw,by,nw
        r = requests.get(self.baseurl, params=self.params)
        if r.status_code == 200:
            return r.json()
        else:
            print(r.status_code)
            return False

    def json_to_dataframe(self) -> pd.DataFrame:
        holiday_list = self.json['feiertage']
        df = pd.DataFrame(holiday_list)
        df.date = pd.to_datetime(df.date)
        relevant_columns = ['date', 'fname']
        return df[relevant_columns]

    def print_holidays(self):
        for i in range(len(self.df)):
            print(f"{i+1:>2}) {self.params.iloc[i]['date'].strftime('%d.%m.%Y')} {self.params.iloc[i]['fname']}")

class VacationScheduler():
    def __init__(self, holiday_df, year, days, vacations):
        self.holidays = holiday_df
        self.year = year
        self.days = days
        self.vacations = vacations
        self.avg_days, self.extra_days = divmod(self.days, self.vacations)
        self.calendar = None
        self.year_slices = []
        self.recommendation = None

        self.find_best_vacations()

    def create_calendar(self):
        date_range = pd.date_range(start=f'{self.year}-01-01', end=f'{self.year}-12-31', freq='D')
        is_workday = ~date_range.to_series().dt.dayofweek.isin([5, 6]) # 5 Saturday, 6 Sunday
        df = pd.DataFrame({'date': date_range, 'is_workday': is_workday.values})
        self.calendar = df

    def add_holidays(self):
        merge_df = pd.merge(self.calendar, self.holidays, on='date', how='left')
        merge_df['is_workday'] = merge_df.apply(
            lambda row: False if pd.notna(row['fname']) else row['is_workday'], axis=1
        )
        self.calendar = merge_df

    def add_possible_end_dates(self):
        end_dates = []
        days_totals = []
        workdays_totals = []

        for i, row in self.calendar.iterrows():
            workdays_count = 0
            total_days_count = 0
            for j in range(i, len(self.calendar)):
                total_days_count += 1
                if self.calendar.iloc[j]['is_workday']:
                    workdays_count += 1
                if workdays_count >= self.avg_days:
                    end_dates.append(self.calendar.iloc[j]['date'])
                    days_totals.append(total_days_count)
                    workdays_totals.append(workdays_count)
                    break
            else:
                # Here we reached the end of the year
                end_dates.append(pd.Timestamp(f'{self.year}-12-31'))
                days_totals.append(total_days_count)
                workdays_totals.append(workdays_count)

        self.calendar['end_date'] = end_dates
        self.calendar['days_total'] = days_totals
        self.calendar['workdays_total'] = workdays_totals

    def split_year(self):
        num_days = len(self.calendar)
        slice_size, extra_days = divmod(num_days, self.vacations)
        start_inx = 0
        for i in range(self.vacations):
            end_inx = start_inx + slice_size + (1 if i < extra_days else 0)
            self.year_slices.append(self.calendar.iloc[start_inx:end_inx])
            start_inx = end_inx

    def reduce_to_max(self):
        if self.year_slices == []:
            raise ValueError('Year is not split.  Please, run split_year first.')

        reduced_slices = []
        tolerance_days = 1 # We have a holiday cluster in spring. Sacrifice vacation length for better distribution
        for df in self.year_slices:
            max_days_total = df['days_total'].max()
            reduced_slices.append(df[df.days_total >= max_days_total - tolerance_days].copy())

        self.year_slices = reduced_slices

    def best_distribution(self):
        best_vacation_indices = []
        max_gap = -1 # to start with because the first calculated current_gap to be larger might be 0

        all_combinations = list(product(*[df.index for df in self.year_slices]))
        df_concatenated = pd.concat(self.year_slices)

        for combo in all_combinations:
            current_gap = 0
            for i in range(len(combo) - 1):
                end_date_current = df_concatenated.loc[combo[i], 'end_date']
                start_date_next = df_concatenated.loc[combo[i+1], 'date']
                gap = (start_date_next - end_date_current).days
                current_gap += gap

            if current_gap > max_gap:
                max_gap = current_gap
                best_vacation_indices = list(combo)

        self.recommendation = df_concatenated.loc[best_vacation_indices]

    def add_extra_days(self):
        if self.extra_days == 0 or self.recommendation is None:
            return

        min_days_total = self.recommendation['days_total'].min()
        candidates = self.recommendation[self.recommendation['days_total'] == min_days_total]

        # shortest or last vacation will be prolonged if more are equally short
        target_idx = candidates.index[-1]

        # If shortest vacation is at years end, extra days will be added before (start) 'date'
        if self.recommendation.at[target_idx, 'end_date'] == pd.Timestamp(f'{self.year}-12-31'):
            self.recommendation.at[target_idx, 'date'] -= pd.Timedelta(days=self.extra_days)
        else:
            self.recommendation.at[target_idx, 'end_date'] += pd.Timedelta(days=self.extra_days)

    def update_days(self):
        if self.recommendation is None:
            return

        for i, row in self.recommendation.iterrows():
            start_date = row['date']
            end_date = row['end_date']

            workdays_total = self.calendar[(self.calendar['date'] >= start_date) & (self.calendar['date'] <= end_date)]['is_workday'].sum()
            self.recommendation.at[i, 'workdays_total'] = workdays_total

        self.recommendation['days_total'] = (self.recommendation['end_date'] - self.recommendation['date']).dt.days + 1

    def included_holidays(self):
        if self.recommendation is None:
            raise ValueError("recommendation is not defined. Please run best_distribution first.")

        incl_holidays = []

        for _, row in self.recommendation.iterrows():
            start_date = row['date']
            end_date = row['end_date']
            included_holidays = self.holidays[(self.holidays['date'] >= start_date) & (self.holidays['date'] <= end_date)]['fname'].tolist()
            incl_holidays.append(included_holidays)

        self.recommendation['incl_holidays'] = incl_holidays

    def find_best_vacations(self):
        self.create_calendar()
        self.add_holidays()
        self.add_possible_end_dates()
        self.split_year()
        self.reduce_to_max()
        self.best_distribution()

        while self.recommendation['workdays_total'].sum() < self.days:
            self.extra_days = self.days - self.recommendation['workdays_total'].sum()
            self.add_extra_days()
            self.update_days()

        self.included_holidays()

if __name__ == "__main__":

    vac_ui = VacationUI()
    holidays = ApiHandler(vac_ui.year, vac_ui.state)
    vs = VacationScheduler(holidays.df, vac_ui.year, vac_ui.days, vac_ui.vacations)
    vac_ui.print_recommendations(vs.recommendation)
