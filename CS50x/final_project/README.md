QuickClient CRM
Video Demo: (https://youtu.be/BxWCte1vz2E)
Description:
QuickClient CRM is a web-based client relationship management system designed specifically for freelancers and small agencies. It provides a centralized platform to manage client information, track multiple projects, monitor deadlines, and calculate projected revenue through a clean, intuitive interface.

As someone interested in freelancing, I recognized a significant gap in the market for client management tools. Freelancers need to stay organized across multiple clients and projects, but available solutions are either too simplistic like spreadsheets or too complex and expensive like enterprise CRM systems. QuickClient bridges this gap by offering exactly what freelancers need, nothing more and nothing less.

The application is built using Flask for Python, SQLite for the database, and Bootstrap for the frontend. Users can register for an account, add clients with their contact information, create projects for each client, and view everything on a central dashboard with sorting capabilities.

app.py is the main application file containing all Flask routes and business logic. It handles user authentication through login, register, and logout routes. The dashboard route is the most complex, performing multiple operations including calculating total projected revenue using SQL SUM with a JOIN to ensure only the current user's projects are counted, implementing dynamic sorting based on URL parameters, and fetching all projects with client names using JOIN queries. The sorting logic uses Python string formatting to dynamically build the SQL ORDER BY clause based on user selection. For importance sorting, it uses a CASE statement to convert text values into numbers for proper ordering.

The file also contains client management routes for adding, editing, deleting, and viewing clients. Each route includes security checks to ensure users can only access their own data by verifying user_id in every query. Project management routes work similarly but are more complex because they require selecting an existing client and include security checks to ensure the selected client belongs to the current user.

helpers.py contains utility functions used throughout the application. The login_required decorator wraps around routes that need authentication, checking if user_id exists in the session and redirecting to login if not. The gbp filter is a Jinja2 custom filter that formats numbers as British pounds using Python's f-string formatting.

project.db is the SQLite database automatically created on first run. It contains three tables with carefully designed relationships. The users table stores user accounts with hashed passwords. The clients table stores client information with a foreign key relationship to users, meaning each client belongs to exactly one user. Many fields are optional because not all clients are companies and contact details may not always be available. The projects table stores project details with a foreign key to clients that includes ON DELETE CASCADE, which is critical because when a client is deleted, all their projects should be deleted too.

The templates directory contains all HTML files using Jinja2. layout.html is the base template that every page extends, providing consistent navigation, flash messages, and footer. home.html is the landing page for non-authenticated users featuring an overview of features and call-to-action buttons. dashboard.html is the most complex template organized into three sections showing stats cards with revenue and counts, a sortable project board, and a client list. The forms for adding and editing clients and projects use Bootstrap styling with proper labels and placeholders. client_details.html uses a two-column layout showing client information on the left and their projects on the right.

styles.css overrides Bootstrap's default primary color to match the QuickClient brand using CSS custom properties. It applies the deep red color scheme to buttons, badges, and the navigation bar with hover states and transitions.

The most important design decision was implementing CASCADE deletes with foreign key constraints. Initially when I built the application, deleting a client would leave orphaned projects in the database, projects that referenced a client_id that no longer existed. This caused errors and data inconsistency. To solve this I added ON DELETE CASCADE to the foreign key constraints so when a client is deleted, all their projects are automatically removed by SQLite itself. However SQLite disables foreign keys by default so I had to add PRAGMA foreign_keys equals ON at the start of the application to make CASCADE deletes actually work.

I made many fields optional after thinking about real world use cases. Some projects are ongoing without specific deadlines, some projects are non-monetary like portfolio work, some clients are individuals with no company name, and contact info may not always be available immediately. This flexibility makes QuickClient more practical for diverse freelance situations.

I implemented sorting on the server in SQL rather than with JavaScript for consistency, performance, and simplicity. SQL sorting is predictable and optimized for large datasets. The trade-off is an extra HTTP request when changing sort order but for a small application the benefits outweigh the cost.

The biggest challenge was ensuring proper data isolation between users. Every SQL query that fetches clients or projects includes a user_id check. For clients this is straightforward but for projects it's more complex because projects don't directly link to users, they link to clients which link to users. So I use JOIN queries to verify ownership through the client relationship.

Another challenge was handling NULL values. SQLite's default behavior puts NULL values first when sorting ascending which meant projects without deadlines appeared before urgent projects. I used NULLS LAST in the ORDER BY clause for deadline sorting to fix this.

Dynamic SQL query building for sorting required different ORDER BY clauses based on user selection while avoiding SQL injection vulnerabilities. I used Python string formatting for the ORDER BY clause while still using parameterized queries for actual data values. This is safe because the sort parameter is validated against a whitelist of allowed values.

For security I implemented password hashing using Werkzeug so no plain text passwords are stored, session-based authentication with Flask-Session, user_id verification on every data access, and SQL injection prevention through parameterized queries. The login_required decorator protects all routes that need authentication.

Building QuickClient taught me about database design including the importance of foreign key relationships, normalization principles, and referential integrity. I learned that good database design prevents bugs before they happen. Web security implementation taught me about password hashing, session management, and the many ways web applications can be vulnerable. Working with Flask gave me deep understanding of routing, request handling, and template rendering. Writing complex SQL queries with JOINs, aggregate functions, and dynamic sorting improved my SQL skills significantly. Creating the interface with Bootstrap and Jinja2 taught me how to build responsive, attractive layouts without excessive custom CSS.

The most satisfying aspect was building a tool that solves a real problem. QuickClient isn't just an academic exercise, it's software I would actually use in freelance work. That made every challenge more meaningful and every solution more rewarding. This project taught me that good software engineering isn't just about writing code that works, it's about writing code that's secure, maintainable, and user-friendly.

Future enhancements could include email reminders for upcoming deadlines, invoice generation and tracking, file uploads for contracts and deliverables, calendar view of project timelines, data export to CSV or PDF, and mobile app version. While QuickClient is fully functional these features would enhance its usefulness for professional freelancers.

This was CS50!

