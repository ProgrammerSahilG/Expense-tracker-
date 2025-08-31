# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO, StringIO
import base64
import csv

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    description = db.Column(db.String(200))

    def __repr__(self):
        return f'<Expense {self.amount} - {self.category}>'

# Create database tables
with app.app_context():
    db.create_all()

# Make datetime available to all templates
@app.context_processor
def inject_datetime():
    return dict(datetime=datetime)

# Routes
@app.route('/')
def index():
    # Get summary statistics
    total_expenses = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    expenses_count = Expense.query.count()
    
    # Get recent expenses
    recent_expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
    
    return render_template('index.html', 
                         total_expenses=total_expenses, 
                         expenses_count=expenses_count,
                         recent_expenses=recent_expenses)

@app.route('/add', methods=['GET', 'POST'])
def add_expense():
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category = request.form['category']
        date = datetime.strptime(request.form['date'], '%Y-%m-%d')
        description = request.form['description']
        
        new_expense = Expense(amount=amount, category=category, date=date, description=description)
        db.session.add(new_expense)
        db.session.commit()
        
        flash('Expense added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_expense.html')

@app.route('/dashboard')
def dashboard():
    # Get all expenses for analytics
    expenses = Expense.query.all()
    
    # Prepare data for charts
    categories = {}
    monthly_data = {}
    
    for expense in expenses:
        # Category breakdown
        if expense.category in categories:
            categories[expense.category] += expense.amount
        else:
            categories[expense.category] = expense.amount
        
        # Monthly data
        month_key = expense.date.strftime('%Y-%m')
        if month_key in monthly_data:
            monthly_data[month_key] += expense.amount
        else:
            monthly_data[month_key] = expense.amount
    
    # Sort monthly data
    sorted_months = sorted(monthly_data.keys())
    monthly_values = [monthly_data[month] for month in sorted_months]
    
    # Generate charts
    category_chart = generate_pie_chart(categories)
    monthly_chart = generate_line_chart(sorted_months, monthly_values)
    
    return render_template('dashboard.html', 
                         category_chart=category_chart,
                         monthly_chart=monthly_chart,
                         categories=categories)

@app.route('/expenses')
def view_expenses():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    return render_template('expenses.html', expenses=expenses)

@app.route('/delete/<int:id>')
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('view_expenses'))

@app.route('/export/csv')
def export_csv():
    expenses = Expense.query.all()
    
    # Create CSV in memory using StringIO
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Category', 'Description', 'Amount (₹)'])
    
    for expense in expenses:
        writer.writerow([
            expense.date.strftime('%Y-%m-%d'),
            expense.category,
            expense.description,
            expense.amount
        ])
    
    # Prepare response
    output.seek(0)
    
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        as_attachment=True,
        download_name='expenses.csv',
        mimetype='text/csv'
    )

# Helper functions for charts
def generate_pie_chart(categories):
    if not categories:
        return None
        
    # Create pie chart
    plt.figure(figsize=(6, 6))
    plt.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%')
    plt.title('Expenses by Category')
    
    # Save to base64 string
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()
    
    return chart_url

def generate_line_chart(months, values):
    if not months:
        return None
        
    # Create line chart
    plt.figure(figsize=(8, 4))
    plt.plot(months, values, marker='o')
    plt.title('Monthly Spending Trend')
    plt.xlabel('Month')
    plt.ylabel('Amount (₹)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save to base64 string
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode('utf8')
    plt.close()
    
    return chart_url

if __name__ == '__main__':
    app.run(debug=True)