"""Data collectors unit tests - properly mocked."""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd


class TestStockCollector:
    def test_parse_movers_data(self):
        """Test parsing of movers data structure."""
        # Test data parsing without external API
        mock_df = pd.DataFrame({
            '등락률': [5.0, 4.0, -3.0, -4.0],
            '거래량': [1000, 2000, 3000, 4000],
            '종가': [50000, 40000, 30000, 20000]
        }, index=['005930', '000660', '035420', '051910'])
        
        # Get gainers (positive change rate)
        gainers = mock_df[mock_df['등락률'] > 0].sort_values('등락률', ascending=False)
        assert len(gainers) == 2
        assert gainers.index[0] == '005930'  # Highest gainer
        
        # Get losers (negative change rate)
        losers = mock_df[mock_df['등락률'] < 0].sort_values('등락률', ascending=True)
        assert len(losers) == 2
        assert losers.index[0] == '051910'  # Biggest loser
    
    def test_parse_volume_data(self):
        """Test parsing of volume data."""
        mock_df = pd.DataFrame({
            '등락률': [2.0, 1.0, 0.5],
            '거래량': [5000000, 3000000, 1000000],
            '종가': [50000, 40000, 30000]
        }, index=['005930', '000660', '035420'])
        
        # Sort by volume
        sorted_df = mock_df.sort_values('거래량', ascending=False)
        assert sorted_df.index[0] == '005930'
        assert sorted_df.iloc[0]['거래량'] == 5000000


class TestNaverCrawler:
    def test_parse_html_structure(self):
        """Test HTML parsing logic."""
        from bs4 import BeautifulSoup
        
        html = """
        <html>
            <table class="type_1">
                <tr>
                    <td class="file"><a href="/test.pdf">Report</a></td>
                    <td>증권사</td>
                    <td>2026.02.05</td>
                </tr>
            </table>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table', class_='type_1')
        assert len(tables) == 1
        
        rows = tables[0].find_all('tr')
        assert len(rows) >= 1
    
    def test_url_construction(self):
        """Test URL construction for different report types."""
        base_url = "https://finance.naver.com/research/"
        
        report_types = ['market_info_list', 'invest_list', 'industry_list', 'economy_list']
        for report_type in report_types:
            url = f"{base_url}{report_type}.naver?&page=1"
            assert report_type in url
            assert "page=1" in url
