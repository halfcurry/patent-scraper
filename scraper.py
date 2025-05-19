import csv
import json
import time
import requests
from bs4 import BeautifulSoup
import re
import argparse
from typing import Dict, List, Any, Optional


class PatentScraper:
    """Class for scraping patent details from Google Patents."""
    
    def __init__(self, sleep_time: float = 1.0):
        """
        Initialize the scraper.
        
        Args:
            sleep_time: Time to sleep between requests (to avoid rate limiting)
        """
        self.base_url = "https://patents.google.com/patent/"
        self.sleep_time = sleep_time
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def clean_patent_id(self, patent_id: str) -> str:
        """
        Clean patent ID by removing non-alphanumeric characters.
        
        Args:
            patent_id: Raw patent ID from CSV
            
        Returns:
            Cleaned patent ID
        """
        # Extract alphanumeric and allowed characters (keeping the basic patent format)
        # This handles common formats like US6285999B1 or US-6285999-B1
        cleaned = re.sub(r'[^A-Za-z0-9]', '', patent_id)
        return cleaned
    
    def get_patent_url(self, patent_id: str) -> str:
        """
        Get the full URL for a patent.
        
        Args:
            patent_id: Patent ID
            
        Returns:
            Full URL for the patent
        """
        return f"{self.base_url}US{patent_id}B2"
    
    def scrape_patent(self, patent_id: str) -> Dict[str, Any]:
        """
        Scrape details for a single patent.
        
        Args:
            patent_id: Patent ID
            
        Returns:
            Dictionary with patent details
        """
        cleaned_id = self.clean_patent_id(patent_id)
        url = self.get_patent_url(cleaned_id)
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                return {
                    "patent_id": patent_id,
                    "error": f"Failed to retrieve patent, status code: {response.status_code}"
                }
                
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract patent data
            data = {
                "patent_id": cleaned_id,
                "url": url,
                "title": self._extract_title(soup),
                "abstract": self._extract_abstract(soup),
                # "inventors": self._extract_inventors(soup),
                # "assignees": self._extract_assignees(soup),
                # "filing_date": self._extract_filing_date(soup),
                # "publication_date": self._extract_publication_date(soup),
                # "classifications": self._extract_classifications(soup),
                "description": self._extract_description(soup),
                # "claims": self._extract_claims(soup),
                # "citations": self._extract_citations(soup),
            }
            
            return data
            
        except Exception as e:
            return {
                "patent_id": patent_id,
                "error": str(e)
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract patent title."""
        title_elem = soup.select_one('h1.title')
        return title_elem.text.strip() if title_elem else ""
    
    def _extract_abstract(self, soup: BeautifulSoup) -> str:
        """Extract patent abstract."""
        abstract_elem = soup.select_one('div.abstract')
        return abstract_elem.text.strip() if abstract_elem else ""
    
    def _extract_inventors(self, soup: BeautifulSoup) -> List[str]:
        """Extract patent inventors."""
        inventors = []
        inventor_elems = soup.select('dd[itemprop="inventor"]')
        
        for elem in inventor_elems:
            name_elem = elem.select_one('span[itemprop="name"]')
            if name_elem:
                inventors.append(name_elem.text.strip())
        
        return inventors
    
    def _extract_assignees(self, soup: BeautifulSoup) -> List[str]:
        """Extract patent assignees."""
        assignees = []
        assignee_elems = soup.select('dd[itemprop="assignee"]')
        
        for elem in assignee_elems:
            name_elem = elem.select_one('span[itemprop="name"]')
            if name_elem:
                assignees.append(name_elem.text.strip())
        
        return assignees
    
    def _extract_filing_date(self, soup: BeautifulSoup) -> str:
        """Extract filing date."""
        date_elem = soup.select_one('dd[itemprop="filingDate"] time')
        return date_elem.text.strip() if date_elem else ""
    
    def _extract_publication_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date."""
        date_elem = soup.select_one('dd[itemprop="publicationDate"] time')
        return date_elem.text.strip() if date_elem else ""
    
    def _extract_classifications(self, soup: BeautifulSoup) -> List[str]:
        """Extract patent classifications."""
        classifications = []
        classification_elems = soup.select('li.classification')
        
        for elem in classification_elems:
            classifications.append(elem.text.strip())
        
        return classifications
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract patent description."""
        description_section = soup.select_one('section[itemprop="description"]')
        if not description_section:
            return ""
            
        # Get all paragraphs in the description section
        paragraphs = description_section.select('div.description-paragraph')
        description_text = "\n\n".join([p.text.strip() for p in paragraphs])
        
        return description_text
    
    def _extract_claims(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract patent claims."""
        claims = []
        claims_section = soup.select_one('section[itemprop="claims"]')
        
        if not claims_section:
            return claims
            
        claim_elements = claims_section.select('div.claim')
        
        for i, claim_elem in enumerate(claim_elements):
            claim_text = claim_elem.text.strip()
            claim_num = i + 1
            
            # Try to determine if it's an independent or dependent claim
            # Usually dependent claims reference other claims
            is_dependent = bool(re.search(r'claim\s+\d+', claim_text.lower()))
            
            # Find which claim it depends on, if any
            depends_on = None
            if is_dependent:
                dependency_match = re.search(r'claim\s+(\d+)', claim_text.lower())
                if dependency_match:
                    depends_on = int(dependency_match.group(1))
            
            claims.append({
                "number": claim_num,
                "text": claim_text,
                "is_dependent": is_dependent,
                "depends_on": depends_on
            })
        
        return claims
    
    def _extract_citations(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract patent citations."""
        citations = []
        citation_elems = soup.select('tr.citation')
        
        for elem in citation_elems:
            citation_id = elem.select_one('td.patent-id')
            citation_title = elem.select_one('td.patent-title')
            
            if citation_id and citation_title:
                citations.append({
                    "id": citation_id.text.strip(),
                    "title": citation_title.text.strip()
                })
        
        return citations


def process_csv(input_file: str, output_file: str, sleep_time: float = 1.0):
    """
    Process CSV file and scrape patents.
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output JSON file
        sleep_time: Time to sleep between requests
    """
    scraper = PatentScraper(sleep_time)
    results = []
    
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            
            # Skip header if present (optional)
            # next(reader, None)
            
            for i, row in enumerate(reader):
                if row and len(row) > 0:
                    patent_id = row[0].strip()
                    
                    print(f"Processing patent ID: {patent_id} (row {i+1})")
                    
                    patent_data = scraper.scrape_patent(patent_id)
                    results.append(patent_data)
                    
                    # Sleep to avoid rate limiting
                    time.sleep(scraper.sleep_time)
    
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
    
    # Write results to JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"Completed! Scraped {len(results)} patents. Results saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape patent details from Google Patents.')
    parser.add_argument('input_csv', help='Input CSV file with patent IDs in the first column')
    parser.add_argument('output_json', help='Output JSON file')
    parser.add_argument('--sleep', type=float, default=1.0, help='Sleep time between requests (default: 1.0 seconds)')
    
    args = parser.parse_args()
    
    process_csv(args.input_csv, args.output_json, args.sleep)