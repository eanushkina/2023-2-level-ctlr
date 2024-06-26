"""
Crawler implementation.
"""
# pylint: disable=too-many-arguments, too-many-instance-attributes, unused-import, undefined-variable
import datetime
import json
import pathlib
import random
import re
import time
from typing import Pattern, Union

import requests
from bs4 import BeautifulSoup

from core_utils.article.article import Article
from core_utils.article.io import to_meta, to_raw
from core_utils.config_dto import ConfigDTO
from core_utils.constants import ASSETS_PATH, CRAWLER_CONFIG_PATH


class IncorrectSeedURLError(Exception):
    pass


class NumberOfArticlesOutOfRangeError(Exception):
    pass


class IncorrectNumberOfArticlesError(Exception):
    pass


class IncorrectHeadersError(Exception):
    pass


class IncorrectEncodingError(Exception):
    pass


class IncorrectTimeoutError(Exception):
    pass


class IncorrectVerifyError(Exception):
    pass


class Config:
    """
    Class for unpacking and validating configurations.
    """

    def __init__(self, path_to_config: pathlib.Path) -> None:
        """
        Initialize an instance of the Config class.

        Args:
            path_to_config (pathlib.Path): Path to configuration.
        """

        self.path_to_config = path_to_config
        self._validate_config_content()
        self.config_dto = self._extract_config_content()

        self._seed_urls = self.config_dto.seed_urls
        self._num_articles = self.config_dto.total_articles
        self._headers = self.config_dto.headers
        self._encoding = self.config_dto.encoding
        self._timeout = self.config_dto.timeout
        self._should_verify_certificate = self.config_dto.should_verify_certificate
        self._headless_mode = self.config_dto.headless_mode

    def _extract_config_content(self) -> ConfigDTO:
        """
        Get config values.

        Returns:
            ConfigDTO: Config values
        """

        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return ConfigDTO(
            config["seed_urls"],
            config["total_articles_to_find_and_parse"],
            config["headers"],
            config["encoding"],
            config["timeout"],
            config["should_verify_certificate"],
            config["headless_mode"],
        )

    def _validate_config_content(self) -> None:
        """
        Ensure configuration parameters are not corrupt.
        """
        with open(self.path_to_config, 'r', encoding='utf-8') as f:
            config = json.load(f)

            if not isinstance(config['seed_urls'], list):
                raise IncorrectSeedURLError

            if not (isinstance(config['seed_urls'], list)
                    and all(re.match(r'https?://(www.)?', seed_url) for seed_url in config['seed_urls'])):
                raise IncorrectSeedURLError

            if (not isinstance(config['total_articles_to_find_and_parse'], int) or
                    config['total_articles_to_find_and_parse'] <= 0):
                raise IncorrectNumberOfArticlesError

            if not 1 < config['total_articles_to_find_and_parse'] <= 150:
                raise NumberOfArticlesOutOfRangeError

            if not isinstance(config['headers'], dict):
                raise IncorrectHeadersError

            if not isinstance(config['encoding'], str):
                raise IncorrectEncodingError

            if not isinstance(config['timeout'], int) or not 0 < config['timeout'] < 60:
                raise IncorrectTimeoutError

            if (not isinstance(config['should_verify_certificate'], bool) or
                    not isinstance(config['headless_mode'], bool)):
                raise IncorrectVerifyError

    def get_seed_urls(self) -> list[str]:
        """
        Retrieve seed urls.

        Returns:
            list[str]: Seed urls
        """
        return self._seed_urls

    def get_num_articles(self) -> int:
        """
        Retrieve total number of articles to scrape.

        Returns:
            int: Total number of articles to scrape
        """
        return self._num_articles

    def get_headers(self) -> dict[str, str]:
        """
        Retrieve headers to use during requesting.

        Returns:
            dict[str, str]: Headers
        """
        return self._headers

    def get_encoding(self) -> str:
        """
        Retrieve encoding to use during parsing.

        Returns:
            str: Encoding
        """
        return self._encoding

    def get_timeout(self) -> int:
        """
        Retrieve number of seconds to wait for response.

        Returns:
            int: Number of seconds to wait for response
        """
        return self._timeout

    def get_verify_certificate(self) -> bool:
        """
        Retrieve whether to verify certificate.

        Returns:
            bool: Whether to verify certificate or not
        """
        return self._should_verify_certificate

    def get_headless_mode(self) -> bool:
        """
        Retrieve whether to use headless mode.

        Returns:
            bool: Whether to use headless mode or not
        """
        return self._headless_mode


def make_request(url: str, config: Config) -> requests.models.Response:
    """
    Deliver a response from a request with given configuration.

    Args:
        url (str): Site url
        config (Config): Configuration

    Returns:
        requests.models.Response: A response from a request
    """
    periods = random.randrange(3)
    time.sleep(periods)

    response = requests.get(url=url, headers=config.get_headers(),
                            timeout=config.get_timeout(),
                            verify=config.get_verify_certificate())
    return response


class Crawler:
    """
    Crawler implementation.
    """

    url_pattern: Union[Pattern, str]

    def __init__(self, config: Config) -> None:
        """
        Initialize an instance of the Crawler class.

        Args:
            config (Config): Configuration
        """
        self.urls = []
        self.config = config
        self.url_pattern = 'https://www.comnews.ru/'

    def _extract_url(self, article_bs: BeautifulSoup) -> str:
        """
        Find and retrieve url from HTML.

        Args:
            article_bs (bs4.BeautifulSoup): BeautifulSoup instance

        Returns:
            str: Url from HTML
        """

        links = article_bs.find(name='div', class_='region region-content')
        for link in links.find_all('a'):
            if link.get('href').startswith("/content/"):
                url = self.url_pattern + link.get('href')
                if url not in self.urls:
                    self.urls.append(url)
                    return url

    def find_articles(self) -> None:
        """
        Find articles.
        """
        seed_urls = self.get_search_urls()
        n_len = self.config.get_num_articles()

        while len(self.urls) < n_len:

            for seed_url in seed_urls:
                response = make_request(seed_url, self.config)
                if not response.ok:
                    continue

                soup = BeautifulSoup(response.text, features='html.parser')

                new_url = self._extract_url(soup)
                if len(self.urls) >= n_len:
                    break
                self.urls.append(new_url)

                if len(self.urls) >= n_len:
                    break

    def get_search_urls(self) -> list:
        """
        Get seed_urls param.

        Returns:
            list: seed_urls param
        """
        return self.config.get_seed_urls()


# 10
# 4, 6, 8, 10


class HTMLParser:
    """
    HTMLParser implementation.
    """

    def __init__(self, full_url: str, article_id: int, config: Config) -> None:
        """
        Initialize an instance of the HTMLParser class.

        Args:
            full_url (str): Site url
            article_id (int): Article id
            config (Config): Configuration
        """
        self.full_url = full_url
        self.article_id = article_id
        self.config = config
        self.article = Article(self.full_url, self.article_id)

    def _fill_article_with_text(self, article_soup: BeautifulSoup) -> None:
        """
        Find text of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        texts = []
        text_paragraphs = article_soup.find_all(class_="field field-text full-html field-name-body")
        for paragraph in text_paragraphs:
            texts.append(paragraph.text)
        self.article.text = ''.join(texts)

    def _fill_article_with_meta_information(self, article_soup: BeautifulSoup) -> None:
        """
        Find meta information of article.

        Args:
            article_soup (bs4.BeautifulSoup): BeautifulSoup instance
        """
        self.article.title = article_soup.find('h1').text

        date_str = article_soup.find(class_='field field-text field-name-date')
        if date_str:
            self.article.date = self.unify_date_format(date_str.text)

        topics = article_soup.find_all(class_='tags')
        if topics:
            for topic in topics:
                tag = topic.find('a').text
                self.article.topics.append(tag)
        else:
            self.article.topics.append("NOT FOUND")

        self.article.author = []
        authors = article_soup.find_all(class_="field field-text field-multiple person field-name-authors")
        if authors:
            for author in authors:
                tmp = author.find('span').text.split(' ')[-1]
                self.article.author.append(tmp)
        else:
            self.article.author.append("NOT FOUND")

    def unify_date_format(self, date_str: str) -> datetime.datetime:
        """
        Unify date format.

        Args:
            date_str (str): Date in text format

        Returns:
            datetime.datetime: Datetime object
        """
        return datetime.datetime.strptime(date_str, '%d.%m.%Y')

    def parse(self) -> Union[Article, bool, list]:
        """
        Parse each article.

        Returns:
            Union[Article, bool, list]: Article instance
        """
        response = make_request(self.full_url, self.config)
        if response.ok:
            article_bs = BeautifulSoup(response.text, 'html.parser')
            self._fill_article_with_text(article_bs)
            self._fill_article_with_meta_information(article_bs)

        return self.article


def prepare_environment(base_path: Union[pathlib.Path, str]) -> None:
    """
    Create ASSETS_PATH folder if no created and remove existing folder.

    Args:
        base_path (Union[pathlib.Path, str]): Path where articles stores
    """
    if not base_path.exists():
        base_path.mkdir(parents=True, exist_ok=True)
    else:
        for file in base_path.iterdir():
            file.unlink()


def main() -> None:
    """
    Entrypoint for scrapper module.
    """
    conf = Config(CRAWLER_CONFIG_PATH)
    crawler = Crawler(conf)
    crawler.find_articles()
    prepare_environment(ASSETS_PATH)

    for i, url in enumerate(crawler.urls, 1):
        parser = HTMLParser(url, i, conf)
        article = parser.parse()
        to_raw(article)
        to_meta(article)


if __name__ == "__main__":
    main()
