--

## Endpoints

### 1. Get All Books
**Endpoint:** `GET /api/books`

**Description:** Scrape and return all books from a specific class page (supports classes 6-12)

**Parameters:**
- `class` (optional, integer): Class number between 6-12 (default: 11)

**Example Request:**
```
GET /api/books?class=11
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "name": "NCERT English",
      "endpoint": "/books/class-11-ncert-english-english-medium-in-hindi-download-questions-answers-solutions",
      "image_url": "https://d10lpgp6xz60nq.cloudfront.net/engagement_framework/B9C1D739-6C24-6C74-5982-10357ACAEA37.webp"
    },
    {
      "name": "NCERT Physics",
      "endpoint": "/books/class-11-ncert-physics-english-medium-in-hindi-download-questions-answers-solutions"
    }
  ],
  "class": 11,
  "count": 15
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Invalid class number",
  "message": "Class number must be between 6 and 12"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Connection timeout",
  "message": "Failed to fetch books from Doubtnut for class 11"
}
```

---

### 2. Get Book Chapters
**Endpoint:** `GET /api/book`

**Description:** Get all chapters and sub-sections for a specific book

**Parameters:**
- `path` (required, string): Book path/endpoint from the books API

**Example Request:**
```
GET /api/book?path=/books/class-11-ncert-english-english-medium-in-hindi-download-questions-answers-solutions
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "chapter_name": "Chapter 1: The Portrait of a Lady",
      "sub_sections": [
        {
          "name": "Thinking About the Text",
          "endpoint": "/books/class-11-ncert-english-solution-chapter-c01-the-portrait--of-lady-english-medium-in-hindi/thinking-about-the-text"
        },
        {
          "name": "Talking About the Text", 
          "endpoint": "/books/class-11-ncert-english-solution-chapter-c01-the-portrait--of-lady-english-medium-in-hindi/talking-about-the-text"
        }
      ],
      "pdf_link": null
    },
    {
      "chapter_name": "Chapter 2: We're Not Afraid to Die",
      "sub_sections": [
        {
          "name": "Understanding the text",
          "endpoint": "/books/class-11-ncert-english-solution-chapter-c02-we-re-not-afraid-to-die-english-medium-in-hindi/understanding-the-text"
        }
      ],
      "pdf_link": "https://example.com/chapter2.pdf"
    }
  ],
  "book_path": "/books/class-11-ncert-english-english-medium-in-hindi-download-questions-answers-solutions",
  "count": 8
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Missing required parameter: path",
  "message": "Please provide a book path parameter"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Failed to parse HTML",
  "message": "Failed to fetch chapters for book: /books/class-11-ncert-english-english-medium-in-hindi-download-questions-answers-solutions"
}
```

---

### 3. Get Questions
**Endpoint:** `GET /api/questions`

**Description:** Get all questions for a specific chapter section

**Parameters:**
- `path` (required, string): Question path/endpoint from the book chapters API

**Example Request:**
```
GET /api/questions?path=/books/class-11-ncert-english-solution-chapter-c01-the-portrait--of-lady-english-medium-in-hindi/thinking-about-the-text
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "question": "What does the author's grandmother look like? How does the author describe her physical appearance?",
      "qna_id": "75909006",
      "answer_endpoint": "/qna/75909006"
    },
    {
      "question": "What was the turning point in the friendship between the author and his grandmother?",
      "qna_id": "75909007", 
      "answer_endpoint": "/qna/75909007"
    },
    {
      "question": "How did the grandmother celebrate the homecoming of the author?",
      "qna_id": "75909008",
      "answer_endpoint": "/qna/75909008"
    }
  ],
  "question_path": "/books/class-11-ncert-english-solution-chapter-c01-the-portrait--of-lady-english-medium-in-hindi/thinking-about-the-text",
  "count": 5
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Missing required parameter: path",
  "message": "Please provide a question path parameter"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "No questions found",
  "message": "Failed to fetch questions for path: /books/class-11-ncert-english-solution-chapter-c01-the-portrait--of-lady-english-medium-in-hindi/thinking-about-the-text"
}
```

---

### 4. Get Answer
**Endpoint:** `GET /api/answer`

**Description:** Get the complete question and answer for a specific QNA ID

**Parameters:**
- `id` (required, string): QNA ID from the questions API

**Example Request:**
```
GET /api/answer?id=75909006
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "qna_id": "75909006",
    "question": "What does the author's grandmother look like? How does the author describe her physical appearance?",
    "answer": "The author describes his grandmother as a very old lady who was terribly wrinkled. Her face was a criss-cross of wrinkles running from everywhere to everywhere. She was short and fat and slightly bent. Her hair was white like the winter snow. She always wore spotless white saree and her hands were hard and gnarled. She had a rosary of beads in her hands which she was always telling.",
    "source_url": "https://www.doubtnut.com/qna/75909006",
    "status": "success"
  },
  "qna_id": "75909006"
}
```

**Partial Success Response (200 OK - when answer extraction is incomplete):**
```json
{
  "success": true,
  "data": {
    "qna_id": "75909006",
    "question": "What does the author's grandmother look like? How does the author describe her physical appearance?",
    "answer": "Answer could not be extracted from this page.",
    "source_url": "https://www.doubtnut.com/qna/75909006",
    "status": "partial"
  },
  "qna_id": "75909006"
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "Missing required parameter: id",
  "message": "Please provide a QNA ID parameter"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "error": "Page not found",
  "message": "Failed to fetch answer for QNA ID: 75909006"
}
```

---


## Usage Examples

### Complete Workflow Example

1. **Get all books for class 11:**
   ```
   GET /api/books?class=11
   ```

2. **Get chapters for a specific book:**
   ```
   GET /api/book?path=/books/class-11-ncert-english-english-medium-in-hindi-download-questions-answers-solutions
   ```

3. **Get questions for a chapter section:**
   ```
   GET /api/questions?path=/books/class-11-ncert-english-solution-chapter-c01-the-portrait--of-lady-english-medium-in-hindi/thinking-about-the-text
   ```

4. **Get answer for a specific question:**
   ```
   GET /api/answer?id=75909006
   ```

---

## Supported Classes

The API supports educational content for classes 6 through 12:
- Class 6, 7, 8, 9, 10, 11, 12

---

## Notes

- All endpoints return JSON responses with UTF-8 encoding
- Image URLs in book responses may be relative or absolute
- PDF links in chapters may be null if not available
- Question text preserves formatting including line breaks for multi-part questions
- Answer extraction quality may vary depending on the source page structure
