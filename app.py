from flask import session, Flask, render_template, request,redirect,jsonify,url_for
from db import Database
from datetime import datetime
app = Flask(__name__)
app.secret_key = 'suraj_super_secret_123'
@app.route('/')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/comp_reg', methods=['POST'])
def comp_reg():
    name       = request.form['username'].strip().title()
    email      = request.form['email'].strip().lower()
    address    = request.form['address'].strip()
    contact    = request.form['contact'].strip()
    license_no = request.form['license_no'].strip().upper()
    db = Database()

    if db.email_exists(email):
        db.close()
        return render_template('register.html', message="This email is already registered", msg_type="error")
    if db.license_exists(license_no):
        db.close()
        return render_template('register.html', message="This license number is already registered", msg_type="error")

    db.insert_user(name, email, address, contact, license_no, request.form['password'])
    db.close()
    return render_template('register.html', message="Registration successful! Please log in.", msg_type="success")

@app.route('/comp_login', methods=['POST'])
def comp_login():
    email = request.form['email'].strip().lower()
    password = request.form['password']
    db = Database()
    
    # Fetch the user record (including id, password, role)
    user = db.get_user_by_email(email)  # We'll assume this returns a dictionary
    db.close()
    
    if user is None:
        return render_template('login.html', message="No account found. Please register first.", msg_type="error")

    # Check password (if using plaintext for now; otherwise, use password hashing & checking)
    if password != user['password']:
        return render_template('login.html', message="Incorrect credentials.", msg_type="error")

    # Store user info in the session for later access
    session['user_id'] = user['id']
    session['email'] = user['email']
    session['role'] = user.get('role', 'customer')
    
    # Redirect based on the user's role:
    if user['role'] == 'admin':
        return  redirect(url_for('admin_reserve_requests'))
    else:
        return redirect(url_for('home'))


@app.route('/home')
def home():
    # 1. Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # 2. Initialize variables
    vehicles = []
    db = None # Ensure db is defined before try block

    try:
        # 3. Connect to the database
        db = Database()
        # Use dictionary=True to access results by column name
        cursor = db.con.cursor(dictionary=True)

        # 4. Define the SQL query to fetch vehicle details
        sql = """
            SELECT
                vehicle_id,
                make,
                model,
                rate_per_km,
                odometer_reading,
                photo_link,
                status
            FROM vehicle
            ORDER BY make, model  # Optional: order the results
        """

        # 5. Execute the query
        cursor.execute(sql)

        # 6. Fetch all results
        vehicles = cursor.fetchall()

        # 7. Close the cursor
        cursor.close()

    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching vehicles for home page: {e}")
        # Optionally, you could show an error message on the page
        # return render_template('error.html', message="Could not load vehicle data.")
        pass # Allow page to render without vehicle data if error occurs

    finally:
        # 8. Ensure database connection is closed
        if db:
            db.close()

    # 9. Get user email from session safely
    user_email = session.get('email')

    # 10. Render the template, passing the user email and the fetched vehicles
    return render_template('home.html', user=user_email, vehicles=vehicles)


@app.route('/vehicles')
def vehicle():
    db=Database()
    vehicles=db.get_vehicles()
    db.close()
    return render_template('vehicles.html',vehicles=vehicles)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect('/login')
    db=Database()
    user=db.get_profile(session['user_id'])
    db.close()
    return render_template('profile.html',user=user)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify(success=False, error='Not logged in'), 401

    data = request.get_json()
    field = data.get('field')
    value = data.get('value').strip()
    user_id = session['user_id']

    # Validate field
    if field not in ('name','email','contact','address'):
        return jsonify(success=False, error='Invalid field'), 400

    db = Database()
    try:
        db.update_user_field(user_id, field, value)
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        db.close()

@app.route('/my_rentals')
def my_rentals():
    if 'user_id' not in session:
        return redirect('/login')

    db=Database()
    active=db.fetch_active(session['user_id'])
    history=db.fetch_history(session['user_id'])
    db.close()

    return render_template('my_rentals.html',
                            active=active,
                            history=history)

@app.route('/reserve_vehicles', methods=['GET', 'POST'])
def reserve_vehicles():
    db = Database()
    cursor = db.con.cursor(dictionary=True)

    term = request.form.get('search', '').strip().lower() if request.method == 'POST' else ''

    if term:
        sql = """
            SELECT * FROM vehicle 
            WHERE status='available' AND 
                  (LOWER(make) LIKE %s OR LOWER(model) LIKE %s)
        """
        params = (f"%{term}%", f"%{term}%")
    else:
        sql = "SELECT * FROM vehicle WHERE status='available'"
        params = ()

    cursor.execute(sql, params)
    vehicles = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template('reserve_vehicles.html', vehicles=vehicles, term=term)


@app.route('/reserve/<int:vehicle_id>', methods=['GET', 'POST'])
def reserve_vehicle_action(vehicle_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = Database()
    cursor = db.con.cursor(dictionary=True)

    # Fetch vehicle & customer
    cursor.execute("SELECT model FROM vehicle WHERE vehicle_id = %s", (vehicle_id,))
    vehicle = cursor.fetchone()
    cursor.execute("SELECT name FROM users WHERE id = %s", (session['user_id'],))
    customer = cursor.fetchone()

    if request.method == 'POST':
        start = request.form['start_datetime']
        end   = request.form['end_datetime']

        # Insert reservation
        cursor.execute(
            "INSERT INTO reservation (customer_id, vehicle_id, start_datetime, end_datetime,status) "
            "VALUES (%s, %s, %s, %s,%s)",
            (session['user_id'], vehicle_id, start, end,'pending')
        )
        # Update vehicle status
        cursor.execute(
            "UPDATE vehicle SET status='reserved' WHERE vehicle_id=%s",
            (vehicle_id,)
        )
        db.con.commit()
        cursor.close()
        db.close()

        # Redirect to a new “success” route
        return redirect(url_for('reservation_success'))

    cursor.close()
    db.close()
    # GET → show form
    return render_template('reserve_form.html',
                            customer_name=customer['name'],
                            vehicle_model=vehicle['model'])

@app.route('/reservation_success')
def reservation_success():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('reservation_success.html')

@app.route('/admin/reserve_requests')
def admin_reserve_requests():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = Database()
    cursor = db.con.cursor(dictionary=True)
    sql = """
      SELECT r.reservation_id,
             u.name AS user_name,
             u.email,
             u.contact,
             r.start_datetime,
             r.end_datetime,
             v.make,
             v.model
      FROM reservation r
      JOIN users u ON r.customer_id = u.id
      JOIN vehicle v ON r.vehicle_id = v.vehicle_id
      WHERE r.status = 'pending'
      ORDER BY r.start_datetime ASC
    """
    cursor.execute(sql)
    requests = cursor.fetchall()
    cursor.close()
    db.close()
    return render_template('admin_reserve_requests.html', requests=requests)


# Admin: Approve a pending reservation
@app.route('/admin/approve_reservation/<int:reservation_id>', methods=['POST'])
def approve_reservation(reservation_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = Database()
    cursor = db.con.cursor()
    # Update the reservation to 'reserved'
    cursor.execute("UPDATE reservation SET status='reserved' WHERE reservation_id=%s", (reservation_id,))
    # Optionally, update the vehicle status as well:
    cursor.execute(
       "UPDATE vehicle SET status='rented' "
       "WHERE vehicle_id=(SELECT vehicle_id FROM reservation WHERE reservation_id=%s)",
       (reservation_id,)
    )
    db.con.commit()
    cursor.close()
    db.close()
    return redirect(url_for('admin_reserve_requests'))


# Admin: Car Pick Up Section (display approved reservations)
@app.route('/admin/carpickup', methods=['GET', 'POST'])
def admin_carpickup():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    term = ''
    db = Database()
    cursor = db.con.cursor(dictionary=True)

    if request.method == 'POST':
        term = request.form.get('search', '').strip().lower()
        like_term = f"%{term}%"
        sql = """
          SELECT r.reservation_id,
                 u.name   AS user_name,
                 u.email,
                 u.contact,
                 r.start_datetime,
                 r.end_datetime,
                 v.make,
                 v.model
          FROM reservation r
          JOIN users u     ON r.customer_id = u.id
          JOIN vehicle v   ON r.vehicle_id   = v.vehicle_id
          WHERE r.status = 'reserved'
            AND (
              LOWER(u.name)   LIKE %s
              OR LOWER(u.email) LIKE %s
              OR u.contact     LIKE %s
            )
          ORDER BY r.start_datetime DESC
        """
        cursor.execute(sql, (like_term, like_term, like_term))
    else:
        sql = """
          SELECT r.reservation_id,
                 u.name   AS user_name,
                 u.email,
                 u.contact,
                 r.start_datetime,
                 r.end_datetime,
                 v.make,
                 v.model
          FROM reservation r
          JOIN users u     ON r.customer_id = u.id
          JOIN vehicle v   ON r.vehicle_id   = v.vehicle_id
          WHERE r.status = 'reserved'
          ORDER BY r.start_datetime DESC
        """
        cursor.execute(sql)

    pickups = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('admin_carpickup.html', pickups=pickups, term=term)


@app.route('/admin/cancel_reservation/<int:reservation_id>', methods=['POST'])
def cancel_reservation(reservation_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = Database()
    cursor = db.con.cursor()

    # 1) Mark reservation as 'cancelled'
    cursor.execute(
        "DELETE from reservation WHERE reservation_id = %s",
        (reservation_id,)
    )
    # 2) Release the vehicle back to available
    cursor.execute(
        "UPDATE vehicle SET status='available' "
        "WHERE vehicle_id = (SELECT vehicle_id FROM reservation WHERE reservation_id = %s)",
        (reservation_id,)
    )

    db.con.commit()
    cursor.close()
    db.close()

    return redirect(url_for('admin_carpickup'))

@app.route('/confirm_rent/<int:reservation_id>', methods=['POST'])
def confirm_rent(reservation_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = Database()
    cursor = db.con.cursor()

    # 1. Update reservation and vehicle status to 'rented'
    cursor.execute(
        "UPDATE reservation SET status='rented' WHERE reservation_id=%s",
        (reservation_id,)
    )
    cursor.execute(
        """
        UPDATE vehicle
           SET status='rented'
         WHERE vehicle_id = (
               SELECT vehicle_id
                 FROM reservation
                WHERE reservation_id=%s
               )
        """,
        (reservation_id,)
    )

    # 2. Insert into rental table, grabbing the odometer_reading as start_odometer
    cursor.execute(
        """
        INSERT INTO rental (reservation_id, actual_pickup, start_odometer)
          SELECT r.reservation_id, NOW(), v.odometer_reading
            FROM reservation r
            JOIN vehicle     v ON v.vehicle_id = r.vehicle_id
           WHERE r.reservation_id = %s
        """,
        (reservation_id,)
    )

    db.con.commit()
    cursor.close()
    db.close()

    return redirect(url_for('admin_carpickup'))


@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('login'))


@app.route('/admin/return', methods=['GET', 'POST'])
def admin_return():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    term = ''
    db = Database()
    cursor = db.con.cursor(dictionary=True)

    if request.method == 'POST':
        term = request.form.get('search', '').strip().lower()
        like = f"%{term}%"
        sql = """
          SELECT r.reservation_id,
                 rental.rental_id,
                 u.name   AS user_name,
                 u.email,
                 v.make,
                 v.model,
                 r.start_datetime,
                 r.end_datetime,
                 v.odometer_reading AS start_odometer
          FROM reservation r
          JOIN rental     rental ON rental.reservation_id = r.reservation_id
          JOIN users      u      ON r.customer_id   = u.id
          JOIN vehicle    v      ON r.vehicle_id    = v.vehicle_id
          WHERE r.status = 'rented'
            AND rental.returned = FALSE
            AND (
                  LOWER(u.name)   LIKE %s
               OR LOWER(u.email)  LIKE %s
               OR u.contact        LIKE %s
            )
          ORDER BY r.start_datetime DESC
        """
        cursor.execute(sql, (like, like, like))
    else:
        sql = """
          SELECT r.reservation_id,
                 rental.rental_id,
                 u.name   AS user_name,
                 u.email,
                 v.make,
                 v.model,
                 r.start_datetime,
                 r.end_datetime,
                 v.odometer_reading AS start_odometer
          FROM reservation r
          JOIN rental     rental ON rental.reservation_id = r.reservation_id
          JOIN users      u      ON r.customer_id   = u.id
          JOIN vehicle    v      ON r.vehicle_id    = v.vehicle_id
          WHERE r.status = 'rented'
            AND rental.returned = FALSE
          ORDER BY r.start_datetime DESC
        """
        cursor.execute(sql)

    returns = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('admin_return.html', returns=returns, term=term)

@app.route('/admin/confirm_return/<int:rental_id>', methods=['GET', 'POST'])
def confirm_return(rental_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = Database()
    cursor = db.con.cursor(dictionary=True)

    if request.method == 'POST':
        actual_return = request.form['actual_return']
        end_odo       = request.form['end_odometer']

        # 1) Update rental record
        cursor.execute("""
            UPDATE rental
               SET actual_return = %s,
                   end_odometer   = %s,
                   returned       = TRUE
             WHERE rental_id = %s
        """, (actual_return, end_odo, rental_id))

        # 2) Update vehicle: set odometer & make available
        cursor.execute("""
            UPDATE vehicle
               SET odometer_reading = %s,
                   status           = 'available'
             WHERE vehicle_id = (
                   SELECT r.vehicle_id
                     FROM reservation r
                     JOIN rental rent ON rent.reservation_id = r.reservation_id
                    WHERE rent.rental_id = %s
                   )
        """, (end_odo, rental_id))

        # 3) Recalculate and update the payment amount
        cursor.execute("""
        INSERT INTO payments (rental_id, amount)
        SELECT 
            rent.rental_id, 
            (rent.end_odometer - rent.start_odometer) * v.rate_per_km
        FROM rental rent
        JOIN reservation r ON r.reservation_id = rent.reservation_id
        JOIN vehicle v ON v.vehicle_id = r.vehicle_id
        WHERE rent.rental_id = %s""", (rental_id,))
        db.con.commit()
        cursor.close()
        db.close()

        return redirect(url_for('admin_return'))

    # GET → show form with prefilled fields
    cursor.execute("""
        SELECT u.email,
               rental.actual_pickup,
               v.odometer_reading AS start_odometer
          FROM rental
          JOIN reservation r ON rental.reservation_id = r.reservation_id
          JOIN users u       ON r.customer_id = u.id
          JOIN vehicle v     ON r.vehicle_id  = v.vehicle_id
         WHERE rental.rental_id = %s
    """, (rental_id,))
    data = cursor.fetchone()
    cursor.close()
    db.close()

    pickup_local = data['actual_pickup'].strftime('%Y-%m-%dT%H:%M')

    return render_template('confirm_return_form.html',
                           rental_id=rental_id,
                           email=data['email'],
                           actual_pickup=pickup_local,
                           start_odometer=data['start_odometer'])

@app.route('/payments')
def payments():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    qr_url = "https://www.emoderationskills.com/wp-content/uploads/2010/08/QR1.jpg"  # ← replace with your actual QR link

    db = Database()
    cursor = db.con.cursor(dictionary=True)
    cursor.execute("""
      SELECT rent.rental_id,
             v.make, v.model,
             rent.actual_pickup,
             rent.actual_return,
             rent.start_odometer,
             rent.end_odometer,
             v.rate_per_km AS rate_per_km,
             p.payment_id
      FROM rental rent
      JOIN reservation r  ON rent.reservation_id = r.reservation_id
      JOIN payments   p  ON rent.rental_id     = p.rental_id
      JOIN vehicle    v  ON r.vehicle_id       = v.vehicle_id
      WHERE r.customer_id    = %s
        AND rent.returned= TRUE
        AND p.status = 'unpaid'
    """, (session['user_id'],))
    rows = cursor.fetchall()
   
    cursor.close()
    db.close()

    # Calculate total_travelled and amount
    for row in rows:
        row['total_travelled'] = row['end_odometer'] - row['start_odometer']
        row['amount'] = row['total_travelled'] * row['rate_per_km']

    return render_template('payments.html',
                           qr_url=qr_url,
                           payments=rows)


# Customer: Confirm payment form & submission
@app.route('/payments/confirm/<int:rental_id>', methods=['GET', 'POST'])
def confirm_payment(rental_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = Database()
    cursor = db.con.cursor(dictionary=True)

    if request.method == 'POST':
        transaction_id = request.form['transaction_id']

        # Mark payment as paid, record transaction and date
        cursor.execute("""
          UPDATE payments
             SET status='paid',
                 transaction_id=%s,
                 payment_date = NOW()
           WHERE rental_id=%s
        """, (transaction_id, rental_id))
        db.con.commit()
        cursor.close()
        db.close()
        return redirect(url_for('payments'))

    # GET → fetch totals for prefill
    cursor.execute("""
      SELECT rent.rental_id,
             rent.start_odometer,
             rent.end_odometer,
             v.rate_per_km 
      FROM rental rent
      JOIN reservation r  ON rent.reservation_id = r.reservation_id
      JOIN vehicle    v  ON r.vehicle_id       = v.vehicle_id
      WHERE rent.rental_id=%s
    """, (rental_id,))
    data = cursor.fetchone()
    total_travelled = data['end_odometer'] - data['start_odometer']
    amount = total_travelled * data['rate_per_km']
    cursor.close()
    db.close()

    

    # Format amount/travelled for display
    return render_template('confirm_payment.html',
                           rental_id=rental_id,
                           total_travelled=total_travelled,
                           amount=amount)

@app.route('/admin/payments', methods=['GET','POST'])
def admin_payments():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    term = ''
    db   = Database()
    cursor = db.con.cursor(dictionary=True)

    if request.method == 'POST':
        term = request.form.get('search','').strip().lower()
        like = f"%{term}%"
        sql = """
          SELECT 
            u.name   AS user_name,
            u.email  AS email,
            CONCAT(v.make, ' ', v.model) AS vehicle,
            rent.actual_pickup,
            rent.actual_return,
            (rent.end_odometer - rent.start_odometer) AS total_travelled,
            p.amount,
            p.transaction_id,
            p.status
          FROM payments p
          JOIN rental     rent ON p.rental_id    = rent.rental_id
          JOIN reservation r    ON rent.reservation_id = r.reservation_id
          JOIN users      u     ON r.customer_id  = u.id
          JOIN vehicle    v     ON r.vehicle_id   = v.vehicle_id
          WHERE
             LOWER(u.name) LIKE %s
          OR LOWER(u.email) LIKE %s
          OR p.transaction_id LIKE %s
          ORDER BY rent.actual_return DESC
        """
        cursor.execute(sql, (like, like, like))
    else:
        sql = """
          SELECT 
            u.name   AS user_name,
            u.email  AS email,
            CONCAT(v.make, ' ', v.model) AS vehicle,
            rent.actual_pickup,
            rent.actual_return,
            (rent.end_odometer - rent.start_odometer) AS total_travelled,
            p.amount,
            p.transaction_id,
            p.status
          FROM payments p
          JOIN rental     rent ON p.rental_id    = rent.rental_id
          JOIN reservation r    ON rent.reservation_id = r.reservation_id
          JOIN users      u     ON r.customer_id  = u.id
          JOIN vehicle    v     ON r.vehicle_id   = v.vehicle_id
          ORDER BY rent.actual_return DESC
        """
        cursor.execute(sql)

    payments = cursor.fetchall()
    cursor.close()
    db.close()

    return render_template('admin_payments.html',
                           payments=payments,
                           term=term)


if __name__ == '__main__':
    app.run(debug=True)
