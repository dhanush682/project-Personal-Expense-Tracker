CREATE DATABASE IF NOT EXISTS personal_expense_tracker;
USE personal_expense_tracker;

CREATE TABLE IF NOT EXISTS categories (
    category_id INT PRIMARY KEY AUTO_INCREMENT,
    category_name VARCHAR(80) NOT NULL,
    category_type ENUM('income','expense') NOT NULL,
    UNIQUE KEY unique_category_type (category_name, category_type)
);

CREATE TABLE IF NOT EXISTS expenses (
    expense_id INT PRIMARY KEY AUTO_INCREMENT,
    expense_date DATE NOT NULL,
    category_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    description VARCHAR(255) NOT NULL,
    payment_method VARCHAR(40) NOT NULL,
    CONSTRAINT fk_expense_category FOREIGN KEY (category_id) REFERENCES categories(category_id),
    CONSTRAINT chk_positive_amount CHECK (amount > 0)
);

INSERT IGNORE INTO categories (category_name, category_type) VALUES
('Food','expense'),('Transport','expense'),('Rent','expense'),
('Healthcare','expense'),('Education','expense'),('Shopping','expense'),
('Entertainment','expense'),('Utilities','expense'),('Other','expense'),
('Salary','income'),('Allowance','income'),('Other income','income');
