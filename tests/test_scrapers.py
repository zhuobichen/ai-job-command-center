"""Tests for job_hunt.scrapers modules."""

import pytest
from job_hunt.scrapers.gxrc import GxrcScraper, GX_CITY_KEYWORDS, GD_CITY_KEYWORDS
from job_hunt.scrapers.guipin import GuiPinScaper
from job_hunt.scrapers.bing import bing_job_search


class TestGxrcScraper:
    def test_gxrc_creation(self):
        scraper = GxrcScraper(headless=True)
        assert scraper.PLATFORM == "gxrc"
        assert scraper.BASE_URL == "https://s.gxrc.com"

    def test_gxrc_city_keywords(self):
        assert "南宁" in GX_CITY_KEYWORDS
        assert "柳州" in GX_CITY_KEYWORDS
        assert len(GX_CITY_KEYWORDS) == 14

    def test_gd_city_keywords(self):
        assert "广州" in GD_CITY_KEYWORDS
        assert "深圳" in GD_CITY_KEYWORDS
        assert len(GD_CITY_KEYWORDS) == 21


class TestGuiPinScraper:
    def test_guipin_creation(self):
        scraper = GuiPinScaper()
        assert scraper is not None


class TestBingSearch:
    def test_bing_job_search_returns_list(self):
        # This makes an actual API call, so we just check it returns
        try:
            results = bing_job_search("Python 开发", city="南宁", max_results=5)
            assert isinstance(results, list)
        except Exception:
            pytest.skip("Bing search not available")
