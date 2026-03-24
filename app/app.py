from flask import Flask, render_template, request, url_for, redirect, session, send_from_directory
import secrets
import pymysql.cursors
import math
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(20)

def get_conn():
    return pymysql.connect(
        host='localhost',
        user=os.getenv('DB_USER', 'yuwkaa'),
        password=os.getenv('DB_PASSWORD', 'fake_db_password'),
        database=os.getenv('DB_NAME', 'wikipanime'),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )

@app.get('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if not username or not password:
            return render_template('error.html', error_message='Username and password are required')
        if len(username) > 100 or len(password) > 100:
            return render_template('error.html', error_message='Username and password are too long')
        conn = None
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username=%s', (username,))
            if cursor.fetchone():
                return render_template('error.html', error_message='Username already exists')
            cursor.execute('INSERT INTO users (username, password) VALUES (%s, %s)',(username, password))
            conn.commit()
        except Exception as e:
            return render_template('error.html', error_message=f'Lỗi Đăng Ký: {str(e)}')
        finally:
            if conn is not None:
                conn.close()
                
        return render_template('success.html', success_message='Registration successful')
    return render_template('register.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if not username or not password:
            return render_template('error.html', error_message='Username and password are required')
        conn = None
        try:
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute('SELECT username, password, role FROM users WHERE username=%s', (username,))
            user = cursor.fetchone()
            if not user:
                return render_template('error.html', error_message='Username does not exist')
            if user['password'] != password:
                return render_template('error.html', error_message='Incorrect username or password')
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        except Exception as e:
            return render_template('error.html', error_message='Login error')
        finally:
            if conn is not None:
                conn.close()
    return render_template('login.html')

@app.get('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('home'))
    
    try:
        page = int(request.args.get('page', 0))
    except Exception:
        page = 0
    
    keyword = request.args.get('keyword', '').strip()
    genre_filter = request.args.get('genre', '').strip()
    
    conn = None
    count = 0
    try:
        conn = get_conn()
        cursor = conn.cursor()
        if page < 0:
            page = 0
        size = 10
        offset = page * size
        
        base_query = """
            SELECT a.*, IFNULL(AVG(r.score), 0) as avg_rating, COUNT(r.id) as total_votes
            FROM anime a
            LEFT JOIN ratings r ON a.id = r.anime_id
        """
        conditions = []
        params = []
        
        if keyword:
            conditions.append("(LOWER(a.title) LIKE %s OR LOWER(a.description) LIKE %s)")
            params.extend([f"%{keyword.lower()}%", f"%{keyword.lower()}%"])
            
        if genre_filter:
            conditions.append("a.genres LIKE %s")
            params.append(f"%{genre_filter}%")
            
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
            
        base_query += " GROUP BY a.id ORDER BY avg_rating DESC, a.id ASC"
        
        cursor.execute(base_query, params)
        all_results = cursor.fetchall()
        count = math.ceil(len(all_results) / size)
        
        start_idx = offset
        end_idx = offset + size
        result = all_results[start_idx:end_idx]
        
    except Exception as e:
        return render_template('error.html', error_message=f'Dashboard Error: {str(e)}')
    finally:
        if conn is not None:
            conn.close()
            
    return render_template('dashboard.html', result=result, page=page, count=count, keyword=keyword, current_genre=genre_filter)

@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.get('/admin')
def admin():
    if ('username' not in session or session['username'] != 'admin'):
        return 'You are not admin'
    filename = request.args.get('filename', None)

    if filename is None:
        return 'No filename provided', 400

    return send_from_directory('files', filename)

@app.route('/anime/<int:anime_id>', methods=["GET", "POST"])
def anime_detail(anime_id):
    if 'username' not in session:
        return redirect(url_for('login'))
        
    conn = None
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            action = request.form.get('action')
            
            if action == 'comment':
                content = request.form.get('content', '').strip()
                if content:
                    cursor.execute(
                        'INSERT INTO comments (anime_id, username, content) VALUES (%s, %s, %s)',
                        (anime_id, session['username'], content)
                    )
                    conn.commit()
                    
            elif action == 'rate':
                score = request.form.get('score')
                if score and score.isdigit() and 1 <= int(score) <= 5:
                    cursor.execute(
                        'REPLACE INTO ratings (username, anime_id, score) VALUES (%s, %s, %s)',
                        (session['username'], anime_id, int(score))
                    )
                    conn.commit()
                    
            return redirect(url_for('anime_detail', anime_id=anime_id))
            
        cursor.execute('''
            SELECT a.*, IFNULL(AVG(r.score), 0) as avg_rating, COUNT(r.id) as total_votes 
            FROM anime a 
            LEFT JOIN ratings r ON a.id = r.anime_id 
            WHERE a.id=%s 
            GROUP BY a.id
        ''', (anime_id,))
        anime = cursor.fetchone()
        
        if not anime:
            return render_template('not_found.html')
            
        cursor.execute('SELECT * FROM comments WHERE anime_id=%s ORDER BY created_at DESC', (anime_id,))
        comments = cursor.fetchall()
        
        cursor.execute('SELECT score FROM ratings WHERE anime_id=%s AND username=%s', (anime_id, session['username']))
        user_rating = cursor.fetchone()
        my_vote = user_rating['score'] if user_rating else 0
        
        return render_template('anime_detail.html', anime=anime, comments=comments, my_vote=my_vote)
        
    except Exception as e:
        return render_template('error.html', error_message=f'Unable to load Anime: {str(e)}')
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)