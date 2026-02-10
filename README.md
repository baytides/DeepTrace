# DeepTrace

**Modern Cold Case Investigation Platform**

A web-based tool for analyzing cold cases with AI-powered insights, evidence tracking, timeline reconstruction, and hypothesis analysis using formal investigative methodologies.

![DeepTrace](https://img.shields.io/badge/Status-Beta-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 🎨 Modern Interface
- **Light & Dark Themes** - Easy on the eyes day or night
- **Accessibility** - Adjustable font sizes, high contrast
- **Responsive Design** - Works on desktop, tablet, and mobile

### 📊 Investigation Tools
- **Case Management** - Create and switch between multiple cases
- **Evidence Tracking** - Organize and categorize evidence items
- **Timeline Builder** - Reconstruct events chronologically
- **Network Analysis** - Visualize relationships between entities
- **Hypothesis Testing** - ACH (Analysis of Competing Hypotheses) matrix
- **Source Assessment** - Admiralty/NATO reliability scoring

### 📥 Data Import (Coming Soon)
- **NamUs** - Missing & unidentified persons database
- **FBI ViCAP** - Violent crime cases
- **CSV/JSON** - Bulk import from spreadsheets
- **NCMEC** - Missing children cases
- **Doe Network** - Cold case database

### 🔒 Security & Privacy
- Session-based case isolation
- Local-first data storage
- No case data leaves your server

## 🚀 Quick Start

### Web Deployment (Recommended)

DeepTrace is designed as a **web application**. Deploy it to:

- **[Vercel](https://vercel.com)** - One-click deploy from GitHub
- **[Railway](https://railway.app)** - Auto-deploy on push
- **[Render](https://render.com)** - Free tier available

See [GITHUB_DEPLOYMENT.md](GITHUB_DEPLOYMENT.md) for detailed instructions.

### Local Development

```bash
# Clone the repository
git clone https://github.com/yourusername/DeepTrace.git
cd DeepTrace

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-web.txt

# Run the server
python wsgi.py
```

Visit http://localhost:8080 in your browser!

## 📖 Usage

### Creating a Case

1. Open DeepTrace in your browser
2. Click "Create Case" on the selector page
3. Enter a case name (e.g., `jane-doe-1995`)
4. Add optional description
5. Start investigating!

### Switching Cases

Click the "🔄 Switch Case" button in the sidebar to access the case selector.

### Importing Data

From the case selector, click "📥 Import from FBI, NamUs, etc." to access import tools.

## 🏗️ Architecture

- **Backend**: Flask (Python)
- **Database**: SQLite (with PostgreSQL support)
- **Frontend**: Modern HTML/CSS/JS with HTMX
- **Visualization**: vis.js for network graphs

## 📁 Project Structure

```
DeepTrace/
├── src/deeptrace/
│   ├── dashboard/          # Web interface
│   │   ├── routes/        # Flask routes
│   │   ├── static/        # CSS, JS, assets
│   │   └── templates/     # HTML templates
│   ├── db.py              # Database layer
│   └── commands/          # CLI commands
├── wsgi.py                # Web server entry point
├── requirements-web.txt   # Production dependencies
└── docs/                  # Documentation
```

## 🎯 Methodology

DeepTrace is grounded in formal investigative frameworks:

- **ACH** (Richards Heuer) - Hypothesis testing
- **BEA** (Brent Turvey) - Behavioral evidence analysis
- **Admiralty System** - Source reliability assessment
- **VIVA Model** - Victimology assessment
- **OSINT Layers** (Michael Bazzell) - Information gathering

## 🔧 Configuration

### Environment Variables

```bash
FLASK_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///deeptrace.db
```

### Deployment Platforms

DeepTrace includes configuration for:
- Vercel (`vercel.json`)
- Railway (`railway.json`)
- Heroku (`Procfile`)

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

Built with methodologies from:
- Richards Heuer (CIA, ACH methodology)
- Brent Turvey (Forensic Analysis)
- Michael Bazzell (OSINT Techniques)
- National Missing Persons databases

## 📧 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/DeepTrace/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/DeepTrace/discussions)

---

**Note**: DeepTrace is designed for ethical cold case investigation, journalism, and research. Always respect privacy laws and regulations.
