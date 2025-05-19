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
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
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
        return f"{self.base_url}US{patent_id}B2/en"  # Added /en to ensure English version
    
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
            print(f"Requesting URL: {url}")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                return {
                    "patent_id": patent_id,
                    "error": f"Failed to retrieve patent, status code: {response.status_code}"
                }
                
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Debug title extraction
            title = self._extract_title(soup)
            # print(f"Extracted title: {title}")
            
            # Extract patent data
            data = {
                "patent_id": cleaned_id,
                "url": url,
                "title": title,
                "abstract": self._extract_abstract(soup),
                "inventors": self._extract_inventors(soup),
                # "assignees": self._extract_assignees(soup),
                "filing_date": self._extract_filing_date(soup),
                "publication_date": self._extract_publication_date(soup),
                # "classifications": self._extract_classifications(soup),
                "description": self._extract_description(soup),
                # "claims": self._extract_claims(soup),
                # "citations": self._extract_citations(soup),
            }
            
            return data
            
        except Exception as e:
            print(f"Error scraping patent {patent_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "patent_id": patent_id,
                "error": str(e)
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract patent title."""
        # Try to find the title using various selectors
        title_selectors = [
            'h1.title',                          # Common selector
            'h1[itemprop="name"]',               # Using itemprop attribute
            'span[itemprop="title"]',            # Alternative using itemprop
            'h1 span[itemprop="title"]',         # Nested inside h1
            'h1.patent-title',                   # Alternative class name
            'title'                              # Fallback to page title
        ]
        
        title = None
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.text.strip():
                title = title_elem.text.strip()
                
                # If using page title, remove site name
                if selector == 'title':
                    # More comprehensive pattern to handle different separators
                    title = re.sub(r'\s*[-–|]\s*Google Patents.*$', '', title)
                    # Also try to remove any patent number prefix
                    title = re.sub(r'^US\d+[A-Z]\d*\s*[-–|:]\s*', '', title)
                
                # If we found a title, break the loop
                if title:
                    break
        
        # Add a fallback method to search for the title
        if not title:
            # Look for any text that appears to be a title
            possible_titles = soup.find_all(['h1', 'h2', 'h3'])
            for elem in possible_titles:
                if elem.text.strip() and 'patent' not in elem.text.lower() and len(elem.text.strip()) > 10:
                    title = elem.text.strip()
                    break
        
        return title if title else "Title could not be extracted"
    
    def _extract_abstract(self, soup: BeautifulSoup) -> str:
        """Extract patent abstract."""
        # Try multiple possible selectors for abstract
        abstract_selectors = [
            'div.abstract',
            'section[itemprop="abstract"]',
            'div[itemprop="abstract"]',
            'span[itemprop="abstract"]',
            'meta[name="description"]'  # Fallback to meta description
        ]
        
        for selector in abstract_selectors:
            abstract_elem = soup.select_one(selector)
            if abstract_elem:
                if selector == 'meta[name="description"]' and 'content' in abstract_elem.attrs:
                    content = abstract_elem.attrs['content']
                    # Try to extract the abstract part after the title
                    if ':' in content:
                        return content.split(':', 1)[1].strip()
                    return content
                else:
                    return abstract_elem.text.strip()
        
        return ""
    
    def _extract_inventors(self, soup: BeautifulSoup) -> List[str]:
        """Extract patent inventors."""
        inventors = []
        
        # Try multiple possible selectors for inventors
        inventor_selectors = [
            'dd[itemprop="inventor"] span[itemprop="name"]',
            'meta[name="DC.contributor"]',
            'span[itemprop="inventor"] span[itemprop="name"]',
            'dd[itemprop="inventor"]'
        ]
        
        for selector in inventor_selectors:
            elements = soup.select(selector)
            if elements:
                if selector == 'meta[name="DC.contributor"]':
                    for elem in elements:
                        if 'content' in elem.attrs:
                            inventors.append(elem.attrs['content'].strip())
                else:
                    for elem in elements:
                        inventors.append(elem.text.strip())
                
                # If we found inventors, return them
                if inventors:
                    return inventors
        
        # If no inventors found with specific selectors, try to find them in text
        inventor_section = soup.find(string=re.compile('Inventors?:|Inventor\(s\):'))
        if inventor_section:
            parent = inventor_section.parent
            if parent:
                # Look for the closest dd or li element
                inventor_container = parent.find_next(['dd', 'li', 'div', 'span'])
                if inventor_container:
                    # Split by commas or semicolons
                    for name in re.split(r'[,;]', inventor_container.text):
                        if name.strip():
                            inventors.append(name.strip())
        
        return inventors
    
    def _extract_assignees(self, soup: BeautifulSoup) -> List[str]:
        """Extract patent assignees."""
        assignees = []
        
        # Try multiple possible selectors for assignees
        assignee_selectors = [
            'dd[itemprop="assignee"] span[itemprop="name"]',
            'meta[name="DC.publisher"]',
            'span[itemprop="assignee"] span[itemprop="name"]',
            'dd[itemprop="assignee"]'
        ]
        
        for selector in assignee_selectors:
            elements = soup.select(selector)
            if elements:
                if selector == 'meta[name="DC.publisher"]':
                    for elem in elements:
                        if 'content' in elem.attrs:
                            assignees.append(elem.attrs['content'].strip())
                else:
                    for elem in elements:
                        assignees.append(elem.text.strip())
                
                # If we found assignees, return them
                if assignees:
                    return assignees
        
        # If no assignees found with specific selectors, try to find them in text
        assignee_section = soup.find(string=re.compile('Assignees?:|Assignee\(s\):'))
        if assignee_section:
            parent = assignee_section.parent
            if parent:
                # Look for the closest dd or li element
                assignee_container = parent.find_next(['dd', 'li', 'div', 'span'])
                if assignee_container:
                    # Split by commas or semicolons
                    for name in re.split(r'[,;]', assignee_container.text):
                        if name.strip():
                            assignees.append(name.strip())
        
        return assignees
    
    def _extract_filing_date(self, soup: BeautifulSoup) -> str:
        """Extract filing date."""
        # Try multiple possible selectors for filing date
        date_selectors = [
            'dd[itemprop="filingDate"] time',
            'time[itemprop="filingDate"]',
            'meta[name="DC.date.submitted"]',
            'dd[itemprop="filingDate"]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                if selector == 'meta[name="DC.date.submitted"]' and 'content' in date_elem.attrs:
                    return date_elem.attrs['content'].strip()
                else:
                    return date_elem.text.strip()
        
        # If no date found with selectors, try to find it in text
        filing_section = soup.find(string=re.compile('Filed:|Filing date:|Application filed:'))
        if filing_section:
            parent = filing_section.parent
            if parent:
                # Get next sibling or next element that might contain the date
                date_container = parent.find_next(['dd', 'span', 'div'])
                if date_container:
                    # Try to extract date-like text
                    date_match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\w+\s+\d{1,2},?\s+\d{4}\b', date_container.text)
                    if date_match:
                        return date_match.group(0)
                    return date_container.text.strip()
        
        return ""
    
    def _extract_publication_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date."""
        # Try multiple possible selectors for publication date
        date_selectors = [
            'dd[itemprop="publicationDate"] time',
            'time[itemprop="publicationDate"]',
            'meta[name="DC.date.issued"]',
            'dd[itemprop="publicationDate"]'
        ]
        
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                if selector == 'meta[name="DC.date.issued"]' and 'content' in date_elem.attrs:
                    return date_elem.attrs['content'].strip()
                else:
                    return date_elem.text.strip()
        
        # If no date found with selectors, try to find it in text
        pub_section = soup.find(string=re.compile('Publication date:|Published:|Issue date:'))
        if pub_section:
            parent = pub_section.parent
            if parent:
                # Get next sibling or next element that might contain the date
                date_container = parent.find_next(['dd', 'span', 'div'])
                if date_container:
                    # Try to extract date-like text
                    date_match = re.search(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\w+\s+\d{1,2},?\s+\d{4}\b', date_container.text)
                    if date_match:
                        return date_match.group(0)
                    return date_container.text.strip()
        
        return ""
    
    def _extract_classifications(self, soup: BeautifulSoup) -> List[str]:
        """Extract patent classifications."""
        classifications = []
        
        # Try multiple possible selectors for classifications
        classification_selectors = [
            'li.classification',
            'span[itemprop="classifications"]',
            'meta[name="DC.subject"]'
        ]
        
        for selector in classification_selectors:
            elements = soup.select(selector)
            if elements:
                if selector == 'meta[name="DC.subject"]':
                    for elem in elements:
                        if 'content' in elem.attrs:
                            classifications.append(elem.attrs['content'].strip())
                else:
                    for elem in elements:
                        classifications.append(elem.text.strip())
                
                # If we found classifications, return them
                if classifications:
                    return classifications
        
        # Check for classifications in a table format
        classification_section = soup.find(string=re.compile('Classifications?:|CPC:'))
        if classification_section:
            parent = classification_section.parent
            if parent:
                # Look for nearby elements that might contain classifications
                for elem in parent.find_next_siblings(['ul', 'table', 'div']):
                    class_items = elem.select('li, td')
                    if class_items:
                        for item in class_items:
                            text = item.text.strip()
                            if text and not text.lower().startswith(('view', 'more', 'classification')):
                                classifications.append(text)
                        
                        if classifications:
                            return classifications
        
        return classifications
    
    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract patent description."""
        # Try multiple possible selectors for description section
        description_selectors = [
            'section[itemprop="description"]',
            'div[itemprop="description"]',
            'div.patent-text',
            'div.description'
        ]
        
        for selector in description_selectors:
            description_section = soup.select_one(selector)
            if description_section:
                # Try different approaches to get paragraphs
                paragraph_selectors = [
                    'div.description-paragraph',
                    'p',
                    'div.patent-paragraph'
                ]
                
                for para_selector in paragraph_selectors:
                    paragraphs = description_section.select(para_selector)
                    if paragraphs:
                        description_text = "\n\n".join([p.text.strip() for p in paragraphs])
                        return description_text
                
                # If no structured paragraphs found, return the whole text
                return description_section.text.strip()
        
        # If nothing found with selectors, try to find description by heading
        description_heading = soup.find(string=re.compile('Description'))
        if description_heading:
            section = description_heading.parent
            if section:
                # Find the section following the description heading
                desc_content = []
                current = section.next_sibling
                
                # Collect text until next heading or end of content
                while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3']):
                    if hasattr(current, 'text'):
                        text = current.text.strip()
                        if text:
                            desc_content.append(text)
                    current = current.next_sibling
                
                if desc_content:
                    return "\n\n".join(desc_content)
        
        return ""
    
    def _extract_claims(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract patent claims."""
        claims = []
        
        # Try multiple possible selectors for claims section
        claims_selectors = [
            'section[itemprop="claims"]',
            'div[itemprop="claims"]',
            'div.claims',
            'div.patent-claims'
        ]
        
        for selector in claims_selectors:
            claims_section = soup.select_one(selector)
            if claims_section:
                # Try different claim element selectors
                claim_element_selectors = [
                    'div.claim',
                    'div.claim-text',
                    'p.claim',
                    'li.claim'
                ]
                
                for claim_selector in claim_element_selectors:
                    claim_elements = claims_section.select(claim_selector)
                    if claim_elements:
                        for i, claim_elem in enumerate(claim_elements):
                            claim_text = claim_elem.text.strip()
                            claim_num = i + 1
                            
                            # Try to extract claim number if present in text
                            num_match = re.match(r'^(\d+)\.\s+', claim_text)
                            if num_match:
                                claim_num = int(num_match.group(1))
                                claim_text = claim_text[len(num_match.group(0)):].strip()
                            
                            # Try to determine if it's independent or dependent
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
                        
                        if claims:
                            return claims
                
                # If no structured claims found but we have the section, 
                # try to extract claims by text parsing
                raw_text = claims_section.text.strip()
                claim_matches = re.finditer(r'(?:^|\n\s*)(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', raw_text, re.DOTALL)
                
                for match in claim_matches:
                    claim_num = int(match.group(1))
                    claim_text = match.group(2).strip()
                    
                    # Determine dependency
                    is_dependent = bool(re.search(r'claim\s+\d+', claim_text.lower()))
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
                
                if claims:
                    return claims
        
        # If nothing found with selectors, try to find claims by heading
        claims_heading = soup.find(string=re.compile('Claims'))
        if claims_heading:
            section = claims_heading.parent
            if section:
                # Try to extract claim text following the heading
                claims_text = ""
                current = section.next_sibling
                
                # Collect text until next heading or end of content
                while current and not (hasattr(current, 'name') and current.name in ['h1', 'h2', 'h3']):
                    if hasattr(current, 'text'):
                        text = current.text.strip()
                        if text:
                            claims_text += text + "\n"
                    current = current.next_sibling
                
                if claims_text:
                    # Try to parse claims from the text
                    claim_matches = re.finditer(r'(?:^|\n\s*)(\d+)\.\s+(.*?)(?=(?:\n\s*\d+\.)|$)', claims_text, re.DOTALL)
                    
                    for match in claim_matches:
                        claim_num = int(match.group(1))
                        claim_text = match.group(2).strip()
                        
                        # Determine dependency
                        is_dependent = bool(re.search(r'claim\s+\d+', claim_text.lower()))
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
        
        # Try multiple possible selectors for citation tables/sections
        citation_selectors = [
            'tr.citation',
            'div.cited-by',
            'table.citation',
            'ul.citation-list'
        ]
        
        for selector in citation_selectors:
            citation_elems = soup.select(selector)
            
            if citation_elems:
                for elem in citation_elems:
                    # Handle table rows
                    if elem.name == 'tr':
                        citation_id = elem.select_one('td.patent-id, td:first-child')
                        citation_title = elem.select_one('td.patent-title, td:nth-child(2)')
                        
                        if citation_id and citation_title:
                            citations.append({
                                "id": citation_id.text.strip(),
                                "title": citation_title.text.strip()
                            })
                    # Handle list items
                    elif elem.name == 'li':
                        citation_text = elem.text.strip()
                        # Try to extract ID and title
                        id_match = re.search(r'([A-Z]{2}\d+[A-Z]\d*|\d{5,})', citation_text)
                        if id_match:
                            citation_id = id_match.group(0)
                            # Everything after the ID (and possible delimiter) is the title
                            title_text = re.sub(r'^.*?([A-Z]{2}\d+[A-Z]\d*|\d{5,})\s*[:\-–—]*\s*', '', citation_text)
                            citations.append({
                                "id": citation_id,
                                "title": title_text.strip()
                            })
                        else:
                            citations.append({
                                "id": "",
                                "title": citation_text
                            })
        
        # If no citations found with selectors, try to find citations section by heading
        if not citations:
            citation_heading = soup.find(string=re.compile('Citations|References|Cited'))
            if citation_heading:
                section = citation_heading.parent
                if section:
                    # Look for list items or table rows near the heading
                    list_items = section.find_next('ul')
                    if list_items:
                        for item in list_items.select('li'):
                            citation_text = item.text.strip()
                            # Try to extract ID and title
                            id_match = re.search(r'([A-Z]{2}\d+[A-Z]\d*|\d{5,})', citation_text)
                            if id_match:
                                citation_id = id_match.group(0)
                                # Everything after the ID is the title
                                title_text = re.sub(r'^.*?([A-Z]{2}\d+[A-Z]\d*|\d{5,})\s*[:\-–—]*\s*', '', citation_text)
                                citations.append({
                                    "id": citation_id,
                                    "title": title_text.strip()
                                })
                            else:
                                citations.append({
                                    "id": "",
                                    "title": citation_text
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