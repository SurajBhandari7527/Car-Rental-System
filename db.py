import mysql.connector

class Database:
    def __init__(self):
        self.con = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Aspirine@27',
            database='db_for_reg'
        )
        self._ensure_table()

    def _ensure_table(self):
        cursor = self.con.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100) UNIQUE,
                address VARCHAR(255),
                contact VARCHAR(20),
                license_no VARCHAR(50) UNIQUE,
                password VARCHAR(255)
            )
        ''')
        self.con.commit()
        cursor.close()

    def insert_user(self, name, email, address, contact, license_no, password):
        cursor = self.con.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, address, contact, license_no, password)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (name, email, address, contact, license_no, password))
        self.con.commit()
        cursor.close()

    def email_exists(self, email):
        cursor = self.con.cursor()
        cursor.execute('SELECT 1 FROM users WHERE email=%s', (email,))
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

    def license_exists(self, license_no):
        cursor = self.con.cursor()
        cursor.execute('SELECT 1 FROM users WHERE license_no=%s', (license_no,))
        exists = cursor.fetchone() is not None
        cursor.close()
        return exists

    def get_password(self, email):
        cursor = self.con.cursor()
        cursor.execute('SELECT id,password FROM users WHERE email=%s', (email,))
        row = cursor.fetchone()
        cursor.close()
        return row if row else None
    def get_vehicles(self):
        cursor=self.con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vehicle")
        rows=cursor.fetchall()
        cursor.close()
        return rows
    
    def get_profile(self,user_id):
        cursor=self.con.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users where id=%s",(user_id,))
        row=cursor.fetchone()
        cursor.close()
        return row

    def update_user_field(self, user_id, field, value):
        # Use parameterized query, but cannot parametrize column name:
        if field not in ('name','email','contact','address'):
            raise ValueError('Invalid field')

        sql = f"UPDATE users SET {field} = %s WHERE id = %s"
        cursor = self.con.cursor()
        cursor.execute(sql, (value, user_id))
        self.con.commit()
        cursor.close()
    def fetch_active(self,user_id):
        cursor = self.con.cursor(dictionary=True)

        # Active rents
        cursor.execute("""
        SELECT r.reservation_id,
               v.make, v.model,
               r.start_datetime, r.end_datetime,
                r.status
            FROM reservation r
            JOIN vehicle v ON r.vehicle_id = v.vehicle_id
            WHERE r.customer_id = %s
            AND (
                r.status = 'reserved' OR r.status= 'pending'
                OR (r.status = 'rented' AND r.end_datetime > NOW())
            )
            ORDER BY r.start_datetime DESC
        """, (user_id,))     
        active = cursor.fetchall()
        cursor.close()
        return active
    def fetch_history(self,user_id):
        # History (all other past reservations)
        cursor = self.con.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.reservation_id,
                v.make, v.model,
                r.start_datetime, r.end_datetime,
                r.status
            FROM reservation r
            JOIN vehicle v ON r.vehicle_id = v.vehicle_id
            WHERE r.customer_id = %s
            AND NOT (
                r.status = 'reserved' or r.status='pending'
                OR (r.status = 'rented' AND r.end_datetime > NOW())
            )
            ORDER BY r.start_datetime DESC
        """, (user_id,))
        history = cursor.fetchall()
        cursor.close()
        return history

    def get_user_by_email(self, email):
        cursor = self.con.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, password, role FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        return user

    def close(self):
            self.con.close()
