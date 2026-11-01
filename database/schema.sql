CREATE DATABASE IF NOT EXISTS estudo_saude
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE estudo_saude;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    score INT NOT NULL DEFAULT 0,
    streak INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS medications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    med_class VARCHAR(150) NOT NULL,
    indication TEXT NOT NULL,
    contraindications TEXT NOT NULL,
    nursing_care TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS simulation_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    procedure_title VARCHAR(200) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'COMPLETED',
    completed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_simulation_logs_user
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_simulation_logs_user_completed
  ON simulation_logs (user_id, completed_at);

-- Catálogo separado de registros regulatórios oficiais da Anvisa.
-- Uma linha é um registro da fonte, não necessariamente um princípio ativo único.
CREATE TABLE IF NOT EXISTS anvisa_medicines (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    source_key CHAR(64) NOT NULL,
    source_hash CHAR(64) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    active_ingredient TEXT NULL,
    therapeutic_class VARCHAR(255) NULL,
    category VARCHAR(150) NULL,
    registration_number VARCHAR(80) NULL,
    company VARCHAR(255) NULL,
    status VARCHAR(40) NOT NULL,
    registration_expiry VARCHAR(40) NULL,
    source_name VARCHAR(100) NOT NULL DEFAULT 'Anvisa - Dados Abertos',
    imported_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_anvisa_source_key (source_key),
    KEY idx_anvisa_registration (registration_number),
    KEY idx_anvisa_status_name (status, product_name),
    FULLTEXT KEY ft_anvisa_search (product_name, active_ingredient, therapeutic_class, company)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- Códigos de barras/QR só podem ser associados após validação humana da embalagem.
CREATE TABLE IF NOT EXISTS medicine_barcodes (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(300) NOT NULL,
    medicine_id BIGINT UNSIGNED NOT NULL,
    verified_by VARCHAR(120) NULL,
    verified_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_medicine_barcode_code (code),
    KEY idx_medicine_barcode_medicine (medicine_id),
    CONSTRAINT fk_medicine_barcode_medicine FOREIGN KEY (medicine_id)
      REFERENCES anvisa_medicines(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
