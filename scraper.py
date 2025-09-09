import requests
from bs4 import BeautifulSoup
import logging
import time
import re
from urllib.parse import urljoin, urlparse

class DoubnutScraper:
    def __init__(self):
        self.base_url = "https://www.doubtnut.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def _make_request(self, url, max_retries=3, delay=1):
        """Make HTTP request with retry logic and rate limiting"""
        for attempt in range(max_retries):
            try:
                time.sleep(delay)  # Rate limiting
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                logging.warning(f"Request attempt {attempt + 1} failed for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay * (attempt + 1))
        
    def _clean_text(self, text):
        """Clean extracted text by removing extra whitespace and formatting"""
        if not text:
            return ""
        
        # Convert <br> tags to newlines first (for question formatting)
        text = text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
        
        # For questions, preserve line breaks but clean up spacing
        if any(keyword in text.lower() for keyword in ['i)', 'ii)', 'iii)', 'iv)', 'v)', 'a)', 'b)', 'c)', 'd)', 'e)']):
            # Split by lines, clean each line, then rejoin
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            text = '\n'.join(lines)
        else:
            # For other text, remove extra whitespace and newlines
            text = ' '.join(text.split())
        
        return text.strip()
    
    def get_all_books(self, class_number=11):
        """Scrape all books from class page (supports classes 6-12)"""
        url = f"{self.base_url}/books/class-{class_number}-all-books-download-questions-answers-solutions"
        
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            books = []
            
            # Find all book links - they have specific class pattern
            book_links = soup.find_all('a', class_=['flex', 'p-2', 'gap-2', 'h-full', 'link'])
            
            for link in book_links:
                href = link.get('href')
                # Filter out URLs with hash fragments and check for class books
                if href and f'/books/class-{class_number}-' in href and '#' not in href:
                    # Extract book name and image from img element
                    img = link.find('img')
                    book_name = ""
                    image_url = ""
                    
                    if img:
                        if img.get('alt'):
                            book_name = img.get('alt')
                        # Get image URL
                        img_src = img.get('src') or img.get('data-src')
                        if img_src:
                            # Convert relative URLs to absolute
                            if img_src.startswith('//'):
                                image_url = 'https:' + img_src
                            elif img_src.startswith('/'):
                                image_url = self.base_url + img_src
                            else:
                                image_url = img_src
                    
                    # Fallback to text content if no img alt
                    if not book_name:
                        book_name = self._clean_text(link.get_text())
                    
                    if book_name and href:
                        book_data = {
                            'name': book_name,
                            'endpoint': href
                        }
                        
                        # Add image URL if found
                        if image_url:
                            book_data['image_url'] = image_url
                            
                        books.append(book_data)
            
            logging.info(f"Found {len(books)} books")
            return books
            
        except Exception as e:
            logging.error(f"Error scraping books: {str(e)}")
            raise
    
    def get_book_chapters(self, book_path):
        """Get all chapters with proper structure based on actual HTML: <ol><li><h3>Chapter X</h3><ol><li>sub-sections</li></ol></li></ol>"""
        url = urljoin(self.base_url, book_path)
        
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            chapters = []
            
            # Look for the actual structure: <ol class="list-none pl-0"><li><h3>Chapter X:</h3><ol><li><a>sub-section</a></li></ol></li></ol>
            main_ol = soup.find('ol', class_='list-none')
            
            if main_ol:
                # Find all chapter items (li elements that contain h3 with chapter title)
                chapter_items = main_ol.find_all('li', class_='pl-0', recursive=False)
                
                for item in chapter_items:
                    # Look for chapter title in h3
                    chapter_title_elem = item.find('h3')
                    if chapter_title_elem:
                        chapter_title = self._clean_text(chapter_title_elem.get_text())
                        
                        # Skip if not a real chapter
                        if not chapter_title or 'chapter' not in chapter_title.lower():
                            continue
                        
                        chapter_data = {
                            'chapter_name': chapter_title,
                            'sub_sections': [],
                            'pdf_link': None
                        }
                        
                        # Look for sub-sections in the nested ol
                        sub_ol = item.find('ol')
                        if sub_ol:
                            sub_items = sub_ol.find_all('li', class_='pl-0')
                            
                            for sub_item in sub_items:
                                # Look for sub-section links
                                link = sub_item.find('a', class_='link')
                                if link and link.get('href'):
                                    href = link.get('href')
                                    link_text = self._clean_text(link.get_text())
                                    
                                    # Filter out hash URLs and add sub-section
                                    if href and '#' not in href and link_text:
                                        chapter_data['sub_sections'].append({
                                            'name': link_text,
                                            'endpoint': href
                                        })
                                
                                # Look for PDF links in this sub-item
                                pdf_link = sub_item.find('a', href=re.compile(r'\.pdf$'))
                                if pdf_link:
                                    chapter_data['pdf_link'] = pdf_link.get('href')
                        
                        # Look for PDF link at chapter level too
                        if not chapter_data['pdf_link']:
                            chapter_pdf = item.find('a', href=re.compile(r'\.pdf$'))
                            if chapter_pdf:
                                chapter_data['pdf_link'] = chapter_pdf.get('href')
                        
                        # Add chapter if it has content
                        if chapter_data['sub_sections']:
                            chapters.append(chapter_data)
            
            # If no chapters found with the primary method, try fallback
            if not chapters:
                # Look for h3 elements with "Chapter" in them
                chapter_headings = soup.find_all('h3', string=re.compile(r'Chapter\s*\d+:', re.I))
                
                for heading in chapter_headings:
                    chapter_title = self._clean_text(heading.get_text())
                    
                    chapter_data = {
                        'chapter_name': chapter_title,
                        'sub_sections': [],
                        'pdf_link': None
                    }
                    
                    # Look for links in the parent container
                    parent = heading.parent
                    if parent:
                        # Find all links in this chapter section
                        chapter_links = parent.find_all('a', href=True)
                        
                        for link in chapter_links:
                            href = link.get('href')
                            link_text = self._clean_text(link.get_text())
                            
                            # Add sub-section links
                            if (href and href.startswith('/books/') and 'chapter' in href and 
                                '#' not in href and link_text):
                                
                                # Filter for common sub-section types
                                if any(keyword in link_text.lower() for keyword in 
                                      ['questions', 'working', 'talking', 'understanding', 
                                       'reading', 'thinking', 'writing', 'exercise']):
                                    
                                    chapter_data['sub_sections'].append({
                                        'name': link_text,
                                        'endpoint': href
                                    })
                            
                            # Check for PDF links
                            elif href and href.endswith('.pdf'):
                                chapter_data['pdf_link'] = href
                    
                    # Add chapter if it has sub-sections
                    if chapter_data['sub_sections']:
                        chapters.append(chapter_data)
            
            logging.info(f"Found {len(chapters)} chapters for book: {book_path}")
            return chapters
            
        except Exception as e:
            logging.error(f"Error scraping book chapters: {str(e)}")
            raise
    
    def get_questions(self, question_path):
        """Get all questions from a chapter section"""
        url = urljoin(self.base_url, question_path)
        
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            questions = []
            
            # Look for question blocks - they typically have qna links
            question_blocks = soup.find_all('a', href=re.compile(r'/qna/\d+'))
            
            for block in question_blocks:
                href = block.get('href')
                question_text = self._clean_text(block.get_text())
                
                if question_text and href:
                    # Extract QNA ID from href
                    qna_match = re.search(r'/qna/(\d+)', href)
                    qna_id = qna_match.group(1) if qna_match else None
                    
                    questions.append({
                        'question': question_text,
                        'qna_id': qna_id,
                        'answer_endpoint': href
                    })
            
            # Alternative approach: look for question-like text patterns
            if not questions:
                # Find elements that might contain questions
                potential_questions = soup.find_all(['p', 'div', 'span'], 
                                                  string=re.compile(r'\?|What|How|Why|When|Where'))
                
                for elem in potential_questions:
                    text = self._clean_text(elem.get_text())
                    if text and len(text) > 20 and '?' in text:
                        # Look for nearby QNA links
                        parent = elem.parent
                        if parent:
                            qna_link = parent.find('a', href=re.compile(r'/qna/\d+'))
                            if qna_link:
                                href = qna_link.get('href')
                                qna_match = re.search(r'/qna/(\d+)', href)
                                qna_id = qna_match.group(1) if qna_match else None
                                
                                questions.append({
                                    'question': text,
                                    'qna_id': qna_id,
                                    'answer_endpoint': href
                                })
            
            logging.info(f"Found {len(questions)} questions for path: {question_path}")
            return questions
            
        except Exception as e:
            logging.error(f"Error scraping questions: {str(e)}")
            raise
    
    def get_answer(self, qna_id):
        """Get question and answer text for a specific QNA ID"""
        url = f"{self.base_url}/qna/{qna_id}"
        
        try:
            response = self._make_request(url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract question text - Priority 1: h1 with id="ocr-text" (most complete)
            question_text = ""
            
            # Look for h1 with id="ocr-text" first (contains complete question)
            h1_ocr = soup.find('h1', id='ocr-text')
            if h1_ocr:
                # Look for span with class="math" inside h1
                math_span = h1_ocr.find('span', class_='math')
                if math_span:
                    # Get the innermost span content
                    inner_span = math_span.find('span')
                    if inner_span:
                        question_text = self._clean_text(inner_span.get_text())
                    else:
                        question_text = self._clean_text(math_span.get_text())
                else:
                    question_text = self._clean_text(h1_ocr.get_text())
            
            # Fallback: Look for og:title meta tag
            if not question_text:
                og_title = soup.find('meta', property='og:title')
                if og_title and og_title.get('content'):
                    question_text = self._clean_text(og_title.get('content'))
            
            # Fallback: Look for title tag
            if not question_text:
                title_tag = soup.find('title')
                if title_tag:
                    question_text = self._clean_text(title_tag.get_text())
            
            # Extract answer text - Priority 1: Meta description (most reliable)
            answer_text = ""
            
            # Look for meta description first (contains answer)
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                answer_text = self._clean_text(meta_desc.get('content'))
            
            # Fallback: Look for og:description
            if not answer_text:
                og_desc = soup.find('meta', property='og:description')
                if og_desc and og_desc.get('content'):
                    answer_text = self._clean_text(og_desc.get('content'))
            
            # Fallback: Look for solution text in the page content
            if not answer_text:
                # Look for div with id="solution-text"
                solution_div = soup.find('div', id='solution-text')
                if solution_div:
                    # Find the math span inside it
                    math_span = solution_div.find('span', class_='math')
                    if math_span:
                        inner_span = math_span.find('span')
                        if inner_span:
                            answer_text = self._clean_text(inner_span.get_text())
                    
                    # If no math span, get direct text
                    if not answer_text:
                        answer_text = self._clean_text(solution_div.get_text())
            
            # Final fallback: Look for any substantial text content
            if not answer_text:
                # Look for text solution containers
                solution_containers = soup.find_all(['div', 'section'], class_=re.compile(r'solution|answer'))
                
                for container in solution_containers:
                    text = self._clean_text(container.get_text())
                    
                    # Skip navigation and promotional content
                    skip_keywords = ['Download', 'Login', 'App', 'Video Solution', 'Text Solution', 'Verified by Experts', 'Show More']
                    if any(keyword in text for keyword in skip_keywords):
                        continue
                    
                    # Look for substantial answer content
                    if text and 30 <= len(text) <= 1000:
                        answer_text = text
                        break
            
            # Clean up extracted text
            if question_text:
                # Remove common suffixes from question
                question_text = re.sub(r'(View Solution|Click here|\d+).*$', '', question_text, flags=re.IGNORECASE).strip()
                
            if answer_text:
                # Remove common prefixes and suffixes from answer
                answer_text = re.sub(r'^(Text Solution|Solution|Answer|Verified by Experts)[:.\s]*', '', answer_text, flags=re.IGNORECASE).strip()
                answer_text = re.sub(r'(Show More|ShareSave|Video Solution|More from this Exercise).*$', '', answer_text, flags=re.IGNORECASE).strip()
            
            # Set default messages if content not found
            if not question_text:
                question_text = "Question text could not be extracted from this page."
            
            if not answer_text:
                answer_text = "Answer could not be extracted from this page."
            
            result = {
                'qna_id': qna_id,
                'question': question_text,
                'answer': answer_text,
                'source_url': url,
                'status': 'success' if answer_text != "Answer could not be extracted from this page." else 'partial'
            }
            
            logging.info(f"Successfully retrieved Q&A for QNA ID: {qna_id}")
            return result
            
        except Exception as e:
            logging.error(f"Error scraping answer for QNA ID {qna_id}: {str(e)}")
            raise
