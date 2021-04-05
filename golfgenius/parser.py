from selenium import webdriver
from bs4 import BeautifulSoup
import os
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import itertools
import time
import re
import logging
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())


class GGParser(object):
    def __init__(self, width=1920, height=1080, headless=False, driver_path=None,
                 screenshots_enabled=True, screenshot_directory='.screenshots'):
        if driver_path is None:
            driver_path = os.path.join(os.path.dirname(__file__), "drivers", "firefox", "0.28", "geckodriver")
        self.screenshots_enabled = screenshots_enabled
        self.screenshot_directory = os.path.abspath(screenshot_directory)
        self.screenshot_count = 0
        if screenshots_enabled:
            if not os.path.isdir(self.screenshot_directory):
                os.makedirs(self.screenshot_directory)
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        self.driver = webdriver.Firefox(
            service_log_path=os.path.devnull,
            options=options,
            executable_path=os.path.abspath(driver_path))
        self.driver.set_window_size(width, height)
        self.base_url = 'https://www.golfgenius.com/'
        self.login_url = self.base_url + "golfgenius"
        logger.debug("opened FireFox driver")
        self.landing_page = None

    def screenshot(self, name=None):
        if self.screenshots_enabled:
            self.screenshot_count += 1
            logger.debug("Creating screenshot #{} ({})".format(self.screenshot_count, name))
            try:
                pngdata = self.driver.get_screenshot_as_png()
                if name is None:
                    fname = os.path.join(self.screenshot_directory, 'screenshot-{}.png'.format(self.screenshot_count))
                else:
                    fname = os.path.join(self.screenshot_directory, '{}.png'.format(name))
                with open(fname, 'wb') as fp:
                    fp.write(pngdata)
                logger.debug("Created screenshot {}".format(fname))
            except:
                logger.error("Unable to save screenshot", exc_info=True)
        else:
            logger.debug("Ignoring screenshot {}".format(name))

    def close(self):
        logger.debug("closing FireFox driver")
        return self.driver.close()

    def sign_in(self, ggid):
        login_url = self.login_url
        logger.debug("Opening %s" % login_url)
        self.driver.get(login_url)
        time.sleep(2)
        logger.debug("Signing in")
        login_button = self._get_element(self.soup.find('a', text='SIGN IN'))
        login_button.click()
        time.sleep(1)
        ggid_input = self._get_element(self.soup.find('input', {u"placeholder": u"Enter Your GGID", u"type": u"text"}))
        ggid_input.clear()
        ggid_input.send_keys(ggid)
        sign_in_button = self._get_element(self.soup.find('input', type="submit", value="Sign In"))
        self.screenshot(name="sign_in")
        sign_in_button.click()
        time.sleep(5)
        sign_in_button2 = self._get_element(self.soup.find('input', type="submit", value="Sign In"))
        self.screenshot(name="sign_in__select_name")
        sign_in_button2.click()
        logger.debug("Waiting 5 secs")
        time.sleep(5)
        logger.debug("Sign In Complete")

    def _parse_tournaments(self):
        results = {}
        logger.debug("Finding tournament IDs")
        tournaments = self._get_all_tournament_ids()
        tournament_ids = [_id for _id, name in tournaments]
        teams = self._get_teams(tournament_ids)
        assert teams is not None, "Unable to parse teams"
        results["teams"] = teams
        logger.debug("populating scores..")
        self._populate_scores(tournament_ids, results)
        return results

    def _populate_scores(self, tournament_ids, results):
        logger.debug("Parsing all scores")
        results["scores"] = {}
        for tournament_id in tournament_ids:
            self.driver.get(self.base_url + "tournaments2/details?adjusting=false&event_id=%s" % tournament_id)
            logger.debug("waiting 3 seconds")
            table = self.soup.find('table', {"class": "scorecard"})
            if table:
                m = re.search("(\d+)\?round_index=(\d+)", tournament_id)
                if m:
                    event_id = m.group(1)
                    round_index = m.group(2)
                else:
                    event_id = self.screenshot_count + 1
                    round_index = tournament_id
                self.screenshot("round-{}-{}".format(round_index, event_id))

                for player_row in [tr for tr in table.find_all('tr', {"class": "net-line"}) if tr.attrs.get("data-net-name") is not None]:
                    player_name = player_row.attrs["data-net-name"].strip()
                    if player_name not in results["scores"]:
                        logger.debug("Creating scores for %s" % player_name)
                        results["scores"][player_name] = {}
                    results["scores"][player_name]["scores"] = {}

                    for score in player_row.find_all('td', {'class': 'score'}):
                        hole, value_int, score_type = None, None, None
                        hole_list = [a for a in score.attrs["class"] if a.startswith('hole')]
                        if len(hole_list) == 1:
                            hole = hole_list[0].replace("hole", "")
                        value = score.find('div', {"class": "single-score"}).text.strip()
                        if value.isdigit():
                            value_int = int(value)
                        type_list = [a for a in score.attrs["class"] if a.endswith('-hole')]
                        if len(type_list) == 1:
                            score_type = type_list[0].replace('-hole', '')
                        if hole is not None and value_int is not None and score_type is not None:
                            if hole not in results["scores"][player_name]["scores"]:
                                results["scores"][player_name]["scores"][hole] = {"score": value_int, "type": score_type}
                                logger.debug("recorded score for %s hole %s: %s" % (player_name, hole, results["scores"][player_name]["scores"][hole]))

    def _get_teams(self, tournament_ids):
        logger.debug("looking up teams..")
        teams = []
        for tournament_id in tournament_ids:
            self.driver.get(self.base_url + "tournaments2/details?adjusting=false&event_id=%s" % tournament_id)
            logger.debug("waiting 3 seconds")
            time.sleep(3)
            table = self.soup.find('table', {"class": "scorecard"})
            if table:
                for tr in table.find_all("tr", {"class": "aggregate_score"}):
                    if "data-aggregate-name" in tr.attrs:
                        team_str = tr.attrs["data-aggregate-name"]
                        team = [x.strip() for x in team_str.split("+")]
                        logger.debug("Found team: %s" % team)
                        teams.append(team)
            if teams:
                return teams

    def _get_all_tournament_ids(self):
        logger.debug("Finding tournaments")
        tournaments = [(t.attrs["href"].split('/')[-1], t.text.strip()) for t in self.soup.find_all('a', {"class": "expand-tournament"})]
        logger.debug("Found %s tournaments" % len(tournaments))
        return tournaments

    def iter_rounds(self, ggid, filter=None):
        """
        :param ggid: Golf Genius ID
        :param filter: Optional compiled re to match against round names to pull
        :return: results as dict
        """
        try:
            logger.info("Logging into {}".format(self.login_url))
            self.sign_in(ggid)
            logger.debug("Loading results")
            self.landing_page = self.driver.current_url
            results_link = self.soup.find('a', text=re.compile(r"\s*Results\s*"))
            results_button = self._get_element(results_link)
            logger.debug("Clicking results_button")
            results_button.click()
            logger.debug("Waiting 5 seconds")
            time.sleep(5)
            results_landing_page = self.driver.current_url
            logger.debug("Switching to iframe")
            self.driver.switch_to.frame("page_iframe")
            logger.debug("Waiting for 3 seconds")
            time.sleep(3)
            logger.debug("Finding Rounds")
            seen = {}
            select_element = self.soup.find(id='round')
            all_options = select_element.find_all('option')
            if isinstance(filter, re.Pattern):
                filtered_options = [option for option in all_options if filter.match(option.text.strip()) is not None]
                logger.info("Discovered {} rounds matching pattern {}. ({} total)".format(
                    len(filtered_options), filter.pattern, len(all_options)
                ))
            else:
                filtered_options = all_options
                logger.info("Discovered {} rounds.".format(
                    len(filtered_options)))

            for option in filtered_options:
                round_name = option.text.strip()
                round_id = option.attrs["value"]
                if round_id in seen:
                    continue
                logger.debug("Parsing round %s (%s)" % (round_name, round_id))
                self._get_element(option).click()
                try:
                    seen[round_id] = True
                    round_results = self._parse_tournaments()
                    player_count = len(round_results.get("scores", {}))
                    logger.info("Stored {} ({} players)".format(round_name, player_count))
                    yield round_name, {"name": round_name, "results": round_results}
                except Exception as exc:
                    import traceback
                    logger.critical("Error parsing round %s" % round_name, exc_info=True)
                    seen[round_id] = True
                finally:
                    logger.debug("Reloading results landing page")
                    self.driver.get(results_landing_page)
                    self.driver.switch_to.default_content()
                    logger.debug("Switching back to iframe")
                    self.driver.switch_to.frame("page_iframe")

        finally:
            pass

    def parse(self, ggid, filter=None):
        """ 
        :param ggid: Golf Genius ID
        :param filter: Optional compiled re to match against round names to pull
        :return: results as dict
        """
        try:
            logger.info("Logging into {}".format(self.login_url))
            self.sign_in(ggid)
            self.screenshot(name="sign_in")
            logger.debug("Loading results")
            self.landing_page = self.driver.current_url
            results_link = self.soup.find('a', text=re.compile(r"\s*Results\s*"))
            results_button = self._get_element(results_link)
            logger.debug("Clicking results_button")
            results_button.click()
            logger.debug("Waiting 5 seconds")
            time.sleep(5)
            self.screenshot(name="results")
            results_landing_page = self.driver.current_url
            logger.debug("Switching to iframe")
            self.driver.switch_to.frame("page_iframe")
            logger.debug("Waiting for 3 seconds")
            time.sleep(3)
            logger.debug("Finding Rounds")
            results = {}
            select_element = self.soup.find(id='round')
            for option in select_element.find_all('option'):
                round_name = option.text.strip()
                round_id = option.attrs["value"]
                if round_id in results:
                    continue
                if isinstance(filter, re.Pattern) and filter.match(round_name) is None:
                    logger.info("Ignoring round {0} due to filter {1}".format(round_name, str(filter.pattern)[:50]))
                    continue
                logger.debug("Parsing round %s (%s)" % (round_name, round_id))
                self._get_element(option).click()
                self.screenshot(name="round %s" % round_name)
                try:
                    results[round_id] = {
                        "name": round_name,
                        "results": self._parse_tournaments()
                    }
                    logger.info("Parsed {}".format(round_name))
                except Exception as exc:
                    import traceback
                    logger.critical("Error parsing round %s" % round_name, exc_info=True)
                    results[round_id] = {
                        "name": round_name,
                        "results": {},
                        "error": str(exc),
                        "traceback": traceback.format_exc()
                    }
                finally:
                    logger.debug("Reloading results landing page")
                    self.driver.get(results_landing_page)
                    self.driver.switch_to.default_content()
                    logger.debug("Switching back to iframe")
                    self.driver.switch_to.frame("page_iframe")

            return results
        finally:
            self.screenshot("parse_final")

    def _get_element(self, e):
        xpath = self.xpath_soup(e)
        return self.driver.find_element_by_xpath(xpath)

    @property
    def soup(self):
        return BeautifulSoup(self.driver.page_source, "html.parser")

    def xpath_soup(self, element):
        """
        Generate xpath of soup element
        :param element: bs4 text or node
        :return: xpath as string
        """
        components = []
        child = element if element.name else element.parent
        for parent in child.parents:
            """
            @type parent: bs4.element.Tag
            """
            previous = itertools.islice(parent.children, 0, parent.contents.index(child))
            xpath_tag = child.name
            xpath_index = sum(1 for i in previous if i.name == xpath_tag) + 1
            components.append(xpath_tag if xpath_index == 1 else '%s[%d]' % (xpath_tag, xpath_index))
            child = parent
        components.reverse()
        return '/%s' % '/'.join(components)

    def to_json(self, ggid, path, filter=None):
        """ Parses results and saves as json files to output_dir.
        :param ggid: Golf Genius ID
        :param path: Directory to save json files to
        :param filter: A compiled regex filter
        :return: None
        """
        assert os.path.isdir(path), "output_dir must be a directory"
        results = self.parse(ggid, filter=filter)
        for round_id, result in results.items():
            with open(os.path.join(path, "%s.json" % result["name"]), "w") as fp:
                json.dump(result, fp, indent=4)

