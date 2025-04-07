from flask import Flask, render_template

app = Flask(__name__)

# Home page route
@app.route('/')
def home():
    return render_template('index.html')

# Admin panel main page
@app.route('/admin')
def admin_panel():
    return render_template('admin_panel.html')

# Additional admin panel feature placeholders (for future routing)
@app.route('/edit-user-role')
def edit_user_role():
    return "<h2>Edit User Roles Page (coming soon)</h2>"

@app.route('/add-admin')
def add_admin():
    return "<h2>Add New Admin Page (coming soon)</h2>"

@app.route('/delete-users')
def delete_users():
    return "<h2>Delete Users Page (coming soon)</h2>"

if __name__ == '__main__':
    app.run(debug=True)
