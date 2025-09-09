#.  doubtnut scraper api endpoints

#.  all boks👇
#.  /api/books?class=11

#.  book chapters 👇
#.  /api/book?path=  

#.  chapter questions 👇
#.  /api/questions?path=

#.  answer fetch 👇
#.  /api/answer?id= 


import os
import logging
from flask import Flask, jsonify, request

# Try importing custom modules with error handling
try:
    from scraper import DoubnutScraper
    from video import DoubtnutScraper as VideoScraper
except ImportError as e:
    logging.error(f"Failed to import modules: {e}")
    # Create dummy classes for testing
    class DoubnutScraper:
        def get_all_books(self, class_number):
            return []
        def get_book_chapters(self, book_path):
            return []
        def get_questions(self, question_path):
            return []
        def get_answer(self, qna_id):
            return {}
    
    class DoubtnutScraper:
        def extract_video_url(self, url):
            return {'success': False, 'video_url': None}

from urllib.parse import urlparse, urljoin

# Configure logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Initialize scrapers
try:
    scraper = DoubnutScraper()
    video_scraper = DoubtnutScraper()
except Exception as e:
    logging.error(f"Error initializing scrapers: {e}")
    scraper = DoubnutScraper()  # Use dummy class
    video_scraper = DoubtnutScraper()

@app.route('/')
def index():
    """API Status endpoint"""
    return jsonify({
        'success': True,
        'message': 'Doubtnut Scraper API is running',
        'endpoints': {
            'books': '/api/books?class=11',
            'book_chapters': '/api/book?path=BOOK_PATH',
            'questions': '/api/questions?path=CHAPTER_PATH',
            'answer': '/api/answer?id=QNA_ID'
        }
    })

@app.route('/api/books')
def get_books():
    """Scrape and return all books from class page (6-12)"""
    class_number = request.args.get('class', 11, type=int)
    
    # Validate class number
    if class_number < 6 or class_number > 12:
        return jsonify({
            'success': False,
            'error': 'Invalid class number',
            'message': 'Class number must be between 6 and 12'
        }), 400
    
    try:
        books = scraper.get_all_books(class_number)
        
        # Remove duplicates based on endpoint
        seen_endpoints = set()
        unique_books = []
        
        for book in books:
            endpoint = book.get('endpoint')
            if endpoint not in seen_endpoints:
                seen_endpoints.add(endpoint)
                unique_books.append(book)
        
        return jsonify({
            'success': True,
            'data': unique_books,
            'class': class_number,
            'count': len(unique_books)
        })
    except Exception as e:
        logging.error(f"Error fetching books: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Failed to fetch books from Doubtnut for class {class_number}'
        }), 500

@app.route('/api/book')
def get_book_chapters():
    """Get chapters and sub-sections for a specific book"""
    book_path = request.args.get('path')
    
    if not book_path:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: path',
            'message': 'Please provide a book path parameter'
        }), 400
    
    try:
        chapters = scraper.get_book_chapters(book_path)
        return jsonify({
            'success': True,
            'data': chapters,
            'book_path': book_path,
            'count': len(chapters)
        })
    except Exception as e:
        logging.error(f"Error fetching book chapters: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Failed to fetch chapters for book: {book_path}'
        }), 500

@app.route('/api/questions')
def get_questions():
    """Get questions for a specific chapter section"""
    question_path = request.args.get('path')
    
    if not question_path:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: path',
            'message': 'Please provide a question path parameter'
        }), 400
    
    try:
        questions_data = scraper.get_questions(question_path)
        
        # Clean the questions data - only keep qna_id and cleaned question
        clean_questions = []
        for question in questions_data:
            clean_question = question.get('question', '').replace('View Solution', '').strip()
            clean_questions.append({
                'qna_id': question.get('qna_id', ''),
                'question': clean_question
            })
        
        return jsonify({
            'success': True,
            'data': clean_questions,
            'count': len(clean_questions)
        })
    except Exception as e:
        logging.error(f"Error fetching questions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Failed to fetch questions for path: {question_path}'
        }), 500

@app.route('/api/answer')
def get_answer():
    """Get answer for a specific question with video URL"""
    qna_id = request.args.get('id')
    
    if not qna_id:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: id',
            'message': 'Please provide a QNA ID parameter'
        }), 400
    
    try:
        # Get answer from scraper.py
        answer_data = scraper.get_answer(qna_id)
        
        # Get video URL from video.py
        doubtnut_url = f"https://www.doubtnut.com/qna/{qna_id}"
        video_result = video_scraper.extract_video_url(doubtnut_url)
        
        # Extract only required fields
        clean_response = {
            'question': answer_data.get('question', ''),
            'answer': answer_data.get('answer', ''),
            'video_url': video_result.get('video_url') if video_result.get('success') else None
        }
        
        return jsonify({
            'success': True,
            'data': clean_response
        })
    except Exception as e:
        logging.error(f"Error fetching answer: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Failed to fetch answer for QNA ID: {qna_id}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Not Found',
        'message': 'The requested endpoint was not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500

# For Vercel
app = app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)