
-- 6.2.1 Users Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    role ENUM('admin', 'provider', 'worker') NOT NULL,
    city VARCHAR(100) NOT NULL,
    area VARCHAR(100) NULL,
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 6.2.2 Worker Profiles Table
CREATE TABLE IF NOT EXISTS worker_profiles (
    worker_id INT PRIMARY KEY,
    bio TEXT NULL,
    daily_wage DECIMAL(10, 2) NOT NULL,
    experience_years INT DEFAULT 0,
    skills TEXT NULL, 
    avg_rating DECIMAL(3, 2) DEFAULT 0.00,
    total_jobs INT DEFAULT 0,
    profile_photo VARCHAR(255) NULL,
    availability_status ENUM('available', 'unavailable', 'busy') DEFAULT 'available',
    FOREIGN KEY (worker_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 6.2.3 Jobs Table
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    provider_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    skill_required VARCHAR(100) NOT NULL,
    location_city VARCHAR(100) NOT NULL,
    location_area VARCHAR(100) NULL,
    job_date DATE NOT NULL,
    duration_hours INT NOT NULL,
    budget DECIMAL(10, 2) NULL,
    status ENUM('open', 'booked', 'in_progress', 'completed', 'cancelled') DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (provider_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 6.2.4 Bookings Table
CREATE TABLE IF NOT EXISTS bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    worker_id INT NOT NULL,
    provider_id INT NOT NULL,
    status ENUM('pending', 'confirmed', 'in_progress', 'completed', 'cancelled') DEFAULT 'pending',
    booked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (worker_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- 6.2.5 Ratings Table
CREATE TABLE IF NOT EXISTS ratings (
    rating_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL UNIQUE,
    worker_id INT NOT NULL,
    provider_id INT NOT NULL,
    score TINYINT NOT NULL CHECK (score >= 1 AND score <= 5),
    review_text TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    FOREIGN KEY (worker_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (provider_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Notifications Table (referenced in 6.1)
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Payments Table (Optional module 3.11)
CREATE TABLE IF NOT EXISTS payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
    transaction_id VARCHAR(255) NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE
);
