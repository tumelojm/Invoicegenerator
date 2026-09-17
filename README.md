# Invoice Generator Web Application

A professional web-based invoice generator that creates PDF invoices. Built with Flask and ReportLab.

## Features

- 🎨 Modern, responsive web interface
- 📄 Professional PDF invoice generation
- 💰 Automatic calculation of totals and taxes
- 📱 Mobile-friendly design
- ⚡ Fast and easy to use

## Local Development

### Prerequisites
- Python 3.8 or higher
- pip

### Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd invoice-generator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.pypython 
```

5. Open your browser and navigate to:
```
http://localhost:5000
```

## Deployment Options

### Option 1: Render (Recommended - FREE)

1. Create account at [render.com](https://render.com)

2. Click "New +" → "Web Service"

3. Connect your GitHub repository

4. Configure:
   - **Name**: invoice-generator (or your choice)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free

5. Add to `requirements.txt`:
```
gunicorn==21.2.0
```

6. Click "Create Web Service"

Your app will be live at: `https://your-app-name.onrender.com`

### Option 2: PythonAnywhere (FREE)

1. Create account at [pythonanywhere.com](https://www.pythonanywhere.com)

2. Upload your code via Git or Files interface

3. Create a new web app:
   - Go to "Web" tab
   - Click "Add a new web app"
   - Choose "Flask" and Python 3.10

4. Configure WSGI file:
```python
import sys
path = '/home/yourusername/invoice-generator'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
```

5. Install dependencies in Bash console:
```bash
pip install -r requirements.txt
```

6. Reload the web app

Your app will be live at: `https://yourusername.pythonanywhere.com`

### Option 3: Heroku

1. Install Heroku CLI and login:
```bash
heroku login
```

2. Create a `Procfile`:
```
web: gunicorn app:app
```

3. Add gunicorn to requirements.txt:
```
gunicorn==21.2.0
```

4. Create Heroku app and deploy:
```bash
heroku create your-app-name
git push heroku main
```

### Option 4: Railway

1. Create account at [railway.app](https://railway.app)

2. Click "New Project" → "Deploy from GitHub repo"

3. Select your repository

4. Railway auto-detects Python and deploys

5. Your app will be live with a generated URL

## Git Setup

```bash
# Initialize git repository
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Invoice generator web app"

# Add remote (GitHub, GitLab, etc.)
git remote add origin <your-repo-url>

# Push to GitHub
git push -u origin main
```

## Project Structure

```
invoice-generator/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── templates/
│   └── index.html        # Web interface
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── script.js     # Frontend logic
└── generated_invoices/   # Generated PDFs (created automatically)
```

## Usage

1. Open the web application
2. Fill in invoice details:
   - Invoice number, dates
   - Your business details (From)
   - Client details (To)
   - Services/products
   - Bank details
3. Click "Calculate Totals" to see summary
4. Click "Generate Invoice PDF"
5. Download your professional PDF invoice

## Technologies Used

- **Backend**: Flask (Python)
- **PDF Generation**: ReportLab
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with gradient design

## License

MIT License - feel free to use this for your business!

## Support

For issues or questions, please open an issue on GitHub.
