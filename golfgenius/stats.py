import json
import os
from operator import itemgetter
import re
import datetime
import numpy as np

MONTH_IDX=['january', 'february', 'march', 'april', 'may', 'june', 'july',
           'august', 'september', 'october', 'november', 'december']


class Stats(object):
    def __init__(self, results_dir='./results', timedelta=None):
        """

        :param results_dir: output_dir to results directory
        :param timedelta: a relative datetime.timedelta to limit range of results
        """
        self.results_dir = results_dir
        self.results = {}
        self.round_regexp = re.compile(r'Round\s+(?P<round_id>\d+)\s+\((Fri|Sat|Sun|Mon|Tue|Wed|Thu)\,\s+(?P<month>\w+)\s+(?P<day>\d+)\)')
        for f in os.listdir(self.results_dir):
            if f.endswith('.json'):
                with open(os.path.join(self.results_dir, f), 'r') as fp:
                    data = json.load(fp)
                    m = self.round_regexp.search(data["name"])
                    if m:
                        round_info = m.groupdict()
                        if int(round_info["round_id"]) > 60:
                            year = 2021
                        else:
                            year = 2020
                        data["results"]["date"] = datetime.date(
                            year, MONTH_IDX.index(round_info["month"].lower()) + 1, int(round_info["day"]))
                    elif timedelta is not None:
                        print("Unable to find round date for round %s, skipping..." % data["name"])
                        continue
                    else:
                        print("Unable to find round date for round %s, assuming today..." % data["name"])
                        data["results"]["date"] = datetime.date.today()
                    if timedelta is None:
                        self.results[data["name"]] = data["results"]
                    else:
                        cutoff_date = datetime.date.today() - timedelta
                        if data["results"]["date"] > cutoff_date:
                            self.results[data["name"]] = data["results"]

    def player_scores(self):
        scoring = {}
        for player in self.all_players():
            scoring[player] = []
            for round_name, results in self.results.items():
                round_date = results["date"]
                player_data = results["scores"].get(player)
                if player_data:
                    round_scores = [h["score"] for h in player_data["scores"].values()]
                    if len(round_scores) == 18:
                        eagles = [
                            hole for hole, val in player_data["scores"].items() if val["type"] == "eagle"
                        ]
                        birdies = [
                            hole for hole, val in player_data["scores"].items() if val["type"] == "birdie"
                        ]
                        pars = [
                            hole for hole, val in player_data["scores"].items() if val["type"] == "par"
                        ]
                        bogeys = [
                            hole for hole, val in player_data["scores"].items() if val["type"] == "plus1"
                        ]
                        double_bogeys = [
                            hole for hole, val in player_data["scores"].items() if val["type"] == "plus2"
                        ]
                        scoring[player].append(
                            {
                                "date": round_date,
                                "round": round_name,
                                "score": sum(round_scores),
                                "eagles": eagles,
                                "birdies": birdies,
                                "pars": pars,
                                "bogeys": bogeys,
                                "double_bogeys": double_bogeys,
                                "hole_data": player_data["scores"]
                            }
                        )
            scoring[player] = sorted(scoring[player], key=itemgetter("date"))
        return scoring

    @staticmethod
    def scores_tolist(scores):
        scores_list = []
        for k in [str(x) for x in range(1, 19)]:
            scores_list.append(scores[k])
        return scores_list

    def iter_player_data(self):
        for player in self.all_players():
            stats = {"rounds": [], "name": player}
            for round_name, results in self.results.items():
                round_data = {}
                round_date = results["date"]
                player_data = results["scores"].get(player)
                if player_data:
                    round_scores = [h["score"] for h in player_data["scores"].values()]
                    if len(round_scores) == 18:
                        score_list = self.scores_tolist(player_data["scores"])
                        round_data["score"] = sum(round_scores)
                        round_data["total"] = sum(round_scores)
                        round_data["front"] = score_list[0:9]
                        round_data["back"] = score_list[9:18]
                        round_data["out"] = sum(round_scores[0:9])
                        round_data["in"] = sum(round_scores[9:18])
                        round_data["name"] = round_name
                        round_data["date"] = round_date
                        round_data["date_timestamp"] = round_date.toordinal()
                        stats["rounds"].append(round_data)
            if len(stats["rounds"]) > 0:
                stats["rounds"] = sorted(stats["rounds"], key=itemgetter("date"))
            stats["scoring_average"] = np.average([r["score"] for r in stats["rounds"] if "score" in r])
            stats["scoring_average"] = float("%.3f" % stats["scoring_average"])
            yield player, stats

    def all_players(self):
        players = set()
        for result in self.results.values():
            for team in result["teams"]:
                for player in team:
                    players.add(player)
        return list(players)

    def _hole_score_averages(self, n_rounds=None, min_rounds=0, weighted_rounds=0, types=["birdie", "eagle"]):
        if isinstance(types, str):
            types = [types]
        scoring = {}
        averages = {}
        for player in self.all_players():
            scoring[player] = []
            for results in self.results.values():
                player_data = results["scores"].get(player)
                if player_data:
                    if len(player_data["scores"]) == 18:
                        birdies_or_better_scores = [h["type"] for h in player_data["scores"].values() if h["type"] in types]
                        scoring[player].append(len(birdies_or_better_scores))
            if scoring[player] and len(scoring[player]) >= min_rounds:
                if n_rounds is not None:
                    if len(scoring[player]) < n_rounds:
                        continue
                    scoring[player] = scoring[player][-n_rounds:]
                if weighted_rounds is None:
                    averages[player] = np.average(scoring[player])
                elif len(scoring[player]) > weighted_rounds:
                    diff = len(scoring[player]) - weighted_rounds
                    weights = []
                    w = 1
                    for i in range(diff):
                        weights.append(w)
                    for i in range(len(scoring[player]) - diff):
                        w = w * 1.5
                        weights.append(w)
                    averages[player] = np.average(scoring[player], weights=weights)
                else:
                    averages[player] = np.average(scoring[player])
        return sorted(averages.items(), key=itemgetter(1), reverse=True)

    def birdies_or_better_averages(self, n_rounds=None, min_rounds=0, weighted_rounds=0):
        return self._hole_score_averages(n_rounds=n_rounds, min_rounds=min_rounds, weighted_rounds=weighted_rounds,
                                         types=["birdie", "eagle"])

    def par_averages(self, n_rounds=None, min_rounds=0, weighted_rounds=0):
        return self._hole_score_averages(n_rounds=n_rounds, min_rounds=min_rounds, weighted_rounds=weighted_rounds,
                                         types="par")
    
    def scoring_averages(self, min_rounds=0):
        scoring = {}
        averages = {}
        for player in self.all_players():
            scoring[player] = []
            for results in self.results.values():
                player_data = results["scores"].get(player)
                if player_data:
                    round_scores = [h["score"] for h in player_data["scores"].values()]
                    if len(round_scores) == 18:
                        scoring[player].append(sum(round_scores))
            if scoring[player] and len(scoring[player]) >= min_rounds:
                averages[player] = sum(scoring[player]) / len(scoring[player])
        return sorted(averages.items(), key=itemgetter(1))

    def reject_outliers(self, raw_data, m=2.):
        data = np.array(raw_data)
        return list(data[abs(data - np.mean(data)) < m * np.std(data)])

    def weighted_sanitized_scoring_averages(self, n_rounds=None, weighted_rounds=3, outlier_distance=2.):
        player_scores = self.player_scores()
        rankings = []
        for player_name, data in player_scores.items():
            # Filter to list of scores
            scores = [d["score"] for d in data if d.get("score")]
            if len(scores) == 0:
                continue
            if n_rounds is not None:
                if len(scores) < n_rounds:
                    continue
                scores = scores[-n_rounds:]
            if outlier_distance is not None:
                scores = self.reject_outliers(scores, m=outlier_distance)
            if weighted_rounds is None:
                rankings.append((player_name, np.average(scores)))
            elif len(scores) > weighted_rounds:
                diff = len(scores) - weighted_rounds
                weights = []
                w = 1
                for i in range(diff):
                    weights.append(w)
                for i in range(len(scores) - diff):
                    w = w * 1.5
                    weights.append(w)
                rankings.append((player_name, np.average(scores, weights=weights)))
        return sorted(rankings, key=itemgetter(1))


if __name__ == '__main__':
    s = Stats('./results')
    output = {
        "Scoring Averages (min 4 rounds)": s.scoring_averages(min_rounds=4)
    }
    print(json.dumps(output, indent=4))
