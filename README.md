# UofT Prerequisites

Visualize the prerequisite tree for any University of Toronto course. Search a course code and explore its full prerequisite chain as an interactive graph. Course data is fetched live from UofT's EASI timetable API and cached locally.

## Tech Stack

**Frontend:** React, Vite, Apollo Client, React Flow, Tailwind CSS  
**Backend:** Django, Graphene-Django (GraphQL), SQLite

## Running Locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies GraphQL requests to Django at `localhost:8000`.

No `.env` file is needed — the app works out of the box with SQLite and the EASI API.

## How It Works

1. A user searches for a course (e.g. `CSC209H1`)
2. The backend checks the local SQLite database first
3. If not found, it fetches the course from UofT's [EASI timetable API](https://ttb.utoronto.ca), saves it, and recursively fetches any prerequisite courses not yet in the database
4. The full prerequisite tree (up to 4 levels deep) is returned via GraphQL and rendered as a node graph

## Project Structure

```
prerequisites.uoft/
├── backend/
│   ├── backend/          # Django settings, URLs
│   └── courses/
│       ├── models.py     # Course model with ManyToMany prerequisites
│       ├── schema.py     # GraphQL resolvers
│       ├── catalog.py    # EASI API client and prerequisite parser
│       └── management/
│           ├── seed_courses.py    # Sample courses for development
│           └── import_courses.py  # Bulk import by department
└── frontend/
    └── src/
        ├── App.jsx                  # Landing page / tree view
        ├── components/
        │   ├── SearchBar.jsx        # Course search with live suggestions
        │   └── FlowVisualizer.jsx   # React Flow graph
        └── graphql/
            └── queries.js           # Apollo queries
```

## Useful Commands

```bash
# Seed the database with a small set of sample courses
python manage.py seed_courses

# Bulk-import all courses for given departments from the EASI API
python manage.py import_courses --depts CSC MAT ECE

# Open the GraphQL explorer
open http://localhost:8000/graphql/
```

## Configuration

Key settings in `backend/backend/settings.py`:

| Setting | Default | Description |
|---|---|---|
| `UOFT_TIMETABLE_FALLBACK_ENABLED` | `True` | Fetch missing courses from EASI |
| `UOFT_TIMETABLE_SESSION` | `20261` | Academic session (Winter 2026) |
| `UOFT_TIMETABLE_TIMEOUT_SECONDS` | `4` | Per-request API timeout |
| `SEARCH_RESULTS_LIMIT` | `25` | Max results returned by search |
