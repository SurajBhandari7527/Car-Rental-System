# 🚗 Car Rental Management System

A full-stack web application built with **Python (Flask)** and **MySQL** to manage vehicle rentals. The system supports two roles: **Customers**, who can browse and reserve cars, and **Admins**, who manage approvals, vehicle pickups, returns, and payments.

## ✨ Features

### 👤 Customer Side
*   **User Authentication:** Secure registration and login.
*   **Profile Management:** View and update personal details (Email, Contact, Address) using AJAX.
*   **Vehicle Catalog:** Browse available cars with real-time status updates.
*   **Reservation System:** Select pickup/return dates and request a vehicle.
*   **My Rentals:** Track active rentals and view historical rental data.
*   **Payments:** View calculated bills based on distance traveled (KM) and submit transaction IDs via QR code payment.

### 🛠️ Admin Side
*   **Reservation Management:** Approve or cancel pending reservation requests.
*   **Car Pickup:** Confirm when a customer picks up a vehicle (automatically logs starting odometer reading).
*   **Return Management:** Process vehicle returns, update final odometer readings, and trigger payment generation.
*   **Payment Logs:** Search and monitor all payment transactions and statuses.

---

## 🛠️ Tech Stack
*   **Backend:** Python 3.x, Flask
*   **Database:** MySQL
*   **Frontend:** HTML5, CSS3, JavaScript (AJAX/Fetch API)
*   **Database Connector:** `mysql-connector-python`

---

## 📊 Database Schema

To run this project, ensure your MySQL database (`db_for_reg`) has the following tables:

```sql
-- 1. Users Table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    address VARCHAR(255),
    contact VARCHAR(20),
    license_no VARCHAR(50) UNIQUE,
    password VARCHAR(255),
    role ENUM('admin', 'customer') DEFAULT 'customer'
);

-- 2. Vehicle Table
CREATE TABLE vehicle (
    vehicle_id INT AUTO_INCREMENT PRIMARY KEY,
    make VARCHAR(50),
    model VARCHAR(50),
    rate_per_km DECIMAL(10,2),
    odometer_reading INT,
    photo_link TEXT,
    status ENUM('available', 'reserved', 'rented') DEFAULT 'available'
);

-- 3. Reservation Table
CREATE TABLE reservation (
    reservation_id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    vehicle_id INT,
    start_datetime DATETIME,
    end_datetime DATETIME,
    status ENUM('pending', 'reserved', 'rented', 'cancelled') DEFAULT 'pending',
    FOREIGN KEY (customer_id) REFERENCES users(id),
    FOREIGN KEY (vehicle_id) REFERENCES vehicle(vehicle_id)
);

-- 4. Rental Table
CREATE TABLE rental (
    rental_id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT,
    actual_pickup DATETIME,
    actual_return DATETIME,
    start_odometer INT,
    end_odometer INT,
    returned BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (reservation_id) REFERENCES reservation(reservation_id)
);

-- 5. Payments Table
CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    rental_id INT,
    amount DECIMAL(10,2),
    status ENUM('unpaid', 'paid') DEFAULT 'unpaid',
    transaction_id VARCHAR(100),
    payment_date DATETIME,
    FOREIGN KEY (rental_id) REFERENCES rental(rental_id)
);
```

---

## 🚀 Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/yourusername/car-rental-flask.git
    cd car-rental-flask
    ```

2.  **Install Dependencies:**
    ```bash
    pip install Flask mysql-connector-python
    ```

3.  **Database Configuration:**
    *   Open `db.py`.
    *   Update the `mysql.connector.connect` parameters (host, user, password) to match your local MySQL setup.

4.  **Initialize Admin:**
    *   Register a user via the UI.
    *   Manually change the `role` to `'admin'` in the `users` table for that specific ID to access admin features.

5.  **Run the Application:**
    ```bash
    python app.py
    ```
    Access the app at `http://127.0.0.1:5000/`.

---

## 📂 Project Structure
*   `app.py`: Main Flask application containing all routes and business logic.
*   `db.py`: Database class handling connection pooling and SQL execution logic.
*   `templates/`: HTML files for rendering the UI.
*   `static/`: CSS styles and images.

---

## 📝 Usage Notes
*   **Distance Calculation:** Payments are calculated as: `(End Odometer - Start Odometer) * Rate Per KM`.
*   **Status Workflow:** 
    1.  Customer creates `pending` reservation.
    2.  Admin approves (Status: `reserved`).
    3.  Admin confirms pickup (Status: `rented`).
    4.  Admin confirms return (Status: `available`, Payment generated).
    5.  Customer pays (Payment Status: `paid`).

---

## 🛡️ License
This project is open-source. Feel free to modify and use it for your own learning or development purposes.
