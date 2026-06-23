from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = 'health_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Health metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            hemoglobin REAL,
            blood_pressure TEXT,
            weight_kg REAL,
            hydration INTEGER,
            energy INTEGER,
            sleep_hours REAL,
            illness TEXT,
            heart_rate INTEGER,
            body_temperature REAL,
            source TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            blood_group TEXT,
            age INTEGER,
            gender TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Health goals table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS health_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            goal_type TEXT,
            target_value REAL,
            current_value REAL,
            deadline TEXT,
            status TEXT DEFAULT 'active',
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # Insert sample user
    cursor.execute('SELECT * FROM users WHERE user_id = "D001"')
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, full_name, blood_group, age, gender)
            VALUES (?, ?, ?, ?, ?)
        ''', ('D001', 'Michael Chen', 'O+', 28, 'Male'))
        
        # Sample health data
        cursor.execute('''
            INSERT INTO health_metrics (
                user_id, hemoglobin, blood_pressure, weight_kg, hydration, 
                energy, sleep_hours, illness, heart_rate, body_temperature, source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('D001', 13.2, '118/76', 68, 82, 85, 7.5, 'none', 72, 98.6, 'manual'))
    
    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

# ==================== HEALTH API ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/api/health/<user_id>', methods=['GET'])
def get_health_metrics(user_id):
    """Get latest health metrics for a user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM health_metrics 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify(dict(row))
    return jsonify({'error': 'No health data found'}), 404

@app.route('/api/health/history/<user_id>', methods=['GET'])
def get_health_history(user_id):
    """Get historical health metrics for trends"""
    limit = request.args.get('limit', 30, type=int)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT hemoglobin, weight_kg, hydration, energy, sleep_hours, heart_rate, timestamp 
        FROM health_metrics 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (user_id, limit))
    
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'history': history})

@app.route('/api/health/update', methods=['POST'])
def update_health_metrics():
    """Add new health metrics record"""
    data = request.json
    
    required_fields = ['user_id', 'hemoglobin', 'weight_kg']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO health_metrics (
            user_id, hemoglobin, blood_pressure, weight_kg, 
            hydration, energy, sleep_hours, illness, heart_rate, 
            body_temperature, source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['user_id'],
        data['hemoglobin'],
        data.get('blood_pressure', '120/80'),
        data['weight_kg'],
        data.get('hydration', 70),
        data.get('energy', 80),
        data.get('sleep_hours', 7),
        data.get('illness', 'none'),
        data.get('heart_rate', 72),
        data.get('body_temperature', 98.6),
        data.get('source', 'manual')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Health metrics updated successfully'})

@app.route('/api/health/eligibility/<user_id>', methods=['GET'])
def check_donation_eligibility(user_id):
    """Check if user is eligible to donate blood based on health metrics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get latest health metrics
    cursor.execute('''
        SELECT hemoglobin, weight_kg, hydration, illness, heart_rate, body_temperature
        FROM health_metrics 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (user_id,))
    
    health = cursor.fetchone()
    conn.close()
    
    if not health:
        return jsonify({'error': 'No health data found'}), 404
    
    hemoglobin, weight, hydration, illness, heart_rate, temperature = health
    
    # Eligibility criteria
    checks = {
        'hemoglobin': {'value': hemoglobin, 'required': 12.5, 'passed': hemoglobin >= 12.5},
        'weight': {'value': weight, 'required': 50, 'passed': weight >= 50},
        'hydration': {'value': hydration, 'required': 70, 'passed': hydration >= 70},
        'illness': {'value': illness, 'required': 'none', 'passed': illness == 'none'},
        'heart_rate': {'value': heart_rate, 'required': '50-100', 'passed': 50 <= heart_rate <= 100},
        'temperature': {'value': temperature, 'required': '< 99.5°F', 'passed': temperature < 99.5}
    }
    
    all_passed = all(check['passed'] for check in checks.values())
    
    # Generate recommendations
    recommendations = []
    if not checks['hemoglobin']['passed']:
        recommendations.append("⚠️ Low hemoglobin. Eat iron-rich foods (spinach, lentils, red meat)")
    if not checks['hydration']['passed']:
        recommendations.append("💧 Low hydration. Drink 2-3 liters of water daily")
    if not checks['weight']['passed']:
        recommendations.append("⚖️ Weight below minimum. Focus on healthy weight gain")
    if not checks['illness']['passed']:
        recommendations.append("🩹 Wait until fully recovered from illness")
    if not checks['heart_rate']['passed']:
        recommendations.append("❤️ Rest and relax. Heart rate should be 50-100 bpm")
    if not checks['temperature']['passed']:
        recommendations.append("🌡️ Slight fever detected. Rest and check again later")
    
    if all_passed:
        recommendations.append("✅ You are eligible to donate blood! Schedule your appointment.")
    
    return jsonify({
        'eligible': all_passed,
        'checks': checks,
        'recommendations': recommendations,
        'health_score': calculate_health_score(checks)
    })

def calculate_health_score(checks):
    """Calculate overall health score (0-100)"""
    score = 0
    weights = {
        'hemoglobin': 30,
        'weight': 20,
        'hydration': 15,
        'heart_rate': 15,
        'temperature': 10,
        'illness': 10
    }
    
    for key, weight in weights.items():
        if checks[key]['passed']:
            score += weight
    
    return score

@app.route('/api/health/trends/<user_id>', methods=['GET'])
def get_health_trends(user_id):
    """Get health trends for visualization"""
    days = request.args.get('days', 30, type=int)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            DATE(timestamp) as date,
            AVG(hemoglobin) as avg_hemoglobin,
            AVG(weight_kg) as avg_weight,
            AVG(hydration) as avg_hydration,
            AVG(energy) as avg_energy,
            AVG(sleep_hours) as avg_sleep
        FROM health_metrics 
        WHERE user_id = ? 
            AND timestamp >= DATE('now', ?)
        GROUP BY DATE(timestamp)
        ORDER BY date ASC
    ''', (user_id, f'-{days} days'))
    
    trends = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'trends': trends})

@app.route('/api/health/compare/<user_id>', methods=['GET'])
def compare_health_metrics(user_id):
    """Compare latest health metrics with previous reading"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get latest two records
    cursor.execute('''
        SELECT hemoglobin, weight_kg, hydration, energy, sleep_hours, timestamp
        FROM health_metrics 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 2
    ''', (user_id,))
    
    records = cursor.fetchall()
    conn.close()
    
    if len(records) < 2:
        return jsonify({'message': 'Need at least 2 health records for comparison', 'has_data': False})
    
    latest = dict(records[0])
    previous = dict(records[1])
    
    comparison = {}
    metrics = ['hemoglobin', 'weight_kg', 'hydration', 'energy', 'sleep_hours']
    
    for metric in metrics:
        diff = latest[metric] - previous[metric]
        comparison[metric] = {
            'current': latest[metric],
            'previous': previous[metric],
            'change': round(diff, 1),
            'trend': 'up' if diff > 0 else 'down' if diff < 0 else 'stable',
            'percentage_change': round((diff / previous[metric]) * 100, 1) if previous[metric] != 0 else 0
        }
    
    return jsonify({
        'has_data': True,
        'comparison': comparison,
        'latest_date': latest['timestamp'],
        'previous_date': previous['timestamp']
    })

@app.route('/api/health/set-goal', methods=['POST'])
def set_health_goal():
    """Set a health goal for the user"""
    data = request.json
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO health_goals (user_id, goal_type, target_value, current_value, deadline)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        data['user_id'],
        data['goal_type'],
        data['target_value'],
        data.get('current_value', 0),
        data.get('deadline')
    ))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Health goal set successfully'})

@app.route('/api/health/goals/<user_id>', methods=['GET'])
def get_health_goals(user_id):
    """Get all health goals for a user"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM health_goals 
        WHERE user_id = ? AND status = 'active'
        ORDER BY deadline ASC
    ''', (user_id,))
    
    goals = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'goals': goals})

@app.route('/api/health/export/<user_id>', methods=['GET'])
def export_health_data(user_id):
    """Export all health data as JSON for download"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM health_metrics 
        WHERE user_id = ? 
        ORDER BY timestamp DESC
    ''', (user_id,))
    
    metrics = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = dict(cursor.fetchone()) if cursor.fetchone() else None
    
    conn.close()
    
    return jsonify({
        'user': user,
        'health_metrics': metrics,
        'export_date': datetime.now().isoformat()
    })

if __name__ == '__main__':
    init_db()
    print("\n" + "="*50)
    print("🏥 Lumina Health API Server")
    print("="*50)
    print(f"📁 Database: {DB_PATH}")
    print(f"🔗 API URL: http://127.0.0.1:5000")
    print("\n📋 Available Endpoints:")
    print("   GET    /api/health/<user_id>           - Get latest health metrics")
    print("   GET    /api/health/history/<user_id>   - Get health history")
    print("   POST   /api/health/update              - Add/update health metrics")
    print("   GET    /api/health/eligibility/<user_id> - Check donation eligibility")
    print("   GET    /api/health/trends/<user_id>    - Get health trends")
    print("   GET    /api/health/compare/<user_id>   - Compare with previous reading")
    print("   POST   /api/health/set-goal            - Set health goal")
    print("   GET    /api/health/goals/<user_id>     - Get health goals")
    print("   GET    /api/health/export/<user_id>    - Export all health data")
    print("="*50 + "\n")
    app.run(debug=True, host='127.0.0.1', port=5000)